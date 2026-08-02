"""Local HTTP replay service for the multiscale Digital Twin prototype."""

from __future__ import annotations

import argparse
import copy
import json
import threading
import time
from collections import deque
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pandas as pd

from src.benchmark.edge_cloud_benchmark import build_monitoring_record
from src.data.prepare_historical_replay import prepare_historical_replay


class ReplayState:
    def __init__(
        self,
        input_path: Path,
        config: dict,
        *,
        input_format: str = "canonical",
        sample_size: int | None = None,
    ):
        replay_config = config["replay"]
        if input_format == "historical_csv":
            self.frame, self.workload_audit = prepare_historical_replay(
                input_path,
                expected_rows=int(replay_config["expected_rows"]),
                reference_rows=int(
                    replay_config["reference_rows_per_replay"]
                ),
                sample_size=sample_size
                or int(replay_config["benchmark_sample_size"]),
                reference_trace=Path(config["data"]["reference_trace"]),
                max_energy_gap_seconds=float(
                    config["energy_integration"]["max_gap_seconds"]
                ),
            )
        else:
            self.frame = pd.read_csv(input_path)
            self.workload_audit = None

        required = {
            "timestamp_utc",
            "source_timestamp_utc",
            "replay_timestamp_utc",
            "device_id",
            "source_type",
            "lineage_classification",
            "replay_id",
            "replay_block_id",
            "source_row_id",
            "source_row_index",
            "temperature_c",
            "humidity_pct",
            "voltage_v",
            "current_a",
            "power_legacy_w",
            "power_formula_w",
            "power_consistency_error_w",
            "energy_interval_legacy_wh",
            "energy_cumulative_legacy_wh",
            "energy_integration_status",
            "people_count",
            "occupancy_status",
            "voltage_status",
            "current_status",
        }
        missing = required - set(self.frame.columns)
        if missing:
            raise ValueError(
                f"Kolom replay kanonis tidak ditemukan: {sorted(missing)}"
            )
        self.frame = self.frame.reset_index(drop=True)
        if self.frame.empty:
            raise ValueError("Tidak ada baris telemetry untuk direplay.")
        self.threshold = float(
            config["benchmark"]["cloud_routing"][
                "power_anomaly_threshold_w"
            ]
        )
        self.source_label = "historical_replay"
        self.digital_twin_config = config.get("digital_twin")
        self.lineage_classification = str(
            self.frame.iloc[0]["lineage_classification"]
        )
        self.index = 0
        self._lock = threading.Lock()
        self._served_records: deque[dict] = deque(maxlen=500)

    def record(self, row: pd.Series) -> dict:
        emitted_at = datetime.now(timezone.utc).isoformat()
        record, compute_ms = build_monitoring_record(
            row,
            self.threshold,
            emitted_timestamp_utc=emitted_at,
            digital_twin_config=self.digital_twin_config,
        )
        serialization_started = time.perf_counter_ns()
        json.dumps(record, separators=(",", ":"), allow_nan=False)
        serialization_ms = (
            time.perf_counter_ns() - serialization_started
        ) / 1_000_000
        edge_path_ms = compute_ms + serialization_ms
        record["processing"]["serialization_latency_ms"] = serialization_ms
        record["processing"]["end_to_end_latency_ms"] = edge_path_ms
        record["processing"]["freshness_ms"] = edge_path_ms
        return record

    def latest(self) -> dict:
        with self._lock:
            row_index = self.index
            row = self.frame.iloc[row_index].copy()
            self.index = (self.index + 1) % len(self.frame)
            emitted_record = self.record(row)
            self._served_records.append(copy.deepcopy(emitted_record))
            return emitted_record

    def history(self, limit: int) -> list[dict]:
        with self._lock:
            return [
                copy.deepcopy(record)
                for record in list(self._served_records)[-limit:]
            ]


def make_handler(state: ReplayState):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, payload: dict, status: int = 200) -> None:
            encoded = json.dumps(payload, allow_nan=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def do_GET(self) -> None:  # noqa: N802
            request = urlparse(self.path)
            if request.path == "/api/telemetry/latest":
                self._send({"success": True, "data": state.latest()})
                return
            if request.path == "/api/telemetry/history":
                query = parse_qs(request.query)
                try:
                    requested_limit = int(query.get("limit", ["60"])[0])
                except ValueError:
                    self._send(
                        {"success": False, "error": "invalid_limit"},
                        status=400,
                    )
                    return
                limit = min(500, max(1, requested_limit))
                self._send(
                    {"success": True, "data": state.history(limit)}
                )
                return
            if request.path == "/api/health":
                self._send(
                    {
                        "status": "ok",
                        "source": state.source_label,
                        "lineage_classification": (
                            state.lineage_classification
                        ),
                        "rows_loaded": len(state.frame),
                        "mode": "monitoring_without_power_estimation_model",
                        "digital_twin": state.digital_twin_config,
                        "replay_clock": (
                            "request_driven_one_row_per_latest_call"
                        ),
                    }
                )
                return
            self._send({"success": False, "error": "not_found"}, status=404)

        def log_message(self, format: str, *args) -> None:
            return

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("outputs/historical_replay_sample.csv"),
    )
    parser.add_argument(
        "--input-format",
        choices=["canonical", "historical_csv"],
        default="canonical",
    )
    parser.add_argument(
        "--config", type=Path, default=Path("configs/experiment.json")
    )
    parser.add_argument("--sample-size", type=int)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    state = ReplayState(
        args.input,
        config,
        input_format=args.input_format,
        sample_size=args.sample_size,
    )
    server = ThreadingHTTPServer(
        (args.host, args.port), make_handler(state)
    )
    print(
        f"Replay API: http://{args.host}:{args.port}/api/telemetry/latest"
    )
    server.serve_forever()


if __name__ == "__main__":
    main()
