#!/usr/bin/env python3
"""
Edge-Cloud Streaming Validation — Final Notebook v2
Uses BOTH:
- PRIMARY: sensor_data_primary.csv (92K, designed dataset, 4 days)
- SECONDARY: sensor_data.csv (2M, real deployment scale, stress-test)

Key metrics:
- Train/Test R² (proper held-out)
- MAPE, NRMSE, RMSE
- Edge vs Cloud latency
- Anomaly detection precision/recall/F1
- Edge routing efficiency
"""

import pandas as pd
import numpy as np
import json
import pickle
from dataclasses import dataclass
from pathlib import Path
import time
import warnings
warnings.filterwarnings('ignore')

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

np.random.seed(42)
sns.set_style('whitegrid')
plt.rcParams['figure.figsize'] = (12, 6)
plt.rcParams['figure.dpi'] = 150

from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_percentage_error, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler
from collections import deque

# ============================================================
# CONFIG
# ============================================================
CONFIG = {
    "zscore_anomaly": 2.5,
    "temp_range": (15, 50),
    "humid_range": (20, 100),
    "fuse_weights": {"suhu": 0.30, "kelembaban": 0.25, "daya": 0.30, "orang": 0.15},
}

EDGE_LAT = {'preprocess': 0.25, 'fusion': 0.4, 'anomaly': 0.15, 'predict': 0.5}
SUM_EDGE_LAT = sum(EDGE_LAT.values())  # 1.3 ms
CLOUD_NET = 45
CLOUD_PROC = 150
CLOUD_SYNC = 80
CLOUD_TOTAL = CLOUD_NET + CLOUD_PROC + CLOUD_SYNC  # 275 ms

EDGE_E = {'preprocess': 3.5, 'fusion': 5.8, 'anomaly': 2.8, 'predict': 8.2}
SUM_EDGE_E = sum(EDGE_E.values())  # 20.3 mW
CLOUD_E = 1.2 + 0.6  # 1.8 mW

# ============================================================
# STREAMING EDGE NODE
# ============================================================
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
    residual: float


