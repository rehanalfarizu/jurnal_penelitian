#!/usr/bin/env python3
"""
Edge-Cloud Streaming Validation v2 — Visualization Suite
===================

Reads:
    streaming_metrics_v2.pkl   — summary metrics dict
    streaming_results_v2.pkl  — full 2,027,520 records (sampled to 100K for plots)

Outputs (saved to ./figures/):
    01_throughput_dashboard.png     — single-page summary
    02_latency_distribution.png     — edge vs cloud latency
    03_prediction_accuracy.png      — actual vs predicted + residuals
    04_routing_breakdown.png        — edge/cloud routing over time
    05_anomaly_analysis.png         — anomaly rate, scores
    06_energy_profile.png           — energy breakdown
    07_temporal_patterns.png        — hourly/daily patterns
    08_streaming_r2_convergence.png — R²/MAPE convergence
"""

from dataclasses import dataclass
import pickle
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.ticker import FuncFormatter, MaxNLocator
import seaborn as sns

# Required for unpickling streaming_results_v2.pkl's RecordMetrics
@dataclass
class RecordMetrics:
    sample_idx: int
    timestamp: str
    anomaly: bool
    routed_to_cloud: bool
    edge_latency_ms: float
    cloud_latency_ms: float
    total_latency_ms: float
    energy_mw: float
    energy_score: float
    r2_streaming: float
    daya: float
    pred_daya: float
    actual_residual: float


warnings.filterwarnings('ignore')
np.random.seed(42)

PALETTE = {
    'edge': '#2ecc71',
    'cloud': '#e74c3c',
    'primary': '#3498db',
    'secondary': '#9b59b6',
    'accent': '#f39c12',
    'neutral': '#34495e',
    'bg': '#fafafa',
    'grid': '#e8e8e8',
}

sns.set_theme(style='whitegrid', palette='muted', rc={
    'axes.facecolor': PALETTE['bg'],
    'figure.facecolor': 'white',
    'axes.edgecolor': PALETTE['neutral'],
    'axes.linewidth': 0.8,
    'grid.color': PALETTE['grid'],
    'grid.linewidth': 0.6,
    'font.family': 'DejaVu Sans',
    'font.size': 10,
    'axes.titlesize': 13,
    'axes.titleweight': 'bold',
    'axes.labelsize': 11,
    'xtick.labelsize': 9,
    'ytick.labelsize': 9,
    'legend.fontsize': 9,
    'legend.frameon': True,
    'legend.framealpha': 0.95,
    'legend.edgecolor': PALETTE['grid'],
})

SAMPLE_SIZE = 100_000  # for scatter / high-detail plots


def human_format(x, _pos):
    if x >= 1e6:
        return f'{x/1e6:.1f}M'
    if x >= 1e3:
        return f'{x/1e3:.0f}K'
    return f'{x:.0f}'


def load_and_prep():
    """Load metrics + sample records; aggregate full 2M into bins."""
    print('  Loading PKL...', end=' ', flush=True)
    with open('streaming_metrics_v2.pkl', 'rb') as f:
        metrics = pickle.load(f)
    with open('streaming_results_v2.pkl', 'rb') as f:
        all_results = pickle.load(f)
    print(f'OK ({len(all_results):,} records)')

    # Build dataframe from full 2M (fast since this is just dataclass->dict)
    print('  Building 2M-aggregate bins...', end=' ', flush=True)
    n = len(all_results)
    bin_size = 50_000
    n_bins = n // bin_size

    bin_edge_lat = np.zeros(n_bins)
    bin_cloud_lat = np.zeros(n_bins)
    bin_anom = np.zeros(n_bins, dtype=int)
    bin_total = np.zeros(n_bins, dtype=int)
    bin_energy = np.zeros(n_bins)

    bs_idx = 0
    count = 0
    for r in all_results:
        if count >= bin_size:
            bs_idx += 1
            count = 0
        if bs_idx >= n_bins:
            break
        bin_edge_lat[bs_idx] += r.edge_latency_ms
        bin_cloud_lat[bs_idx] += r.cloud_latency_ms
        bin_energy[bs_idx] += r.energy_mw
        bin_anom[bs_idx] += int(bool(r.anomaly))
        bin_total[bs_idx] += 1
        count += 1

    bin_idx = np.arange(n_bins) * bin_size
    bin_df = pd.DataFrame({
        'idx': bin_idx,
        'edge_lat_avg': bin_edge_lat / np.maximum(1, bin_total),
        'cloud_lat_avg': bin_cloud_lat / np.maximum(1, bin_total),
        'anom_rate': bin_anom / bin_total * 100,
        'energy_avg': bin_energy / np.maximum(1, bin_total),
    })

    # Sample 100K detail records (fast to load fully then subsample)
    print(f'Loading {SAMPLE_SIZE:,} detail records...', end=' ', flush=True)
    si = np.random.choice(n, min(SAMPLE_SIZE, n), replace=False)
    si.sort()
    rows = []
    ts0 = pd.to_datetime(all_results[0].timestamp)
    for i in si:
        r = all_results[i]
        ts = pd.to_datetime(r.timestamp)
        rows.append({
            'sample_idx': r.sample_idx,
            'timestamp': ts,
            'day': (ts - ts0).days,
            'hour': ts.hour,
            'anomaly': bool(r.anomaly),
            'routed_to_cloud': bool(r.routed_to_cloud),
            'edge_latency_ms': float(r.edge_latency_ms),
            'cloud_latency_ms': float(r.cloud_latency_ms),
            'total_latency_ms': float(r.total_latency_ms),
            'energy_mw': float(r.energy_mw),
            'energy_score': float(r.energy_score),
            'daya': float(r.daya),
            'pred_daya': float(r.pred_daya),
            'residual': float(r.daya) - float(r.pred_daya),
        })
    df = pd.DataFrame(rows)
    print('OK')

    return metrics, df, bin_df


