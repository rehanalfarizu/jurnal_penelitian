"""
Robustness audit v2 — Static R² contamination analysis.

Fixes 2 methodological flaws from v1:
  A. Replaces rolling-window R² (shared deque maxlen=1000) with STATIC per-record-pair R²
  B. Changes distance threshold from 300 → 1000 (matching the actual window size)

Uses: streaming_results_z25.pkl + anomaly_indices.pkl
"""
import pandas as pd
import numpy as np
import pickle
import sys
from dataclasses import dataclass
from scipy import stats

# Define RecordMetrics so pickle can deserialize
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


def static_r2(y_true, y_pred):
    """Classic batch R² = 1 - SS_res / SS_tot. Computed independently per group."""
    ss_res = np.sum((np.asarray(y_true) - np.asarray(y_pred)) ** 2)
    ss_tot = np.sum((np.asarray(y_true) - np.mean(np.asarray(y_true))) ** 2)
    if ss_tot < 1e-12:
        return 0.0
    return 1.0 - ss_res / ss_tot

# ---- Load data ----
with open('streaming_results_z25.pkl', 'rb') as f:
    all_results = pickle.load(f)
with open('anomaly_indices.pkl', 'rb') as f:
    anomaly_idx = pickle.load(f)
hard_indices = np.sort(anomaly_idx['hard_indices'])
soft_indices = anomaly_idx['soft_indices']

# Build DataFrame from pickled results
records = []
for r in all_results:
    records.append({
        'sample_idx': r.sample_idx,
        'timestamp': r.timestamp,
        'is_anomaly': r.anomaly,
        'routed_to_cloud': r.routed_to_cloud,
        'energy_score': r.energy_score,
        'edge_latency_ms': r.edge_latency_ms,
        'daya': r.daya,
        'pred_daya': r.pred_daya,
        # v1 metrics (for reference only):
        'r2_running': getattr(r, 'r2_running', None),
        'r2_raw': getattr(r, 'r2_raw', None),
    })
df = pd.DataFrame(records)
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('sample_idx').reset_index(drop=True)
n = len(df)
print(f"Total stream results: {n:,}")
print(f"Hard anomaly indices: {len(hard_indices)}")
print(f"Soft anomaly indices: {len(soft_indices)}")

# ---- Distance to previous HARD anomaly (vectorized) ----
def compute_dist_to_prev_hard(indices_array, sorted_hard):
    """For each index, compute distance to the nearest hard anomaly STRICTLY BEFORE it."""
    # searchsorted(right) gives position where index would be inserted keeping order
    # pos-1 = index of the rightmost hard anomaly <= index
    # We want strictly before, so if indices_array[pos-1] == indices_array[i], skip it
    n = len(indices_array)
    dists = np.full(n, np.inf)
    for i in range(n):
        val = indices_array[i]
        pos = np.searchsorted(sorted_hard, val, side='right')
        if pos == 0:
            dists[i] = np.inf  # no hard anomaly before this
        elif sorted_hard[pos - 1] == val:
            dists[i] = np.inf  # this record IS a hard anomaly itself
        else:
            dists[i] = val - sorted_hard[pos - 1]
    return dists

df['dist_to_prev_hard'] = compute_dist_to_prev_hard(df['sample_idx'].values, hard_indices)

# Filter: clean records only (exclude ALL injected anomalies + records with inf distance)
# Fix: soft_indices could be ndarray or list depending on how it was saved
try:
    soft_indices_set = set(soft_indices)
except TypeError:
    soft_indices_set = set(soft_indices.tolist())

clean_mask = (
    (~df['is_anomaly']) &
    (~df['sample_idx'].isin(set(hard_indices))) &
    (~df['sample_idx'].isin(soft_indices_set)) &
    (df['dist_to_prev_hard'] < np.inf)
)
df_clean = df[clean_mask].copy()
print(f"\nClean records (no anomaly, with previous hard anomaly): {len(df_clean):,}")

# ---- Groups: threshold = 1000 (matches deque maxlen) ----
THRESHOLD = 1000
group_near = df_clean[df_clean['dist_to_prev_hard'] < THRESHOLD]
group_far  = df_clean[df_clean['dist_to_prev_hard'] >= THRESHOLD]

print(f"\n{'='*70}")
print(f"GROUP definitions (threshold = {THRESHOLD}, matching deque maxlen=1000):")
print(f"  NEAR  (dist < {THRESHOLD}):  n = {len(group_near):,} ({len(group_near)/len(df_clean)*100:.1f}%)")
print(f"  FAR   (dist >= {THRESHOLD}): n = {len(group_far):,}  ({len(group_far)/len(df_clean)*100:.1f}%)")

