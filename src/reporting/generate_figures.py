"""Generate clearly labelled diagnostic figures from experiment outputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.data.audit_trace import load_trace
from src.models.train_baselines import FEATURES, prepare


COLORS = {
    "real": "#334155",
    "synthetic": "#0ea5e9",
    "truth": "#111827",
    "observed": "#f59e0b",
    "estimated": "#16a34a",
}
RESULT_LABEL = "SMOKE TEST DIAGNOSTIC — BUKAN HASIL FINAL JURNAL"


def add_diagnostic_label(figure: plt.Figure) -> None:
    figure.text(
        0.995,
        0.005,
        RESULT_LABEL,
        ha="right",
        va="bottom",
        fontsize=8,
        color="#b91c1c",
        weight="bold",
    )


def save(figure: plt.Figure, output: Path) -> None:
    add_diagnostic_label(figure)
    figure.savefig(output, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(figure)


def plot_calibration(real: pd.DataFrame, synthetic: pd.DataFrame, output: Path) -> None:
    normal = synthetic[synthetic["scenario_id"].eq("normal")]
    variables = [
        ("temperature_c", "observed_temperature_c", "Suhu", "°C"),
        ("humidity_pct", "observed_humidity_pct", "Kelembapan", "%"),
        ("voltage_v", "observed_voltage_v", "Tegangan", "V"),
        ("power_w", "observed_power_w", "Daya legacy V×I", "W"),
    ]
    figure, axes = plt.subplots(2, 2, figsize=(12, 8))
    for axis, (real_col, synthetic_col, title, unit) in zip(axes.flat, variables):
        real_values = real[real_col].dropna()
        synthetic_values = normal[synthetic_col].dropna()
        combined = pd.concat([real_values, synthetic_values])
        lower, upper = combined.quantile([0.01, 0.99])
        bins = np.linspace(lower, upper, 40)
        axis.hist(
            real_values,
            bins=bins,
            density=True,
            alpha=0.48,
            color=COLORS["real"],
            label="Trace asli",
        )
        axis.hist(
            synthetic_values,
            bins=bins,
            density=True,
            alpha=0.48,
            color=COLORS["synthetic"],
            label="Sintetis: normal",
        )
        axis.set_title(title)
        axis.set_xlabel(unit)
        axis.set_ylabel("Densitas")
        axis.grid(alpha=0.2)
    axes[0, 0].legend(frameon=False)
    figure.suptitle(
        "Pemeriksaan Kalibrasi Distribusi\nTrace asli vs skenario sintetis normal",
        fontsize=15,
        weight="bold",
    )
    figure.tight_layout(rect=(0, 0.03, 1, 0.94))
    save(figure, output)


def plot_timeseries(synthetic: pd.DataFrame, artifact: dict, output: Path) -> None:
    selected_run = "sensor_degraded_run_00"
    frame = prepare(synthetic[synthetic["run_id"].eq(selected_run)]).iloc[:400].copy()
    frame["estimated_power_w"] = artifact["model"].predict(frame[FEATURES])
    model_label = artifact["model_name"].replace("_", " ").title()
    x = np.arange(len(frame))
    figure, axis = plt.subplots(figsize=(13, 5.5))
    axis.plot(
        x,
        frame["true_power_w"],
        color=COLORS["truth"],
        linewidth=2,
        label="Ground truth sintetis",
    )
    axis.plot(
        x,
        frame["observed_power_w"],
        color=COLORS["observed"],
        linewidth=1.2,
        alpha=0.8,
        label="Observasi firmware V×I",
    )
    axis.plot(
        x,
        frame["estimated_power_w"],
        color=COLORS["estimated"],
        linewidth=1.5,
        label=f"Estimasi {model_label}",
    )
    axis.set_title(f"Contoh Estimasi Near Real-Time — {selected_run}", weight="bold")
    axis.set_xlabel("Urutan pesan valid")
    axis.set_ylabel("Daya (W)")
    axis.grid(alpha=0.2)
    axis.legend(ncol=3, frameon=False)
    figure.tight_layout(rect=(0, 0.03, 1, 1))
    save(figure, output)


def plot_model_metrics(metrics: dict, output: Path) -> None:
    models = [
        "constant_train_median",
        "firmware_v_times_i",
        "ridge",
        "random_forest",
    ]
    labels = ["Median", "Firmware V×I", "Ridge", "Random Forest"]
    overall = metrics["metrics"]
    def run_summary(model: str, metric: str) -> dict:
        return overall[model]["run_level_summary"][metric]

    mae = [run_summary(name, "mae_w")["mean"] for name in models]
    rmse = [run_summary(name, "rmse_w")["mean"] for name in models]
    r2 = [run_summary(name, "r2")["mean"] for name in models]
    mae_error = [
        run_summary(name, "mae_w")["ci95_high"] - run_summary(name, "mae_w")["mean"]
        for name in models
    ]
    rmse_error = [
        run_summary(name, "rmse_w")["ci95_high"] - run_summary(name, "rmse_w")["mean"]
        for name in models
    ]
    r2_error = [
        run_summary(name, "r2")["ci95_high"] - run_summary(name, "r2")["mean"]
        for name in models
    ]
    x = np.arange(len(models))

    figure, axes = plt.subplots(1, 2, figsize=(13, 5))
    width = 0.36
    axes[0].bar(
        x - width / 2,
        mae,
        width,
        yerr=mae_error,
        capsize=4,
        label="MAE",
        color="#0ea5e9",
    )
    axes[0].bar(
        x + width / 2,
        rmse,
        width,
        yerr=rmse_error,
        capsize=4,
        label="RMSE",
        color="#6366f1",
    )
    axes[0].set_xticks(x, labels, rotation=15, ha="right")
    axes[0].set_ylabel("Galat (W), lebih rendah lebih baik")
    axes[0].set_title("MAE dan RMSE")
    axes[0].legend(frameon=False)
    axes[0].grid(axis="y", alpha=0.2)

    colors = ["#64748b" if value >= 0 else "#dc2626" for value in r2]
    axes[1].bar(x, r2, yerr=r2_error, capsize=4, color=colors)
    axes[1].axhline(0, color="#111827", linewidth=0.8)
    axes[1].set_xticks(x, labels, rotation=15, ha="right")
    axes[1].set_ylabel("R², lebih tinggi lebih baik")
    axes[1].set_title("Koefisien Determinasi")
    axes[1].grid(axis="y", alpha=0.2)

    figure.suptitle(
        "Perbandingan pada Skenario Test yang Ditahan\n"
        "Rata-rata run dengan 95% confidence interval",
        fontsize=15,
        weight="bold",
    )
    figure.tight_layout(rect=(0, 0.03, 1, 0.94))
    save(figure, output)


def plot_latency(benchmark: dict, output: Path) -> None:
    percentiles = ["p50_ms", "p95_ms", "p99_ms"]
    labels = ["P50", "P95", "P99"]
    compute = [benchmark["actual_local_compute"][key] for key in percentiles]
    serialization = [benchmark["actual_json_serialization"][key] for key in percentiles]
    network = [
        benchmark["configured_network_emulation"]["generated_latency"][key]
        for key in percentiles
    ]
    cloud_path = [
        benchmark["configured_cloud_path"][key] for key in percentiles
    ]
    end_to_end = [benchmark["configured_end_to_end"][key] for key in percentiles]
    x = np.arange(3)

    figure, axes = plt.subplots(1, 2, figsize=(13, 5))
    axes[0].bar(x - 0.18, compute, 0.36, label="Inference lokal", color="#16a34a")
    axes[0].bar(x + 0.18, serialization, 0.36, label="Serialisasi JSON", color="#0ea5e9")
    axes[0].set_yscale("log")
    axes[0].set_xticks(x, labels)
    axes[0].set_ylabel("Latency terukur (ms, skala log)")
    axes[0].set_title("Komputasi aktual pada mesin uji")
    axes[0].legend(frameon=False)
    axes[0].grid(axis="y", alpha=0.2)

    axes[1].bar(x - 0.25, network, 0.25, label="Profil jaringan", color="#f59e0b")
    axes[1].bar(
        x,
        cloud_path,
        0.25,
        label="Cloud-path terkonfigurasi",
        color="#ef4444",
    )
    axes[1].bar(
        x + 0.25,
        end_to_end,
        0.25,
        label="Hybrid E2E (edge + cloud)",
        color="#8b5cf6",
    )
    axes[1].set_xticks(x, labels)
    axes[1].set_ylabel("Latency terkonfigurasi (ms)")
    axes[1].set_title("Hybrid: mayoritas pesan diproses di edge")
    axes[1].legend(frameon=False)
    axes[1].grid(axis="y", alpha=0.2)

    figure.suptitle("Karakteristik Latency Edge-Cloud", fontsize=15, weight="bold")
    figure.tight_layout(rect=(0, 0.03, 1, 0.94))
    save(figure, output)


def main() -> None:
    global RESULT_LABEL
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--real",
        type=Path,
        default=Path("Data/sensor_data_export_2026-05-17_to_2026-05-23.xlsx"),
    )
    parser.add_argument("--outputs", type=Path, default=Path("outputs"))
    parser.add_argument("--figures", type=Path, default=Path("outputs/figures"))
    args = parser.parse_args()
    args.figures.mkdir(parents=True, exist_ok=True)

    real = load_trace(args.real)
    synthetic = pd.read_csv(args.outputs / "synthetic_telemetry.csv")
    metrics = json.loads((args.outputs / "model_metrics.json").read_text())
    benchmark = json.loads((args.outputs / "benchmark_metrics.json").read_text())
    summary = json.loads((args.outputs / "experiment_summary.json").read_text())
    if summary.get("run_type") == "final_configured_experiment":
        RESULT_LABEL = "EVALUASI BERBASIS SIMULASI — BUKAN VALIDASI LAPANGAN"
    artifact = joblib.load(args.outputs / "power_estimator.joblib")

    plot_calibration(real, synthetic, args.figures / "01_calibration_distribution.png")
    plot_timeseries(synthetic, artifact, args.figures / "02_power_timeseries.png")
    plot_model_metrics(metrics, args.figures / "03_model_comparison.png")
    plot_latency(benchmark, args.figures / "04_latency_characteristics.png")
    print(f"Empat visual diagnostik tersimpan di {args.figures}")


if __name__ == "__main__":
    main()