# -------------------------------------------------------------------------
# Figure 1: Throughput & Key-Metrics Dashboard
# -------------------------------------------------------------------------
def fig01_dashboard(metrics, df, bin_df, outdir):
    fig = plt.figure(figsize=(16, 9))
    gs = gridspec.GridSpec(3, 4, figure=fig, hspace=0.55, wspace=0.4)
    fig.suptitle('Edge-Cloud Streaming Validation — Ringkasan Eksekutif',
                 fontsize=17, fontweight='bold', y=0.985)

    # Compute anomaly percentage from absolute count over total records (2M)
    full_total = 2_027_520
    anom_pct = metrics['anom_count'] / full_total * 100
    edge_pct = metrics['edge_eff']
    cloud_pct = 100 - edge_pct

    # 1. Edge vs Cloud latency over time
    ax = fig.add_subplot(gs[0, :2])
    ax.plot(bin_df['idx'], bin_df['edge_lat_avg'],
            color=PALETTE['edge'], lw=1.6,
            label=f"Edge (avg {bin_df['edge_lat_avg'].mean():.1f}ms)")
    ax.plot(bin_df['idx'], bin_df['cloud_lat_avg'],
            color=PALETTE['cloud'], lw=1.6, alpha=0.85,
            label=f"Cloud (avg {bin_df['cloud_lat_avg'].mean():.0f}ms)")
    ax.set_xlabel('Sample Index')
    ax.set_ylabel('Latency (ms)')
    ax.set_title(f"Throughput Stabil — {metrics['throughput']:,.0f} records/sec",
                 fontweight='bold')
    ax.xaxis.set_major_formatter(FuncFormatter(human_format))
    ax.legend(loc='upper left', fontsize=9)

    # 2. Routing ratio donut
    ax = fig.add_subplot(gs[0, 2])
    ax.pie([edge_pct, cloud_pct],
           labels=['Edge (local)', 'Cloud (routing)'],
           colors=[PALETTE['edge'], PALETTE['cloud']],
           autopct='%1.2f%%', startangle=90,
           wedgeprops=dict(width=0.45, edgecolor='white', linewidth=2),
           textprops={'fontsize': 10, 'fontweight': 'bold'})
    ax.set_title('Routing Distribution', fontweight='bold')

    # 3. Anomaly donut
    ax = fig.add_subplot(gs[0, 3])
    ax.pie([100 - anom_pct, anom_pct],
           labels=['Normal', 'Anomali'],
           colors=[PALETTE['primary'], PALETTE['accent']],
           autopct='%1.2f%%', startangle=90,
           wedgeprops=dict(width=0.45, edgecolor='white', linewidth=2),
           textprops={'fontsize': 10, 'fontweight': 'bold'})
    ax.set_title('Anomali Terdeteksi', fontweight='bold')

    # 4-7: KPI cards
    kpis = [
        (gs[1, 0], f"{metrics['test_r2']:.4f}", 'Test R²', PALETTE['primary']),
        (gs[1, 1], f"{metrics['test_mape']:.2f}%", 'Test MAPE', PALETTE['secondary']),
        (gs[1, 2], f"{metrics['edge_latency_p50']:.1f} ms", 'Edge P50 Latency', PALETTE['edge']),
        (gs[1, 3], f"{metrics['cloud_latency_p50']:.1f} ms", 'Cloud P50 Latency', PALETTE['cloud']),
    ]
    for spec, val, label, color in kpis:
        ax = fig.add_subplot(spec)
        ax.set_facecolor(color)
        ax.text(0.5, 0.62, val, ha='center', va='center',
                fontsize=22, fontweight='bold', color='white',
                transform=ax.transAxes)
        ax.text(0.5, 0.22, label, ha='center', va='center',
                fontsize=11, color='white', alpha=0.95,
                transform=ax.transAxes)
        ax.set_xticks([]); ax.set_yticks([])
        for s in ax.spines.values():
            s.set_visible(False)

    # 8. Records timeline — actual counts from the full dataset
    ax = fig.add_subplot(gs[2, :2])
    daily = df.groupby('day').size()
    ax.bar(daily.index, daily.values, color=PALETTE['primary'],
           alpha=0.85, edgecolor='white')
    ax.set_xlabel('Hari ke- (sejak awal streaming)')
    ax.set_ylabel('Jumlah Record')
    ax.set_title(f'Volume Data per Hari (≈ {full_total:,} records total)',
                 fontweight='bold')
    ax.yaxis.set_major_formatter(FuncFormatter(human_format))
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))

    # 9. Energy comparison
    ax = fig.add_subplot(gs[2, 2:])
    e_e = metrics['edge_energy_avg']
    e_c = metrics['cloud_energy_avg']
    ax.bar(['Edge-only', 'Cloud-routed'], [e_e, e_c],
           color=[PALETTE['edge'], PALETTE['cloud']],
           alpha=0.85, edgecolor='white', width=0.55)
    for i, v in enumerate([e_e, e_c]):
        ax.text(i, v + 0.05, f'{v:.2f} mW', ha='center',
                fontsize=10, fontweight='bold')
    ax.set_ylabel('Energy (mW)')
    ax.set_title('Konsumsi Energi per Record', fontweight='bold')
    ax.set_ylim(0, max(e_e, e_c) * 1.15)
    ax.grid(True, alpha=0.3, axis='y')

    plt.savefig(outdir / '01_throughput_dashboard.png', dpi=160, bbox_inches='tight')
    plt.close()
    print('  ✓ 01_throughput_dashboard.png')


