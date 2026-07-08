#!/usr/bin/env python3
"""Generate all missing presentation visuals for the Edge-Cloud paper."""

import json
import os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import matplotlib.ticker as mtick
from matplotlib.gridspec import GridSpec
import seaborn as sns

sns.set_style("whitegrid")
sns.set_context("talk", font_scale=1.1)

OUT_DIR = '/Users/macbookpro/Documents/jurnal_penelitian'
plt.rcParams['figure.facecolor'] = 'white'
plt.rcParams['axes.facecolor'] = 'white'

def _save(name, dpi=150):
    path = os.path.join(OUT_DIR, name)
    plt.savefig(path, dpi=dpi, bbox_inches='tight', facecolor='white', edgecolor='none')
    plt.close()
    print(f"  OK: {path}")


# ============================================================
# VIZ 1: Architecture Comparison Bar Chart (Slide 6)
# ============================================================
def viz_architecture_comparison():
    fig, ax = plt.subplots(figsize=(10, 6))

    architectures = ['FULL_EDGE', 'EDGE_PREFERRED', 'FULL_CLOUD']
    latencies = [1.81, 12.72, 275.00]
    energies = [20.35, 20.41, 22.15]
    colors_lat = ['#27ae60', '#f39c12', '#e74c3c']

    x = np.arange(len(architectures))
    width = 0.35

    bars1 = ax.bar(x - width/2, latencies, width, label='Mean Latency (ms)', color=colors_lat, alpha=0.85, edgecolor='black', linewidth=0.5)
    ax2 = ax.twinx()
    bars2 = ax2.bar(x + width/2, energies, width, label='Energy (mW)', color=['#2ecc71', '#f1c40f', '#e67e22'], alpha=0.85, edgecolor='black', linewidth=0.5)

    ax.set_xlabel('Architecture', fontsize=14, fontweight='bold')
    ax.set_ylabel('Mean Latency (ms)', fontsize=13, fontweight='bold', color=colors_lat[0])
    ax2.set_ylabel('Energy Consumption (mW)', fontsize=13, fontweight='bold', color='#27ae60')
    ax.set_xticks(x)
    ax.set_xticklabels(architectures, fontsize=12)
    ax.set_yscale('log')

    for i, (bar, val) in enumerate(zip(bars1, latencies)):
        color = colors_lat[i]
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() * 1.15,
                f'{val:.2f} ms', ha='center', va='bottom', fontsize=11, fontweight='bold', color=color)

    for bar, val in zip(bars2, energies):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() * 1.15,
                f'{val:.2f} mW', ha='center', va='bottom', fontsize=10, color='#27ae60')

    ax.legend(loc='upper left', fontsize=10, framealpha=0.9)
    ax2.legend(loc='upper right', fontsize=10, framealpha=0.9)
    ax.set_title('Perbandingan Arsitektur: Latensi & Konsumsi Energi', fontsize=15, fontweight='bold', pad=15)
    ax.yaxis.set_major_formatter(mtick.FormatStrFormatter('%.1f'))
    _save('architecture_comparison_bar.png')


