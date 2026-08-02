"""Benchmark the monitoring path used by the historical-replay prototype."""

from __future__ import annotations

import argparse
import json
import math
import platform
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from src.data.prepare_historical_replay import prepare_historical_replay


MONITORING_FIELDS = (
    "temperature_c",
    "humidity_pct",
    "voltage_v",
    "current_a",
    "power_legacy_w",
    "power_formula_w",
    "power_consistency_error_w",
    "energy_interval_legacy_wh",
    "energy_cumulative_legacy_wh",
    "people_count",
)
ROUTE_REASONS = (
    "normal_local_monitoring",
    "missing_or_nonfinite_value",
    "invalid_electrical_reading",
    "current_below_legacy_threshold",
    "power_above_trace_p99",
)


def _safe_float(value: object) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _percentiles(values: list[float] | np.ndarray) -> dict:
    array = np.asarray(values, dtype=float)
    if array.size == 0:
        return {
            "mean_ms": None,
            "p50_ms": None,
            "p95_ms": None,
            "p99_ms": None,
            "max_ms": None,
        }
    return {
        "mean_ms": float(array.mean()),
        "p50_ms": float(np.quantile(array, 0.50)),
        "p95_ms": float(np.quantile(array, 0.95)),
        "p99_ms": float(np.quantile(array, 0.99)),
        "max_ms": float(array.max()),
    }