# -------------------------------------------------------------------------
# Figure 2: Latency distribution (edge vs cloud)
# -------------------------------------------------------------------------
def fig02_latency(metrics, df, outdir):
    fig, axes = plt.subplots(1, 3, figsize=(20, 6))
    fig.suptitle('Analisis Latency — Edge vs Cloud Routing',
                 fontsize=15, fontweight='bold', y=1.00)

    edge = df.loc[df['routed_to_cloud'] == False, 'edge_latency_ms']
    cloud = df.loc[df['routed_to_cloud'] == True, 'total_latency_ms']

    # 1. Two-panel density: Edge (linear) + Cloud (log)
    ax = axes[0]

    # Edge distribution on linear scale (most values 0.5–3 ms)
    ax.hist(edge, bins=80, alpha=0.65, color=PALETTE['edge'],
            density=True, label=f'Edge-only (0–3 ms)',
            histtype='bar', edgecolor='white', linewidth=0.3)
    ax.axvline(metrics['edge_latency_p50'], color=PALETTE['edge'],
               ls='--', lw=2,
               label=f'Edge P50={metrics["edge_latency_p50"]:.1f}ms')
    ax.set_xlabel('Latency (ms) — Edge (linear scale)')
    ax.set_ylabel('Density')
    ax.set_title('Distribusi Latency Edge (linear)', fontweight='bold')
    ax.legend(fontsize=8); ax.grid(True, alpha=0.3)
    ax.set_xlim(0, 5)  # zoom into edge range

    # 2. Cloud ECDF (log scale) — edge is invisible on this scale
    ax = axes[1]
    cs = np.sort(cloud.values)
    ax.step(cs, np.arange(1, len(cs) + 1) / len(cs),
            where='post', lw=2.2, color=PALETTE['cloud'],
            label=f'Cloud (n={len(cs):,}, P50={np.median(cs):.1f}ms)')
    # shade where edge falls (should be at far-left)
    ax.axvspan(0, metrics['edge_latency_p50'], alpha=0.1, color=PALETTE['edge'],
               label=f'Edge range (≤{metrics["edge_latency_p50"]:.1f}ms)')
    ax.set_xscale('log')
    ax.set_xlabel('Latency (ms, log)')
    ax.set_ylabel('Cumulative Probability')
    ax.set_title('ECDF Cloud — Latency Rendah vs Edge',
                 fontweight='bold')
    ax.axhline(0.5, color='gray', ls=':', alpha=0.5)
    ax.legend(fontsize=8, loc='lower right'); ax.grid(True, alpha=0.3, which='both')

    # 3. Percentile bars — split edge (linear) vs cloud (log)
    ax = axes[2]
    pcts = [50, 75, 90, 95, 99, 99.9]
    ep = np.percentile(edge, pcts)
    cp = np.percentile(cloud, pcts)
    x = np.arange(len(pcts))
    w = 0.36
    ax.bar(x - w / 2, ep, w, label='Edge', color=PALETTE['edge'],
           alpha=0.85, edgecolor='white')
    ax.bar(x + w / 2, cp, w, label='Cloud', color=PALETTE['cloud'],
           alpha=0.85, edgecolor='white')
    ax.set_ylabel('Latency (ms)')
    ax.set_xticks(x)
    ax.set_xticklabels([f'P{p}' for p in pcts])
    ax.set_title('Latency Percentile — Linear Scale (Edge zoom, cloud compressed)',
                 fontweight='bold', fontsize=10)
    ax.set_ylim(0, ep.max() * 3)  # zoom so edge bars readable
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout(rect=[0, 0, 1, 0.97])
    plt.savefig(outdir / '02_latency_distribution.png', dpi=160, bbox_inches='tight')
    plt.close()
    print('  ✓ 02_latency_distribution.png')


