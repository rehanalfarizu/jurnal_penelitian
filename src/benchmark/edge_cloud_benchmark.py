"""Benchmark local inference and an explicitly configured cloud-network emulation."""

from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from src.data.prepare_augmented_workload import prepare_augmented_workload


def add_time_features(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    timestamp = pd.to_datetime(result["timestamp_utc"], utc=True, format="mixed")
    hour = timestamp.dt.hour + timestamp.dt.minute / 60.0
    result["hour_sin"] = np.sin(2 * np.pi * hour / 24.0)
    result["hour_cos"] = np.cos(2 * np.pi * hour / 24.0)
    return result


def _percentiles(values: list[float]) -> dict:
    array = np.asarray(values, dtype=float)
    return {
        "mean_ms": float(array.mean()),
        "p50_ms": float(np.quantile(array, 0.50)),
        "p95_ms": float(np.quantile(array, 0.95)),
        "p99_ms": float(np.quantile(array, 0.99)),
        "max_ms": float(array.max()),
    }


def benchmark(
    frame: pd.DataFrame,
    artifact: dict,
    config: dict,
    workload_scope: dict | None = None,
) -> dict:
    sample_size = min(int(config["benchmark"]["sample_size"]), len(frame))
    sample = add_time_features(frame.iloc[:sample_size]).reset_index(drop=True)
    features = artifact["features"]
    model = artifact["model"]
    # Parallel worker startup dominates single-record inference and would make
    # the latency benchmark measure scheduler overhead rather than inference.
    if hasattr(model, "n_jobs"):
        model.n_jobs = 1
    rng = np.random.default_rng(int(config["model"]["random_state"]))

    # Warm-up is intentionally excluded from timing.
    model.predict(sample.loc[[0], features])
    edge_compute_ms: list[float] = []
    serialization_ms: list[float] = []
    predictions: list[float] = []
    payload_bytes: list[int] = []
    routes: list[str] = []
    invalid_electrical_flags: list[bool] = []
    power_anomaly_flags: list[bool] = []
    routing_config = config["benchmark"]["cloud_routing"]
    power_anomaly_threshold = float(
        routing_config["power_anomaly_threshold_w"]
    )

    for _, row in sample.iterrows():
        started = time.perf_counter_ns()
        prediction = float(model.predict(pd.DataFrame([row[features]], columns=features))[0])
        compute_ms = (time.perf_counter_ns() - started) / 1_000_000
        payload = {
            "timestamp_utc": row["timestamp_utc"],
            "device_id": row["device_id"],
            "source_type": row["source_type"],
            "observed_power_w": row["observed_power_w"],
            "estimated_power_w": prediction,
        }
        serialization_started = time.perf_counter_ns()
        encoded = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        serialization_ms.append(
            (time.perf_counter_ns() - serialization_started) / 1_000_000
        )
        edge_compute_ms.append(compute_ms)
        predictions.append(prediction)
        payload_bytes.append(len(encoded))
        invalid_electrical = (
            float(row["observed_voltage_v"]) == 0
            or float(row["observed_current_a"]) == 0
        )
        power_anomaly = float(row["observed_power_w"]) > power_anomaly_threshold
        invalid_electrical_flags.append(invalid_electrical)
        power_anomaly_flags.append(power_anomaly)
        routes.append("cloud" if invalid_electrical or power_anomaly else "edge")

    edge_mask = np.asarray(routes) == "edge"
    cloud_mask = ~edge_mask
    network = config["benchmark"]["cloud_network_profile"]
    network_ms = np.maximum(
        0.0,
        rng.normal(
            float(network["median_ms"]),
            float(network["jitter_ms"]),
            size=sample_size,
        ),
    )
    dropped = (
        rng.random(sample_size) < float(network["drop_probability"])
    ) & cloud_mask
    compute = np.asarray(edge_compute_ms)
    serialize = np.asarray(serialization_ms)
    edge_path = compute + serialize
    cloud_path = edge_path + network_ms
    configured_e2e = compute + serialize + np.where(cloud_mask, network_ms, 0.0)
    delivered_e2e = configured_e2e[~dropped]
    sample_interval_ms = float(config["data"]["sample_interval_seconds"]) * 1000.0

    elapsed_seconds = max(sum(edge_compute_ms) / 1000.0, 1e-9)
    return {
        "scope": {
            "compute": (
                "Measured on this machine using time.perf_counter_ns; "
                "not a Raspberry Pi or public-cloud measurement."
            ),
            "network": str(network["label"]),
            "sample_size": sample_size,
            "model_name": artifact["model_name"],
            "workload": workload_scope
            or {
                "source_type": str(sample["source_type"].iloc[0]),
                "available_rows": len(frame),
                "role": "unspecified benchmark input",
            },
            "runtime": {
                "platform": platform.platform(),
                "python": sys.version.split()[0],
                "numpy": np.__version__,
                "pandas": pd.__version__,
            },
        },
        "actual_local_compute": _percentiles(edge_compute_ms),
        "actual_json_serialization": _percentiles(serialization_ms),
        "actual_edge_path": {
            **_percentiles(edge_path.tolist()),
            "definition": "local inference plus JSON serialization",
        },
        "configured_cloud_path": {
            **_percentiles(cloud_path.tolist()),
            "definition": (
                "local compute proxy plus configured network latency; "
                "not a public-cloud measurement"
            ),
        },
        "configured_network_emulation": {
            "parameters": network,
            "generated_latency": _percentiles(network_ms.tolist()),
            "generated_drop_count": int(dropped.sum()),
        },
        "configured_end_to_end": {
            **_percentiles(delivered_e2e.tolist()),
            "deadline_ms": sample_interval_ms,
            "deadline_miss_count": int((delivered_e2e > sample_interval_ms).sum()),
            "deadline_miss_rate": float((delivered_e2e > sample_interval_ms).mean()),
            "twin_staleness_proxy": (
                "Equal to configured end-to-end latency; browser render latency "
                "is not included."
            ),
            "warning": "Includes configured, not field-measured, network latency.",
        },
        "routing": {
            "edge_count": int(edge_mask.sum()),
            "cloud_count": int(cloud_mask.sum()),
            "invalid_electrical_count": int(sum(invalid_electrical_flags)),
            "power_anomaly_count": int(sum(power_anomaly_flags)),
            "power_anomaly_threshold_w": power_anomaly_threshold,
            "rule": (
                "Cloud when voltage/current is zero or observed legacy power "
                f"exceeds {power_anomaly_threshold:.1f} W; otherwise edge."
            ),
            "basis": str(routing_config["basis"]),
        },
        "throughput": {
            "sequential_model_inferences_per_second": float(sample_size / elapsed_seconds),
            "definition": "sample count divided by summed local inference compute time",
        },
        "payload": {
            "mean_bytes": float(np.mean(payload_bytes)),
            "p95_bytes": float(np.quantile(payload_bytes, 0.95)),
        },
        "prediction_checksum": float(np.sum(predictions)),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("configs/experiment.json"))
    parser.add_argument("--input", type=Path, default=Path("outputs/synthetic_telemetry.csv"))
    parser.add_argument("--model", type=Path, default=Path("outputs/power_estimator.joblib"))
    parser.add_argument("--output", type=Path, default=Path("outputs/benchmark_metrics.json"))
    parser.add_argument(
        "--input-format",
        choices=["synthetic", "legacy_augmented"],
        default="synthetic",
    )
    parser.add_argument(
        "--workload-audit-output",
        type=Path,
        default=Path("outputs/augmented_workload_audit.json"),
    )
    parser.add_argument("--sample-size", type=int)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    if args.sample_size:
        config["benchmark"]["sample_size"] = args.sample_size
    workload_scope = None
    if args.input_format == "legacy_augmented":
        workload = config["benchmark"]["workload"]
        frame, audit = prepare_augmented_workload(
            args.input,
            expected_rows=int(workload["expected_rows"]),
            reference_rows=int(workload["reference_rows_per_replay"]),
            sample_size=int(config["benchmark"]["sample_size"]),
        )
        args.workload_audit_output.write_text(
            json.dumps(audit, indent=2), encoding="utf-8"
        )
        workload_scope = {
            "source_type": "legacy_augmented_replay",
            "available_rows": audit["source"]["rows"],
            "sample_selection": audit["benchmark_sample"]["method"],
            "covered_replay_blocks": audit["benchmark_sample"][
                "covered_replay_blocks"
            ],
            "role": (
                "architecture latency, throughput, routing, and Web-3D replay; "
                "excluded from model fitting and accuracy evaluation"
            ),
        }
    else:
        frame = pd.read_csv(args.input)
        frame = frame[
            frame["packet_received"].astype(str).str.lower().eq("true")
        ].dropna()
    report = benchmark(
        frame.dropna(), joblib.load(args.model), config, workload_scope
    )
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Benchmark tersimpan: {args.output}")


if __name__ == "__main__":
    main()
