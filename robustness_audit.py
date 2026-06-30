"""
Robustness audit for streaming notebook — rolling mean contamination analysis.
Requires: streaming_results_z25.pkl and anomaly_indices.pkl (created by stream_full_audit.py).

Tests whether clean records close to injected hard anomalies
have lower R² due to corrupted rolling mean features.
"""
import pandas as pd
import numpy as np
import pickle
from dataclasses import dataclass
from sklearn.metrics import r2_score
from scipy import stats

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

with open('streaming_results_z25.pkl', 'rb') as f:
    all_results = pickle.load(f)
with open('anomaly_indices.pkl', 'rb') as f:
    anomaly_idx = pickle.load(f)
hard_indices = anomaly_idx['hard_indices']
soft_indices = anomaly_idx['soft_indices']

# Build dataframe
df = pd.DataFrame([{
    'sample_idx': r.sample_idx, 'anomaly': r.anomaly, 'r2_raw': r.r2_raw,
    'daya': r.daya, 'pred_daya': r.pred_daya, 'timestamp': r.timestamp,
    'routed_to_cloud': r.routed_to_cloud,
} for r in all_results])
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Sort by sample_idx (should already be sorted, but ensure)
df = df.sort_values('sample_idx').reset_index(drop=True)
n = len(df)

print(f"Total stream results: {n:,}")
print(f"Hard anomaly indices: {len(hard_indices)}")
print(f"Soft anomaly indices: {len(soft_indices)}")

# ---- Compute distance to nearest hard anomaly BEFORE each record ----
sorted_hard = np.sort(hard_indices)  # np.ndarray

def distance_to_previous_hard(idx, sorted_hard):
    """Return distance to nearest hard anomaly strictly before idx, or inf if none."""
    # bisect_right finds insertion point; index-1 is the largest hard < idx
    pos = np.searchsorted(sorted_hard, idx, side='right')
    if pos == 0:
        return float('inf')  # no hard anomaly before this record
    return idx - sorted_hard[pos - 1]

# Vectorized: for each record, compute distance to previous hard anomaly
distances = np.full(n, np.inf)
for i in range(n):
    idx_val = int(df.loc[i, 'sample_idx'])
    # Find previous hard
    pos = np.searchsorted(sorted_hard, idx_val, side='right')
    if pos > 0:
        distances[i] = idx_val - sorted_hard[pos - 1]
    # else inf

df['dist_to_prev_hard'] = distances

# Filter: clean records only (not anomaly, not hard, not soft)
clean_mask = (
    (df['anomaly'] == False) &
    (~df['sample_idx'].isin(set(hard_indices))) &
    (~df['sample_idx'].isin(set(soft_indices))) &
    (df['r2_raw'].notna())
)
df_clean = df[clean_mask].copy()
print(f"\nClean records: {len(df_clean):,}")

# Group 1: dist < 300 (potentially contaminated by rolling window of maxlen=300)
group_near = df_clean[df_clean['dist_to_prev_hard'] < 300]
# Group 2: dist >= 300 (rolling window clear)
group_far = df_clean[df_clean['dist_to_prev_hard'] >= 300]

print(f"\n{'='*70}")
print(f"GROUP 1 (dist < 300 from previous hard anomaly): n = {len(group_near):,}")
print(f"GROUP 2 (dist >= 300 from previous hard anomaly): n = {len(group_far):,}")

for name, grp in [("Near (<300)", group_near), ("Far (>=300)", group_far)]:
    r2_vals = grp['r2_raw'].dropna()
    if len(r2_vals) > 0:
        r2_mean = r2_vals.mean()
        r2_median = r2_vals.median()
        rmse = np.sqrt(((grp['daya'] - grp['pred_daya']) ** 2).mean())
        mae = (grp['daya'] - grp['pred_daya']).abs().mean()
        print(f"\n  {name}:")
        print(f"    Count:  {len(r2_vals):,}")
        print(f"    R² mean:     {r2_mean:.6f}")
        print(f"    R² median:   {r2_median:.6f}")
        print(f"    R² std:      {r2_vals.std():.6f}")
        print(f"    RMSE:        {rmse:.4f}")
        print(f"    MAE:         {mae:.4f}")
        print(f"    R² < 0:      {(r2_vals < 0).sum():,} ({(r2_vals < 0).mean()*100:.1f}%)")
        print(f"    R² < 0.5:   {(r2_vals < 0.5).sum():,} ({(r2_vals < 0.5).mean()*100:.1f}%)")
    else:
        print(f"\n  {name}: no clean records available")

# Statistical test: t-test comparing R² means
r2_near = group_near['r2_raw'].dropna().values
r2_far = group_far['r2_raw'].dropna().values
if len(r2_near) > 1 and len(r2_far) > 1:
    t_stat, p_val = stats.ttest_ind(r2_near, r2_far)
    print(f"\n{'='*70}")
    print(f"T-test (r2_near vs r2_far):")
    print(f"  t-stat = {t_stat:.4f}")
    print(f"  p-value = {p_val:.2e}")
    print(f"  Significant (p<0.05)? {'YES' if p_val < 0.05 else 'NO'}")
    print(f"  Effect size (Cohen's d): {stats.ttest_ind(r2_near, r2_far, equal_var=False)[0] / np.sqrt((np.concatenate([r2_near, r2_far]).std()))}")

    d = (np.mean(r2_near) - np.mean(r2_far)) / np.sqrt((np.std(r2_near)**2 + np.std(r2_far)**2) / 2)
    print(f"  Cohen's d = {d:.4f}")
    print(f"  Interpretation: {'Near group has significantly LOWER R² → rolling mean contamination confirmed!' if d < -0.2 else 'No strong evidence of contamination.'}")

# Additional: histogram of distances
print(f"\n{'='*70}")
print("Distance distribution (histogram):")
bins = [0, 10, 50, 100, 150, 200, 250, 300, 500, 1000, np.inf]
bin_labels = ['0-10', '10-50', '50-100', '100-150', '150-200', '200-250', '250-300', '300-500', '500-1000', '>1000']
df_clean['dist_bin'] = pd.cut(df_clean['dist_to_prev_hard'], bins=bins, labels=bin_labels)
print(df_clean['dist_bin'].value_counts().sort_index())
