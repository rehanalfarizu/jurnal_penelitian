"""
Full streaming pipeline with z=2.5 anomaly threshold.
Replaces the interrupted notebook execution.
Runs the complete 2M records and saves all results.
"""
import pandas as pd
import numpy as np
import pickle
import time
import warnings
warnings.filterwarnings('ignore')

from collections import deque
from dataclasses import dataclass
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge

np.random.seed(42)

CONFIG = {
    "csv_path": "sensor_data.csv",
    "zscore_anomaly": 2.5,  # FIXED: was 2.0
    "temp_range": (15, 50),
    "humid_range": (20, 100),
    "fuse_weights": {"suhu": 0.30, "kelembaban": 0.25, "daya": 0.30, "orang": 0.15},
}

EDGE_LAT_MEDIAN = {'preprocess': 0.25, 'fusion': 0.4, 'anomaly': 0.15, 'predict': 0.5}
SUM_EDGE_LAT_MEDIAN = sum(EDGE_LAT_MEDIAN.values())
CLOUD_NET_OVERHEAD = 45
CLOUD_PROC_LAT = 150
CLOUD_DT_SYNC_LAT = 80
CLOUD_TOTAL_LAT = CLOUD_NET_OVERHEAD + CLOUD_PROC_LAT + CLOUD_DT_SYNC_LAT
EDGE_ENERGY_PER = {'preprocess': 3.5, 'fusion': 5.8, 'anomaly': 2.8, 'predict': 8.2}
SUM_EDGE_ENG = sum(EDGE_ENERGY_PER.values())
CLOUD_ENERGY = 1.2 + 0.6
DRIFT_INTERVAL = 10000
DRIFT_MAX_RATIO = 0.01