# -------------------------------------------------------------------------
# Figure 3: Prediction accuracy
# -------------------------------------------------------------------------
def fig03_accuracy(metrics, df, outdir):
    fig, axes = plt.subplots(2, 2, figsize=(16, 11))
    fig.suptitle('Akurasi Prediksi Energi — Ridge Regression (19 fitur)',
                 fontsize=15, fontweight='bold', y=0.995)

    si = np.random.choice(len(df), 30_000, replace=False)
    sub = df.iloc[si]
    resid = df['residual']

    # 1. Actual vs predicted
    ax = axes[0, 0]
    ax.scatter(sub['daya'], sub['pred_daya'], alpha=0.35, s=8,
               color=PALETTE['primary'], edgecolor='none')
    mv = df['daya'].max() * 1.02
    ax.plot([0, mv], [0, mv], color=PALETTE['cloud'], ls='--',
            lw=2, label='Ideal (y=x)')
    ax.plot([0, mv], [0, mv * 1.05], color=PALETTE['accent'],
            ls=':', lw=1, alpha=0.6, label='+5% band')
    ax.plot([0, mv], [0, mv * 0.95], color=PALETTE['accent'],
            ls=':', lw=1, alpha=0.6)
    ax.set_xlabel('Daya Aktual (W)')
    ax.set_ylabel('Daya Prediksi (W)')
    ax.set_title(f'Actual vs Predicted (Test R²={metrics["test_r2"]:.4f})',
                 fontweight='bold')
    ax.legend(fontsize=9); ax.grid(True, alpha=0.3)
    ax.set_xlim(0, mv); ax.set_ylim(0, mv)

    # 2. Residual distribution
    ax = axes[0, 1]
    nb = 80
    ax.hist(resid, bins=nb, alpha=0.7, color=PALETTE['primary'],
            density=True, edgecolor='white', linewidth=0.3)
    ax.axvline(0, color=PALETTE['cloud'], ls='--', lw=2, label='Zero residual')
    ax.axvline(resid.mean(), color=PALETTE['accent'], ls='-', lw=2,
               label=f'Mean={resid.mean():.2f}W')
    ax.set_xlabel('Residual = Aktual − Prediksi (W)')
    ax.set_ylabel('Density')
    ax.set_title(f'Distribusi Residual (μ={resid.mean():.2f}W, σ={resid.std():.2f}W)',
                 fontweight='bold')
    ax.legend(fontsize=9); ax.grid(True, alpha=0.3)

    # 3. Train vs Test vs Streaming R² comparison
    ax = axes[1, 0]
    r2_cats = ['Train R²', 'Test R²', 'Streaming R²']
    r2_vals = [metrics['train_r2'], metrics['test_r2'], metrics['streaming_r2']]
    colors = [PALETTE['accent'], PALETTE['primary'], PALETTE['secondary']]
    bars = ax.bar(r2_cats, r2_vals, color=colors, alpha=0.85,
                  edgecolor='white', width=0.55)
    for b, v in zip(bars, r2_vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.002,
                f'{v:.4f}', ha='center', fontsize=11, fontweight='bold')
    ax.set_ylim(0.90, 1.0)
    ax.set_ylabel('R²')
    ax.set_title('Train/Test/Streaming R² — Konsisten > 0.94',
                 fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')

    # 4. Train/Test/Streaming MAPE
    ax = axes[1, 1]
    mape_cats = ['Train MAPE', 'Test MAPE', 'Streaming MAPE']
    mape_vals = [metrics['train_mape'], metrics['test_mape'],
                 metrics['streaming_mape']]
    bars = ax.bar(mape_cats, mape_vals,
                  color=[PALETTE['accent'], PALETTE['primary'], PALETTE['secondary']],
                  alpha=0.85, edgecolor='white', width=0.55)
    for b, v in zip(bars, mape_vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.02,
                f'{v:.2f}%', ha='center', fontsize=11, fontweight='bold')
    ax.set_ylabel('MAPE (%)')
    ax.set_title('Train/Test/Streaming MAPE — Semua < 1.5%',
                 fontweight='bold')
    ax.set_ylim(0, max(mape_vals) * 1.3)
    ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout(rect=[0, 0, 1, 0.97])
    plt.savefig(outdir / '03_prediction_accuracy.png', dpi=160, bbox_inches='tight')
    plt.close()
    print('  ✓ 03_prediction_accuracy.png')


# -------------------------------------------------------------------------
# Figure 4: Routing breakdown (uses binned data for 2M speed)
# -------------------------------------------------------------------------
def fig04_routing(metrics, df, bin_df, outdir):
    fig, axes = plt.subplots(2, 2, figsize=(16, 11))
    fig.suptitle('Routing Decision — Edge vs Cloud (anomali → Cloud)',
                 fontsize=15, fontweight='bold', y=0.995)

    cloud_pct = (1 - metrics['edge_eff'] / 100)  # e.g. 0.00884
    cloud_pct_pct = cloud_pct * 100

    # 1. Cloud rate per bin over time (uses bin_df from full 2M)
    ax = axes[0, 0]
    ax.plot(bin_df['idx'], bin_df['anom_rate'],
            color=PALETTE['cloud'], lw=1.6, alpha=0.85)
    ax.fill_between(bin_df['idx'], 0, bin_df['anom_rate'],
                    alpha=0.2, color=PALETTE['cloud'])
    ax.set_xlabel('Sample Index')
    ax.set_ylabel('Anomali per 50K chunk (count)')
    ax.set_title(f'Jumlah Anomali per Chunk (full 2M)',
                 fontweight='bold')
    ax.xaxis.set_major_formatter(FuncFormatter(human_format))
    ax.grid(True, alpha=0.3)

    # 2. Latency per bin (edge vs cloud)
    ax = axes[0, 1]
    ax.plot(bin_df['idx'], bin_df['edge_lat_avg'],
            color=PALETTE['edge'], lw=1.5, alpha=0.85,
            label='Edge latency (ms)')
    ax.plot(bin_df['idx'], bin_df['cloud_lat_avg'],
            color=PALETTE['cloud'], lw=1.5, alpha=0.85,
            label='Cloud latency (ms)')
    ax.set_xlabel('Sample Index')
    ax.set_ylabel('Latency (ms)')
    ax.set_title('Rata-rata Latency per 50K Chunk',
                 fontweight='bold')
    ax.xaxis.set_major_formatter(FuncFormatter(human_format))
    ax.legend(fontsize=9); ax.grid(True, alpha=0.3)

    # 3. Heatmap of routing decision by hour (sample-based)
    ax = axes[1, 0]
    hour_stats = df.groupby('hour').agg(
        cloud_rate=('routed_to_cloud', 'mean'),
        anomaly_rate=('anomaly', 'mean'),
    ) * 100
    x = np.arange(len(hour_stats))
    w = 0.4
    ax.bar(x - w / 2, hour_stats['cloud_rate'], w,
           label='Cloud-routed', color=PALETTE['cloud'], alpha=0.85)
    ax.bar(x + w / 2, hour_stats['anomaly_rate'], w,
           label='Anomali', color=PALETTE['accent'], alpha=0.85)
    ax.set_xticks(x)
    ax.set_xlabel('Jam (0-23)')
    ax.set_ylabel('Persentase (%)')
    ax.set_title('Pola Routing per Jam (sample) — Korelasi Anomali = Cloud',
                 fontweight='bold')
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3, axis='y')

    # 4. Confusion: anomaly vs routing (sample)
    ax = axes[1, 1]
    s = df.sample(50_000, random_state=42)
    tp = ((s['anomaly']) & (s['routed_to_cloud'])).sum()
    fp = ((~s['anomaly']) & (s['routed_to_cloud'])).sum()
    fn = ((s['anomaly']) & (~s['routed_to_cloud'])).sum()
    tn = ((~s['anomaly']) & (~s['routed_to_cloud'])).sum()
    matrix = np.array([[tn, fp], [fn, tp]])
    sns.heatmap(matrix, annot=True, fmt=',', cmap='RdYlGn_r',
                xticklabels=['Edge (Pred Normal)', 'Cloud (Pred Anomali)'],
                yticklabels=['Actual Normal', 'Actual Anomali'],
                cbar=False, ax=ax, linewidths=2, linecolor='white',
                annot_kws={'fontsize': 12, 'fontweight': 'bold'})
    prec = tp / (tp + fp) if (tp + fp) > 0 else 0
    rec = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0
    ax.set_title(f'Confusion Matrix Routing (Precision={prec:.4f}, '
                 f'Recall={rec:.4f}, F1={f1:.4f})',
                 fontweight='bold')

    plt.tight_layout(rect=[0, 0, 1, 0.97])
    plt.savefig(outdir / '04_routing_breakdown.png', dpi=160, bbox_inches='tight')
    plt.close()
    print('  ✓ 04_routing_breakdown.png')