# ---- A. Static R² per group ----
print(f"\n{'='*70}")
print("A. STATIC R² (primary metric — independent computation per group)")
print(f"{'='*70}")

for name, grp in [("NEAR (dist < 1000)", group_near), ("FAR (dist >= 1000)", group_far)]:
    r2 = static_r2(grp['daya'].values, grp['pred_daya'].values)
    print(f"  {name:.<40} R²_static = {r2:.6f}")

r2_near_static = static_r2(group_near['daya'].values, group_near['pred_daya'].values)
r2_far_static  = static_r2(group_far['daya'].values, group_far['pred_daya'].values)
delta_static = r2_near_static - r2_far_static
print(f"\n  Delta R²_static (NEAR - FAR) = {delta_static:+.6f}")
if abs(delta_static) > 0.01:
    print(f"  >>> SIGNIFICANT difference: {'NEAR worse' if delta_static < 0 else 'FAR worse'}")
else:
    print(f"  >>> Practically ZERO difference (< 0.01 absolute)")

# ---- B. RMSE per group ----
print(f"\n{'='*70}")
print("B. RMSE per group")
print(f"{'='*70}")

for name, grp in [("NEAR", group_near), ("FAR", group_far)]:
    rmse = np.sqrt(((grp['daya'] - grp['pred_daya']) ** 2).mean())
    mae = (grp['daya'] - grp['pred_daya']).abs().mean()
    median_abs = np.median(np.abs(grp['daya'].values - grp['pred_daya'].values))
    mape_mask = grp['daya'].abs() > 1e-6
    if mape_mask.any():
        mape = np.mean(np.abs((grp.loc[mape_mask, 'daya'].values - grp.loc[mape_mask, 'pred_daya'].values) / grp.loc[mape_mask, 'daya'].values)) * 100
    else:
        mape = 0.0
    print(f"  {name:.<30} RMSE={rmse:.4f}  MAE={mae:.4f}  MedianAbs={median_abs:.4f}  MAPE={mape:.4f}%")

# ---- C. v1 rolling R² comparison (for reference only) ----
print(f"\n{'='*70}")
print("C. V1 Rolling-window R² (deprecated — included for reference)")
print(f"{'='*70}")

for name, grp in [("NEAR", group_near), ("FAR", group_far)]:
    vals = grp['r2_raw'].dropna()
    if len(vals) > 0:
        print(f"  {name:.<30} mean={vals.mean():.6f}  median={vals.median():.6f}  std={vals.std():.6f}")
        print(f"             R² < 0: {(vals < 0).sum():,}/{len(vals):,} ({(vals < 0).mean()*100:.1f}%)")
    else:
        print(f"  {name:.<30} no r2_raw values")

# ---- D. Distance distribution ----
print(f"\n{'='*70}")
print("D. Distribution of dist_to_prev_hard (ALL clean records)")
print(f"{'='*70}")

bins_edges = [0, 10, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 50000, np.inf]
bin_labels = ['<10', '10-50', '50-100', '100-200', '200-500', '500-1000', '1000-2K', '2K-5K', '5K-10K', '10K-50K', '>50K']
df_clean['dist_bin'] = pd.cut(df_clean['dist_to_prev_hard'], bins=bins_edges, labels=bin_labels)
counts = df_clean['dist_bin'].value_counts().sort_index()
total_clean = len(df_clean)
for label, cnt in counts.items():
    pct = cnt / total_clean * 100
    bar = '#' * int(pct / 2)
    print(f"  {label:>10}: {cnt:>7,} ({pct:>5.1f}%) {bar}")

# Summary stats
dist_arr = df_clean['dist_to_prev_hard'].values
print(f"\n  Overall stats:")
print(f"    Min:   {dist_arr.min():.0f}")
print(f"    Max:   {dist_arr.max():,.0f}")
print(f"    Mean:  {dist_arr.mean():,.0f}")
print(f"    Median:{np.median(dist_arr):,.0f}")
print(f"    >=1000: {(dist_arr >= 1000).sum():,} ({(dist_arr >= 1000).mean()*100:.1f}%)")
print(f"    >=500:  {(dist_arr >= 500).sum():,}  ({(dist_arr >= 500).mean()*100:.1f}%)")
print(f"    <300:   {(dist_arr < 300).sum():,}  ({(dist_arr < 300).mean()*100:.1f}%)")

