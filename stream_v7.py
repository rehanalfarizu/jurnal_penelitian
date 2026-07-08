#!/usr/bin/env python3
"""v7 Optimized Streaming Pipeline — 17 features, Ridge alpha=1e-2, z=2.5"""
import os, sys
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', buffering=1)
sys.stderr = os.fdopen(sys.stderr.fileno(), 'w', buffering=1)

import pandas as pd
import numpy as np
import pickle
import time
import warnings
warnings.filterwarnings('ignore')

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

np.random.seed(42)
sns.set_style('whitegrid')
plt.rcParams['figure.figsize'] = (12, 5)

from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from collections import deque

CONFIG = {
    "csv_path": "sensor_data.csv",
    "zscore_anomaly": 2.5,
    "fuse_weights": {"suhu": 0.30, "kelembaban": 0.25, "daya": 0.30, "orang": 0.15},
}

SUM_EDGE_LAT = 1.3
SUM_EDGE_ENG = 20.3
CLOUD_TOTAL_LAT = 275.0
CLOUD_ENERGY = 1.8
DRIFT_INTERVAL = 10000

print('Config OK | z=2.5 | Ridge 17-fitur')

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

class EdgeStreamingNode:
    def __init__(self, config, retrain_every=None):
        self.config = config
        self.weights = config["fuse_weights"]
        self.window_scores = deque(maxlen=1000)
        self.total_samples = 0
        self.anomaly_count = 0
        self.cloud_route_count = 0
        self.scaler = StandardScaler()
        self.model = None
        self._wp = deque(maxlen=1000)
        self._wh = deque(maxlen=1000)
        self._wt = deque(maxlen=1000)
        self._hp = deque(maxlen=300)
        self._hs = deque(maxlen=300)
        self.retrain_every = retrain_every
        self._chunks_processed = 0
        self._tod_cache = {}
        for h in range(24):
            if 6 <= h < 10: tod = (1,0,0,0,0)
            elif 10 <= h < 14: tod = (0,1,0,0,0)
            elif 14 <= h < 18: tod = (0,0,1,0,0)
            elif 18 <= h < 22: tod = (0,0,0,1,0)
            else: tod = (0,0,0,0,1)
            self._tod_cache[h] = tod

    def predict(self, X):
        X_scaled = self.scaler.transform(X)
        return self.model.predict(X_scaled)

    def _energy_score(self, row):
        s = self.weights
        return (
            s["suhu"] * max(0, min(1, (row["suhu"] - 25) / 10 + 0.5)) +
            s["kelembaban"] * max(0, min(1, (row["kelembaban"] - 50) / 30 + 0.5)) +
            s["daya"] * max(0, min(1, row["daya"] / 500)) +
            s["orang"] * max(0, min(1, row["jumlah_orang"] / 10))
        )

    def _extract_features(self, row):
        ts = row["timestamp"]
        h = ts.hour
        m, md, af, ev, nt = self._tod_cache.get(h, (0,0,0,0,1))
        dow = float(ts.dayofweek)
        d = float(ts.day)
        tegangan = row["tegangan"]
        arus = row["arus"]
        suhu = row["suhu"]
        kelembaban = row["kelembaban"]
        daya = row["daya"]
        orang = row["jumlah_orang"]
        hp = list(self._hp)
        hs = list(self._hs)
        ma_short_p = sum(hp) / min(len(hp), 100) if hp else 0.0
        ma_long_p = sum(hp[-300:]) / 300 if len(hp) >= 300 else (ma_short_p if hp else 0.0)
        ma_short_t = sum(hs) / min(len(hs), 100) if hs else 0.0
        return np.array([[
            suhu, kelembaban, tegangan, arus, orang,
            suhu * kelembaban,
            float(h), dow, d,
            float(m), float(md), float(af), float(ev), float(nt),
            ma_short_p, ma_long_p, ma_short_t,
        ]])

    def process_record(self, row, idx):
        self.total_samples += 1
        X = self._extract_features(row)
        es = self._energy_score(row)
        self.window_scores.append(es)
        self._wp.append(row["daya"])
        self._wh.append(row["kelembaban"])
        self._wt.append(row["suhu"])

        is_anomaly = False
        if len(self.window_scores) > 10:
            recent = list(self.window_scores)[-50:]
            mu = sum(recent) / len(recent)
            var = sum((x - mu) ** 2 for x in recent) / len(recent)
            std = var ** 0.5
            if std > 0:
                zscore = abs(es - mu) / std
                if zscore > self.config["zscore_anomaly"]:
                    is_anomaly = True

        if is_anomaly:
            self.anomaly_count += 1

        if self.model is not None:
            y_pred = self.model.predict(self.scaler.transform(X))[0]
        else:
            y_pred = 0.0

        routed = is_anomaly
        if routed:
            self.cloud_route_count += 1
            return RecordMetrics(
                sample_idx=idx, timestamp=str(row["timestamp"]),
                anomaly=True, routed_to_cloud=True,
                edge_latency_ms=SUM_EDGE_LAT, cloud_latency_ms=CLOUD_TOTAL_LAT,
                total_latency_ms=SUM_EDGE_LAT + CLOUD_TOTAL_LAT,
                energy_mw=SUM_EDGE_ENG + CLOUD_ENERGY,
                energy_score=round(es, 4),
                r2_running=0.0, r2_raw=0.0,
                daya=float(row["daya"]), pred_daya=float(y_pred),
            )
        else:
            return RecordMetrics(
                sample_idx=idx, timestamp=str(row["timestamp"]),
                anomaly=False, routed_to_cloud=False,
                edge_latency_ms=SUM_EDGE_LAT, cloud_latency_ms=0.0,
                total_latency_ms=SUM_EDGE_LAT,
                energy_mw=SUM_EDGE_ENG,
                energy_score=round(es, 4),
                r2_running=0.0, r2_raw=0.0,
                daya=float(row["daya"]), pred_daya=float(y_pred),
            )

    def update_history(self, row):
        self._hp.append(float(row["daya"]))
        self._hs.append(float(row["suhu"]))

    def update_model(self, batch_X, batch_y):
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(batch_X)
        self.model = Ridge(alpha=1e-2, solver="auto", fit_intercept=True)
        self.model.fit(X_scaled, batch_y)