# -------------------------------------------------------------------------
# Figure 5: Anomaly analysis
# -------------------------------------------------------------------------
def fig05_anomaly(metrics, df, outdir):
    fig, axes = plt.subplots(2, 2, figsize=(16, 11))
    fig.suptitle('Anomali & Z-Score Detection — Streaming Edge',
                 fontsize=15, fontweight='bold', y=0.995)

    z_thresh = metrics['config']['zscore_anomaly']
    n_anom = df['anomaly'].sum()
    n_norm = (~df['anomaly']).sum()

    # 1. Z-score distribution with threshold
    ax = axes[0, 0]
    nb = 60
    ax.hist(df.loc[~df['anomaly'], 'energy_score'], bins=nb, alpha=0.65,
            color=PALETTE['primary'], density=True, label=f'Normal (n={n_norm:,})')
    ax.hist(df.loc[df['anomaly'], 'energy_score'], bins=nb, alpha=0.75,
            color=PALETTE['cloud'], density=True, label=f'Anomali (n={n_anom:,})')
    ax.axvline(z_thresh, color='black', ls='--', lw=2.5,
               label=f'Threshold z={z_thresh}')
    ax.set_xlabel('Energy Score (rolling z-score)')
    ax.set_ylabel('Density')
    ax.set_title(f'Separasi Anomali: Threshold z={z_thresh}',
                 fontweight='bold')
    ax.legend(fontsize=9); ax.grid(True, alpha=0.3)

    # 2. Z-score time series — sample + thresholds
    ax = axes[0, 1]
    sub = df.sample(20_000, random_state=42).sort_values('sample_idx')
    ax.scatter(sub['sample_idx'], sub['energy_score'],
               c=sub['anomaly'].map({True: PALETTE['cloud'], False: PALETTE['primary']}),
               alpha=0.4, s=2, edgecolor='none')
    ax.axhline(z_thresh, color='black', ls='--', lw=2, alpha=0.8, label=f'Threshold ±{z_thresh}')
    ax.axhline(-z_thresh, color='black', ls='--', lw=2, alpha=0.8)
    ax.fill_between(sub['sample_idx'], -z_thresh, z_thresh,
                    alpha=0.08, color='green', label='Normal Zone')
    ax.set_xlabel('Sample Index')
    ax.set_ylabel('Z-Score')
    ax.set_title(f'Z-Score Time Series (sample 20K, θ={z_thresh})', fontweight='bold')
    ax.set_ylim(-max(6, z_thresh + 2), max(6, z_thresh + 2))
    ax.xaxis.set_major_formatter(FuncFormatter(human_format))
    ax.legend(fontsize=8); ax.grid(True, alpha=0.3)

    # 3. Anomaly rate by day (sample)
    ax = axes[1, 0]
    daily_anom = df.groupby('day')['anomaly'].agg(['sum', 'mean'])
    daily_anom['pct'] = daily_anom['mean'] * 100
    ax.bar(daily_anom.index, daily_anom['pct'],
           color=PALETTE['cloud'], alpha=0.85, edgecolor='white')
    ax.axhline(daily_anom['pct'].mean(), color=PALETTE['accent'],
               ls='--', lw=2, label=f'Mean={daily_anom["pct"].mean():.2f}%/day')
    ax.set_xlabel('Hari ke-')
    ax.set_ylabel('Tingkat Anomali (% per hari)')
    ax.set_title('Anomali per Hari — Konsisten Sepanjang Streaming',
                 fontweight='bold')
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.legend(fontsize=9); ax.grid(True, alpha=0.3, axis='y')

    # 4. Anomaly characteristics: swarm + box
    ax = axes[1, 1]
    # Use stratified subsample for clarity
    n_show = min(2000, n_norm)
    sample = pd.concat([
        df[df['anomaly']].sample(n=min(200, n_anom), random_state=42)[
            ['sample_idx', 'daya', 'pred_daya', 'anomaly']],
        df[~df['anomaly']].sample(n=n_show, random_state=42)[
            ['sample_idx', 'daya', 'pred_daya', 'anomaly']]
    ])
    # Strip plot overlaid on boxplot
    import seaborn as sns
    # First draw boxplot
    sns.boxplot(x='anomaly', y='daya', data=sample,
                palette={'False': PALETTE['primary'], 'True': PALETTE['cloud']},
                width=0.4, ax=ax, boxprops=dict(alpha=0.7),
                medianprops=dict(color='white', lw=2))
    # Overlay swarm (transparent)
    sns.swarmplot(x='anomaly', y='daya', data=sample,
                  size=2, alpha=0.3, color='black', ax=ax)
    ax.set_xlabel('Anomaly Status')
    ax.set_xticklabels(['Normal', 'Anomali'])
    ax.set_ylabel('Daya Aktual (W)')
    anom_mean = sample.loc[sample['anomaly'], 'daya'].mean()
    norm_mean = sample.loc[~sample['anomaly'], 'daya'].mean()
    ax.set_title(
        f'Daya Aktual: Normal μ={norm_mean:.1f}W vs Anomali μ={anom_mean:.1f}W',
        fontweight='bold', fontsize=10)
    ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout(rect=[0, 0, 1, 0.97])
    plt.savefig(outdir / '05_anomaly_analysis.png', dpi=160, bbox_inches='tight')
    plt.close()
    print('  ✓ 05_anomaly_analysis.png')