def build_monitoring_record(
    row: pd.Series,
    power_anomaly_threshold_w: float,
    *,
    emitted_timestamp_utc: str | None = None,
    digital_twin_config: dict | None = None,
) -> tuple[dict, float]:
    """Validate one replay row, apply routing, and build the API contract."""
    started = time.perf_counter_ns()
    values = {name: _safe_float(row.get(name)) for name in MONITORING_FIELDS}
    missing_or_nonfinite = [
        name for name, value in values.items() if value is None
    ]
    voltage = values["voltage_v"]
    current = values["current_a"]
    power = values["power_legacy_w"]
    invalid_electrical = (
        voltage is None
        or current is None
        or power is None
        or voltage <= 0
        or current < 0
        or power < 0
    )
    below_current_threshold = current is not None and current < 0.1
    power_anomaly = (
        power is not None and power > float(power_anomaly_threshold_w)
    )
    if missing_or_nonfinite:
        route_reason = "missing_or_nonfinite_value"
    elif invalid_electrical:
        route_reason = "invalid_electrical_reading"
    elif below_current_threshold:
        route_reason = "current_below_legacy_threshold"
    elif power_anomaly:
        route_reason = "power_above_trace_p99"
    else:
        route_reason = "normal_local_monitoring"
    tier = (
        "cloud"
        if (
            missing_or_nonfinite
            or invalid_electrical
            or below_current_threshold
            or power_anomaly
        )
        else "edge"
    )

    replay_timestamp = str(row.get("replay_timestamp_utc", row["timestamp_utc"]))
    source_timestamp = row.get("source_timestamp_utc")
    if pd.isna(source_timestamp):
        source_timestamp = None
    record = {
        "timestamp_utc": emitted_timestamp_utc or str(row["timestamp_utc"]),
        "device_id": str(row["device_id"]),
        "source_type": "historical_replay",
        "provenance": {
            "lineage_classification": str(
                row.get(
                    "lineage_classification",
                    "historical_replay_lineage_not_audited",
                )
            ),
            "source_timestamp_utc": (
                str(source_timestamp) if source_timestamp is not None else None
            ),
            "replay_timestamp_utc": replay_timestamp,
            "replay_id": str(row["replay_id"]),
            "replay_block_id": int(row["replay_block_id"]),
            "source_row_id": str(row["source_row_id"]),
            "source_row_index": int(row["source_row_index"]),
        },
        "monitoring": {
            "temperature_c": values["temperature_c"],
            "humidity_pct": values["humidity_pct"],
            "voltage_v": voltage,
            "current_a": current,
            "power_legacy_w": power,
            "power_formula_w": values["power_formula_w"],
            "power_consistency_error_w": values["power_consistency_error_w"],
            "energy_interval_legacy_wh": values[
                "energy_interval_legacy_wh"
            ],
            "energy_cumulative_legacy_wh": values[
                "energy_cumulative_legacy_wh"
            ],
            "energy_integration_status": str(
                row.get("energy_integration_status", "unknown")
            ),
            "people_count": (
                int(values["people_count"])
                if values["people_count"] is not None
                else None
            ),
            "occupancy_status": str(
                row.get("occupancy_status", "unknown")
            ),
            "voltage_status": str(row.get("voltage_status", "unknown")),
            "current_status": str(row.get("current_status", "unknown")),
        },
        "digital_twin": digital_twin_config
        or {
            "representation_class": "monitoring_oriented_one_way_prototype",
            "synchronization_mode": "request_driven_historical_replay",
            "supported_views": [
                "geospatial_site",
                "building",
                "indoor",
            ],
            "application_lod": [
                {
                    "lod_id": "LoD-A",
                    "view": "geospatial_site",
                    "scale": "site",
                    "detail": (
                        "macro geospatial context, legacy coordinate, "
                        "and edge-cloud relation"
                    ),
                },
                {
                    "lod_id": "LoD-B",
                    "view": "building",
                    "scale": "building",
                    "detail": (
                        "building-level monitoring summary, energy, "
                        "occupancy, and routing"
                    ),
                },
                {
                    "lod_id": "LoD-C",
                    "view": "indoor",
                    "scale": "indoor",
                    "detail": (
                        "detailed indoor 3D scene, sensor state, and "
                        "occupancy indicator"
                    ),
                },
            ],
            "lod_transition": "manual_view_selection",
            "geospatial_reference": {
                "latitude": -7.723,
                "longitude": 110.5187,
                "crs": "EPSG:4326",
                "verification_status": (
                    "legacy_coordinate_not_survey_validated"
                ),
            },
            "scale_semantics": (
                "three project-defined application LoD levels: LoD-A "
                "geospatial site, LoD-B building, and LoD-C indoor 3D; "
                "conformance to CityGML, IndoorGML, IFC, or 3D Tiles "
                "geometric LoD has not been evaluated"
            ),
            "data_direction": (
                "physical_or_replayed_source_to_digital_representation_only"
            ),
        },
        "processing": {
            "tier": tier,
            "valid": not invalid_electrical and not missing_or_nonfinite,
            "route_reason": route_reason,
            "compute_latency_ms": 0.0,
            "serialization_latency_ms": 0.0,
            "network_latency_ms": None,
            "end_to_end_latency_ms": None,
            "freshness_ms": None,
        },
    }
    compute_ms = (time.perf_counter_ns() - started) / 1_000_000
    record["processing"]["compute_latency_ms"] = compute_ms
    return record, compute_ms


