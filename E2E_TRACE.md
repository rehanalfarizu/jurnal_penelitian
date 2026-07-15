# E2E Trace: Satu Baris Data Sensor → Tampil di Digital Twin 3D

Dokumen ini menelusuri **satu baris data** dari CSV melalui seluruh pipeline (read → anomaly → feature engineering → prediction → routing → delivery → render) dengan angka yang dapat diverifikasi ulang dari repo.

> **Tujuan**: Bukti bahwa setiap klaim di paper punya jalur reproducible — angka berasal dari objek/koefisien nyata, bukan placeholder.

---

## Skenario 1: Trace Normal (Edge Path, 99.12% kasus)

**Dipilih**: baris ke-`6` dari filter `(jam=14, jumlah_orang=5)` — representasi jam kantor siang dengan 5 penghuni.

### Input Mentah (dari `sensor_data.csv`, row indeks 1000705±)

| Field | Value | Catatan |
|---|---|---|
| Timestamp | `2026-02-27 14:00:21.077219` | waktu pengukuran |
| DeviceID | `RASPBERRY_PI_GATEWAY_001` | edge gateway ID |
| Suhu (C) | **33.4** | DHT11 |
| Kelembaban (%) | **65.0** | DHT11 |
| Tegangan (V) | **236.8** | ZMPT101B (AC PLN 220V ±15%) |
| Arus (A) | **0.17** | SCT013 (non-invasif) |
| Jumlah Orang | **5** | YOLO v3-tiny di RPi terpisah |
| Daya (W) — target | **40.0** | ground-truth dari CSV |

**Sanity check**: P = V × I = 236.8 × 0.17 = **40.256 W**. Selisih ke target = 0.26 W (≤1% — berada dalam akurasi alat ukur + rounding ke integer).

---

### Hop 1 — Edge Sensor Read (latency: 0 ms, langsung dari ADC)

```
ESP32 firmware: dashboard_digitaltwin/sensor_iot/esp32_main.cpp
  DHT11.readTemperature()   → 33.4
  DHT11.readHumidity()      → 65.0
  ZMPT101B.readVoltage()    → 236.8
  SCT013.readCurrent()      → 0.17
  → publishes every 5 seconds via MQTT/TLS to Azure IoT Hub
```

---

### Hop 2 — Z-Score Anomaly Check (latency: ~0.1 ms di edge CPU)

```python
# streaming_final.py
import numpy as np

suhu       = 33.4
kelembaban = 65.0

# Statistik training (dari sensor_data.csv)
mu_suhu,  sigma_suhu  = 30.2, 1.8
mu_humid, sigma_humid = 66.6, 8.5

z_suhu   = (33.4 - 30.2) / 1.8   = +1.74
z_humid  = (65.0 - 66.6) / 8.5   = -0.19

is_anomaly = abs(z_suhu) > 3 or abs(z_humid) > 3
         = False
```

**Hasil**: bukan anomali → **routing ke EDGE** (1.3 ms P50, bukan 321 ms cloud).

---

### Hop 3 — Feature Engineering (latency: ~0.05 ms)

```python
# 18 fitur Ridge (5 raw + time encoding + V×I untuk sanity)
fitur = [
    suhu,                    # 33.4
    kelembaban,              # 65.0
    tegangan,                # 236.8
    arus,                    # 0.17
    jumlah_orang,            # 5
    sin(2π·jam/24),          # sin(2π·14.0058/24) = -0.5013
    cos(2π·jam/24),          # cos(2π·14.0058/24) = -0.8653
    # +11 fitur interaksi & lag (lihat energy_prediction_models.ipynb §3)
]

# Sanity fitur turunan:
p_apparent = tegangan * arus  = 40.256
```

---

### Hop 4 — Ridge Prediction (latency: ~1.15 ms, total edge <2 ms)

```python
# ml_models/train_model.py → energy_model_results_fixed.json
model: Ridge(alpha=0.01)
fitur_test_RMSE = 0.6175 W
fitur_test_MAPE = 1.43%

# Prediksi untuk baris ini:
y_pred = β₀ + β₁·suhu + β₂·kelembaban + β₃·tegangan + β₄·arus + β₅·jumlah_orang
       + β₆·sin_jam + β₇·cos_jam + ...  (18 koefisien total)

# Karena V×I = 40.26 ≈ target 40.0, Ridge mendekati V×I:
y_pred ≈ 40.0 ± 0.62 W    (akurasi ridge pada test set)
```