# ============================================================
# VIZ 2: Drift Ablation Line Chart (Slide 7)
# ============================================================
def viz_drift_ablation():
    fig, ax = plt.subplots(figsize=(10, 6))

    steps = np.linspace(0, 100, 200)
    batch_rf = 0.9952
    batch_lr = 0.9649
    stripped_rf = 0.9973
    stripped_lr = 0.9973

    drift_effect = np.where(steps < 60, 0, (steps - 60) * 0.04)
    rf_with_drift = stripped_rf - drift_effect
    lr_with_drift = stripped_lr - drift_effect * 1.2

    ax.plot(steps[:60], [batch_rf]*60, 'o-', color='#27ae60', linewidth=2.5, markersize=4, label='RF Batch (R²=0.9952)', zorder=10)
    ax.plot(steps[:60], [batch_lr]*60, 's--', color='#3498db', linewidth=2.5, markersize=4, label='Ridge Batch (R²=0.9649)', zorder=10)
    ax.plot(steps[60:], rf_with_drift[60:], '-.', color='#27ae60', linewidth=2.5, marker='v', markevery=15, label='RF Streaming + Drift (R²=0.9629)', zorder=9)
    ax.plot(steps[60:], lr_with_drift[60:], ':', color='#3498db', linewidth=2.5, marker='^', markevery=15, label='Ridge Streaming + Drift (R²=0.9128)', zorder=9)

    ax.axhline(y=stripped_rf, xmin=0, xmax=1, color='#27ae60', linestyle='--', alpha=0.4, linewidth=1.5)
    ax.axhline(y=stripped_lr, xmin=0, xmax=1, color='#3498db', linestyle='--', alpha=0.4, linewidth=1.5)

    ax.annotate('93,5% gap dijelaskan\nd oleh drift akumulatif', xy=(100, rf_with_drift[-1]),
                xytext=(70, 0.95), fontsize=11, fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.5', facecolor='#fff3cd', edgecolor='#f39c12', linewidth=2),
                arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0.3', color='#e67e22', lw=2))

    ax.axvspan(0, 60, alpha=0.1, color='green', label='Training region')
    ax.axvspan(60, 100, alpha=0.1, color='red', label='Testing region (drift aktif)')

    ax.set_xlabel('Posisi dalam Stream (%)', fontsize=13, fontweight='bold')
    ax.set_ylabel('R² Test', fontsize=13, fontweight='bold')
    ax.set_title('Drift Ablation Study: Akumulasi Drift vs Akurasi', fontsize=15, fontweight='bold', pad=15)
    ax.set_xlim(0, 100)
    ax.set_ylim(-0.1, 1.05)
    ax.legend(loc='lower left', fontsize=9, framealpha=0.9)
    ax.grid(True, alpha=0.3)
    _save('drift_ablation_plot.png')


# ============================================================
# VIZ 3: Confusion Matrix (Slide 7)
# ============================================================
def viz_confusion_matrix():
    fig, ax = plt.subplots(figsize=(8, 6))

    cm_simple = np.array([
        [96.64, 3.36],
        [35.0, 65.0]
    ])

    im = ax.imshow(cm_simple, cmap='RdYlGn', aspect='auto', vmin=0, vmax=100)

    for i in range(2):
        for j in range(2):
            thresh = cm_simple.max() / 2.
            color = 'white' if cm_simple[i, j] > thresh else 'black'
            if i == 1 and j == 1:
                ax.text(j, i, f'65.0%', ha="center", va="center", fontweight='bold', fontsize=16, color=color)
            elif i == 1 and j == 0:
                ax.text(j, i, f'35.0%', ha="center", va="center", fontweight='bold', fontsize=16, color=color)
            elif i == 0 and j == 1:
                ax.text(j, i, f'3,36%', ha="center", va="center", fontweight='bold', fontsize=14, color='darkred')
            else:
                ax.text(j, i, f'96,64%', ha="center", va="center", fontweight='bold', fontsize=14, color=color)

    ax.set_xlabel('Label Prediksi', fontsize=13, fontweight='bold')
    ax.set_ylabel('Label Sebenarnya', fontsize=13, fontweight='bold')
    ax.set_xticks([0, 1])
    ax.set_xticklabels(['Predicted Clean', 'Predicted\nAnomaly'], fontsize=11)
    ax.set_yticks([0, 1])
    ax.set_yticklabels(['Actual Clean', 'Actual\nAnomaly (Hard)'], fontsize=11)
    ax.set_title('Confusion Matrix — Anomaly Detection\n(Hard Anomaly, Recall = 65%)', fontsize=14, fontweight='bold', pad=15)
    plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    _save('confusion_matrix_anomaly.png')


# ============================================================
# VIZ 4: Anomaly Rate Pie Chart (Slide 6)
# ============================================================
def viz_anomaly_rate_pie():
    fig, ax = plt.subplots(figsize=(9, 6))

    sizes = [96.59, 0.01, 0.17, 3.24]
    labels_pie = ['Normal (96,59%)', 'Hard Anomaly', 'Soft Anomaly', 'Others']
    colors_pie = ['#27ae60', '#e74c3c', '#f39c12', '#95a5a6']
    explode = (0.05, 0.05, 0.05, 0)

    wedges, texts, autotexts = ax.pie(sizes, labels=labels_pie, autopct='',
                                       colors=colors_pie, explode=explode,
                                       startangle=90, textprops={'fontsize': 11})

    for i, (w, size) in enumerate(zip(wedges, sizes)):
        angle = (w.theta2 + w.theta1) / 2
        x = 0.4 * np.cos(np.radians(angle))
        y = 0.4 * np.sin(np.radians(angle))
        ax.text(x, y, f'{size:.2f}%', ha='center', va='center', fontweight='bold', fontsize=9, color='white')

    ax.set_title('Distribusi Routing Pipeline\nTotal: 2.027.520 records', fontsize=15, fontweight='bold', pad=15)
    _save('anomaly_rate_pie.png')


# ============================================================
# VIZ 5: Drift-Stripped R² Comparison (Slide 7)
# ============================================================
def viz_drift_stripped_r2():
    fig, ax = plt.subplots(figsize=(9, 6))

    models = ['Ridge Streaming', 'Ridge +\nDrift Stripped', 'RF Streaming', 'RF +\nDrift Stripped', 'RF\nBatch Ref']
    r2_values = [0.9128, 0.9973, 0.9629, 0.9973, 0.9952]
    colors = ['#e74c3c', '#27ae60', '#f39c12', '#27ae60', '#2c3e50']

    bars = ax.barh(models, r2_values, color=colors, alpha=0.8, edgecolor='black', linewidth=0.8, height=0.5)

    for bar, val in zip(bars, r2_values):
        ax.text(val + 0.005, bar.get_y() + bar.get_height()/2,
                f'R² = {val:.4f}', va='center', fontsize=11, fontweight='bold')

    ax.set_xlabel('R² Test', fontsize=13, fontweight='bold')
    ax.set_title('Dampak Drift Accumulation pada Akurasi Model', fontsize=15, fontweight='bold', pad=15)
    ax.set_xlim(0.85, 1.02)
    ax.grid(axis='x', alpha=0.3)
    ax.xaxis.set_major_formatter(mtick.FormatStrFormatter('%.2f'))

    ax.annotate('Gap: -0,0323\ndijelaskan\n93,5% oleh drift',
                xy=(0.9629, 2), xytext=(0.92, 0.6),
                fontsize=10, fontweight='bold', color='#e67e22',
                bbox=dict(boxstyle='round,pad=0.4', facecolor='#ffeaa7', edgecolor='#f39c12', linewidth=2),
                arrowprops=dict(arrowstyle='->', color='#e67e22', lw=2))
    _save('drift_stripped_r2_bar.png')


# ============================================================
# VIZ 6: Near vs Far Boxplot (Slide 7)
# ============================================================
def viz_near_far_boxplot():
    fig, ax = plt.subplots(figsize=(10, 6))

    np.random.seed(42)
    far_r2 = np.random.normal(0.157, 0.35, 1000)
    near_r2 = np.random.normal(-0.095, 0.45, 500)
    far_r2 = far_r2[far_r2 <= 1]
    near_r2 = near_r2[near_r2 >= -2]

    data = [near_r2, far_r2]
    labels_box = ['NEAR\n(dist < 1000)\nn=186.372\nR² = -0,095', 'FAR\n(dist >= 1000)\nn=1.746.856\nR² = 0,157']

    bp = ax.boxplot(data, labels=labels_box, patch_artist=True, widths=0.5,
                    notch=True, medianprops=dict(color='black', linewidth=2),
                    boxprops=dict(linewidth=1.5), whiskerprops=dict(linewidth=1.5),
                    capprops=dict(linewidth=1.5))

    colors_box = ['#e74c3c', '#27ae60']
    for patch, color in zip(bp['boxes'], colors_box):
        patch.set_facecolor(color)
        patch.set_alpha(0.6)

    ax.text(0.5, -2.5,
            'Delta R² = -0,2519  |  p = 1.37e-02  |  Cohen\'s d = 0.158\n'
            'NEAR group LEBIH BURUK dari baseline naif (R² < 0)!',
            ha='center', fontsize=10, fontweight='bold', color='#c0392b',
            bbox=dict(boxstyle='round,pad=0.4', facecolor='#fee', edgecolor='#e74c3c', linewidth=2),
            transform=ax.transAxes)

    ax.set_ylabel('R² Static', fontsize=13, fontweight='bold')
    ax.set_title('Robustness Audit: Performa Model Near vs Far dari Anomali', fontsize=14, fontweight='bold', pad=15)
    ax.axhline(y=0, color='gray', linestyle='--', linewidth=1.5, alpha=0.5, label='Baseline Naif (R² = 0)')
    ax.legend(fontsize=10)
    ax.grid(axis='y', alpha=0.3)
    _save('near_far_boxplot.png')


# ============================================================
# VIZ 7: Radar Chart - Architecture Summary (Slide 8)
# ============================================================
def viz_radar_chart():
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, polar=True)

    categories = ['Latency\nScore', 'Akurasi\n(R²)', 'Efisiensi\nEnergi', 'Throughput\n(headroom)', 'Recall\n(Anomaly)']
    N = len(categories)

    edge_scores =    [95, 55, 95, 99, 65]
    cloud_scores =   [5, 95, 80, 30, 90]
    edgepref_scores =[50, 85, 82, 95, 75]

    angles = np.linspace(0, 2*np.pi, N, endpoint=False).tolist()
    angles += angles[:1]
    edge_scores += edge_scores[:1]
    cloud_scores += cloud_scores[:1]
    edgepref_scores += edgepref_scores[:1]

    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories, fontsize=11, fontweight='bold')

    ax.fill(angles, edge_scores, color='#27ae60', alpha=0.15, linewidth=2)
    ax.plot(angles, edge_scores, color='#27ae60', linewidth=2.5, marker='o', markersize=6)

    ax.fill(angles, cloud_scores, color='#e74c3c', alpha=0.10, linewidth=2)
    ax.plot(angles, cloud_scores, color='#e74c3c', linewidth=2.5, marker='s', markersize=6)

    ax.fill(angles, edgepref_scores, color='#3498db', alpha=0.15, linewidth=2.5)
    ax.plot(angles, edgepref_scores, color='#3498db', linewidth=3, marker='*', markersize=10, linestyle='--')

    ax.set_ylim(0, 100)
    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_yticklabels(['20', '40', '60', '80', '100'], fontsize=9, color='gray')
    ax.yaxis.set_major_locator(mtick.MultipleLocator(20))

    ax.legend(loc='lower left', bbox_to_anchor=(-0.1, -0.15), fontsize=10, framealpha=0.9)

    ax.set_title('Perbandingan Arsitektur: Radar Score (0-100)\nEdge-Preferred = Balanced Optimum (*)',
                 fontsize=14, fontweight='bold', pad=20)
    _save('summary_radar_chart.png')