print(f"[CONFIG] zscore threshold = {CONFIG['zscore_anomaly']} (was 2.0)")

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
        self.window_power = deque(maxlen=1000)
        self.window_humidity = deque(maxlen=1000)
        self.window_temp = deque(maxlen=1000)
        self.total_samples = 0
        self.anomaly_count = 0
        self.cloud_route_count = 0
        self.scaler = StandardScaler()
        self.model = None
        self._r2_actual = deque(maxlen=1000)
        self._r2_pred = deque(maxlen=1000)
        self._r2_history = deque(maxlen=1000)
        self._warmup_count = 0
        self._cumulative_drift = 0.0
        self._history_power = deque(maxlen=300)
        self._history_suhu = deque(maxlen=300)
        self.retrain_every = retrain_every
        self._chunks_processed = 0
        self._stream_buffer_X = []
        self._stream_buffer_y = []
        self._buffer_max = 100000

    def compute_energy_score(self, row):
        s = self.weights
        return (
            s["suhu"] * max(0, min(1, (row["suhu"] - 25) / 10 + 0.5)) +
            s["kelembaban"] * max(0, min(1, (row["kelembaban"] - 50) / 30 + 0.5)) +
            s["daya"] * max(0, min(1, row["daya"] / 500)) +
            s["orang"] * max(0, min(1, row["jumlah_orang"] / 10))
        )

    def _extract_features(self, row):
        ts = pd.Timestamp(row["timestamp"]) if isinstance(row.get("timestamp"), (str, pd.Timestamp)) else pd.Timestamp.now()
        tegangan = row.get("tegangan", 220.0)
        arus = row.get("arus", row["daya"] / max(tegangan, 1))
        hour = ts.hour
        if 6 <= hour < 10: morning, midday, afternoon, evening, night = 1, 0, 0, 0, 0
        elif 10 <= hour < 14: morning, midday, afternoon, evening, night = 0, 1, 0, 0, 0
        elif 14 <= hour < 18: morning, midday, afternoon, evening, night = 0, 0, 1, 0, 0
        elif 18 <= hour < 22: morning, midday, afternoon, evening, night = 0, 0, 0, 1, 0
        else: morning, midday, afternoon, evening, night = 0, 0, 0, 0, 1
        h_power = list(self._history_power)
        h_suhu = list(self._history_suhu)
        ma_short_p = float(np.mean(h_power[-100:])) if len(h_power) >= 100 else (float(np.mean(h_power)) if h_power else 0.0)
        ma_long_p = float(np.mean(h_power[-300:])) if len(h_power) >= 300 else (ma_short_p if h_power else 0.0)
        ma_short_t = float(np.mean(h_suhu[-100:])) if len(h_suhu) >= 100 else (float(np.mean(h_suhu)) if h_suhu else 0.0)
        return np.array([[
            row["suhu"], row["kelembaban"], tegangan, arus, row["jumlah_orang"],
            tegangan * arus, row["suhu"] * row["kelembaban"],
            float(hour), float(ts.dayofweek), float(ts.day),
            float(morning), float(midday), float(afternoon), float(evening), float(night),
            ma_short_p, ma_long_p, ma_short_t,
        ]])

    def update_model(self, batch_X, batch_y):
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(batch_X)
        self.model = Ridge(alpha=1e-2, solver="auto", fit_intercept=True)
        self.model.fit(X_scaled, batch_y)
        return self.model

    def predict(self, X):
        X_scaled = self.scaler.transform(X)
        return self.model.predict(X_scaled)

    def estimate_r2(self, y_true, y_pred):
        self._r2_actual.append(y_true)
        self._r2_pred.append(y_pred)
        n = len(self._r2_actual)
        if n < 5:
            return None
        y_a = np.fromiter(self._r2_actual, dtype=float)
        y_p = np.fromiter(self._r2_pred, dtype=float)
        ss_res = np.sum((y_a - y_p) ** 2)
        ss_tot = np.sum((y_a - y_a.mean()) ** 2)
        if ss_tot <= 1e-6:
            return None
        r2 = 1.0 - ss_res / ss_tot
        self._r2_history.append(r2)
        return float(r2)

    def buffer_for_retrain(self, X, y):
        self._stream_buffer_X.append(X.flatten())
        self._stream_buffer_y.append(y)
        if len(self._stream_buffer_X) >= self._buffer_max:
            return True

    def flush_retrain(self):
        if not self._stream_buffer_X:
            return None
        buf_X = np.array(self._stream_buffer_X)
        buf_y = np.array(self._stream_buffer_y)
        self._stream_buffer_X.clear()
        self._stream_buffer_y.clear()
        self.update_model(buf_X, buf_y)
        print(f"  [RETRAIN] Fitted on {len(buf_y):,} buffered records")
        return buf_X, buf_y

    def maybe_retrain_chunk(self):
        if self.retrain_every is None:
            return
        self._chunks_processed += 1
        if self._chunks_processed % self.retrain_every == 0:
            self.flush_retrain()

    def process_record(self, row, idx):
        t0 = time.perf_counter()
        self.total_samples += 1
        temp_ok = self.config["temp_range"][0] <= row["suhu"] <= self.config["temp_range"][1]
        humid_ok = self.config["humid_range"][0] <= row["kelembaban"] <= self.config["humid_range"][1]
        energy_score = self.compute_energy_score(row)
        self.window_scores.append(energy_score)
        self.window_power.append(row["daya"])
        self.window_humidity.append(row["kelembaban"])
        self.window_temp.append(row["suhu"])
        is_anomaly = False
        if len(self.window_scores) > 10:
            recent = list(self.window_scores)[-50:]
            mean_s = np.mean(recent)
            std_s = np.std(recent)
            if std_s > 0:
                zscore = abs(energy_score - mean_s) / std_s
                if zscore > self.config["zscore_anomaly"]:
                    is_anomaly = True
        if is_anomaly:
            self.anomaly_count += 1
        X = self._extract_features(row)
        y_pred = self.predict(X)[0] if self.model else row.get("daya", 0)
        r2_raw = self.estimate_r2(row["daya"], y_pred)
        if r2_raw is None:
            r2_raw = 0.0
        self._history_power.append(float(row.get("daya", 0)))
        self._history_suhu.append(float(row.get("suhu", 0)))
        if self.model is not None:
            self.buffer_for_retrain(X, row["daya"])
        edge_lat = SUM_EDGE_LAT_MEDIAN
        edge_e = SUM_EDGE_ENG
        routed_to_cloud = is_anomaly or not temp_ok or not humid_ok
        total_lat = edge_lat
        total_e = edge_e
        cloud_lat = 0.0
        if routed_to_cloud:
            self.cloud_route_count += 1
            cloud_lat = CLOUD_TOTAL_LAT
            total_lat = edge_lat + CLOUD_NET_OVERHEAD + cloud_lat
            total_e = edge_e + CLOUD_ENERGY
        elapsed_ms = (time.perf_counter() - t0) * 1000
        return RecordMetrics(
            sample_idx=idx, timestamp=str(row["timestamp"]),
            anomaly=is_anomaly, routed_to_cloud=routed_to_cloud,
            edge_latency_ms=edge_lat + elapsed_ms, cloud_latency_ms=cloud_lat,
            total_latency_ms=total_lat + elapsed_ms, energy_mw=total_e + elapsed_ms * 0.1,
            energy_score=round(energy_score, 4), r2_running=round(r2_raw, 4),
            r2_raw=round(r2_raw, 6), daya=float(row["daya"]), pred_daya=float(y_pred),
        )

