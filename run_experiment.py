"""Run the reproducible historical-replay architecture evaluation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.benchmark.edge_cloud_benchmark import benchmark
from src.data.audit_trace import audit_trace
from src.data.prepare_historical_replay import prepare_historical_replay


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("configs/experiment.json"))
    parser.add_argument(
        "--sample-size",
        type=int,
        help="Override jumlah sampel benchmark untuk smoke test.",
    )
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    if args.sample_size:
        config["replay"]["benchmark_sample_size"] = args.sample_size

    output_dir = Path(config["data"]["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    reference_path = Path(config["data"]["reference_trace"])
    replay_path = Path(config["data"]["historical_replay"])

    trace_audit = audit_trace(
        reference_path,
        max_energy_gap_seconds=float(
            config["energy_integration"]["max_gap_seconds"]
        ),
    )
    (output_dir / "trace_audit.json").write_text(
        json.dumps(trace_audit, indent=2), encoding="utf-8"
    )
    print(
        "[1/3] Trace historis diaudit: "
        f"{trace_audit['source']['rows']:,} observasi"
    )

    replay_config = config["replay"]
    replay_sample, replay_audit = prepare_historical_replay(
        replay_path,
        expected_rows=int(replay_config["expected_rows"]),
        reference_rows=int(replay_config["reference_rows_per_replay"]),
        sample_size=int(replay_config["benchmark_sample_size"]),
        reference_trace=reference_path,
        max_energy_gap_seconds=float(
            config["energy_integration"]["max_gap_seconds"]
        ),
    )
    replay_sample.to_csv(
        output_dir / "historical_replay_sample.csv", index=False
    )
    (output_dir / "historical_replay_audit.json").write_text(
        json.dumps(replay_audit, indent=2), encoding="utf-8"
    )
    print(
        "[2/3] Replay historis diaudit: "
        f"{replay_audit['source']['rows']:,} baris, "
        f"{replay_audit['provenance']['inferred_replay_blocks']:.0f} blok"
    )

    workload_scope = {
        "source_type": "historical_replay",
        "available_rows_scanned": replay_audit["source"]["rows"],
        "messages_benchmarked": len(replay_sample),
        "available_rows_are_not_messages_benchmarked": True,
        "independent_reference_rows": replay_audit["provenance"][
            "reference_rows"
        ],
        "lineage_classification": replay_audit["lineage"][
            "classification"
        ],
        "sample_selection": replay_audit["benchmark_sample"]["method"],
        "covered_replay_blocks": replay_audit["benchmark_sample"][
            "covered_replay_blocks"
        ],
        "role": (
            "monitoring-path latency, throughput, routing, provenance, "
            "legacy-proxy energy, occupancy, and multiscale Digital Twin replay"
        ),
        "used_for_model_training_or_accuracy": False,
    }
    benchmark_report = benchmark(replay_sample, config, workload_scope)
    (output_dir / "benchmark_metrics.json").write_text(
        json.dumps(benchmark_report, indent=2), encoding="utf-8"
    )
    print("[3/3] Benchmark jalur pemantauan edge-cloud selesai")

    summary = {
        "pipeline_status": "completed",
        "evaluation_type": "historical_replay_architecture_evaluation",
        "project_title": config["project"]["title"],
        "claim_scope": config["project"]["claim_scope"],
        "reference_trace": {
            "rows": trace_audit["source"]["rows"],
            "device_count": trace_audit["source"]["device_count"],
            "timestamp_start_utc": trace_audit["source"][
                "timestamp_start_utc"
            ],
            "timestamp_end_utc": trace_audit["source"]["timestamp_end_utc"],
            "derived_energy": trace_audit["derived_energy"],
            "measurement_provenance": config["project"][
                "field_sensor_trace"
            ],
        },
        "near_realtime_deadline": {
            "seconds": config["data"]["near_realtime_deadline_seconds"],
            "basis": config["data"]["deadline_basis"],
        },
        "historical_replay": {
            "rows": replay_audit["source"]["rows"],
            "replay_blocks": replay_audit["provenance"][
                "inferred_replay_blocks"
            ],
            "sample_rows": len(replay_sample),
            "rows_scanned_not_messages_benchmarked": True,
            "lineage_classification": replay_audit["lineage"][
                "classification"
            ],
            "all_replay_payloads_identical_to_first_block": replay_audit[
                "lineage"
            ]["all_replay_payloads_identical_to_first_block"],
            "transformation_code_available": replay_audit["lineage"][
                "transformation_code_available"
            ],
            "independent_field_observations_claimed": False,
        },
        "monitoring_results": {
            "local_monitoring": benchmark_report[
                "actual_local_monitoring"
            ],
            "edge_path": benchmark_report["actual_edge_path"],
            "configured_end_to_end": benchmark_report[
                "configured_end_to_end"
            ],
            "throughput": benchmark_report["throughput"],
            "routing": benchmark_report["routing"],
            "data_quality": benchmark_report["data_quality"],
            "architecture_comparison": benchmark_report[
                "architecture_comparison"
            ],
            "field_trace_energy": trace_audit["derived_energy"],
            "replay_payload_energy": replay_audit["quality"][
                "energy_integration"
            ],
            "occupancy": replay_audit["quality"]["occupancy"],
        },
        "digital_twin": config["digital_twin"],
        "excluded_claims": [
            "model accuracy or prediction precision",
            "recomputed calibration error against the PLN kWh meter, because interval readings are not stored in this repository",
            "active-power or power-factor measurement beyond the legacy V×I signal",
            "survey-validated geospatial coordinates or standards-certified LOD",
            "measured public-cloud latency",
            "2,027,520 independent field observations",
            "2,027,520 messages benchmarked or load-tested",
            "raw equality between the replay CSV and exported workbook",
            "operational bidirectional Digital Twin validation",
        ],
    }
    (output_dir / "experiment_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(f"Ringkasan: {output_dir / 'experiment_summary.json'}")


if __name__ == "__main__":
    main()