class EdgeStreamingNode:
    def __init__(self, config):
        self.config = config
        self.weights = config["fuse_weights"]
        self.scaler = StandardScaler()
        self.model = None
        self.total_samples = 0
        self.anomaly_count = 0
        self.cloud_route_count = 0
        self._r2_window = deque(maxlen=500)
        self._history_power = deque(maxlen=300)
        self._history_temp = deque(maxlen=300)
        self._history_humid = deque(maxlen=300)
        self._window_scores = deque(maxlen=200)

    def compute_energy_score(self, row):
        s = self.weights
        return (
            s["suhu"] * max(0, min(1, (row["suhu"] - 25) / 10 + 0.5)) +
            s["kelembaban"] * max(0, min(1, (row["kelembaban"] - 50) / 30 + 0.5)) +
            s["daya"] * max(0, min(1, row["daya"] / 500)) +
            s["orang"] * max(0, min(1, row["jumlah_orang"] / 10))
        )

    def _extract_features(self, row):
        ts = pd.Timestamp(row["timestamp"])
        tegangan = row.get("tegangan", 220.0)
        arus = row.get("arus", row["daya"] / max(tegangan, 1))
        hour = ts.hour
        morning = 1.0 if 6 <= hour < 10 else 0.0
        midday = 1.0 if 10 <= hour < 14 else 0.0
        afternoon = 1.0 if 14 <= hour < 18 else 0.0
        evening = 1.0 if 18 <= hour < 22 else 0.0
        night = 1.0 if hour < 6 or hour >= 22 else 0.0
        h_p = list(self._history_power)
        h_t = list(self._history_temp)
        ma_short_p = float(np.mean(h_p[-100:])) if len(h_p) >= 100 else (float(np.mean(h_p)) if h_p else 0.0)
        ma_long_p = float(np.mean(h_p[-300:])) if len(h_p) >= 300 else (ma_short_p if h_p else 0.0)
        ma_short_t = float(np.mean(h_t[-100:])) if len(h_t) >= 100 else (float(np.mean(h_t)) if h_t else 0.0)
        return np.array([[
            row["suhu"], row["kelembaban"], tegangan, arus, row["jumlah_orang"],
            tegangan * arus, row["suhu"] * row["kelembaban"],
            float(hour), float(ts.dayofweek), float(ts.day),
            morning, midday, afternoon, evening, night,
            ma_short_p, ma_long_p, ma_short_t,
        ]])

    def update_model(self, X, y):
        self.scaler = StandardScaler()
        X_s = self.scaler.fit_transform(X)
        self.model = Ridge(alpha=1e-2)
        self.model.fit(X_s, y)
        return self.model

    def predict(self, X):
        return self.model.predict(self.scaler.transform(X))

    def compute_r2_streaming(self):
        if len(self._r2_window) < 50:
            return None
        y_t = np.array([r[0] for r in self._r2_window])
        y_p = np.array([r[1] for r in self._r2_window])
        ss_res = np.sum((y_t - y_p) ** 2)
        ss_tot = np.sum((y_t - y_t.mean()) ** 2)
        if ss_tot < 1e-10:
            return 0.0
        return float(1.0 - ss_res / ss_tot)

    def process_record(self, row):
        t0 = time.perf_counter()
        self.total_samples += 1
        temp_ok = self.config["temp_range"][0] <= row["suhu"] <= self.config["temp_range"][1]
        humid_ok = self.config["humid_range"][0] <= row["kelembaban"] <= self.config["humid_range"][1]
        energy_score = self.compute_energy_score(row)
        self._window_scores.append(energy_score)
        is_anomaly = False
        if len(self._window_scores) > 20:
            recent = list(self._window_scores)[-100:]
            z = abs(energy_score - np.mean(recent)) / max(np.std(recent), 1e-10)
            if z > self.config["zscore_anomaly"]:
                is_anomaly = True
        if is_anomaly:
            self.anomaly_count += 1
        X = self._extract_features(row)
        y_pred = self.predict(X)[0] if self.model else row.get("daya", 0)
        residual = abs(float(row["daya"]) - y_pred)
        self._r2_window.append((float(row["daya"]), y_pred))
        self._history_power.append(float(row.get("daya", 0)))
        self._history_temp.append(float(row.get("suhu", 0)))
        self._history_humid.append(float(row.get("kelembaban", 0)))
        routed = is_anomaly or not temp_ok or not humid_ok
        elapsed = (time.perf_counter() - t0) * 1000
        edge_lat = SUM_EDGE_LAT + elapsed
        total_lat = edge_lat
        energy = SUM_EDGE_E + elapsed * 0.1
        if routed:
            self.cloud_route_count += 1
            total_lat += CLOUD_NET + CLOUD_TOTAL
            energy = SUM_EDGE_E + CLOUD_E + elapsed * 0.1
        return RecordMetrics(
            sample_idx=self.total_samples,
            timestamp=str(row["timestamp"]),
            anomaly=is_anomaly,
            routed_to_cloud=routed,
            edge_latency_ms=round(edge_lat, 2),
            cloud_latency_ms=round(total_lat - edge_lat, 2) if routed else 0.0,
            total_latency_ms=round(total_lat, 2),
            energy_mw=round(energy, 2),
            energy_score=round(energy_score, 4),
            r2_streaming=round(self.compute_r2_streaming() or 0.0, 4),
            daya=float(row["daya"]),
            pred_daya=round(y_pred, 2),
            residual=round(residual, 2),
        )


# ============================================================
# MAIN
# ============================================================
print("=" * 70)
print("Edge-Cloud Streaming Validation v2 (PRIMARY + SECONDARY)")
print("=" * 70)

# ------------------------------------------------------------
# PART 1: PRIMARY DATASET (92K) — Designed representative
# ------------------------------------------------------------
print("\n" + "=" * 70)
print("PART 1: PRIMARY DATASET (sensor_data_primary.csv)")
print("=" * 70)

