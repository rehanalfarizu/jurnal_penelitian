"""Measure the real Azure HTTPS -> Function -> Table Storage path.

The workload is an evenly spaced replay of the archived physical-sensor trace.
It is deliberately marked as historical replay and is persisted in the
separate ``BenchmarkTelemetry`` table by ``SaveSensorData``.

No Azure key is written to disk. The script reads ``AZURE_FUNCTION_KEY`` when
present; otherwise it obtains the function key from the already-authenticated
Azure CLI process and keeps it in memory only.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import http.client
import json
import math
import os
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import numpy as np
import pandas as pd

# Make direct execution (`python scripts/run_azure_live_benchmark.py`) resolve
# the repository's src package just like `python -m ...` from the repo root.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.data.audit_trace import load_trace


DEFAULT_ENDPOINT = "https://func-digitaltwin-2026.azurewebsites.net/api/sensor/save"
FUNCTION_VERSION = "v3.0-azure-live-replay"
DEADLINE_MS = 3_500.0


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def get_function_key(resource_group: str, function_app: str) -> str:
    from_environment = os.environ.get("AZURE_FUNCTION_KEY", "").strip()
    if from_environment:
        return from_environment

    command = [
        "az",
        "functionapp",
        "function",
        "keys",
        "list",
        "--resource-group",
        resource_group,
        "--name",
        function_app,
        "--function-name",
        "SaveSensorData",
        "--query",
        "default",
        "--output",
        "tsv",
    ]
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    key = result.stdout.strip()
    if not key:
        raise RuntimeError("Default key untuk SaveSensorData tidak ditemukan.")
    return key


def source_indices(row_count: int, message_count: int) -> np.ndarray:
    if row_count <= 0 or message_count <= 0:
        raise ValueError("row_count dan message_count harus positif.")
    if message_count > row_count:
        raise ValueError("message_count tidak boleh melebihi jumlah baris sumber.")
    return np.linspace(0, row_count - 1, message_count, dtype=int)


def optional_number(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def build_payload(row: pd.Series, *, run_id: str, message_number: int, source_row: int) -> dict:
    replay_sent_at = utc_now()
    source_timestamp = pd.Timestamp(row["timestamp"]).isoformat()
    payload: dict[str, Any] = {
        "deviceId": str(row["device_id"]),
        "esp32": {
            "suhu": optional_number(row["temperature_c"]),
            "kelembaban": optional_number(row["humidity_pct"]),
            "tegangan": optional_number(row["voltage_v"]),
            "arus": optional_number(row["current_a"]),
            "daya": optional_number(row["power_w"]),
        },
        "benchmark": {
            "mode": "historical_replay",
            "runId": run_id,
            "messageId": f"msg-{message_number:05d}",
            "sourceRowId": f"historical:{source_row:06d}",
            "replayBlockId": 0,
            "sourceTimestamp": source_timestamp,
            "replaySentAt": replay_sent_at,
            "gatewayId": str(row["device_id"]),
            "sourceNodeId": "ESP32_ENERGY_MONITOR_001",
            "sourceNodeAttribution": "architecture_metadata_not_row_level_field",
        },
    }
    people_count = optional_number(row["people_count"])
    if people_count is not None:
        payload["camera"] = {"people_count": int(round(people_count))}
    return payload


def make_connection(endpoint: str, timeout_seconds: float) -> tuple[http.client.HTTPSConnection, str]:
    parsed = urlsplit(endpoint)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("Endpoint benchmark harus berupa URL HTTPS.")
    port = parsed.port or 443
    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"
    return http.client.HTTPSConnection(parsed.hostname, port, timeout=timeout_seconds), path


def send_payload(
    connection: http.client.HTTPSConnection,
    path: str,
    payload: dict,
    function_key: str,
    *,
    warmup: bool,
) -> dict:
    body = json.dumps(payload, separators=(",", ":"), allow_nan=False).encode("utf-8")
    started_at = utc_now()
    started = time.perf_counter()
    status = 0
    response_body = b""
    response_json: dict[str, Any] = {}
    error = ""

    try:
        connection.request(
            "POST",
            path,
            body=body,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "x-functions-key": function_key,
                "Connection": "keep-alive",
                "User-Agent": "jurnal-azure-live-benchmark/1.0",
            },
        )
        response = connection.getresponse()
        status = int(response.status)
        response_body = response.read()
        if response_body:
            response_json = json.loads(response_body.decode("utf-8"))
    except Exception as exc:  # captured as measurement evidence
        error = f"{type(exc).__name__}: {exc}"
        connection.close()

    ended = time.perf_counter()
    ended_at = utc_now()
    elapsed_ms = (ended - started) * 1000.0
    benchmark = response_json.get("benchmark") or {}
    server_ms = response_json.get("serverProcessingMs")
    storage_ms = response_json.get("storageWriteMs")
    contract_ok = (
        status == 200
        and response_json.get("success") is True
        and response_json.get("functionVersion") == FUNCTION_VERSION
        and benchmark.get("runId") == payload["benchmark"]["runId"]
        and benchmark.get("messageId") == payload["benchmark"]["messageId"]
        and benchmark.get("physicalSensorLive") is False
    )

    return {
        "warmup": warmup,
        "run_id": payload["benchmark"]["runId"],
        "message_id": payload["benchmark"]["messageId"],
        "source_row_id": payload["benchmark"]["sourceRowId"],
        "source_timestamp_utc": payload["benchmark"]["sourceTimestamp"],
        "client_started_at_utc": started_at,
        "client_ended_at_utc": ended_at,
        "http_status": status,
        "contract_ok": contract_ok,
        "deadline_met": contract_ok and elapsed_ms <= DEADLINE_MS,
        "end_to_end_ms": round(elapsed_ms, 3),
        "server_processing_ms": round(float(server_ms), 3) if server_ms is not None else None,
        "storage_write_ms": round(float(storage_ms), 3) if storage_ms is not None else None,
        "client_network_overhead_ms": (
            round(max(0.0, elapsed_ms - float(server_ms)), 3)
            if server_ms is not None
            else None
        ),
        "request_bytes": len(body),
        "response_bytes": len(response_body),
        "function_version": response_json.get("functionVersion"),
        "azure_received_at_utc": response_json.get("receivedAt"),
        "azure_persisted_at_utc": response_json.get("persistedAt"),
        "error": error or (response_json.get("error") if status != 200 else ""),
    }


def distribution(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {key: None for key in ("min", "mean", "p50", "p95", "p99", "max")} | {"n": 0}
    array = np.asarray(values, dtype=float)
    return {
        "n": int(array.size),
        "min": float(array.min()),
        "mean": float(array.mean()),
        "p50": float(np.percentile(array, 50)),
        "p95": float(np.percentile(array, 95)),
        "p99": float(np.percentile(array, 99)),
        "max": float(array.max()),
    }


def summarize(records: list[dict], *, duration_seconds: float) -> dict:
    measured = [record for record in records if not record["warmup"]]
    successful = [record for record in measured if record["contract_ok"]]
    deadlines = [record for record in successful if record["deadline_met"]]

    def numbers(field: str) -> list[float]:
        return [float(record[field]) for record in successful if record[field] is not None]

    return {
        "sample": {
            "warmup_requests": sum(bool(record["warmup"]) for record in records),
            "measured_requests": len(measured),
            "successful_contract_requests": len(successful),
            "failed_requests": len(measured) - len(successful),
            "sampling": "evenly_spaced_rows_from_archived_physical_sensor_trace",
            "concurrency": 1,
            "http_connection": "persistent_https_keep_alive_after_warmup",
        },
        "reliability": {
            "success_rate_percent": 100.0 * len(successful) / len(measured) if measured else 0.0,
            "error_rate_percent": 100.0 * (len(measured) - len(successful)) / len(measured) if measured else 0.0,
            "deadline_ms": DEADLINE_MS,
            "deadline_compliance_percent": 100.0 * len(deadlines) / len(successful) if successful else 0.0,
            "http_status_counts": {
                str(status): sum(record["http_status"] == status for record in measured)
                for status in sorted({record["http_status"] for record in measured})
            },
        },
        "latency_ms": {
            "client_end_to_end": distribution(numbers("end_to_end_ms")),
            "function_server_processing": distribution(numbers("server_processing_ms")),
            "table_storage_write": distribution(numbers("storage_write_ms")),
            "client_network_overhead_estimate": distribution(numbers("client_network_overhead_ms")),
        },
        "throughput": {
            "measured_requests_per_second": len(measured) / duration_seconds if duration_seconds > 0 else None,
            "successful_requests_per_second": len(successful) / duration_seconds if duration_seconds > 0 else None,
        },
    }


def write_csv(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)


def plot_results(path: Path, records: list[dict], report: dict) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    measured = [record for record in records if not record["warmup"] and record["contract_ok"]]
    end_to_end = [record["end_to_end_ms"] for record in measured]
    server = [record["server_processing_ms"] for record in measured if record["server_processing_ms"] is not None]
    storage = [record["storage_write_ms"] for record in measured if record["storage_write_ms"] is not None]
    overhead = [record["client_network_overhead_ms"] for record in measured if record["client_network_overhead_ms"] is not None]

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.8), constrained_layout=True)
    fig.suptitle("Kinerja Jalur Azure Publik dengan Replay Data Historis", fontsize=15, fontweight="bold")

    ax = axes[0]
    sorted_latency = np.sort(end_to_end)
    cumulative = np.arange(1, len(sorted_latency) + 1) / max(1, len(sorted_latency)) * 100
    ax.plot(sorted_latency, cumulative, color="#176B87", linewidth=2.2)
    latency = report["latency_ms"]["client_end_to_end"]
    for percentile, color in (("p50", "#2A9D8F"), ("p95", "#E9C46A"), ("p99", "#E76F51")):
        value = latency[percentile]
        if value is not None:
            ax.axvline(value, color=color, linestyle="--", linewidth=1.4, label=f"{percentile.upper()} {value:.1f} ms")
    ax.set_title("A. Distribusi kumulatif latensi")
    ax.set_xlabel("Latensi end-to-end (ms)")
    ax.set_ylabel("Permintaan selesai (%)")
    ax.set_ylim(0, 103)
    ax.grid(alpha=0.22)
    ax.legend(frameon=False, fontsize=8, loc="lower right")

    ax = axes[1]
    box_data = [values for values in (overhead, storage, server, end_to_end) if values]
    labels = [label for label, values in zip(
        ["HTTPS di luar Function", "Tulis Table Storage", "Proses Function", "End-to-end"],
        (overhead, storage, server, end_to_end),
    ) if values]
    ax.boxplot(box_data, orientation="horizontal", tick_labels=labels, showfliers=False, patch_artist=True,
               boxprops={"facecolor": "#A8DADC", "edgecolor": "#176B87"},
               medianprops={"color": "#D1495B", "linewidth": 1.8})
    ax.set_title("B. Komponen waktu terukur")
    ax.set_xlabel("Waktu (ms)")
    ax.grid(axis="x", alpha=0.22)

    ax = axes[2]
    reliability = report["reliability"]
    values = [reliability["success_rate_percent"], reliability["deadline_compliance_percent"]]
    bars = ax.bar(["Kontrak berhasil", "≤ 3,5 detik"], values, color=["#2A9D8F", "#457B9D"], width=0.62)
    ax.set_ylim(0, 108)
    ax.set_ylabel("Persentase (%)")
    ax.set_title("C. Keandalan permintaan")
    ax.grid(axis="y", alpha=0.22)
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 1.5, f"{value:.1f}%", ha="center", fontsize=10)

    fig.text(
        0.5,
        -0.02,
        "Cakupan: klien HTTPS → Azure Function → Azure Table Storage; sumber payload: replay trace sensor arsip.",
        ha="center",
        fontsize=9,
        color="#374151",
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("Data/sensor_data_export_2026-05-17_to_2026-05-23.xlsx"))
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--resource-group", default="rg-digitaltwin")
    parser.add_argument("--function-app", default="func-digitaltwin-2026")
    parser.add_argument("--messages", type=int, default=200)
    parser.add_argument("--warmup", type=int, default=5)
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    parser.add_argument("--output-dir", type=Path, default=Path("results/final"))
    args = parser.parse_args()

    if args.messages < 20:
        raise ValueError("Gunakan sedikitnya 20 permintaan terukur untuk ringkasan persentil.")
    if args.warmup < 1:
        raise ValueError("Gunakan sedikitnya satu warm-up untuk memisahkan startup awal.")

    trace = load_trace(args.input)
    indices = source_indices(len(trace), args.messages + args.warmup)
    run_id = f"azure-live-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    function_key = get_function_key(args.resource_group, args.function_app)
    connection, request_path = make_connection(args.endpoint, args.timeout_seconds)

    records: list[dict] = []
    measured_started = None
    for position, source_row in enumerate(indices):
        is_warmup = position < args.warmup
        if not is_warmup and measured_started is None:
            measured_started = time.perf_counter()
        payload = build_payload(
            trace.iloc[int(source_row)],
            run_id=run_id,
            message_number=position,
            source_row=int(source_row),
        )
        record = send_payload(connection, request_path, payload, function_key, warmup=is_warmup)
        records.append(record)
        if record["error"] and record["http_status"] == 0:
            connection, request_path = make_connection(args.endpoint, args.timeout_seconds)

    measured_ended = time.perf_counter()
    connection.close()
    duration_seconds = measured_ended - (measured_started or measured_ended)
    metrics = summarize(records, duration_seconds=duration_seconds)
    report = {
        "schema_version": "1.0",
        "run_id": run_id,
        "generated_at_utc": utc_now(),
        "title": "Evaluasi Kinerja Digital Twin Edge–Cloud Multiskala untuk Monitoring Energi dan Okupansi",
        "measurement_scope": {
            "classification": "measured_public_azure_path_with_historical_replay_payloads",
            "endpoint": args.endpoint,
            "azure_services_included": ["Azure Functions", "Azure Table Storage"],
            "azure_region": "Southeast Asia",
            "source_data": "archived_physical_sensor_trace",
            "physical_sensor_streaming_live": False,
            "iot_hub_included_in_measured_path": False,
            "browser_render_included": False,
            "client_host_timezone": "Asia/Jakarta",
            "interpretation": (
                "Latensi adalah pengukuran aktual jalur HTTPS publik sampai tulis Azure Table dikonfirmasi. "
                "Payload berasal dari replay trace sensor lapangan yang diarsipkan; sensor fisik tidak aktif saat benchmark."
            ),
        },
        "provenance": {
            "input_path": str(args.input),
            "input_sha256": sha256(args.input),
            "input_rows": int(len(trace)),
            "source_device_ids": sorted(trace["device_id"].dropna().astype(str).unique().tolist()),
            "source_node_id_status": "architecture_metadata_not_row_level_field",
        },
        "runtime": {
            "client_python": platform.python_version(),
            "client_platform": platform.platform(),
            "expected_function_version": FUNCTION_VERSION,
        },
        **metrics,
    }

    csv_path = args.output_dir / "azure_live_requests.csv"
    json_path = args.output_dir / "azure_live_metrics.json"
    figure_path = args.output_dir / "figures" / "06_azure_live_performance.png"
    write_csv(csv_path, records)
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    plot_results(figure_path, records, report)

    success = report["reliability"]["success_rate_percent"]
    p95 = report["latency_ms"]["client_end_to_end"]["p95"]
    print(f"Azure live benchmark selesai: {args.messages} pesan, sukses {success:.1f}%, P95 {p95:.1f} ms")
    print(f"Artefak: {json_path}, {csv_path}, {figure_path}")


if __name__ == "__main__":
    main()
