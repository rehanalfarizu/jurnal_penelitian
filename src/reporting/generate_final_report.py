"""Create the compact, reviewable final-results package."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _metric_row(name: str, model_report: dict) -> str:
    summary = model_report["run_level_summary"]
    mae = summary["mae_w"]
    rmse = summary["rmse_w"]
    r2 = summary["r2"]
    return (
        f"| {name} | {mae['mean']:.3f} "
        f"[{mae['ci95_low']:.3f}, {mae['ci95_high']:.3f}] | "
        f"{rmse['mean']:.3f} [{rmse['ci95_low']:.3f}, {rmse['ci95_high']:.3f}] | "
        f"{r2['mean']:.3f} [{r2['ci95_low']:.3f}, {r2['ci95_high']:.3f}] |"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--outputs", type=Path, default=Path("outputs"))
    parser.add_argument("--destination", type=Path, default=Path("results/final"))
    parser.add_argument("--config", type=Path, default=Path("configs/experiment.json"))
    args = parser.parse_args()
    args.destination.mkdir(parents=True, exist_ok=True)

    config = json.loads(args.config.read_text(encoding="utf-8"))
    summary = json.loads((args.outputs / "experiment_summary.json").read_text())
    model = json.loads((args.outputs / "model_metrics.json").read_text())
    validation = json.loads((args.outputs / "synthetic_validation.json").read_text())
    benchmark = json.loads((args.outputs / "benchmark_metrics.json").read_text())
    audit = json.loads((args.outputs / "trace_audit.json").read_text())
    augmented = json.loads(
        (args.outputs / "augmented_workload_audit.json").read_text()
    )

    json_names = [
        "trace_audit.json",
        "augmented_workload_audit.json",
        "synthetic_validation.json",
        "model_metrics.json",
        "benchmark_metrics.json",
        "experiment_summary.json",
    ]
    for name in json_names:
        shutil.copy2(args.outputs / name, args.destination / name)
    shutil.copy2(args.config, args.destination / "experiment_config.json")

    manifest_files = [
        args.config,
        Path(config["data"]["reference_trace"]),
        Path(config["data"]["augmented_legacy"]),
        args.outputs / "synthetic_telemetry.csv",
        args.outputs / "power_estimator.joblib",
    ]
    manifest = {
        "run_type": summary["run_type"],
        "files": {
            str(path): {
                "sha256": _sha256(path),
                "bytes": path.stat().st_size,
            }
            for path in manifest_files
        },
    }
    (args.destination / "artifact_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )

    test_metrics = model["test_metrics"]
    model_labels = {
        "constant_train_median": "Median train",
        "firmware_v_times_i": "Firmware V×I",
        "ridge": "Ridge",
        "random_forest": "Random Forest",
    }
    metric_rows = "\n".join(
        _metric_row(model_labels[name], test_metrics[name])
        for name in model_labels
    )
    calibration = validation["calibration_comparison"]
    calibration_rows = "\n".join(
        (
            f"| {name} | {values['normalized_quantile_mae']:.3f} | "
            f"{abs(values['real_zero_rate'] - values['synthetic_zero_rate']):.3f} | "
            f"{abs(values['real_acf_lag_1'] - values['synthetic_acf_lag_1']):.3f} | "
            f"{'Lulus' if calibration['acceptance_criteria']['by_variable'][name]['accepted'] else 'Tidak lulus'} |"
        )
        for name, values in calibration["variables"].items()
    )
    compute = benchmark["actual_local_compute"]
    edge_path = benchmark["actual_edge_path"]
    cloud_path = benchmark["configured_cloud_path"]
    e2e = benchmark["configured_end_to_end"]
    design = model["evaluation_design"]
    selection = model["model_selection"]

    report = f"""# Hasil eksperimen final terkonfigurasi

Status: **evaluasi berbasis simulasi; bukan validasi lapangan**.

## Cakupan

- Trace kalibrasi: {audit['source']['rows']:,} baris, satu gateway.
- Workload sintetis: {summary['rows']:,} baris dan {summary['runs']} run.
- Workload replay arsitektur: {augmented['source']['rows']:,} baris augmented,
  setara {augmented['provenance']['inferred_replay_blocks']:.0f} replay trace asli.