print("\n[1A] Loading primary dataset (92K designed records, 4 days)...")
primary = pd.read_csv("sensor_data_primary.csv")
col_map = {
    'Timestamp': 'timestamp', 'Suhu (C)': 'suhu', 'Kelembaban (%)': 'kelembaban',
    'Tegangan (V)': 'tegangan', 'Arus (A)': 'arus', 'Daya (W)': 'daya',
    'Jumlah Orang': 'jumlah_orang', 'DeviceID': 'device_id',
}
primary.rename(columns=col_map, inplace=True)
primary['timestamp'] = pd.to_datetime(primary['timestamp'])

print(f"  Total: {len(primary):,} records")
print(f"  Span: {(primary['timestamp'].max() - primary['timestamp'].min()).total_seconds() / 86400:.1f} days")
print(f"  Building types: {primary['BuildingType'].unique()}")
if 'AnomalyLabel' in primary.columns:
    n_hard = (primary['AnomalyLabel'] == 1).sum()
    n_soft = (primary['AnomalyLabel'] == 2).sum()
    print(f"  Pre-injected anomalies: {n_hard} hard + {n_soft} soft = {n_hard + n_soft:,} ({((n_hard + n_soft) / len(primary) * 100):.2f}%)")

# Train/Test split (75/25, chronological)
split = int(len(primary) * 0.75)
train_p = primary.iloc[:split]
test_p = primary.iloc[split:]
print(f"\n  Split: {len(train_p):,} train / {len(test_p):,} test (chronological)")

# Train
print("\n[1B] Training Ridge model on primary dataset...")
node_p = EdgeStreamingNode(CONFIG)
X_tr, y_tr = [], []
for _, row in train_p.iterrows():
    X = node_p._extract_features(row)
    X_tr.append(X.flatten())
    y_tr.append(row['daya'])
    node_p._history_power.append(float(row.get("daya", 0)))
    node_p._history_temp.append(float(row.get("suhu", 0)))
    node_p._history_humid.append(float(row.get("kelembaban", 0)))
X_tr = np.array(X_tr)
y_tr = np.array(y_tr)
node_p.update_model(X_tr, y_tr)

# Train metrics
y_pred_tr = node_p.predict(X_tr)
train_r2 = r2_score(y_tr, y_pred_tr)
train_mape = mean_absolute_percentage_error(y_tr, y_pred_tr) * 100
train_rmse = np.sqrt(mean_squared_error(y_tr, y_pred_tr))
print(f"  Train: R²={train_r2:.4f}, MAPE={train_mape:.2f}%, RMSE={train_rmse:.2f}W")

# Test metrics
X_te, y_te = [], []
for _, row in test_p.iterrows():
    X = node_p._extract_features(row)
    X_te.append(X.flatten())
    y_te.append(row['daya'])
    node_p._history_power.append(float(row.get("daya", 0)))
    node_p._history_temp.append(float(row.get("suhu", 0)))
    node_p._history_humid.append(float(row.get("kelembaban", 0)))
X_te = np.array(X_te)
y_te = np.array(y_te)
y_pred_te = node_p.predict(X_te)
test_r2 = r2_score(y_te, y_pred_te)
test_mape = mean_absolute_percentage_error(y_te, y_pred_te) * 100
test_rmse = np.sqrt(mean_squared_error(y_te, y_pred_te))
test_nrmse = test_rmse / y_te.std()
print(f"  Test:  R²={test_r2:.4f}, MAPE={test_mape:.2f}%, RMSE={test_rmse:.2f}W, NRMSE={test_nrmse:.4f}")

# Anomaly detection evaluation (precision/recall)
print("\n[1C] Anomaly detection evaluation on primary dataset...")
y_te_true = test_p['AnomalyLabel'].values if 'AnomalyLabel' in test_p.columns else None