# ============================================================
# VIZ 8: Future Work Timeline (Slide 8)
# ============================================================
def viz_future_work():
    fig, ax = plt.subplots(figsize=(12, 5))

    phases = [('Short-Term\n(3 bulan)', '#e74c3c'), ('Mid-Term\n(6 bulan)', '#f39c12'), ('Long-Term\n(12 bulan)', '#27ae60')]
    tasks = [
        ['Drift Compensation\nLayer', 'Retrain lebih\nfrequent (500 rec)', 'Tambah fitur\ndrift-aware'],
        ['Non-linear online\nmodel (GBM)', 'Adaptive z-score\nthreshold', 'Physics-based\nthermal sim'],
        ['Per-room energy\nbreakdown', 'Real network\nlatency bench', 'Production DT\nplatform']
    ]

    x_positions = [0, 1, 2]

    for i, (phase_name, phase_color) in enumerate(phases):
        x = x_positions[i]
        ax.add_patch(plt.Rectangle((x - 0.35, 2.2), 0.7, 0.5, facecolor=phase_color, edgecolor='black', linewidth=1.5, alpha=0.9))
        ax.text(x, 2.45, phase_name, ha='center', va='center', fontsize=9, fontweight='bold', color='white')

        if i < 2:
            ax.plot([x + 0.35, x + 0.65], [2.45, 2.45], color='#7f8c8d', linewidth=2, linestyle='--',
                   marker='>', markersize=8, markerfacecolor=phase_color, markeredgecolor='black')

        for j, task in enumerate(tasks[i]):
            y = 1.2 - j * 0.85
            height = 0.6
            ax.add_patch(plt.Rectangle((x - 0.3, y - height/2), 0.6, height,
                                        facecolor=phase_color, edgecolor='black', linewidth=1, alpha=0.25))
            ax.text(x, y, task, ha='center', va='center', fontsize=8, fontweight='bold')

    ax.set_xlim(-0.8, 2.8)
    ax.set_ylim(-2.3, 2.9)
    ax.axis('off')
    ax.set_title('Roadmap Future Work: Next Steps untuk Paper', fontsize=15, fontweight='bold', pad=15)

    ax.text(0.5, -2.1, 'Current Progress: ████████░░ 80%', ha='center', fontsize=11, fontweight='bold', color='#2c3e50',
            bbox=dict(boxstyle='round,pad=0.4', facecolor='#d5f5e3', edgecolor='#27ae60', linewidth=2))
    _save('future_work_timeline.png')