# ============ LOAD & PREPARE DATA ============
print("Loading dataset...")
raw = pd.read_csv(CONFIG['csv_path'])
col_map = {'Timestamp': 'timestamp', 'Suhu (C)': 'suhu', 'Kelembaban (%)': 'kelembaban',
           'Tegangan (V)': 'tegangan', 'Arus (A)': 'arus', 'Daya (W)': 'daya',
           'Jumlah Orang': 'jumlah_orang'}
raw.rename(columns=col_map, inplace=True)
raw['timestamp'] = pd.to_datetime(raw['timestamp'])
V = raw['tegangan'].values
I = raw['arus'].values
clean_day = V * I
noise_std = 0.05 * np.std(clean_day)
noise = np.random.normal(0, noise_std, len(clean_day))
raw['daya'] = clean_day + noise

# Drift
drift_signal = np.zeros(len(raw), dtype=float)
drift_accumulator = 0.0
for i in range(len(raw)):
    if i % DRIFT_INTERVAL == 0 and i > 0:
        drift_accumulator += np.random.randn() * 0.005 * max(abs(V[i]), abs(I[i]))
    drift_signal[i] = drift_accumulator
raw['daya'] += drift_signal

# Hard anomalies
n_hard = 200
hard_indices = np.random.choice(range(1000, len(raw) - 1000), n_hard, replace=False)
hard_indices_set = set(hard_indices.tolist())
for idx in hard_indices:
    anomaly_type = np.random.choice(['high_power', 'low_temp', 'negative_current'])
    if anomaly_type == 'high_power':
        raw.iloc[idx, raw.columns.get_loc('daya')] = np.random.uniform(800, 2000)
    elif anomaly_type == 'low_temp':
        raw.iloc[idx, raw.columns.get_loc('suhu')] = np.random.uniform(-50, -10)
    else:
        raw.iloc[idx, raw.columns.get_loc('arus')] = -np.random.uniform(10, 50)

# Soft anomalies
n_soft = 2000
available = np.setdiff1d(np.arange(len(raw)), list(hard_indices))
soft_indices = np.random.choice(available, n_soft, replace=False)
soft_indices_set = set(soft_indices.tolist())
for idx in soft_indices:
    drift_type = np.random.choice(['power_drift', 'temp_drift'])
    if drift_type == 'power_drift':
        raw.iloc[idx, raw.columns.get_loc('daya')] *= np.random.uniform(0.9, 1.1)
    else:
        raw.iloc[idx, raw.columns.get_loc('suhu')] += np.random.uniform(-8, 8)

print(f"Data ready: {len(raw):,} records, hard={n_hard}, soft={n_soft}")
print(f"   Hard indices sorted: {sorted(hard_indices)[:5]} ... {sorted(hard_indices)[-5:]}")

