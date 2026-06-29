# Jurnal Penelitian — Claude Memory

> File ini dibaca otomatis di awal setiap sesi Claude Code di repo ini.
> Berisi konteks penelitian yang harus selalu diingat.

---

## Judul Penelitian
**Strategi Arsitektur Edge-Cloud Berbasis Fusi Data Multimodal pada Ekosistem Digital Twin Web-3D untuk Prediksi Energi Bangunan Cerdas**

## Empat Pilar Penelitian
1. **Edge-Cloud** — Arsitektur hybrid edge-cloud untuk streaming & prediksi real-time
2. **Fusi Data Multimodal** — Kombinasi data sensor numerik (DHT11, ZMPT101B, SCT013) + visual (YOLO people detection)
3. **Digital Twin Web-3D** — Visualisasi 3D bangunan pakai Babylon.js
4. **Prediksi Energi** — Model ML untuk prediksi konsumsi energi bangunan

## Dataset Utama
- **File:** `sensor_data.csv` (154.7 MB)
- **Ukuran:** 2.027.520 baris × 8 kolom
- **Periode:** 2026-02-23 23:14:43 → 2026-05-24 01:22:06 (≈ 90 hari)
- **Device:** RASPBERRY_PI_GATEWAY_001 (label agregasi, lihat klarifikasi di bawah)
- **Kolom:** Timestamp, DeviceID, Suhu (C), Kelembaban (%), Tegangan (V), Arus (A), Daya (W), Jumlah Orang

## Klarifikasi Single-Column DeviceID di CSV
CSV hanya punya 1 nilai `device_id` karena **gateway me-relabel payload** saat ingest ke Azure.
Sumber asli bersifat **multi-node & multi-modalitas**:

| Sumber | Tipe | Sensor/Modality | Acuan File |
|---|---|---|---|
| ESP32 (numerik) | Edge | DHT11 (suhu/kelembaban), ZMPT101B (tegangan), SCT013 (arus) | `sensor_iot/esp32_main.cpp` line 2383 `doc["deviceId"] = deviceId` |
| Raspberry Pi Camera | Edge vision | YOLO people detection → `jumlah_orang` | `sensor_iot/raspberry_pi/people_counter_yolo.py` |
| RPi Gateway | Edge aggregator | Health (CPU/RAM/disk) + batch metadata | `sensor_iot/esp32_main.cpp` line 45-51 (RPI_GATEWAY_URL = `http://192.168.1.14:5001/api/collect`) |
| Azure Function | Cloud | Storage Tabel + ingestion pipeline | `sensor_iot/azure_setup/azure-function/SaveSensorData/index.js` line 59-130 |

**Bukti agregasi multi-source** (`SaveSensorData/index.js` line 59-130):
```js
const deviceId = sensorData.deviceId || "RASPBERRY_PI_GATEWAY_001";
if (sensorData.esp32) {       // ESP32 numeric block
    entity.suhu = parseFloat(esp32.suhu);
    // ... + TinyML + AC + health
}
if (sensorData.camera) {      // Camera/YOLO block
    entity.people_count = sensorData.camera.people_count;
}
if (sensorData.gateway) {     // RPi gateway health
    entity.gateway_cpu_percent = gw.cpu_percent;
}
```

**Jadi:** "RASPBERRY_PI_GATEWAY_001" di CSV = `partitionKey` untuk agregasi ESP32 + Camera + Gateway, BUKAN single sensor.

**Implikasi untuk paper:** Arsitektur terbukti multi-node & multi-modalitas (numerik + visual + gateway metadata). Label `device_id` di CSV adalah identifier agregator, bukan sensor tunggal.

## Hasil Eksperimen Inti (2M records, no data leakage)
| Komponen | Metrik | Nilai |
|---|---|---|
| Edge latency | median per-record | 1.49 ms (SLA <2ms) ✓ |
| Cloud latency | incl. network | 196 ms (anomali only) |
| Anomaly rate | dari 2M records | 3.24% |
| Prediksi online (SGD, 4 fitur) | R² | 0.5950 |
| Prediksi batch (RF, 18 fitur) | **R²** | **0.9952** |
| Prediksi batch (LR, 18 fitur) | R² | 0.9651 |
| Prediksi batch (RF) | RMSE | 0.2115 W |
| Prediksi batch (RF) | MAE | 0.1530 W |
| Prediksi batch (RF) | MAPE | 0.42% |
| Prediksi batch (LR) | RMSE | 0.5702 W |
| Prediksi batch (LR) | MAE | 0.4613 W |
| Total fitur model | — | **18 fitur** (10 base + 2 interaksi + 3 time + 5 time_period + 3 rolling) |

## Arsitektur yang Divalidasi
```
[Sensor IoT] → [Edge: preprocess + fusion + anomaly + prediction]
                       ↓
              ┌────────┴────────┐
       Normal (96.8%)     Anomaly (3.2%)
              ↓                ↓
       Realtime <2ms      Cloud: heavy + DT sync
                          ~200ms (incl network)
```

## File-file Kunci di Repo
| File | Peran |
|---|---|
| `edge_cloud_streaming.ipynb` | **Notebook utama** — Streaming 2M records, validasi arsitektur Edge-Cloud |
| `energy_prediction_models.ipynb` | Validasi akurasi model (LR + RF) dengan feature engineering |
| `sensor_data.csv` | Dataset IoT 2M records (154.7 MB) |
| `dashboard_digitaltwin/` | Sub-modul TwinSpace (Vue + Babylon.js + ESP32 + YOLO + Azure) |
| `best_energy_model.joblib` | Model RF terlatih (R² = 0.9952, 18 fitur) |
| `energy_scaler.joblib` | StandardScaler untuk 18 fitur input |
| `energy_feature_columns.joblib` | Daftar 18 fitur input model |
| `energy_model_results.json` | Ringkasan metrik akurasi (LR + RF) |
| `references.md` | 38 jurnal Scopus 2021-2026 (topik: EC, DT, MM, EP) |
| `pdf_references/` | 30 PDF jurnal yang sudah di-download (OA) |

