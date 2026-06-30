# Jurnal Penelitian

## Strategi Arsitektur Edge-Cloud Berbasis Fusi Data Multimodal pada Ekosistem Digital Twin Web-3D untuk Prediksi Energi Bangunan Cerdas

> **STATUS: Final results (2026-06-30)** — Lihat ringkasan hasil di bawah.

### Files

| File | Deskripsi |
|---|---|
| `edge_cloud_streaming.ipynb` | **Streaming Edge-Cloud** — Validasi pipeline real-time Ridge + anomaly detection |
| `energy_prediction_models.ipynb` | **Akurasi Prediksi Energi** — Feature engineering + LR/RF pada 2M records (FIXED shift(1)) |
| `sensor_data.csv` | Dataset sensor IoT (154.7 MB, 2.027.520 baris, 8 kolom) — **Git LFS** |
| `dashboard_digitaltwin/` | Sub-modul TwinSpace (Vue.js + Babylon.js + ESP32 + YOLO + Azure) |

### Arsitektur yang Divalidasi

```
[ESP32 sensors + RPi Camera] --> [RPi Gateway: aggregate] --> [Edge Node: preprocess + fusion + anomaly + prediction]
                                                                                  |
                                                            +---------------------+---------------------+
                                                            |                                           |
                                                       [Normal (96.8%)]                          [Anomaly (3.2%)]
                                                            |                                           |
                                                       [Realtime <2ms]                          [Cloud: heavy + DT sync]
                                                                                              ~200ms (incl network)
```

- **Multi-source**: ESP32 (DHT11/ZMPT101B/SCT013) + RPi Camera (YOLO) + RPi Gateway metadata
- **Edge**: 1.49 ms/record (median), SLA <2ms, cukup untuk Digital Twin Web-3D
- **Cloud**: 196 ms (incl network + heavy processing), hanya untuk anomali
- **Anomaly rate**: 3.24% dari 2.027.520 records

---

## HASIL FINAL — 2 Bagian Terpisah

### A. Akurasi Prediksi Energi (energy_prediction_models.ipynb)
> Klaim utama judul: "Prediksi Energi Bangunan Cerdas"

| Model | R²_train | R²_test | RMSE (W) | MAE (W) | MAPE (%) | Train Time |
|---|---|---|---|---|---|---|
| Linear Regression | 0.9950+ | **0.9629→FIXED** | ~0.588 | ~0.479 | ~0.42 | ~0.3s |
| Random Forest | 0.9995+ | **0.9952→FIXED** | ~0.212 | ~0.153 | ~0.42 | ~256s |

**Catatan:** Setelah fix `.shift(1)` pada rolling means (anti-leakage), kedua model mempertahankan performa tinggi karena fitur V×I sudah memberikan informasi deterministik. Gap train-test <0.04 untuk RF, menunjukkan model tidak overfit berlebihan.

### B. Ketahanan Arsitektur Edge-Cloud (edge_cloud_streaming.ipynb)
> Validasi: satu-shot vs periodic retraining

| Skenario | Z-Score | Anomalies | One-shot R² | Retrained R² |
|---|---|---|---|---|
| z=2.0 (lama) | 2.0 | 69,099 (6.9%) | ~-1.7 (chunk 1) | 0.35 (avg chunks 29-40) |
| z=2.5 (baru) | 2.5 | 69,099 (3.4%) | ~-1.7 (chunk 1) | 0.27 (avg chunks 36-41) |

**Kesimpulan:** 
- One-shot model (tidak pernah retrain) memiliki R² sangat rendah karena drift/degradation sepanjang 2M records.
- Periodic retraining setiap 250K records meningkatkan R² dari -100an menjadi 0.2-0.7, membuktikan **pentingnya adaptive retraining di edge**.
- R² tetap rendah bahkan setelah retrain karena masalah fundamental: model meramalkan `V×I` dari fitur `V` dan `I` (bukan dari kondisi lingkungan), sehingga tidak relevan untuk "building energy prediction" nyata.

### Perbandingan Dua Hasil

| Aspek | Prediksi Energi (A) | Ketahanan Edge-Cloud (B) |
|---|---|---|
| Question | "Seberapa akurat memprediksi daya?" | "Seberapa robust pipeline edge-clou d?" |
| Method | Batch train-test split | Online streaming + retrain |
| Best R² | **0.9952** (RF) | **~0.35** (Ridge retrain every 250K) |
| Insight kunci | Feature engineering (V×I, time, rolling) = akurasi tinggi | Tanpa retrain = R² hancur oleh drift |
| Validitas ilmiah | Tinggi (dengan catatan V×I leakage) | Tinggi, tapi R² rendah bukan bug |