- Durasi: {config['data']['duration_hours']} jam per run.
- Interval: {config['data']['sample_interval_seconds']} detik.
- Train scenario: {', '.join(design['train_scenarios'])}.
- Validation scenario: {', '.join(design['validation_scenarios'])}.
- Test scenario ditahan: {', '.join(design['test_scenarios'])}.

## Pemeriksaan kalibrasi skenario normal

| Variabel | Normalized quantile MAE | Galat zero-rate | Galat ACF lag-1 | Status |
|---|---:|---:|---:|---|
{calibration_rows}

Status keseluruhan: **{'Lulus' if calibration['acceptance_criteria']['overall_accepted'] else 'Tidak lulus'}**.
Ambang diagnostik dideklarasikan di `synthetic_validation.json`.

## Estimasi daya pada skenario test tertahan

Angka adalah rata-rata per run dan 95% confidence interval.

| Model | MAE W [95% CI] | RMSE W [95% CI] | R² [95% CI] |
|---|---:|---:|---:|
{metric_rows}

Model terpilih: **{selection['selected_model']}**, menggunakan kriteria
`{selection['criterion']}`. Test metrics tidak digunakan saat seleksi.

Metrik ini hanya mengukur generalisasi antarskenario sintetis. Workbook asli
tidak mempunyai ground truth daya independen.

## Posisi data augmented 2 juta

File augmented **tidak digunakan** untuk training, validation, maupun test
akurasi model. File digunakan sebagai workload replay arsitektur dengan label
`legacy_augmented_replay`.

- Baris tersedia: {augmented['source']['rows']:,}.
- Sampel benchmark: {augmented['benchmark_sample']['selected_rows']:,} posisi
  yang tersebar merata pada seluruh
  {len(augmented['benchmark_sample']['covered_replay_blocks'])} blok replay.
- Fungsi: menguji inference, serialisasi, routing, throughput, dan aliran
  telemetry menuju Digital Twin Web-3D.
- Larangan klaim: bukan 2 juta observasi lapangan independen dan bukan bukti
  akurasi estimasi daya.

## Benchmark arsitektur

- Sumber workload: `{benchmark['scope']['workload']['source_type']}`.
- Mesin/runtime: `{benchmark['scope']['runtime']['platform']}`; Python {benchmark['scope']['runtime']['python']}.
- Inference lokal aktual: P50 {compute['p50_ms']:.3f} ms, P95 {compute['p95_ms']:.3f} ms, P99 {compute['p99_ms']:.3f} ms.
- Edge-path aktual: P50 {edge_path['p50_ms']:.3f} ms, P95 {edge_path['p95_ms']:.3f} ms, P99 {edge_path['p99_ms']:.3f} ms.
- Cloud-path terkonfigurasi: P50 {cloud_path['p50_ms']:.3f} ms, P95 {cloud_path['p95_ms']:.3f} ms, P99 {cloud_path['p99_ms']:.3f} ms.
- Hybrid end-to-end terkonfigurasi: P50 {e2e['p50_ms']:.3f} ms, P95 {e2e['p95_ms']:.3f} ms, P99 {e2e['p99_ms']:.3f} ms.
- Routing: {benchmark['routing']['edge_count']:,} pesan ke edge dan
  {benchmark['routing']['cloud_count']:,} pesan anomali/invalid ke cloud
  menggunakan ambang daya legacy {benchmark['routing']['power_anomaly_threshold_w']:.1f} W.
- Deadline miss: {e2e['deadline_miss_count']} ({e2e['deadline_miss_rate']:.3%}) pada deadline {e2e['deadline_ms']:.1f} ms.
- Profil jaringan adalah emulasi, bukan pengukuran public cloud.
- Browser render latency belum termasuk.

## Visual

- [Kalibrasi distribusi](figures/01_calibration_distribution.png)
- [Contoh estimasi pada test scenario](figures/02_power_timeseries.png)
- [Perbandingan model dan confidence interval](figures/03_model_comparison.png)
- [Karakteristik latency](figures/04_latency_characteristics.png)

## Batas klaim

Hasil dapat digunakan sebagai hasil final untuk studi **simulation-based
evaluation calibrated from a real four-day trace**. Hasil tidak boleh disebut
sebagai akurasi lapangan, pengukuran Raspberry Pi, pengukuran Azure produksi,
atau validasi banyak bangunan.
"""
    (args.destination / "RESULTS.md").write_text(report, encoding="utf-8")
    print(f"Paket hasil final tersimpan: {args.destination}")


if __name__ == "__main__":
    main()
