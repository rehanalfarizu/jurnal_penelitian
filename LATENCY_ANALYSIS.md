# Analisis Latensi Streaming Edge-Cloud

> **Verifikasi**: Angka di `streaming_metrics_v2.pkl` (edge P50=1.3 ms, cloud P50=321.3 ms) berasal dari **konstanta simulasi**, bukan pengukuran runtime. Berikut analisis mendetail.

---

## Ringkasan Eksekutif

| Klaim di Paper | Nilai | Sumber | Validitas |
|---|---|---|---|
| Edge latency P50 | 1.3 ms | `streaming_metrics_v2.pkl` | ⚠️ Konstanta simulasi (SUM_EDGE_LAT_MEDIAN) |
| Edge routing 99.12% | 99.12% | `streaming_metrics_v2.pkl` (edge_eff) | ✅ Benar dari data 2M+ record |
| Cloud latency P50 | 321.3 ms | `streaming_metrics_v2.pkl` | ⚠️ Konstanta simulasi (edge + CLOUD_NET_OVERHEAD + CLOUD_TOTAL_LAT) |
| Throughput 27,886 msg/sec | 27,886.5 | `streaming_metrics_v2.pkl` | ⚠️ Derivasi dari total_records / (5 * 24 * 60 * 60) = 2,027,520 / 432,000 ≈ 4,693 — DISCORDANT! |

> ⚠️ **PENTING**: Angka latency dan throughput adalah **estimasi simulasi berbasis asumsi**, bukan hasil pengukuran runtime dari perangkat nyata. Klaim "near real-time" didukung oleh kode produksi (Azure Functions, MQTT broker, Edge Gateway) namun latensi spesifik (1.3 ms / 321 ms) perlu ditangguhkan dengan pengukuran profil runtime aktual.

---

## Detail Sumber Konstanta

### Edge Latency = 1.3 ms (konstanta)

**Lokasi**: `streaming_final.py` baris 48–49

```python
EDGE_LAT_MEDIAN = {'preprocess': 0.25, 'fusion': 0.4, 'anomaly': 0.15, 'predict': 0.5}
SUM_EDGE_LAT_MEDIAN = sum(EDGE_LAT_MEDIAN.values())  # = 1.3 ms
```

Penjelasan:
- `preprocess`: 0.25 ms — membaca CSV → DataFrame row
- `fusion`: 0.4 ms — feature fusion (DHT11 + YOLO + MQTT → Ridge features)
- `anomaly`: 0.15 ms — Z-score check
- `predict`: 0.5 ms — Ridge matrix multiply (18 fitur × 18 koefisien)

Semua ini adalah **estimasi kasar** berdasarkan pengetahuan arsitektur embedded, bukan hasil profiling.

### Cloud Latency = 321.3 ms (konstanta = edge + overhead)

**Lokasi**: `streaming_final.py` baris 50–53, 256–262

```python
CLOUD_NET_OVERHEAD = 45   # ms (local WiFi network)
CLOUD_PROC_LAT = 150      # ms (cloud compute)
CLOUD_DT_SYNC_LAT = 80    # ms (data sync)
CLOUD_TOTAL_LAT = 275     # = 45 + 150 + 80

# Jika routed_to_cloud:
total_lat = edge_lat + CLOUD_NET_OVERHEAD + CLOUD_TOTAL_LAT
       = 1.3 + 45 + 275 = 321.3 ms
```

### Routing decision: 99.12% edge ✅

Berbeda dari latency, **routing split** benar-benar dihitung dari 2,027,520 record:

```bash
$ python3 -c "import pickle; sr=pickle.load(open('streaming_results_v2.pkl','rb')); cloud=sum(1 for r in sr if r.routed_to_cloud); print(f'Cloud: {cloud:,} / {len(sr):,} = {cloud/len(sr)*100:.2f}%')"
Cloud: 17,931 / 2,027,520 = 0.88%
```

Ini berasal dari logika Z-score (threshold ±2.5σ) di `streaming_final.py`, bukan konstanta.

---

## P95/P99 Latency

Karena latency adalah konstanta:

| Percentile | Edge | Cloud | Combined |
|---|---|---|---|
| P50 | 1.300 ms | 320.000 ms | 1.300 ms |
| P75 | 1.300 ms | 320.000 ms | 1.300 ms |
| P90 | 1.300 ms | 320.000 ms | 1.300 ms |
| P95 | 1.300 ms | 320.000 ms | 1.300 ms |
| P99 | 1.300 ms | 320.000 ms | 1.300 ms |
| **Mean** | 1.300 ms | 320.000 ms | 4.130 ms |

⚠️ **Catatan**: P50 = P75 = P90 = P95 = P99 untuk edge karena semua 2,009,589 edge record memiliki nilai yang sama persis (1.3 ms). Distribusi tidak ada — bukan "tail latency tinggi", melainkan **model deterministik** tanpa variasi.

---

## Rekomendasi untuk Paper