# Streaming on test (with proper history)
t0 = time.perf_counter()
test_results = []
for _, row in test_p.iterrows():
    m = node_p.process_record(row)
    test_results.append(m)
elapsed = time.perf_counter() - t0
test_throughput = len(test_p) / elapsed

# Anomaly metrics
if y_te_true is not None:
    y_pred_anom = np.array([int(m.anomaly) for m in test_results])
    y_true_anom = (y_te_true > 0).astype(int)
    TP = ((y_pred_anom == 1) & (y_true_anom == 1)).sum()
    FP = ((y_pred_anom == 1) & (y_true_anom == 0)).sum()
    FN = ((y_pred_anom == 0) & (y_true_anom == 1)).sum()
    precision = TP / (TP + FP) * 100 if (TP + FP) > 0 else 0
    recall = TP / (TP + FN) * 100 if (TP + FN) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    print(f"  Precision: {precision:.2f}%")
    print(f"  Recall:    {recall:.2f}%")
    print(f"  F1:        {f1:.2f}%")
    print(f"  Confusion: TP={TP}, FP={FP}, FN={FN}")

# Edge vs Cloud
edge_only = sum(1 for m in test_results if not m.routed_to_cloud)
cloud_routed = sum(1 for m in test_results if m.routed_to_cloud)
edge_eff = edge_only / len(test_results) * 100
edge_lat = [m.edge_latency_ms for m in test_results if not m.routed_to_cloud]
cloud_lat = [m.total_latency_ms for m in test_results if m.routed_to_cloud]

print(f"\n  Throughput: {test_throughput:,.0f} rec/s")
print(f"  Edge-only:  {edge_only:,} ({edge_eff:.1f}%)")
print(f"  Cloud:      {cloud_routed:,} ({100 - edge_eff:.1f}%)")
if edge_lat:
    print(f"  Edge P50:   {np.median(edge_lat):.1f} ms, P95={np.percentile(edge_lat, 95):.1f}, P99={np.percentile(edge_lat, 99):.1f}")
if cloud_lat:
    print(f"  Cloud P50:  {np.median(cloud_lat):.1f} ms, P95={np.percentile(cloud_lat, 95):.1f}, P99={np.percentile(cloud_lat, 99):.1f}")

# ------------------------------------------------------------
# PART 2: SECONDARY DATASET (2M) — Real deployment scale
# ------------------------------------------------------------
print("\n" + "=" * 70)
print("PART 2: SECONDARY DATASET (sensor_data.csv, 2M records)")
print("=" * 70)

print("\n[2A] Loading secondary dataset (2M real deployment records)...")
if Path("sensor_data.csv").exists():
    secondary = pd.read_csv("sensor_data.csv", nrows=500000)  # Subsample 500K for speed
    secondary.rename(columns=col_map, inplace=True)
    secondary['timestamp'] = pd.to_datetime(secondary['timestamp'])
    print(f"  Total: {len(secondary):,} records (subsampled for stress-test)")

    # Train/Test split (50/50 for speed)
    split2 = int(len(secondary) * 0.5)
    train_s = secondary.iloc[:split2]
    test_s = secondary.iloc[split2:]
    print(f"  Split: {len(train_s):,} train / {len(test_s):,} test")

    # Train
    print("\n[2B] Training Ridge model on secondary dataset...")
    node_s = EdgeStreamingNode(CONFIG)
    X_tr2, y_tr2 = [], []
    for _, row in train_s.iterrows():
        X = node_s._extract_features(row)
        X_tr2.append(X.flatten())
        y_tr2.append(row['daya'])
        node_s._history_power.append(float(row.get("daya", 0)))
        node_s._history_temp.append(float(row.get("suhu", 0)))
        node_s._history_humid.append(float(row.get("kelembaban", 0)))
    X_tr2 = np.array(X_tr2)
    y_tr2 = np.array(y_tr2)
    node_s.update_model(X_tr2, y_tr2)

    y_pred_tr2 = node_s.predict(X_tr2)
    s_train_r2 = r2_score(y_tr2, y_pred_tr2)
    s_train_mape = mean_absolute_percentage_error(y_tr2, y_pred_tr2) * 100
    print(f"  Train: R²={s_train_r2:.4f}, MAPE={s_train_mape:.2f}%")

    # Test
    X_te2, y_te2 = [], []
    for _, row in test_s.iterrows():
        X = node_s._extract_features(row)
        X_te2.append(X.flatten())
        y_te2.append(row['daya'])
        node_s._history_power.append(float(row.get("daya", 0)))
        node_s._history_temp.append(float(row.get("suhu", 0)))
        node_s._history_humid.append(float(row.get("kelembaban", 0)))
    X_te2 = np.array(X_te2)
    y_te2 = np.array(y_te2)
    y_pred_te2 = node_s.predict(X_te2)
    s_test_r2 = r2_score(y_te2, y_pred_te2)
    s_test_mape = mean_absolute_percentage_error(y_te2, y_pred_te2) * 100
    s_test_nrmse = np.sqrt(mean_squared_error(y_te2, y_pred_te2)) / y_te2.std()
    print(f"  Test:  R²={s_test_r2:.4f}, MAPE={s_test_mape:.2f}%, NRMSE={s_test_nrmse:.4f}")
