"""
evaluate_anomaly_recall.py — Measure anomaly recall for the streaming pipeline.

Inputs (already produced by edge_cloud_streaming.ipynb):
  - streaming_results_z25.pkl  : RecordMetrics list from the chunked run
  - anomaly_indices.pkl        : {'hard_indices': np.array, 'soft_indices': np.array}

What this script does:
  - Loads both pickles
  - Joins injected anomaly indices (ground truth) with the stream's anomaly flags
  - Reports recall for: hard, soft, combined
  - Reports false-positive rate over the clean window
  - Reports confusion-matrix counts for context

Output:
  - Prints a summary to stdout
  - Writes anomaly_recall.json next to the script

Usage:
  python evaluate_anomaly_recall.py
"""
import json
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (
    confusion_matrix,
    precision_recall_fscore_support,
)


HERE = Path(__file__).resolve().parent


# Shim for unpickling — the streaming pipeline pickles RecordMetrics by
# its fully-qualified name; we re-define the same dataclass here so
# pickle.load can locate it without importing the notebook's module.
from dataclasses import dataclass


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
    r2_running: float
    r2_raw: float
    daya: float
    pred_daya: float


def load_results():
    with open(HERE / 'streaming_results_z25.pkl', 'rb') as f:
        results = pickle.load(f)
    with open(HERE / 'anomaly_indices.pkl', 'rb') as f:
        gt = pickle.load(f)
    return results, gt['hard_indices'], gt['soft_indices']


def build_dfs(results, hard_idx, soft_idx):
    df = pd.DataFrame([
        {
            'sample_idx': r.sample_idx,
            'timestamp': r.timestamp,
            'detected_anomaly': bool(r.anomaly),
            'routed_to_cloud': bool(r.routed_to_cloud),
            'energy_score': r.energy_score,
            'daya': r.daya,
            'pred_daya': r.pred_daya,
        }
        for r in results
    ])
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['is_hard_inject'] = df['sample_idx'].isin(set(int(i) for i in hard_idx))
    df['is_soft_inject'] = df['sample_idx'].isin(set(int(i) for i in soft_idx))
    df['is_any_inject'] = df['is_hard_inject'] | df['is_soft_inject']
    df = df.sort_values('sample_idx').reset_index(drop=True)
    return df


def recall_for(mask_truth, mask_detected, name):
    truth = mask_truth.values
    detected = mask_detected.values
    n_truth = int(truth.sum())
    if n_truth == 0:
        return {'group': name, 'n_injected': 0, 'recall': float('nan'), 'tp': 0, 'fn': 0}

    tp = int((truth & detected).sum())
    fn = int((truth & ~detected).sum())
    fp = int((~truth & detected).sum())
    tn = int((~truth & ~detected).sum())

    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)
          if (precision + recall) > 0 else 0.0)

    return {
        'group': name,
        'n_injected': n_truth,
        'tp': tp,
        'fn': fn,
        'fp': fp,
        'tn': tn,
        'recall': round(recall, 6),
        'precision': round(precision, 6),
        'f1': round(f1, 6),
    }


def main():
    results, hard_idx, soft_idx = load_results()
    df = build_dfs(results, hard_idx, soft_idx)
    n_total = len(df)

    print('=' * 70)
    print(f'Loaded {n_total:,} stream results')
    print(f'  hard inject: {len(hard_idx):,}')
    print(f'  soft inject: {len(soft_idx):,}')
    print(f'  total ground-truth anomalies: {int(df["is_any_inject"].sum()):,} '
          f'({df["is_any_inject"].mean()*100:.3f}% of stream)')
    detected = df['detected_anomaly']
    print(f'  pipeline flagged anomalies:  {int(detected.sum()):,} '
          f'({detected.mean()*100:.3f}% of stream)')

    rows = []
    rows.append(recall_for(df['is_hard_inject'], detected, 'HARD'))
    rows.append(recall_for(df['is_soft_inject'], detected, 'SOFT'))
    rows.append(recall_for(df['is_any_inject'], detected, 'COMBINED'))

    print()
    print('=' * 70)
    print(f"{'Group':<10} {'n':>6} {'TP':>6} {'FN':>6} {'FP':>7} {'Recall':>9} {'Precision':>10} {'F1':>9}")
    print('-' * 70)
    for r in rows:
        print(f"{r['group']:<10} {r['n_injected']:>6,} {r['tp']:>6,} {r['fn']:>6,} "
              f"{r['fp']:>7,} {r['recall']*100:>8.2f}% {r['precision']*100:>9.2f}% "
              f"{r['f1']:>9.4f}")

    # Confusion-matrix over the whole stream
    y_true = df['is_any_inject'].astype(int).values
    y_pred = detected.astype(int).values
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    print()
    print('=' * 70)
    print('Confusion matrix (rows=truth, cols=predicted; 0=normal, 1=anomaly)')
    print(cm)

    # False-positive rate among true-clean records
    clean_mask = ~df['is_any_inject']
    clean_n = int(clean_mask.sum())
    fp_among_clean = int((clean_mask & detected).sum())
    fpr_clean = fp_among_clean / clean_n if clean_n else 0.0
    print()
    print('=' * 70)
    print(f'False-positive rate on clean records: {fpr_clean*100:.3f}% '
          f'({fp_among_clean:,} of {clean_n:,})')

    # Detection latency for hard anomalies: median distance between hard_idx
    # and the nearest detected record at-or-after that hard index
    detected_idx = df.loc[detected, 'sample_idx'].values
    detected_idx_sorted = np.sort(detected_idx)
    if len(detected_idx_sorted) > 0:
        latencies = []
        for h in hard_idx:
            pos = np.searchsorted(detected_idx_sorted, h, side='left')
            if pos < len(detected_idx_sorted):
                latencies.append(int(detected_idx_sorted[pos]) - int(h))
        if latencies:
            lat_arr = np.array(latencies, dtype=float)
            print()
            print('=' * 70)
            print(f'Detection latency for hard anomalies (records until first flag, n={len(lat_arr)})')
            print(f'  median = {np.median(lat_arr):.0f}')
            print(f'  mean   = {lat_arr.mean():.1f}')
            print(f'  P90    = {np.percentile(lat_arr, 90):.0f}')
            print(f'  max    = {lat_arr.max():.0f}')

    # Save JSON
    summary = {
        'n_total': n_total,
        'n_hard_inject': int(len(hard_idx)),
        'n_soft_inject': int(len(soft_idx)),
        'n_detected': int(detected.sum()),
        'fpr_clean': round(fpr_clean, 6),
        'confusion_matrix': cm.tolist(),
        'by_group': rows,
    }
    out_path = HERE / 'anomaly_recall.json'
    with open(out_path, 'w') as f:
        json.dump(summary, f, indent=2)
    print()
    print(f'Saved: {out_path.name}')


if __name__ == '__main__':
    main()