# ============ WARMUP ============
node = EdgeStreamingNode(CONFIG, retrain_every=5)
warmup_size = 50000
print(f"\nWarming up on {warmup_size:,} records...")
X_warmup_list, y_warmup_list = [], []
for local_idx, (_, row) in enumerate(raw.head(warmup_size).iterrows()):
    X = node._extract_features(row)
    X_warmup_list.append(X.flatten())
    y_warmup_list.append(row['daya'])
    node._history_power.append(float(row.get("daya", 0)))
    node._history_suhu.append(float(row.get("suhu", 0)))
X_warmup = np.array(X_warmup_list)
y_warmup = np.array(y_warmup_list)
node.update_model(X_warmup, y_warmup)
y_pred_train = node.predict(X_warmup)
train_r2 = 1 - np.sum((y_warmup - y_pred_train)**2) / np.sum((y_warmup - y_warmup.mean())**2)
print(f"  Training R² = {train_r2:.4f}")

# ============ STREAMING ============
chunk_size = 50000
all_results = []
start_global = time.time()

for chunk_start in range(0, len(raw), chunk_size):
    chunk = raw.iloc[chunk_start:chunk_start + chunk_size]
    chunk_num = chunk_start // chunk_size + 1
    n_records = len(chunk)
    t0_stream = time.perf_counter()
    chunk_results = []
    for local_idx, (_, row) in enumerate(chunk.iterrows()):
        global_idx = chunk_start + local_idx
        metrics = node.process_record(row, global_idx)
        chunk_results.append(metrics)
    elapsed = time.perf_counter() - t0_stream
    throughput = n_records / elapsed if elapsed > 0 else 0
    anom = sum(1 for r in chunk_results if r.anomaly)
    cloud = sum(1 for r in chunk_results if r.routed_to_cloud)
    all_r2 = [r.r2_raw for r in chunk_results]
    valid_r2 = [r for r in all_r2 if r is not None]
    mean_r2 = np.mean(valid_r2) if valid_r2 else 0.0
    neg_r2_count = sum(1 for r in valid_r2 if r < 0)

    retrain_result = node.maybe_retrain_chunk()
    if retrain_result is not None:
        buf_X, buf_y = retrain_result
        buf_pred = node.predict(buf_X)
        buf_r2 = 1.0 - np.sum((buf_y - buf_pred)**2) / np.sum((buf_y - buf_y.mean())**2) if np.sum((buf_y - buf_y.mean())**2) > 0 else 0.0
        print(f"    [BUFFER R²] Chunk {chunk_num}: R²={buf_r2:.4f}")
    if len(node._r2_history) > 0:
        print(f"    [ROLLING R²] Mean: {np.mean(list(node._r2_history)):.4f}")

    all_results.extend(chunk_results)
    print(f'Chunk {chunk_num:>2} | {n_records:>6,} rec | anom={anom:>5} ({anom/n_records*100:.1f}%) | '
          f'cloud={cloud:>5} | through={throughput:6.0f}/s | R²={mean_r2:.4f} | neg_R²={neg_r2_count}/{len(valid_r2):,}')

stream_time = time.time() - start_global
print(f"\n{'='*60}")
print(f"Streaming DONE in {stream_time:.0f}s ({len(raw):,} records, {len(all_results):,} processed)")
print(f"Total anomalies detected: {sum(1 for r in all_results if r.anomaly):,}")
print(f"Total cloud-routed: {sum(1 for r in all_results if r.routed_to_cloud):,}")

# Save
import pickle
with open('streaming_results_z25.pkl', 'wb') as f:
    pickle.dump(all_results, f)
print("Saved: streaming_results_z25.pkl")

# Save hard/soft indices for analysis 2
with open('anomaly_indices.pkl', 'wb') as f:
    pickle.dump({'hard_indices': hard_indices, 'soft_indices': soft_indices}, f)
print("Saved: anomaly_indices.pkl")