# ---- E. Paired test: R² distributions (not just mean) ----
print(f"\n{'='*70}")
print("E. Pairwise comparison: static R² per 10K-sample blocks")
print(f"{'='*70}")

# Compute static R² in overlapping 10K windows for NEAR and FAR separately
def r2_per_block(group, block_size=10000):
    r2_list = []
    arr = group[['daya', 'pred_daya']].values
    for i in range(0, len(arr), block_size):
        block = arr[i:i+block_size]
        if len(block) < 100:  # too small
            continue
        r2 = static_r2(block[:, 0], block[:, 1])
        r2_list.append(r2)
    return r2_list

r2_near_blocks = r2_per_block(group_near.sort_values('sample_idx'))
r2_far_blocks  = r2_per_block(group_far.sort_values('sample_idx'))

print(f"\n  Near  blocks: {len(r2_near_blocks)} windows")
print(f"  Far   blocks:  {len(r2_far_blocks)} windows")

if len(r2_near_blocks) > 0:
    r2n = np.array(r2_near_blocks)
    print(f"  NEAR  block R²:  mean={r2n.mean():.6f}  median={np.median(r2n):.6f}  std={r2n.std():.6f}")
    print(f"  NEAR  block R²  min={r2n.min():.6f},  max={r2n.max():.6f}")

if len(r2_far_blocks) > 0:
    r2f = np.array(r2_far_blocks)
    print(f"  FAR   block R²:  mean={r2f.mean():.6f}  median={np.median(r2f):.6f}  std={r2f.std():.6f}")
    print(f"  FAR   block R²  min={r2f.min():.6f},  max={r2f.max():.6f}")

# Mann-Whitney U test (non-parametric, no normality assumption)
if len(r2_near_blocks) > 10 and len(r2_far_blocks) > 10:
    u_stat, p_u = stats.mannwhitneyu(r2_near_blocks, r2_far_blocks, alternative='two-sided')
    cohens_d = (r2n.mean() - r2f.mean()) / np.sqrt((r2n.var() + r2f.var()) / 2)
    print(f"\n  Mann-Whitney U: u={u_stat:.0f}, p={p_u:.2e}")
    print(f"  Cohen's d (block-level): {cohens_d:.4f}")

# ---- F. Cross-tabulation: NEAR records that overlap with FAR R² range ----
print(f"\n{'='*70}")
print("F. Overlap analysis: do NEAR and FAR have DIFFERENT distributions?")
print(f"{'='*70}")

if len(r2_near_blocks) > 0 and len(r2_far_blocks) > 0:
    r2n = np.array(r2_near_blocks)
    r2f = np.array(r2_far_blocks)

    # How many NEAR blocks have R² BETTER than FAR median?
    far_median = np.median(r2f)
    near_above_far_median = (r2n > far_median).mean()
    near_below_far_median = (r2n <= far_median).mean()

    print(f"  FAR median block R² = {far_median:.6f}")
    print(f"  NEAR blocks ABOVE FAR median: {near_above_far_median*100:.1f}%")
    print(f"  NEAR blocks BELOW FAR median: {near_below_far_median*100:.1f}%")

    if near_above_far_median > 0.4:
        print(f"  >>> NEAR blocks are often as good as FAR → contamination EFFECTIVELY negligible")
    else:
        print(f"  >>> NEAR blocks consistently worse than FAR → contamination EXISTS")

# ---- SAVE JSON ----
summary = {
    'threshold': THRESHOLD,
    'total_clean': len(df_clean),
    'group_near': {
        'n': len(group_near),
        'pct': round(len(group_near)/len(df_clean)*100, 1),
        'r2_static': round(r2_near_static, 6),
        'rmse': round(np.sqrt(((group_near['daya'] - group_near['pred_daya'])**2).mean()), 4),
        'mae': round((group_near['daya'] - group_near['pred_daya']).abs().mean(), 4),
    },
    'group_far': {
        'n': len(group_far),
        'pct': round(len(group_far)/len(df_clean)*100, 1),
        'r2_static': round(r2_far_static, 6),
        'rmse': round(np.sqrt(((group_far['daya'] - group_far['pred_daya'])**2).mean()), 4),
        'mae': round((group_far['daya'] - group_far['pred_daya']).abs().mean(), 4),
    },
    'delta_r2_static': round(delta_static, 6),
    'n_near_blocks': len(r2_near_blocks),
    'n_far_blocks': len(r2_far_blocks),
}

import json
with open('robustness_audit_v2.json', 'w') as f:
    json.dump(summary, f, indent=2)
print(f"\nSaved: robustness_audit_v2.json")