def benchmark(
    frame: pd.DataFrame,
    config: dict,
    workload_scope: dict | None = None,
) -> dict:
    """Measure validation/routing/serialization and emulate the configured network."""
    configured_size = int(config["replay"]["benchmark_sample_size"])
    sample_size = min(configured_size, len(frame))
    sample = frame.iloc[:sample_size].reset_index(drop=True)
    if sample.empty:
        raise ValueError("Tidak ada baris replay yang dapat dibenchmark.")

    routing_config = config["benchmark"]["cloud_routing"]
    threshold = float(routing_config["power_anomaly_threshold_w"])
    rng = np.random.default_rng(int(config["replay"]["random_seed"]))
    compute_ms: list[float] = []
    serialization_ms: list[float] = []
    payload_bytes: list[int] = []
    routes: list[str] = []
    reasons: list[str] = []
    valid_flags: list[bool] = []
    consistency_errors: list[float] = []

    wall_started = time.perf_counter_ns()
    for _, row in sample.iterrows():
        record, measured_compute_ms = build_monitoring_record(
            row,
            threshold,
            digital_twin_config=config.get("digital_twin"),
        )
        serialization_started = time.perf_counter_ns()
        encoded = json.dumps(
            record, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
        measured_serialization_ms = (
            time.perf_counter_ns() - serialization_started
        ) / 1_000_000
        compute_ms.append(measured_compute_ms)
        serialization_ms.append(measured_serialization_ms)
        payload_bytes.append(len(encoded))
        routes.append(record["processing"]["tier"])
        reasons.append(record["processing"]["route_reason"])
        valid_flags.append(bool(record["processing"]["valid"]))
        error = record["monitoring"]["power_consistency_error_w"]
        if error is not None:
            consistency_errors.append(float(error))
    wall_seconds = max(
        (time.perf_counter_ns() - wall_started) / 1_000_000_000, 1e-9
    )

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
    drop_draw = rng.random(sample_size)
    dropped = (
        drop_draw < float(network["drop_probability"])
    ) & cloud_mask
    cloud_only_dropped = drop_draw < float(network["drop_probability"])
    compute = np.asarray(compute_ms)
    serialize = np.asarray(serialization_ms)
    edge_path = compute + serialize
    configured_e2e = edge_path + np.where(cloud_mask, network_ms, 0.0)
    delivered_e2e = configured_e2e[~dropped]
    cloud_network_ms = network_ms[cloud_mask]
    delivered_cloud_mask = cloud_mask & ~dropped
    delivered_cloud_e2e = configured_e2e[delivered_cloud_mask]
    cloud_only_e2e = edge_path + network_ms
    delivered_cloud_only_e2e = cloud_only_e2e[~cloud_only_dropped]
    deadline_ms = (
        float(config["data"]["near_realtime_deadline_seconds"]) * 1000.0
    )
    deadline_basis = str(config["data"]["deadline_basis"])
    reason_counts = {reason: reasons.count(reason) for reason in ROUTE_REASONS}
    covered_reasons = [
        reason for reason, count in reason_counts.items() if count > 0
    ]
    uncovered_reasons = [
        reason for reason, count in reason_counts.items() if count == 0
    ]
    errors = np.asarray(consistency_errors, dtype=float)
    cloud_only_deadline_misses = int(
        (delivered_cloud_only_e2e > deadline_ms).sum()
    )
    mixed_p95 = float(np.quantile(delivered_e2e, 0.95))
    cloud_only_p95 = float(
        np.quantile(delivered_cloud_only_e2e, 0.95)
    )
    network_bytes_edge_cloud = int(
        np.asarray(payload_bytes, dtype=int)[cloud_mask].sum()
    )
    network_bytes_cloud_only = int(np.asarray(payload_bytes, dtype=int).sum())

    return {
        "scope": {
            "evaluation_type": "historical_replay_architecture_benchmark",
            "compute": (
                "Measured on this machine using time.perf_counter_ns; "
                "not a dedicated edge device measurement."
            ),
            "network": str(network["label"]),
            "sample_size": sample_size,
            "messages_benchmarked": sample_size,
            "available_rows_are_not_messages_benchmarked": True,
            "near_realtime_deadline": {
                "milliseconds": deadline_ms,
                "basis": deadline_basis,
            },
            "workload": workload_scope
            or {
                "source_type": "historical_replay",
                "available_rows_scanned": len(frame),
                "messages_benchmarked": len(frame),
                "available_rows_are_not_messages_benchmarked": True,
                "role": "monitoring-path benchmark input",
            },
            "runtime": {
                "platform": platform.platform(),
                "python": sys.version.split()[0],
                "numpy": np.__version__,
                "pandas": pd.__version__,
            },
        },
        "actual_local_monitoring": {
            **_percentiles(compute_ms),
            "definition": (
                "Structural/electrical value checks, power-consistency check, "
                "routing, and payload construction on the local host."
            ),
            "validation_scope": (
                "Software-level structure and value checks only; not field "
                "validation or metrological validation of active power."
            ),
        },
        "actual_json_serialization": _percentiles(serialization_ms),
        "actual_edge_path": {
            **_percentiles(edge_path),
            "definition": "local monitoring processing plus JSON serialization",
        },
        "configured_network_emulation": {
            "parameters": network,
            "generated_latency": _percentiles(cloud_network_ms),
            "generated_for_cloud_routed_messages": int(cloud_mask.sum()),
            "generated_cloud_drop_count": int(dropped.sum()),
        },
        "configured_cloud_route_end_to_end": {
            **_percentiles(delivered_cloud_e2e),
            "routed_count": int(cloud_mask.sum()),
            "delivered_count": int(delivered_cloud_mask.sum()),
            "definition": (
                "Local monitoring plus serialization and configured network "
                "latency, calculated only for cloud-routed messages."
            ),
            "warning": "Network latency is configured, not field-measured.",
        },
        "configured_end_to_end": {
            **_percentiles(delivered_e2e),
            "attempted_count": sample_size,
            "delivered_count": int((~dropped).sum()),
            "dropped_count": int(dropped.sum()),
            "deadline_ms": deadline_ms,
            "deadline_basis": deadline_basis,
            "deadline_miss_count": int((delivered_e2e > deadline_ms).sum()),
            "deadline_miss_rate": float(
                (delivered_e2e > deadline_ms).mean()
            ),
            "freshness_proxy": (
                "Processing plus configured network latency; browser rendering "
                "and historical age are excluded."
            ),
            "warning": "Network latency is configured, not field-measured.",
            "definition": (
                "Overall mixture of edge-routed and delivered cloud-routed "
                "messages; route composition affects its percentiles."
            ),
        },
        "configured_cloud_only_baseline": {
            **_percentiles(delivered_cloud_only_e2e),
            "attempted_count": sample_size,
            "delivered_count": int((~cloud_only_dropped).sum()),
            "dropped_count": int(cloud_only_dropped.sum()),
            "deadline_ms": deadline_ms,
            "deadline_miss_count": cloud_only_deadline_misses,
            "deadline_miss_rate": float(
                cloud_only_deadline_misses
                / max(int((~cloud_only_dropped).sum()), 1)
            ),
            "definition": (
                "Counterfactual baseline in which every message traverses the "
                "same configured network profile after identical local "
                "processing and serialization."
            ),
            "warning": "Network latency is configured, not field-measured.",
        },
        "architecture_comparison": {
            "edge_cloud_p95_ms": mixed_p95,
            "cloud_only_p95_ms": cloud_only_p95,
            "configured_p95_latency_reduction_percent": float(
                (cloud_only_p95 - mixed_p95) / cloud_only_p95 * 100.0
                if cloud_only_p95 > 0
                else 0.0
            ),
            "network_offload_rate": float(edge_mask.mean()),
            "network_payload_bytes_edge_cloud": network_bytes_edge_cloud,
            "network_payload_bytes_cloud_only": network_bytes_cloud_only,
            "network_payload_bytes_avoided": (
                network_bytes_cloud_only - network_bytes_edge_cloud
            ),
            "network_payload_reduction_rate": float(
                1.0
                - network_bytes_edge_cloud
                / max(network_bytes_cloud_only, 1)
            ),
            "comparison_basis": (
                "Same replay sample, local processing, serialized payloads, "
                "seed, and configured network draws. This is a controlled "
                "emulation comparison, not a measured public-cloud trial."
            ),
        },
        "routing": {
            "edge_count": int(edge_mask.sum()),
            "cloud_count": int(cloud_mask.sum()),
            "reason_counts": reason_counts,
            "covered_reasons": covered_reasons,
            "uncovered_reasons": uncovered_reasons,
            "power_anomaly_threshold_w": threshold,
            "rule": (
                "Cloud for missing/non-finite values, invalid electrical "
                "readings, current below the legacy 0.1 A threshold, or "
                f"legacy power above {threshold:.1f} W."
            ),
            "basis": str(routing_config["basis"]),
        },
        "data_quality": {
            "valid_count": int(sum(valid_flags)),
            "invalid_count": int(sample_size - sum(valid_flags)),
            "validity_definition": (
                "All required values are finite and electrical values satisfy "
                "the software bounds; this is not field validation."
            ),
            "power_consistency_error_w": {
                "mean": float(errors.mean()) if errors.size else None,
                "p95": float(np.quantile(errors, 0.95)) if errors.size else None,
                "max": float(errors.max()) if errors.size else None,
                "above_0_11_w_count": int((errors > 0.11).sum()),
            },
            "legacy_proxy_energy": {
                "trace_cycle_max_cumulative_wh_in_sample": float(
                    sample["energy_cumulative_legacy_wh"].max()
                ),
                "integrated_interval_count_in_sample": int(
                    sample["energy_integration_status"]
                    .eq("integrated")
                    .sum()
                ),
                "interpretation": (
                    "Trapezoidal integral of the transformed CSV replay "
                    "payload's legacy V×I field. This is workload context; "
                    "the archived field-trace energy is calculated separately "
                    "and no direct kWh-meter or power-factor channel is "
                    "included."
                ),
            },
            "occupancy": {
                "occupied_count": int(
                    sample["occupancy_status"].eq("occupied").sum()
                ),
                "unoccupied_count": int(
                    sample["occupancy_status"].eq("unoccupied").sum()
                ),
                "people_count_mean": float(sample["people_count"].mean()),
                "people_count_max": int(sample["people_count"].max()),
            },
        },
        "throughput": {
            "sequential_messages_per_second": float(sample_size / wall_seconds),
            "definition": (
                "Messages divided by measured wall time for monitoring and "
                "serialization loop on this machine."
            ),
        },
        "payload": {
            "mean_bytes": float(np.mean(payload_bytes)),
            "p95_bytes": float(np.quantile(payload_bytes, 0.95)),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("configs/experiment.json"))
    parser.add_argument("--input", type=Path, default=Path("Data/sensor_data.csv"))
    parser.add_argument("--output", type=Path, default=Path("outputs/benchmark_metrics.json"))
    parser.add_argument(
        "--workload-audit-output",
        type=Path,
        default=Path("outputs/historical_replay_audit.json"),
    )
    parser.add_argument("--sample-size", type=int)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    if args.sample_size:
        config["replay"]["benchmark_sample_size"] = args.sample_size
    replay = config["replay"]
    frame, audit = prepare_historical_replay(
        args.input,
        expected_rows=int(replay["expected_rows"]),
        reference_rows=int(replay["reference_rows_per_replay"]),
        sample_size=int(replay["benchmark_sample_size"]),
        reference_trace=Path(config["data"]["reference_trace"]),
        max_energy_gap_seconds=float(
            config["energy_integration"]["max_gap_seconds"]
        ),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.workload_audit_output.write_text(
        json.dumps(audit, indent=2), encoding="utf-8"
    )
    report = benchmark(
        frame,
        config,
        workload_scope={
            "source_type": "historical_replay",
            "available_rows_scanned": audit["source"]["rows"],
            "messages_benchmarked": len(frame),
            "available_rows_are_not_messages_benchmarked": True,
            "lineage_classification": audit["lineage"]["classification"],
            "sample_selection": audit["benchmark_sample"]["method"],
            "covered_replay_blocks": audit["benchmark_sample"][
                "covered_replay_blocks"
            ],
            "role": "architecture monitoring and Digital Twin replay only",
        },
    )
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Benchmark tersimpan: {args.output}")


if __name__ == "__main__":
    main()