# ===== DATA LOADING =====
col_map = {
    'Timestamp': 'timestamp', 'Suhu (C)': 'suhu',
    'Kelembaban (%)': 'kelembaban', 'Tegangan (V)': 'tegangan',
    'Arus (A)': 'arus', 'Daya (W)': 'daya',
    'Jumlah Orang': 'jumlah_orang',
}
print('Reading dataset...')
raw = pd.read_csv(CONFIG['csv_path'])
raw.rename(columns=col_map, inplace=True)
raw['timestamp'] = pd.to_datetime(raw['timestamp'])
n_total = len(raw)
print(f'Dataset: {n_total:,} records | Daya: mean={raw["daya"].mean():.1f}W std={raw["daya"].std():.1f}W')

# Drift injection
drift_signal = np.zeros(n_total, dtype=float)
drift_acc = 0.0
for i in range(n_total):
    if i % DRIFT_INTERVAL == 0 and i > 0:
        drift_acc += np.random.randn() * 0.005 * max(abs(raw['tegangan'].iloc[i]), 1)
    drift_signal[i] = drift_acc
raw['daya_drift'] = raw['daya'] + drift_signal

# Hard anomalies
n_hard = 200
hard_idx = np.random.choice(range(1000, n_total - 1000), n_hard, replace=False)
for idx in hard_idx:
    atype = np.random.choice(['high_power', 'low_temp', 'negative_current'])
    if atype == 'high_power':
        raw.at[idx, 'daya'] = np.random.uniform(800, 2000)
    elif atype == 'low_temp':
        raw.at[idx, 'suhu'] = np.random.uniform(-50, -10)
    else:
        raw.at[idx, 'arus'] = -np.random.uniform(10, 50)

# Soft anomalies
n_soft = 2000
avail = np.setdiff1d(np.arange(n_total), hard_idx)
soft_idx = np.random.choice(avail, n_soft, replace=False)
for idx in soft_idx:
    if np.random.choice(['power', 'temp']):
        raw.at[idx, 'daya'] *= np.random.uniform(0.9, 1.1)
    else:
        raw.at[idx, 'suhu'] += np.random.uniform(-8, 8)

print(f'Drift + {n_hard} hard + {n_soft} soft injected')

# ===== WARMUP =====
warmup_n = 50000
node = EdgeStreamingNode(CONFIG, retrain_every=5)
print(f'\nWarmup: {warmup_n:,} records...')
t0 = time.time()
X_warm, y_warm = [], []
for _, row in raw.head(warmup_n).iterrows():
    X = node._extract_features(row)
    X_warm.append(X.flatten())
    y_warm.append(row['daya'])
    node.update_history(row)
X_warm = np.array(X_warm)
y_warm = np.array(y_warm)
node.update_model(X_warm, y_warm)
warmup_time = time.time() - t0

yp = node.predict(X_warm)
ss_res = np.sum((y_warm - yp)**2)
ss_tot = np.sum((y_warm - y_warm.mean())**2)
train_r2 = 1 - ss_res / ss_tot
print(f'Training R²={train_r2:.4f} | pred mean={yp.mean():.2f} actual mean={y_warm.mean():.2f}')
print(f'Rolling features populated: {sum(1 for x in X_warm[:, 14] if x != 0.0)}/{warmup_n}')
print(f'Warmup throughput: {warmup_n/warmup_time:,.0f} rec/s in {warmup_time:.1f}s')

# ===== STREAMING =====
print(f'\n=== STREAMING {n_total:,} records ===')
all_results = []
node._hp.clear()
node._hs.clear()
start_time = time.time()
chunk_size = 200000

for cs in range(0, n_total, chunk_size):
    ce = min(cs + chunk_size, n_total)
    chunk_num = cs // chunk_size + 1
    n_rec = ce - cs
    t0 = time.time()

    for gi in range(cs, ce):
        row = raw.iloc[gi]
        m = node.process_record(row, gi)
        node.update_history(row)
        all_results.append(m)

    elapsed = time.time() - t0
    tp = n_rec / elapsed if elapsed > 0 else 0
    anom = sum(1 for r in all_results[cs:ce] if r.anomaly)
    cloud = sum(1 for r in all_results[cs:ce] if r.routed_to_cloud)

    print(
        f'  Chunk {chunk_num:>2} ({cs:>8,}-{ce:>8,}) | '
        f'{elapsed:6.1f}s | {tp:7,.0f} rec/s | '
        f'anom={anom:>5} | cloud={cloud:>5}'
    )

total_elapsed = time.time() - start_time
total_tp = n_total / total_elapsed if total_elapsed > 0 else 0
print(f'\nDone in {total_elapsed:.0f}s')
print(f'  Throughput: {total_tp:,.0f} rec/s')
print(f'  Anomalies detected: {sum(1 for r in all_results if r.anomaly):,}')
print(f'  Cloud-routed: {sum(1 for r in all_results if r.routed_to_cloud):,}')

with open('streaming_results.pkl', 'wb') as f:
    pickle.dump(all_results, f)
print(f'Saved: streaming_results.pkl ({len(all_results):,} records)')
print('DONE')