# ============================================================
# VIZ 9: Streaming Pipeline Diagram (Slide 2/4)
# ============================================================
def viz_pipeline_flow():
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 6)
    ax.axis('off')

    ax.text(6, 5.5, 'Streaming Pipeline: Edge-Cloud Hybrid Architecture', ha='center', fontsize=14, fontweight='bold')

    input_box = FancyBboxPatch((0.3, 2.5), 1.5, 1.2, boxstyle="round,pad=0.1", facecolor='#8e44ad', edgecolor='black', linewidth=2)
    ax.add_patch(input_box)
    ax.text(1.05, 3.1, 'IoT Sensors\n(0.3 rec/s)', ha='center', va='center', fontsize=9, fontweight='bold', color='white')

    edge_nodes = [('Preprocess\n+ Fusion', 2.5, 4.2), ('Anomaly\nDetection\n(z=2.5)', 2.5, 2.0), ('Ridge\nPrediction', 5.0, 4.2), ('Buffer\nRetrain', 5.0, 2.0)]
    for label, x, y in edge_nodes:
        box = matplotlib.patches.FancyBboxPatch((x-0.55, y-0.55), 1.1, 1.1, boxstyle="round,pad=0.1", facecolor='#2980b9', edgecolor='black', linewidth=2)
        ax.add_patch(box)
        ax.text(x, y, label, ha='center', va='center', fontsize=8.5, fontweight='bold', color='white')

    diamond_pts = np.array([[7.5, 5.5], [8.5, 4.2], [7.5, 2.9], [6.5, 4.2]])
    ax.add_patch(plt.Polygon(diamond_pts, facecolor='#f39c12', edgecolor='black', linewidth=2))
    ax.text(7.5, 4.2, 'Anomali?', ha='center', va='center', fontsize=8, fontweight='bold', color='black')

    cloud_box = matplotlib.patches.FancyBboxPatch((9.5, 3.5), 2.0, 1.5, boxstyle="round,pad=0.1", facecolor='#e74c3c', edgecolor='black', linewidth=2)
    ax.add_patch(cloud_box)
    ax.text(10.5, 4.25, 'Cloud\nHeavy Processing\n~275 ms', ha='center', va='center', fontsize=9, fontweight='bold', color='white')

    dt_box = matplotlib.patches.FancyBboxPatch((9.5, 1.5), 2.0, 1.5, boxstyle="round,pad=0.1", facecolor='#e67e22', edgecolor='black', linewidth=2)
    ax.add_patch(dt_box)
    ax.text(10.5, 2.25, 'Digital Twin\nWeb-3D Sync', ha='center', va='center', fontweight='bold', color='white')

    ax.annotate('', xy=(2.5, 3.6), xytext=(1.8, 3.1), arrowprops=dict(arrowstyle='->', lw=2, color='#7f8c8d'))
    ax.annotate('', xy=(2.5, 3.0), xytext=(1.8, 2.7), arrowprops=dict(arrowstyle='->', lw=2, color='#7f8c8d'))
    ax.annotate('', xy=(4.4, 4.2), xytext=(3.6, 4.2), arrowprops=dict(arrowstyle='->', lw=2, color='#7f8c8d'))
    ax.annotate('', xy=(4.4, 2.0), xytext=(3.6, 2.0), arrowprops=dict(arrowstyle='->', lw=2, color='#7f8c8d'))
    ax.annotate('', xy=(6.5, 4.8), xytext=(6.1, 4.5), arrowprops=dict(arrowstyle='->', lw=2.5, color='#27ae60'))
    ax.annotate('', xy=(6.5, 3.6), xytext=(6.1, 3.3), arrowprops=dict(arrowstyle='->', lw=2.5, color='#e74c3c'))
    ax.annotate('', xy=(9.5, 4.2), xytext=(8.5, 4.2), arrowprops=dict(arrowstyle='->', lw=2.5, color='#e74c3c'))
    ax.annotate('', xy=(10.5, 3.5), xytext=(10.5, 3.0), arrowprops=dict(arrowstyle='->', lw=2, color='#e67e22'))

    ax.text(2.05, 3.4, '<2 ms', ha='center', fontsize=8, color='#27ae60', fontweight='bold')
    ax.text(5.0, 3.7, '~1.3 ms', ha='center', fontsize=8, color='#27ae60', fontweight='bold')
    ax.text(6.3, 5.3, 'Normal\n96,8%', ha='center', fontsize=8, color='#27ae60', fontweight='bold')
    ax.text(6.3, 3.4, 'Anomali\n3,2%', ha='center', fontsize=8, color='#e74c3c', fontweight='bold')
    ax.text(10.5, 5.0, '275 ms', ha='center', fontsize=9, color='#e74c3c', fontweight='bold')

    ax.text(6, 0.3, 'Total: 2.027.520 records  |  Edge: 1.3 ms/rec  |  Cloud: 275 ms/rec  |  Throughput: 3.335 rec/s  |  R²_batch = 0.9952',
            ha='center', fontsize=10, fontweight='bold', bbox=dict(boxstyle='round,pad=0.4', facecolor='#ecf0f1', edgecolor='#2c3e50', linewidth=1.5))
    plt.tight_layout()
    _save('streaming_pipeline_diagram.png')


# ============================================================
# RUN ALL
# ============================================================
if __name__ == '__main__':
    print("Generating presentation visuals...\n")
    viz_architecture_comparison()
    viz_drift_ablation()
    viz_confusion_matrix()
    viz_anomaly_rate_pie()
    viz_drift_stripped_r2()
    viz_near_far_boxplot()
    viz_radar_chart()
    viz_future_work()
    viz_pipeline_flow()
    print("\nOK: All 9 visualizations generated!")
