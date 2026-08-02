"""Generate publication-ready figures for the multiscale Digital Twin evaluation."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

_matplotlib_cache = Path("outputs/.matplotlib").resolve()
_matplotlib_cache.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_matplotlib_cache))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd

from src.data.audit_trace import load_trace


COLORS = {
    "navy": "#0f172a",
    "blue": "#0284c7",
    "cyan": "#06b6d4",
    "green": "#16a34a",
    "orange": "#f59e0b",
    "red": "#dc2626",
    "violet": "#7c3aed",
    "slate": "#64748b",
}

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "axes.titlesize": 11.5,
        "axes.titleweight": "semibold",
        "axes.labelsize": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.axisbelow": True,
        "figure.titlesize": 15,
        "figure.titleweight": "semibold",
        "legend.frameon": False,
    }
)


def save(figure: plt.Figure, output: Path) -> None:
    figure.savefig(output, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(figure)


def style_axis(axis: plt.Axes, grid_axis: str = "y") -> None:
    axis.grid(axis=grid_axis, color="#e2e8f0", linewidth=0.8)
    axis.tick_params(colors="#334155", labelsize=9)
    axis.xaxis.label.set_color(COLORS["navy"])
    axis.yaxis.label.set_color(COLORS["navy"])


def label_bars(axis: plt.Axes, bars, fmt: str = "{:,.0f}") -> None:
    labels = [fmt.format(bar.get_height()) for bar in bars]
    axis.bar_label(bars, labels=labels, padding=3, fontsize=8)


def plot_trace_profile(real: pd.DataFrame, output: Path) -> None:
    step = max(1, len(real) // 1800)
    view = real.iloc[::step]
    figure, axes = plt.subplots(2, 2, figsize=(13, 7.6))
    time_specs = [
        ("power_w", "A. Daya legacy", "Daya (W)", COLORS["orange"]),
        ("voltage_v", "B. Tegangan", "Tegangan (V)", COLORS["blue"]),
        ("current_a", "C. Arus", "Arus (A)", COLORS["green"]),
    ]
    for axis, (column, title, ylabel, color) in zip(
        axes.flat[:3], time_specs
    ):
        series = real[column].dropna()
        upper = max(series.quantile(0.995) * 1.08, series.quantile(0.95))
        locator = mdates.AutoDateLocator(minticks=4, maxticks=7)
        axis.plot(view["timestamp"], view[column], color=color, linewidth=0.9)
        axis.set_title(title, loc="left")
        axis.set_ylabel(ylabel)
        axis.set_ylim(bottom=0, top=upper)
        axis.xaxis.set_major_locator(locator)
        axis.xaxis.set_major_formatter(
            mdates.ConciseDateFormatter(locator)
        )
        style_axis(axis)

    power = real["power_w"].dropna()
    power_limit = power.quantile(0.995)
    axes[1, 1].hist(
        power[power <= power_limit],
        bins=40,
        color=COLORS["orange"],
        alpha=0.9,
        edgecolor="white",
        linewidth=0.35,
    )
    axes[1, 1].set_title(
        "D. Distribusi daya pada rentang utama", loc="left"
    )
    axes[1, 1].set_xlabel("Daya legacy (W)")
    axes[1, 1].set_ylabel("Jumlah observasi")
    style_axis(axes[1, 1])
    figure.suptitle(
        f"Profil Trace Historis Asli ({len(real):,} observasi)",
        y=0.985,
    )
    figure.tight_layout(rect=(0, 0, 1, 0.95), h_pad=2.0, w_pad=1.8)
    save(figure, output)


def plot_replay_provenance(
    replay_sample: pd.DataFrame, replay_audit: dict, output: Path
) -> None:
    counts = replay_sample.groupby("replay_block_id").size()
    figure, axes = plt.subplots(1, 2, figsize=(13, 5.3))
    bars = axes[0].bar(
        counts.index.astype(int),
        counts.values,
        color=COLORS["blue"],
        width=0.75,
    )
    label_bars(axes[0], bars)
    axes[0].set_xlabel("ID blok replay")
    axes[0].set_ylabel("Jumlah sampel")
    axes[0].set_title("A. Cakupan sampel per blok", loc="left")
    axes[0].set_xticks(counts.index.astype(int)[::2])
    axes[0].set_ylim(0, counts.max() * 1.18)
    style_axis(axes[0])

    axes[1].scatter(
        replay_sample["replay_block_id"],
        replay_sample["source_row_index"],
        s=8,
        alpha=0.35,
        color=COLORS["violet"],
        edgecolors="none",
    )
    axes[1].set_xlabel("ID blok replay")
    axes[1].set_ylabel("Indeks posisi pada workbook rujukan")
    axes[1].set_title("B. Ancestry posisional sampel", loc="left")
    axes[1].set_xticks(counts.index.astype(int)[::2])
    style_axis(axes[1], grid_axis="both")
    blocks = replay_audit["provenance"]["inferred_replay_blocks"]
    reference_rows = replay_audit["provenance"]["reference_rows"]
    figure.suptitle(
        f"Cakupan Sampel Replay Turunan — "
        f"{blocks:.0f} blok identik × {reference_rows:,} posisi",
        y=0.98,
    )
    figure.tight_layout(rect=(0, 0, 1, 0.92), w_pad=2.4)
    save(figure, output)


def plot_monitoring_checks(
    replay_sample: pd.DataFrame, benchmark: dict, output: Path
) -> None:
    reason_counts = benchmark["routing"]["reason_counts"]
    reason_labels = {
        "normal_local_monitoring": "Normal → edge",
        "current_below_legacy_threshold": "Arus <0,1 A → cloud",
        "power_above_trace_p99": "Daya >P99 → cloud",
        "invalid_electrical_reading": "Listrik invalid → cloud",
        "missing_or_nonfinite_value": "Nilai hilang → cloud",
    }
    labels = [reason_labels.get(key, key) for key in reason_counts]
    values = list(reason_counts.values())
    colors = [
        COLORS["green"] if "edge" in label else COLORS["orange"]
        for label in labels
    ]
    figure, axes = plt.subplots(2, 2, figsize=(13.5, 8.2))
    bars = axes[0, 0].barh(labels, values, color=colors, height=0.58)
    total = sum(values)
    axes[0, 0].bar_label(
        bars,
        labels=[
            f"{value:,} ({value / total:.1%})" for value in values
        ],
        padding=5,
        fontsize=9,
    )
    axes[0, 0].set_xlabel("Jumlah pesan")
    axes[0, 0].set_title("A. Keputusan routing", loc="left")
    axes[0, 0].set_xlim(0, max(values) * 1.22)
    axes[0, 0].invert_yaxis()
    style_axis(axes[0, 0], grid_axis="x")

    errors = np.sort(
        replay_sample["power_consistency_error_w"].dropna().to_numpy()
    )
    cumulative = np.arange(1, len(errors) + 1) / len(errors) * 100
    axes[0, 1].step(
        errors,
        cumulative,
        where="post",
        color=COLORS["cyan"],
        linewidth=2.2,
    )
    p50 = float(np.quantile(errors, 0.50))
    p95 = float(np.quantile(errors, 0.95))
    axes[0, 1].axvline(
        p50,
        color=COLORS["slate"],
        linestyle="--",
        linewidth=1.2,
        label=f"P50 {p50:.2f} W",
    )
    axes[0, 1].axvline(
        p95,
        color=COLORS["red"],
        linestyle="--",
        linewidth=1.2,
        label=f"P95 {p95:.2f} W",
    )
    axes[0, 1].set_xlabel("|Daya legacy − V×I hasil hitung ulang| (W)")
    axes[0, 1].set_ylabel("Persentase kumulatif (%)")
    axes[0, 1].set_title(
        "B. Konsistensi daya legacy terhadap V×I", loc="left"
    )
    axes[0, 1].set_ylim(0, 102)
    axes[0, 1].legend(loc="lower right")
    style_axis(axes[0, 1], grid_axis="both")

    occupancy_counts = (
        replay_sample["occupancy_status"]
        .value_counts()
        .reindex(["occupied", "unoccupied"], fill_value=0)
    )
    occupancy_bars = axes[1, 0].bar(
        ["Terisi", "Kosong"],
        occupancy_counts.values,
        color=[COLORS["violet"], COLORS["slate"]],
        width=0.55,
    )
    label_bars(axes[1, 0], occupancy_bars)
    axes[1, 0].set_ylabel("Jumlah pesan")
    axes[1, 0].set_title("C. Status okupansi pada sampel", loc="left")
    axes[1, 0].set_ylim(
        0, max(float(occupancy_counts.max()) * 1.18, 1)
    )
    style_axis(axes[1, 0])

    cycle = (
        replay_sample.loc[replay_sample["replay_block_id"].eq(0)]
        .sort_values("source_row_index")
    )
    axes[1, 1].plot(
        cycle["source_row_index"],
        cycle["energy_cumulative_legacy_wh"],
        color=COLORS["blue"],
        linewidth=2.2,
    )
    axes[1, 1].fill_between(
        cycle["source_row_index"],
        cycle["energy_cumulative_legacy_wh"],
        0,
        color=COLORS["cyan"],
        alpha=0.18,
    )
    axes[1, 1].set_xlabel("Indeks posisi trace sumber")
    axes[1, 1].set_ylabel("Energi legacy kumulatif (Wh)")
    axes[1, 1].set_title(
        "D. Energi kumulatif pada payload replay", loc="left"
    )
    style_axis(axes[1, 1], grid_axis="both")
    figure.suptitle(
        f"Pemeriksaan Monitoring Energi–Okupansi pada Replay "
        f"({len(replay_sample):,} pesan)",
        y=0.985,
    )
    figure.tight_layout(
        rect=(0, 0, 1, 0.95), h_pad=2.4, w_pad=2.4
    )
    save(figure, output)


def plot_latency(benchmark: dict, output: Path) -> None:
    percentile_keys = ["p50_ms", "p95_ms", "p99_ms"]
    percentile_labels = ["P50", "P95", "P99"]
    monitoring = [
        benchmark["actual_local_monitoring"][key]
        for key in percentile_keys
    ]
    serialization = [
        benchmark["actual_json_serialization"][key]
        for key in percentile_keys
    ]
    edge_path = [
        benchmark["actual_edge_path"][key] for key in percentile_keys
    ]
    cloud_route = [
        benchmark["configured_cloud_route_end_to_end"][key]
        for key in percentile_keys
    ]
    overall = benchmark["configured_end_to_end"]
    cloud_only = benchmark["configured_cloud_only_baseline"]
    routing = benchmark["routing"]
    x = np.arange(3)
    figure, axes = plt.subplots(2, 2, figsize=(13.5, 8.2))

    local_series = [
        ("Pemantauan lokal", monitoring, COLORS["green"], "o"),
        ("Serialisasi JSON", serialization, COLORS["blue"], "s"),
        ("Jalur edge", edge_path, COLORS["violet"], "^"),
    ]
    for label, values, color, marker in local_series:
        axes[0, 0].plot(
            x,
            values,
            color=color,
            marker=marker,
            linewidth=2.0,
            markersize=6,
            label=label,
        )
        axes[0, 0].annotate(
            f"{values[-1]:.3f}",
            xy=(x[-1], values[-1]),
            xytext=(7, 0),
            textcoords="offset points",
            va="center",
            fontsize=8,
            color=color,
        )
    axes[0, 0].set_yscale("log")
    axes[0, 0].set_xticks(x, percentile_labels)
    axes[0, 0].set_ylabel("Latensi (ms, skala log)")
    axes[0, 0].set_title(
        "A. Profil persentil komponen lokal", loc="left"
    )
    axes[0, 0].legend(loc="upper left", fontsize=8)
    axes[0, 0].set_xlim(-0.12, 2.2)
    style_axis(axes[0, 0], grid_axis="both")

    route_width = 0.34
    edge_route_bars = axes[0, 1].bar(
        x - route_width / 2,
        edge_path,
        route_width,
        label="Host lokal (diukur)",
        color=COLORS["violet"],
    )
    cloud_route_bars = axes[0, 1].bar(
        x + route_width / 2,
        cloud_route,
        route_width,
        label="Lokal + profil jaringan",
        color=COLORS["orange"],
    )
    axes[0, 1].set_yscale("log")
    axes[0, 1].set_xticks(x, percentile_labels)
    axes[0, 1].set_ylabel("Latensi ujung-ke-ujung (ms, skala log)")
    axes[0, 1].set_title(
        "B. Dampak profil jaringan pada rute",
        loc="left",
        pad=34,
    )
    axes[0, 1].legend(
        loc="lower center",
        bbox_to_anchor=(0.5, 1.005),
        ncol=2,
        fontsize=8,
        columnspacing=1.4,
        handletextpad=0.6,
    )
    style_axis(axes[0, 1])
    for bars in (edge_route_bars, cloud_route_bars):
        axes[0, 1].bar_label(
            bars,
            labels=[f"{bar.get_height():.3g}" for bar in bars],
            padding=4,
            fontsize=8,
        )

    route_values = [routing["edge_count"], routing["cloud_count"]]
    route_total = sum(route_values)
    wedges, _, percentage_texts = axes[1, 0].pie(
        route_values,
        colors=[COLORS["green"], COLORS["orange"]],
        startangle=90,
        counterclock=False,
        explode=(0, 0.08),
        autopct=lambda percent: f"{percent:.1f}%",
        pctdistance=0.72,
        wedgeprops={"edgecolor": "white", "linewidth": 1.5},
        textprops={"fontsize": 10, "weight": "semibold"},
    )
    percentage_texts[0].set_color("white")
    percentage_texts[1].set_color(COLORS["navy"])
    axes[1, 0].set_title("C. Distribusi keputusan routing", loc="left")
    axes[1, 0].legend(
        wedges,
        [
            f"Edge — {route_values[0]:,} pesan",
            f"Cloud — {route_values[1]:,} pesan",
        ],
        loc="lower center",
        bbox_to_anchor=(0.5, -0.08),
        ncol=2,
        fontsize=9,
    )

    overall_values = np.array(
        [overall[key] for key in percentile_keys]
    )
    cloud_only_values = np.array(
        [cloud_only[key] for key in percentile_keys]
    )
    axes[1, 1].plot(
        x,
        overall_values,
        color=COLORS["green"],
        marker="o",
        linewidth=2.5,
        markersize=7,
        label="Edge–cloud selektif",
    )
    axes[1, 1].plot(
        x,
        cloud_only_values,
        color=COLORS["orange"],
        marker="s",
        linewidth=2.5,
        markersize=7,
        label="Baseline cloud-only",
    )
    axes[1, 1].set_xticks(x, percentile_labels)
    axes[1, 1].set_ylabel("Latensi ujung-ke-ujung (ms)")
    axes[1, 1].set_ylim(
        0, max(overall_values.max(), cloud_only_values.max()) * 1.18
    )
    axes[1, 1].set_title(
        "D. Edge–cloud vs baseline cloud-only", loc="left"
    )
    axes[1, 1].legend(loc="upper left", fontsize=8)
    style_axis(axes[1, 1], grid_axis="both")
    figure.suptitle(
        "Ringkasan Latensi dan Routing Edge–Cloud",
        y=0.985,
    )
    figure.tight_layout(rect=(0, 0, 1, 0.95), h_pad=2.3, w_pad=2.3)
    save(figure, output)


def plot_multiscale_contract(config: dict, output: Path) -> None:
    """Show how one replay payload is linked across the three visual scales."""
    figure, axis = plt.subplots(figsize=(13.5, 5.4))
    axis.set_xlim(0, 13.5)
    axis.set_ylim(0, 5.4)
    axis.axis("off")
    boxes = [
        (
            0.1,
            "ESP32\nakuisisi sensor",
            COLORS["slate"],
        ),
        (
            2.75,
            "Raspberry Pi\ngateway · okupansi",
            COLORS["green"],
        ),
        (
            5.4,
            "Edge\nvalidasi · routing",
            COLORS["orange"],
        ),
        (
            8.05,
            "Cloud selektif\nprofil terkonfigurasi",
            COLORS["blue"],
        ),
        (
            10.7,
            "API replay\nenergi · okupansi",
            COLORS["violet"],
        ),
    ]
    for x, label, color in boxes:
        axis.add_patch(
            plt.Rectangle(
                (x, 3.35),
                2.25,
                1.15,
                facecolor=color,
                edgecolor="none",
                alpha=0.92,
            )
        )
        axis.text(
            x + 1.125,
            3.92,
            label,
            ha="center",
            va="center",
            color="white",
            fontsize=10,
            weight="semibold",
        )
    for x in [2.35, 5.0, 7.65, 10.3]:
        axis.annotate(
            "",
            xy=(x + 0.35, 3.92),
            xytext=(x, 3.92),
            arrowprops={
                "arrowstyle": "->",
                "color": COLORS["navy"],
                "lw": 1.8,
            },
        )
    hub_x, hub_y = 11.825, 2.72
    axis.annotate(
        "",
        xy=(hub_x, hub_y),
        xytext=(hub_x, 3.33),
        arrowprops={
            "arrowstyle": "->",
            "color": COLORS["navy"],
            "lw": 1.8,
        },
    )
    axis.scatter(
        [hub_x],
        [hub_y],
        s=34,
        color=COLORS["navy"],
        zorder=4,
    )
    view_specs = [
        (6.25, "LoD-A · Tapak", "EPSG:4326", COLORS["cyan"]),
        (8.45, "LoD-B · Bangunan", "energi + rute", COLORS["violet"]),
        (10.65, "LoD-C · Indoor 3D", "okupansi + sensor", COLORS["green"]),
    ]
    for x, title, detail, color in view_specs:
        axis.add_patch(
            plt.Rectangle(
                (x, 0.75),
                1.75,
                1.35,
                facecolor="white",
                edgecolor=color,
                linewidth=2.2,
            )
        )
        axis.text(
            x + 0.875,
            1.55,
            title,
            ha="center",
            va="center",
            color=COLORS["navy"],
            fontsize=10,
            weight="semibold",
        )
        axis.text(
            x + 0.875,
            1.15,
            detail,
            ha="center",
            va="center",
            color=COLORS["slate"],
            fontsize=8.5,
        )
        axis.annotate(
            "",
            xy=(x + 0.875, 2.18),
            xytext=(hub_x, hub_y - 0.04),
            arrowprops={
                "arrowstyle": "->",
                "color": color,
                "lw": 1.4,
            },
        )
    coordinate = config["digital_twin"]["geospatial_reference"]
    axis.text(
        0.45,
        2.05,
        "Kontrak evaluasi",
        fontsize=12,
        weight="semibold",
        color=COLORS["navy"],
    )
    axis.text(
        0.45,
        1.72,
        "• trace historis 92.160 observasi dari arsitektur ESP32–Raspberry Pi\n"
        "• satu payload dan provenance yang sama pada tiga skala\n"
        "• hirarki LoD aplikatif dengan perpindahan tampilan manual\n"
        "• koordinat legacy "
        f"{coordinate['latitude']:.4f}, {coordinate['longitude']:.4f}",
        fontsize=9.5,
        color=COLORS["slate"],
        linespacing=1.45,
        va="top",
    )
    figure.suptitle(
        "Pemetaan Arsitektur dan Visualisasi Digital Twin Multiskala",
        y=0.98,
    )
    figure.tight_layout(rect=(0, 0, 1, 0.94))
    save(figure, output)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--real",
        type=Path,
        default=Path(
            "Data/sensor_data_export_2026-05-17_to_2026-05-23.xlsx"
        ),
    )
    parser.add_argument("--outputs", type=Path, default=Path("outputs"))
    parser.add_argument(
        "--config", type=Path, default=Path("configs/experiment.json")
    )
    parser.add_argument(
        "--figures", type=Path, default=Path("outputs/figures")
    )
    args = parser.parse_args()
    args.figures.mkdir(parents=True, exist_ok=True)

    real = load_trace(args.real)
    replay_sample = pd.read_csv(
        args.outputs / "historical_replay_sample.csv"
    )
    replay_audit = json.loads(
        (args.outputs / "historical_replay_audit.json").read_text()
    )
    benchmark_report = json.loads(
        (args.outputs / "benchmark_metrics.json").read_text()
    )
    config = json.loads(args.config.read_text(encoding="utf-8"))
    plot_trace_profile(real, args.figures / "01_trace_profile.png")
    plot_replay_provenance(
        replay_sample,
        replay_audit,
        args.figures / "02_replay_provenance.png",
    )
    plot_monitoring_checks(
        replay_sample,
        benchmark_report,
        args.figures / "03_monitoring_checks.png",
    )
    plot_latency(
        benchmark_report,
        args.figures / "04_latency_characteristics.png",
    )
    plot_multiscale_contract(
        config,
        args.figures / "05_multiscale_digital_twin.png",
    )
    print(f"Lima visual hasil tersimpan di {args.figures}")


if __name__ == "__main__":
    main()