## 18 Fitur Input Model (setelah patch anti-leakage)
**Base numerik (10):**
1. `suhu` — suhu raw
2. `kelembaban` — kelembaban raw
3. `tegangan` — tegangan raw
4. `arus` — arus raw
5. `jumlah_orang` — occupancy count (multimodal: YOLO output)

**Interaksi (2):**
6. `tegangan_arus` — V×A (interaction, importance 0.81 di RF)
7. `suhu_kelembaban` — T×RH (interaction)

**Time features (3):**
8. `hour` — jam dari timestamp
9. `dayofweek` — hari dalam minggu
10. `day` — hari dalam bulan

**Time period one-hot (5):**
11. `time_period_afternoon`
12. `time_period_evening`
13. `time_period_midday`
14. `time_period_morning`
15. `time_period_night`

**Rolling means (3, anti-leakage):**
16. `daya_ma_short` — moving average pendek daya (window 100)
17. `daya_ma_long` — moving average panjang daya (window 300)
18. `suhu_ma_short` — moving average pendek suhu (window 100)

## 38 Referensi Jurnal (Kategori)
- **Edge-Cloud:** 19 jurnal
- **Digital Twin:** 21 jurnal
- **Multimodal:** 22 jurnal
- **Energy Prediction:** 31 jurnal
- Sumber: Scopus (2021-2026), 30 PDF sudah terdownload di `pdf_references/`

## Komponen Implementasi TwinSpace (`dashboard_digitaltwin/`)
- **Edge firmware:** `sensor_iot/esp32_main.cpp` (DHT11, ZMPT101B, SCT013)
- **Edge vision:** `sensor_iot/raspberry_pi/people_counter_yolo.py` (YOLO)
- **Cloud:** `sensor_iot/azure_setup/azure-function/` (Azure Functions: ingestion + ML)
- **ML training:** `ml_models/train_model.py`, `ml_models/train_ac_recommendation.py`
- **Web-3D viewer:** `view_virtual/src/components/DigitalTwin3D_Babylon.vue`

## Catatan Penting
- Repo TwinSpace asli ada di `~/Desktop/dashboard_digitaltwin/` dan `~/Documents/dashboard_digitaltwin/`
- Sub-modul di repo ini adalah salinan ramping tanpa `node_modules` & kredensial
- **Patch Anti-leakage (sudah diterapkan):** Rolling means dihitung independen per train/test set, sehingga R² RF=0.9952 valid untuk deployment real-time
- **Multi-source dataset:** CSV `device_id` = label aggregator (bukan single sensor). Payload asli mengandung blok ESP32 + Camera + Gateway (lihat section "Klarifikasi Single-Column DeviceID" di atas)

## Progress Selanjutnya

### Sesi — Validasi Feature Completeness & Cleanup
**Status:** V6 chosen as baseline. File cleanup selesai (V1-V5, gen scripts, EXEC_v6 duplikat dihapus).

- [x] Validasi streaming pipeline (`edge_cloud_streaming.ipynb`) menggunakan 15 fitur
- [x] Git LFS setup — sensor_data.csv + best_energy_model.joblib di-LFS tracking
- [x] Force-push ke GitHub berhasil
- [x] **Cleanup:** gen_notebook_v*.py (semua versi), edge_cloud_streaming_EXEC_v*.ipynb (duplikat), PNG lama (v3-v5), fix_kernel.py, ridge_online_model.pkl → **dihapus**
- [x] **Upgrade ke 18 fitur:** rolling means (`daya_ma_short`, `daya_ma_long`, `suhu_ma_short`) sudah ditambahkan ke streaming notebook
- [x] **Analisa false positive anomaly detection** selesai — hasilnya:
  - Total detected: 55,028 vs injected: 2,200
  - **Hard anomalies** (physics impossible): 200/200 = **100%** ✓
  - **Soft anomalies** (±15% drift): 169/2,000 = **8.5%** ❌
  - **FP: 54,659** dari 1.97M normal → 99.96% FP memiliki zscore dekat threshold (1.9-2.1)
  - **Diagnosis:** z-score threshold 2.0 terlalu sensitif + heavy tails di energy score distribution
  - **Rekomendasi:** naikkkan threshold ke 2.5 (precision naik ke 4.3%) atau ganti sliding window temporal
- [x] **Perbaikan visualisasi timeline** — ganti `fill_between` sequential dengan stacked bar per 10K bin
  - Hasil: `axes[1,0]` menampilkan stacked bar edge-only vs cloud-routed per 10K records
  - Reference line 10% cloud routing ditambahkan untuk context

## Preferensi Kolaborasi

- **JANGAN** langsung menulis artikel/naskah jurnal — user hanya minta cek & validasi proyek
- **SELALU** cek file sebelum memberikan saran (asumsi = salah, baca dulu)
- **GUNAKAN** task tracking untuk pekerjaan multi-step
- **REFERENSI** yang tersedia: 38 jurnal dengan tag [EC]/[DT]/[MM]/[EP], 30 sudah jadi PDF