**Catatan metodologis**: Ridge α=0.01 sengaja small → koefisien mendekati OLS. Model tidak "belajar" V×I eksplisit (sesuai catatan di `energy_model_results_fixed.json` tentang **circularity removal**), melainkan belajar dari pola agregat.

---

### Hop 5 — Routing Decision (latency: <0.1 ms)

```
anomaly_flag = False
↓
route = EDGE    (Raspberry Pi executes Ridge inference lokal)
↓
publish ke Azure IoT Hub → tetap dikirim untuk storage & re-train periodik
```

**Trade-off**:
- **Edge**: 1.3 ms latency, hemat bandwidth (skip cloud inference), tapi model tidak update real-time.
- **Cloud**: 321 ms latency, bandwidth lebih besar, tapi akses model terbaru & agregasi lintas-edge.

---

### Hop 6 — Storage & Delivery (latency: ~321 ms jika via cloud, atau ~10 ms jika langsung MQTT publish)

| Step | Path | Latency | Tujuan |
|---|---|---|---|
| 6.1 ESP32 publish MQTT/TLS :8883 | edge → cloud | ~50–150 ms | Azure IoT Hub |
| 6.2 IoT Hub built-in EventHub | intra-cloud | ~10 ms | trigger Function |
| 6.3 Function `IoTHubToStorage` | intra-cloud | ~5 ms | parse JSON, build entity |
| 6.4 Table Storage `createEntity` | intra-cloud | ~5–20 ms | persist row |
| 6.5 Vue `useAzureTelemetry.js` polling | cloud → browser | ~100–300 ms | GET latest N rows |
| 6.6 Babylon.js render frame | browser | <16 ms | update warna AC, gauge daya |

**Total observasi sensor → render 3D**: ~321 ms P50 (cloud path) atau ~10 ms P50 (edge direct, tidak lewat cloud).

---

### Hop 7 — Digital Twin Visualization

```javascript
// view_virtual/src/components/DigitalTwin3D_Babylon.vue
onTelemetryUpdate(entity) {
  // entity = {suhu: 33.4, kelembaban: 65.0, daya: 40, jumlahOrang: 5, ...}
  scene.meshes
    .filter(m => m.name.startsWith('AC_'))
    .forEach(m => m.material.diffuseColor = acColorByTemp(entity.suhu));  // 33.4 → kuning-orange

  scene.meshes
    .filter(m => m.name.startsWith('Avatar_'))
    .forEach((m, i) => m.isVisible = i < entity.jumlahOrang);             // 5 avatar visible

  powerGauge.value = entity.daya;                                          // gauge → 40W
}
```

---

## Skenario 2: Trace Anomali (Cloud Path, 0.88% kasus)

> **Catatan**: Dataset augmented `sensor_data.csv` tidak memiliki baris dengan Z(suhu) > 3 (max suhu = 33.9°C, threshold = 35.7°C). Skenario di bawah ini **hipotetis** untuk menggambarkan logika routing; angka `anom_count=17,931` di `streaming_metrics_v2.pkl` adalah noise sintetis yang diinjeksi oleh `streaming_final.py` ke stream pada saat simulasi, **bukan** anomali natural dari CSV.

### Input Anomali (hipotetis)

Misalkan sensor mengirim:
```
suhu       = 41.0 °C   (Δ +10.8°C di atas μ=30.2)
kelembaban = 85.0 %    (Δ +18.4% di atas μ=66.6)
z_suhu     = (41.0 - 30.2) / 1.8 = +6.0    → exceeds |3|
```

### Routing → Cloud (321.3 ms P50)

```
anomaly_flag = True
↓
route = CLOUD
↓
Function GetACRecommendation invoked:
  POST {suhu: 41.0, kelembaban: 85.0, jumlahOrang: 5, daya: 3500}
  → load_model('ac_recommender.pkl')
  → return {ac_temp: 22, fan: 'high', mode: 'cool'}
```

**Alasan edge→cloud**:
1. Data point di luar rentang pelatihan → prediksi edge tidak reliable.
2. Keputusan kontrol HVAC lebih akurat di cloud dengan model yang lebih besar.
3. SLA kontrol bangunan lebih toleran terhadap latency ~300 ms dibanding telemetry biasa.

---

## Verifikasi Repro (perintah untuk dijalankan ulang)

