"""Run the reproducible research pipeline from audit to benchmark."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib

from src.benchmark.edge_cloud_benchmark import benchmark
from src.data.audit_trace import audit_trace, load_trace
from src.data.generate_synthetic import generate_dataset
from src.data.prepare_augmented_workload import prepare_augmented_workload
from src.data.validate_synthetic import validate
from src.models.train_baselines import train_and_evaluate


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("configs/experiment.json"))
    parser.add_argument(
        "--rows-per-run",
        type=int,
        help="Override jumlah baris per run untuk smoke test.",
    )
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    if args.rows_per_run:
        config["benchmark"]["sample_size"] = min(
            int(config["benchmark"]["sample_size"]), 500
        )
    output_dir = Path(config["data"]["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    real_path = Path(config["data"]["reference_trace"])

    calibration = audit_trace(real_path)
    (output_dir / "trace_audit.json").write_text(
        json.dumps(calibration, indent=2), encoding="utf-8"
    )
    print("[1/6] Audit trace asli selesai")

    synthetic = generate_dataset(config, calibration, args.rows_per_run)
    synthetic_path = output_dir / "synthetic_telemetry.csv"
    synthetic.to_csv(synthetic_path, index=False)
    print(f"[2/6] Data sintetis: {len(synthetic):,} baris")

    validation = validate(load_trace(real_path), synthetic)
    (output_dir / "synthetic_validation.json").write_text(
        json.dumps(validation, indent=2), encoding="utf-8"
    )
    print("[3/6] Validasi diagnostik selesai")

    model_report, artifact = train_and_evaluate(synthetic, config)
    (output_dir / "model_metrics.json").write_text(
        json.dumps(model_report, indent=2), encoding="utf-8"
    )
    joblib.dump(artifact, output_dir / "power_estimator.joblib")
    print("[4/6] Evaluasi model selesai")

    workload_config = config["benchmark"]["workload"]
    augmented_sample, augmented_audit = prepare_augmented_workload(
        Path(config["data"]["augmented_legacy"]),
        expected_rows=int(workload_config["expected_rows"]),
        reference_rows=int(workload_config["reference_rows_per_replay"]),
        sample_size=int(config["benchmark"]["sample_size"]),
    )
    (output_dir / "augmented_workload_audit.json").write_text(
        json.dumps(augmented_audit, indent=2), encoding="utf-8"
    )
    print(
        "[5/6] Workload augmented diaudit: "
        f"{augmented_audit['source']['rows']:,} baris; "
        "khusus replay arsitektur"
    )

    benchmark_input = augmented_sample.dropna()
    benchmark_report = benchmark(
        benchmark_input,
        artifact,
        config,
        workload_scope={
            "source_type": "legacy_augmented_replay",
            "available_rows": augmented_audit["source"]["rows"],
            "sample_selection": augmented_audit["benchmark_sample"]["method"],
            "covered_replay_blocks": augmented_audit["benchmark_sample"][
                "covered_replay_blocks"
            ],
            "role": (
                "architecture latency, throughput, routing, and Web-3D replay; "
                "excluded from model fitting and accuracy evaluation"
            ),
        },
    )
    (output_dir / "benchmark_metrics.json").write_text(
        json.dumps(benchmark_report, indent=2), encoding="utf-8"
    )
    print("[6/6] Benchmark arsitektur selesai")

    summary = {
        "pipeline_status": "completed",
        "run_type": (
            "smoke_test" if args.rows_per_run else "final_configured_experiment"
        ),
        "rows": int(len(synthetic)),
        "runs": int(synthetic["run_id"].nunique()),
        "architecture_workload": {
            "source_type": "legacy_augmented_replay",
            "rows": augmented_audit["source"]["rows"],
            "inferred_replay_blocks": augmented_audit["provenance"][
                "inferred_replay_blocks"
            ],
            "used_for_model_accuracy": False,
        },
        "model_metrics": model_report["metrics"],
        "benchmark_scope": benchmark_report["scope"],
    }
    (output_dir / "experiment_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(f"Ringkasan: {output_dir / 'experiment_summary.json'}")


if __name__ == "__main__":
    main()