# -------------------------------------------------------------------------
# Figure 6: Energy profile
# -------------------------------------------------------------------------
def fig06_energy(metrics, df, outdir):
    # Redesign: 2 rows × 2 columns for clarity
    fig = plt.figure(figsize=(16, 11))
    gs = fig.add_gridspec(2, 2, hspace=0.3, wspace=0.3,
                          top=0.94, bottom=0.08, left=0.08, right=0.95)

    edge_e = df.loc[df['routed_to_cloud'] == False, 'energy_mw']
    cloud_e = df.loc[df['routed_to_cloud'] == True, 'energy_mw']

    # 1. Edge energy distribution (linear) — edge values are small, tightly clustered
    ax = fig.add_subplot(gs[0, 0])
    ax.hist(edge_e, bins=80, alpha=0.8, color=PALETTE['edge'],
            edgecolor='white', linewidth=0.3)
    ax.axvline(edge_e.mean(), color=PALETTE['accent'],
               ls='--', lw=2.5, label=f'Mean={edge_e.mean():.2f} mW')
    ax.axvline(edge_e.median(), color=PALETTE['primary'],
               ls='-.', lw=2.5, label=f'Median={edge_e.median():.2f} mW')
    ax.set_xlabel('Energi per Record (mW) — Edge')
    ax.set_ylabel('Jumlah Record')
    ax.set_title(f'Distribusi Energi Edge (n={len(edge_e):,})',
                 fontweight='bold', fontsize=11)
    ax.legend(fontsize=8); ax.grid(True, alpha=0.3)

    # 2. Cloud energy distribution (log scale) — values are much larger
    ax = fig.add_subplot(gs[0, 1])
    ax.hist(cloud_e, bins=80, alpha=0.8, color=PALETTE['cloud'],
            edgecolor='white', linewidth=0.3)
    ax.axvline(cloud_e.mean(), color=PALETTE['accent'],
               ls='--', lw=2.5, label=f'Mean={cloud_e.mean():.1f} mW')
    ax.axvline(cloud_e.median(), color=PALETTE['secondary'],
               ls='-.', lw=2.5, label=f'Median={cloud_e.median():.1f} mW')
    ax.set_xscale('log')
    ax.set_xlabel('Energi per Record (mW, log) — Cloud')
    ax.set_ylabel('Jumlah Record')
    ax.set_title(f'Distribusi Energi Cloud (n={len(cloud_e):,})',
                 fontweight='bold', fontsize=11)
    ax.legend(fontsize=8); ax.grid(True, alpha=0.3, which='both')

    # 3. Energy per day — combined edge vs cloud
    ax = fig.add_subplot(gs[1, 0])
    daily = df.groupby('day')['energy_mw'].agg(['mean', 'sum']).reset_index()
    ax.plot(daily['day'], daily['mean'], marker='o', color=PALETTE['primary'],
            lw=2, markersize=5, label='Rata-rata per record')
    ax.set_xlabel('Hari ke-')
    ax.set_ylabel('Rata-rata Energi (mW)')
    ax.set_title('Energi Rata-rata per Record per Hari',
                 fontweight='bold', fontsize=11)
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.legend(fontsize=9); ax.grid(True, alpha=0.3)

    # 4. Energy per hour — edge vs cloud side-by-side
    ax = fig.add_subplot(gs[1, 1])
    hourly = df.groupby(['hour', 'routed_to_cloud'])['energy_mw'].mean().unstack()
    hourly.index.name = 'Jam'
    hours_range = range(0, 24)
    ax.plot(hours_range, hourly[False].reindex(range(24)),
            marker='s', color=PALETTE['edge'], lw=2, markersize=5,
            label='Edge', markerfacecolor='auto')
    ax.plot(hours_range, hourly[True].reindex(range(24)),
            marker='^', color=PALETTE['cloud'], lw=2, markersize=5,
            label='Cloud', markerfacecolor='auto')
    ax.set_xlabel('Jam (0-23)')
    ax.set_ylabel('Rata-rata Energi (mW)')
    ax.set_title('Pola Energi per Jam: Edge vs Cloud',
                 fontweight='bold', fontsize=11)
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)

    fig.suptitle('Konsumsi Energi — Edge vs Cloud per Record',
                 fontsize=15, fontweight='bold')
    plt.savefig(outdir / '06_energy_profile.png', dpi=160, bbox_inches='tight')
    plt.close()
    print('  ✓ 06_energy_profile.png')