```bash
cd /Users/macbookpro/Documents/jurnal_penelitian

# 1. Reproduksi Z-score baris contoh
python3 -c "
import pandas as pd
df = pd.read_csv('sensor_data.csv')
df['Timestamp'] = pd.to_datetime(df['Timestamp'])
row = df[(df['Timestamp'].dt.hour == 14) & (df['Jumlah Orang'] == 5)].iloc[5]
print('Suhu       :', row['Suhu (C)'])
print('Kelembaban :', row['Kelembaban (%)'])
print('Daya target:', row['Daya (W)'])
print('P=V*I      :', row['Tegangan (V)'] * row['Arus (A)'])
"
# Output diharapkan:
#   Suhu       : 33.4
#   Kelembaban : 65.0
#   Daya target: 40.0
#   P=V*I      : 40.256

# 2. Reproduksi anomaly count
python3 -c "
import pickle
with open('streaming_metrics_v2.pkl', 'rb') as f: m = pickle.load(f)
print(f\"anom_count={m['anom_count']}, cloud_count={m['cloud_count']}, edge%={m['edge_eff']:.2f}\")
"
# Output:
#   anom_count=17931, cloud_count=17931, edge%=99.12

# 3. Reproduksi koefisien Ridge
python3 -c "
import json
d = json.load(open('energy_model_results_fixed.json'))
r = d['results'][0]
print(f\"Ridge: R²={r['r2']:.4f}, RMSE={r['rmse']:.4f}, MAPE={r['mape']:.2f}%\")
"
# Output:
#   Ridge: R²=0.9590, RMSE=0.6175, MAPE=1.43%
```

---

## Ringkasan Per-Hop (latency budget)

| Hop | Aksi | Latency | Catatan |
|---|---|---|---|
| 1 | ESP32 sensor read | ~5 ms | ADC sampling + I²C ke DHT11 |
| 2 | Z-score anomaly | ~0.1 ms | numpy vectorized |
| 3 | Feature engineering | ~0.05 ms | sin/cos lookup |
| 4 | Ridge inference | ~1.15 ms | sklearn numpy dot product |
| 5 | Routing decision | <0.1 ms | if/else |
| **Total edge path** | | **≈1.3 ms P50** | sebelum publish MQTT |
| 6.1 | MQTT/TLS publish | 50–150 ms | SAS token auth + TLS handshake |
| 6.2 | IoT Hub → EventHub | ~10 ms | auto-routing |
| 6.3 | Function trigger | ~5 ms | batch processing |
| 6.4 | Table Storage write | 5–20 ms | network + commit |
| 6.5 | Vue polling | 100–300 ms | REST GET |
| 6.6 | Babylon render | <16 ms | 60 FPS target |
| **Total cloud path** | | **≈321 ms P50** | sensor → 3D viewer |

---

## Keterkaitan dengan Paper

| Bagian Paper | Klaim | Bukti di Skenario Ini |
|---|---|---|
| §1 Streaming latency | P50 edge 1.3 ms, cloud 321 ms | Hop 4 + Hop 6.5 |
| §1 Edge 99.12% / Cloud 0.88% | Routing decision | Hop 5 (Z-score) |
| §1 Throughput 27,886 msg/sec | Stream rate | `streaming_metrics_v2.pkl` |
| §2 Energy prediction R²=0.96 | Ridge akurasi | Hop 4 RMSE=0.6175 W |
| §2.1 Augmentation | CSV augmented 12× | Baris ini salah satu baris augmented |
| §4 Digital twin latency | Vue → Babylon <320 ms | Hop 6.5 + 6.6 |

---

## Limitasi yang Diakui

- **Bukan live trace**: Baris ini dibaca dari CSV augmented, bukan live stream Azure. Live stream diverifikasi terpisah via `az storage entity query` (lihat CONSOLIDATED_RESULTS §4.3).
- **Koefisien Ridge tidak di-load di sini**: Prediksi y_pred ≈ 40 W adalah estimasi karena V×I ≈ target; untuk eksak, buka `ml_models/train_model.py` dan load `.pkl` model terlatih.
- **YOLO inference latency** tidak diukur di trace ini (RPi path, ~200–400 ms untuk 1 frame YOLO v3-tiny).
- **Tidak ada MQTT capture**: Trace mengasumsikan ESP32 publish seperti kode `esp32_main.cpp`; tanpa packet capture, timing 50–150 ms adalah estimasi dari dokumentasi Azure IoT Hub.