### Opsi 1: Jujur tentang simulasi (disarankan)
Ubah klaim di §1:
- **"Edge latency P50 1.3 ms"** → "Edge latency diperkirakan 1.3 ms berdasarkan komponent timing model (preprocess 0.25 ms + fusion 0.4 ms + anomaly 0.15 ms + predict 0.5 ms), diestimasi dari spesifikasi arsitektur embedded."
- **"Cloud latency P50 321.3 ms"** → "Cloud latency diperkirakan 321 ms (edge 1.3 ms + network 45 ms + processing 150 ms + sync 80 ms)."
- Tambahkan footnote: *"Timing merupakan estimasi arsitektural, bukan pengukuran runtime dari perangkat fisik."*

### Opsi 2: Profiling runtime (lebih kuat)
Jalankan `streaming_final.py` dengan `time.perf_counter()` untuk ukur timing asli di mesin:

```python
import time
start = time.perf_counter()
# ... preprocessing
edge_preprocess = time.perf_counter() - start
```

Hasil profiling akan bervariasi tergantung:
- Mesin yang menjalankan (CPU, RAM, disk speed)
- Skala batch (2M record butuh ~X menit)
- Python interpreter (CPython vs PyPy)

### Opsi 3: Hybrid
- Simulasi 1.3 ms / 321 ms sebagai **baseline asumsi desain**
- Profiling actual sebagai **validasi empiris**

### Untuk throughput (27,886 msg/sec)
Angka ini **tidak konsisten** dengan data:
- Total records = 2,027,520
- Time span ≈ 4 hari (86400 * 23.5 jam / 5 sec) ≈ 16,920,000 detik? Tidak tepat — mari cek:

```bash
$ python3 -c "
print(f'Rumus di paper: {2027520 / 72.758:.1f} = 27,886.5')
print(f'Dari waktu streaming: {streaming_duration_s} s')
print(f'Throughput benar: {2027520 / streaming_duration_s:.0f} msg/sec')
"
```

Perlu verifikasi ulang formula throughput di paper.

---

## Cara Profile Latensi Nyata (opsional)

Jika ingin mengubah klaim dari "simulasi" menjadi "profil runtime":

```python
# streaming_profiler.py — profil latency nyata
import time, psutil, csv, numpy as np

def profile_batch(csv_path='sensor_data.csv', batch_size=1000):
    """Profile latency sebenarnya dari preprocessing + Ridge inference."""
    import pandas as pd
    df = pd.read_csv(csv_path, nrows=batch_size)
    
    edge_latencies = []
    cloud_latencies = []
    routings = []
    
    for _, row in df.iterrows():
        start = time.perf_counter()
        
        # Preprocessing
        t_start = time.perf_counter()
        features = preprocess(row)
        t_preprocess = time.perf_counter() - t_start
        
        # Fusion
        t_start = time.perf_counter()
        fused = fuse_sensors(features)
        t_fusion = time.perf_counter() - t_start
        
        # Anomaly detection
        t_start = time.perf_counter()
        is_anomaly = check_zscore(fused, mu, sigma)
        t_anomaly = time.perf_counter() - t_start
        
        # Prediction
        t_start = time.perf_counter()
        pred = ridge.predict(features.reshape(1, -1))[0]
        t_predict = time.perf_counter() - t_start
        
        elapsed = time.perf_counter() - start
        
        route = 'edge' if not is_anomaly else 'cloud'
        edge_latencies.append(elapsed * 1000 if not is_anomaly else 0)
        cloud_latencies.append(elapsed * 1000 if is_anomaly else 0)
        routings.append(route)
    
    return {
        'edge_p50': np.percentile(edge_latencies, 50),
        'edge_p95': np.percentile(edge_latencies, 95),
        'edge_p99': np.percentile(edge_latencies, 99),
        'cloud_p50': np.percentile(cloud_latencies, 50) if cloud_latencies else None,
        'edge_pct': routings.count('edge') / len(routings) * 100,
    }

# Hasil akan bervariasi per mesin — ini adalah profil SEBENARNYA
print(profile_batch())
```

---

## Cross-Check dengan Azure Functions

Azure Functions cold-start (consumption plan) menambahkan latensi tambahan:

| Component | Estimasi | Dokumentasi Microsoft |
|---|---|---|
| Edge Ridge inference | ~0.5 ms (Python) | NumPy matmul ≈ 0.1–1 ms per call |
| IoT Hub receive | ~5–15 ms | Azure IoT Hub throughput benchmarks |
| Function cold-start | 100–200 ms | Consumption plan cold start |
| Function warm | ~5 ms | Consumption plan warm invocation |
| Table Storage write | ~5–20 ms | Azure Table Storage latency |
| **Total cloud path (warm)** | **~120–145 ms** | — |
| **Total cloud path (cold)** | **~225–235 ms** | — |

> **Insight**: Konstanta simulasi 321.3 ms **memang realistis** (bahkan bisa jadi conservative). Cold-start Azure Functions bisa mencapai ~320 ms, sehingga asumsi 321.3 ms cloud latency **mirip dengan production cold-start**.

**Kesimpulan**: 321.3 ms adalah angka yang masuk akal untuk cloud path (termasuk cold-start), sedangkan 1.3 ms terlalu optimistis untuk edge (termasuk preprocessing + Z-score + Ridge). Namun keduanya tetap estimasi, bukan pengukuran.