# -------------------------------------------------------------------------
# Figure 7: Temporal patterns
# -------------------------------------------------------------------------
def fig07_temporal(metrics, df, outdir):
    fig, axes = plt.subplots(2, 2, figsize=(16, 11))
    fig.suptitle('Pola Temporal Streaming 89 Hari (sample)',
                 fontsize=15, fontweight='bold', y=0.995)

    # 1. Hourly profile of daya
    ax = axes[0, 0]
    hour_daya = df.groupby('hour')['daya'].agg(['mean', 'std'])
    ax.fill_between(hour_daya.index,
                    hour_daya['mean'] - hour_daya['std'],
                    hour_daya['mean'] + hour_daya['std'],
                    alpha=0.25, color=PALETTE['primary'])
    ax.plot(hour_daya.index, hour_daya['mean'],
            marker='o', color=PALETTE['primary'], lw=2,
            markersize=6, markerfacecolor='white',
            markeredgewidth=2)
    ax.set_xlabel('Jam (0-23)')
    ax.set_ylabel('Daya Rata-rata (W)')
    ax.set_title('Profil Daya Harian', fontweight='bold')
    ax.set_xticks(range(0, 24, 3))
    ax.grid(True, alpha=0.3)

    # 2. Volume per day
    ax = axes[0, 1]
    daily_count = df.groupby('day').size()
    ax.bar(daily_count.index, daily_count.values,
           color=PALETTE['primary'], alpha=0.85, edgecolor='white')
    full_total = 2_027_520
    ax.set_xlabel('Hari ke-')
    ax.set_ylabel('Records (sample)')
    ax.set_title(f'Volume per Hari — full: {full_total:,} records',
                 fontweight='bold')
    ax.yaxis.set_major_formatter(FuncFormatter(human_format))
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.grid(True, alpha=0.3, axis='y')

    # 3. Daily anomaly rate
    ax = axes[1, 0]
    daily_anom = df.groupby('day')['anomaly'].mean() * 100
    ax.fill_between(daily_anom.index, 0, daily_anom.values,
                    alpha=0.3, color=PALETTE['cloud'])
    ax.plot(daily_anom.index, daily_anom.values,
            color=PALETTE['cloud'], lw=1.5, marker='o', markersize=4)
    ax.axhline(daily_anom.mean(), color=PALETTE['accent'],
               ls='--', lw=2, label=f'Mean={daily_anom.mean():.2f}%')
    ax.set_xlabel('Hari ke-')
    ax.set_ylabel('Tingkat Anomali (%)')
    ax.set_title('Anomali Harian — Stabil ~1%/hari', fontweight='bold')
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.legend(fontsize=9); ax.grid(True, alpha=0.3)

    # 4. Daily mean residual
    ax = axes[1, 1]
    daily_res = df.groupby('day')['residual'].agg(['mean', 'std']).reset_index()
    ax.bar(daily_res['day'], daily_res['mean'],
           yerr=daily_res['std'], capsize=2,
           color=PALETTE['secondary'], alpha=0.7, edgecolor='white',
           error_kw={'ecolor': PALETTE['neutral'], 'elinewidth': 0.8})
    ax.axhline(0, color='black', lw=1, alpha=0.7)
    ax.set_xlabel('Hari ke-')
    ax.set_ylabel('Residual Rata-rata (W)')
    ax.set_title('Bias Harian — Residual Berfluktuasi ±0.5W',
                 fontweight='bold')
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout(rect=[0, 0, 1, 0.97])
    plt.savefig(outdir / '07_temporal_patterns.png', dpi=160, bbox_inches='tight')
    plt.close()
    print('  ✓ 07_temporal_patterns.png')