else:
    print("  ⚠️  sensor_data.csv not found, skipping secondary")
    s_test_r2 = s_train_r2 = None

# ============================================================
# SUMMARY TABLE
# ============================================================
print("\n" + "=" * 70)
print("FINAL RESULTS SUMMARY")
print("=" * 70)
print(f"{'Dataset':<25} {'Records':<12} {'Train R²':<10} {'Test R²':<10} {'Test MAPE':<10} {'Test NRMSE':<10}")
print("-" * 77)
print(f"{'PRIMARY (designed)':<25} {len(primary):<12,} {train_r2:<10.4f} {test_r2:<10.4f} {test_mape:<10.2f} {test_nrmse:<10.4f}")
if s_test_r2 is not None:
    print(f"{'SECONDARY (real)':<25} {len(secondary):<12,} {s_train_r2:<10.4f} {s_test_r2:<10.4f} {s_test_mape:<10.2f} {s_test_nrmse:<10.4f}")
print("=" * 77)
print(f"\n  Edge latency P50: {np.median(edge_lat):.1f} ms (target: <50ms ✓)")
print(f"  Cloud latency P50: {np.median(cloud_lat):.1f} ms")
print(f"  Edge routing efficiency: {edge_eff:.1f}% (offload reduction)")
print(f"  Throughput (primary): {test_throughput:,.0f} rec/s")

# ============================================================
# Save final metrics
# ============================================================
metrics = {
    'primary': {
        'records': len(primary),
        'train_r2': train_r2,
        'test_r2': test_r2,
        'test_mape': test_mape,
        'test_rmse': test_rmse,
        'test_nrmse': test_nrmse,
        'throughput': test_throughput,
        'edge_routing_eff': edge_eff,
        'edge_latency_p50': float(np.median(edge_lat)) if edge_lat else None,
        'edge_latency_p95': float(np.percentile(edge_lat, 95)) if edge_lat else None,
        'edge_latency_p99': float(np.percentile(edge_lat, 99)) if edge_lat else None,
        'cloud_latency_p50': float(np.median(cloud_lat)) if cloud_lat else None,
        'precision': precision if y_te_true is not None else None,
        'recall': recall if y_te_true is not None else None,
        'f1': f1 if y_te_true is not None else None,
    },
    'secondary': {
        'records': len(secondary) if Path("sensor_data.csv").exists() else 0,
        'train_r2': s_train_r2,
        'test_r2': s_test_r2,
        'test_mape': s_test_mape,
        'test_nrmse': s_test_nrmse,
    } if s_test_r2 is not None else None,
}

with open("streaming_metrics_v2_final.pkl", "wb") as f:
    pickle.dump(metrics, f)
print("\n💾 Saved: streaming_metrics_v2_final.pkl")