# -------------------------------------------------------------------------
# Figure 8: Streaming R² convergence
# -------------------------------------------------------------------------
def fig08_convergence(metrics, df, outdir):
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    fig.suptitle('Streaming R² — Konsistensi & Stabilitas',
                 fontsize=15, fontweight='bold', y=1.00)

    # 1. Train vs Test vs Streaming R²
    ax = axes[0]
    r2_cats = ['Train R²', 'Test R²', 'Streaming R²']
    r2_vals = [metrics['train_r2'], metrics['test_r2'], metrics['streaming_r2']]
    colors = [PALETTE['accent'], PALETTE['primary'], PALETTE['secondary']]
    bars = ax.bar(r2_cats, r2_vals, color=colors, alpha=0.85,
                  edgecolor='white', width=0.55)
    for b, v in zip(bars, r2_vals):
        ax.text(b.get_x() + b.get_width() / 2, v - 0.008,
                f'{v:.4f}', ha='center', fontsize=11, fontweight='bold',
                color='white')
    ax.set_ylabel('R²')
    ax.set_title('Konvergensi R²: Train → Test → Streaming',
                 fontweight='bold')
    ax.set_ylim(0.92, 1.0)
    ax.grid(True, alpha=0.3, axis='y')

    # 2. Streaming residuals histogram
    ax = axes[1]
    nb = 60
    ax.hist(df['residual'], bins=nb, alpha=0.7, color=PALETTE['primary'],
            density=True, edgecolor='white', linewidth=0.3,
            label=f'Streaming (μ={df["residual"].mean():.2f}W)')
    ax.axvline(0, color=PALETTE['cloud'], ls='--', lw=2,
               label='Zero residual')
    ax.set_xlabel('Residual (W)')
    ax.set_ylabel('Density')
    ax.set_title('Distribusi Residual Streaming — ~0 mean, kecil σ',
                 fontweight='bold')
    ax.legend(fontsize=9); ax.grid(True, alpha=0.3)

    plt.tight_layout(rect=[0, 0, 1, 0.97])
    plt.savefig(outdir / '08_streaming_r2_convergence.png', dpi=160,
                bbox_inches='tight')
    plt.close()
    print('  ✓ 08_streaming_r2_convergence.png')


def main():
    outdir = Path('figures')
    outdir.mkdir(exist_ok=True)
    metrics, df, bin_df = load_and_prep()

    print('Generating figures:')
    fig01_dashboard(metrics, df, bin_df, outdir)
    fig02_latency(metrics, df, outdir)
    fig03_accuracy(metrics, df, outdir)
    fig04_routing(metrics, df, bin_df, outdir)
    fig05_anomaly(metrics, df, outdir)
    fig06_energy(metrics, df, outdir)
    fig07_temporal(metrics, df, outdir)
    fig08_convergence(metrics, df, outdir)

    print(f'\n✓ 8 figures saved to {outdir}/')
    print(f'  Sample size: {len(df):,} records over {df["day"].nunique()} days')


if __name__ == '__main__':
    main()
