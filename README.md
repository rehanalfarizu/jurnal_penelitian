# Jurnal Penelitian

## Strategi Arsitektur Edge-Cloud Berbasis Fusi Data Multimodal pada Ekosistem Digital Twin Web-3D untuk Prediksi Energi Bangunan Cerdas

> **STATUS: Final results (2026-06-30)** — Lihat ringkasan hasil di bawah.

### Files

| File | Deskripsi |
|---|---|
| `edge_cloud_streaming.ipynb` | **Streaming Edge-Cloud** — Validasi pipeline near-real-time Ridge + anomaly detection |
| `energy_prediction_models.ipynb` | **Akurasi Prediksi Energi** — Feature engineering + LR/RF pada 2M records (FIXED shift(1)) |
| `sensor_data.csv` | Dataset sensor IoT (154.7 MB, 2.027.520 baris, 8 kolom) — **Git LFS** |
| `dashboard_digitaltwin/` | Sub-modul TwinSpace (Vue.js + Babylon.js + ESP32 + YOLO + Azure) |
| `eval_energy_fixed.py` | Static R² evaluator (hold-out test) |
| `final_drift_ablation_test.py` | Drift on/off ablation — closes 93% of streaming-vs-static R² gap |
| `robustness_audit_v2.py` | Near/far R² audit (static, threshold=1000) |
| `evaluate_anomaly_recall.py` | Recall / FPR / detection latency vs ground truth |
| `compare_architectures.py` | Edge vs edge-preferred vs full-cloud counterfactual |
| `CONSOLIDATED_RESULTS.md` | Tabel angka final paper (satu sumber kebenaran) |

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

### Status Modul Digital Twin: Reference Architecture / Prototype

Sesuai keputusan desain D4, modul `dashboard_digitaltwin/` diposisikan sebagai **reference architecture / prototype**, bukan Digital Twin fungsional yang tervalidasi. Bukti:

- **Yang ada:** Vue 3 + Babylon.js 3D rendering (glTF floor plan + sensor icon overlay), AC 3D primitive dengan particle effect, Cesium 3D map viewer, 7 composables (Azure telemetry polling, dummy data, MQTT), ESP32 firmware (DHT11 + ZMPT101B + SCT013), RPi YOLO people detection, Azure Functions untuk IoT data pipeline.
- **Yang TIDAK ada:**
  1. Tidak ada physics-based thermal/electrical simulation (no thermal solver, no HVAC model, no occupancy-driven energy model).
  2. Tidak ada per-room/zone energy breakdown — hanya single aggregate kW prediction.
  3. Tidak ada evaluasi prediksi-vs-terukur per ruangan (no error metric per zone).
  4. Fitur model yang di-deploy (5 fitur) tidak match dengan 18-fitur notebook energy_prediction_models.
  5. Tidak ada integrasi antara pipeline streaming 2M-record di notebook dengan dashboard ML models (3 model .pkl yang berbeda dilatih via script terpisah).

**Verdict:** Untuk paper, modul ini layak disebut "implemented reference architecture" dengan cakupan visualisasi 3D + sensor overlay + arsitektur IoT penuh. **Jangan diklaim** sebagai Digital Twin fungsional/tervalidasi kecuali physics-based simulation + per-room evaluation ditambahkan (lihat `AUDIT_REPORT.md` Bagian 4 untuk detail).

---

## Keputusan Desain (6 final)

1. **Model = Ridge 18-fitur end-to-end**. Tidak ada SGD 4-fitur. Notebook
   `edge_cloud_streaming.ipynb` adalah satu-satunya canonical model.
2. **Streaming threshold default = z=2.5** (bukan 2.0 atau 3.0). File
   `streaming_results_z25.pkl` adalah hasil canonical.
3. **Robustness = STATIC R² per group**, threshold = 1000 (matching
   `deque(maxlen=1000)`). Shared rolling-window R² dari v1 dibuang karena
   bocor antar group.
4. **Anomali = 200 hard + 2000 soft, pre-injected**. Ground truth dari
   `anomaly_indices.pkl`.
5. **Counterfactual arsitektur = bootstrap dari observed edge/cloud latency
   & energy distribution**, bukan simulator terpisah.
6. **Latensi "near-real-time" = simulasi**. `cloud_latency_ms` adalah parameter
   yang di-inject untuk eksperimen routing, bukan pengukuran jaringan nyata.

---

## HASIL FINAL — 2 Bagian Terpisah

### A. Akurasi Prediksi Energi (energy_prediction_models.ipynb)
> Klaim utama judul: "Prediksi Energi Bangunan Cerdas"

| Model | R²_train | R²_test | RMSE (W) | MAE (W) | MAPE (%) | Train Time |
|---|---|---|---|---|---|---|
| Linear Regression | 0.9950+ | **0.9629→FIXED** | ~0.588 | ~0.479 | ~0.42 | ~0.3s |
| Random Forest | 0.9995+ | **0.9952→FIXED** | ~0.212 | ~0.153 | ~0.42 | ~256s |

**Catatan:** Setelah fix `.shift(1)` pada rolling means (anti-leakage), kedua model mempertahankan performa tinggi karena fitur 18-fitur mencakup base numerik, time period, dan rolling/window features. Gap train-test <0.04 untuk RF, menunjukkan model tidak overfit berlebihan.

### B. Streaming Edge-Cloud (Ketahanan Arsitektur)
> Validasi: adaptive retraining + drift compensation — lihat CONSOLIDATED_RESULTS.md § 1–2

| Metrik | Nilai |
|---|---|
| Computational throughput | 3,335 rec/s (benchmarked, see CONSOLIDATED_RESULTS § 1) |
| Edge latency (wall-clock) | 1.81 ms/record (EDGE_ONLY), 12.72 ms (EDGE_PREFERRED w/ 3.4% cloud) |
| Cloud latency | 275 ms (hardcoded assumption — SIMULATED, not measured) |
| Anomaly rate | 3.41% (z=2.5) — routed to cloud |
| Batch energy model (RF) | R²=0.9952 (see §A above) |

**Drift ablation** (CONSOLIDATED_RESULTS.md § 2): accumulated drift explains **93.5%** of the streaming-vs-batch R² gap. After drift stripping, RF reaches R²=0.997 (virtually identical to batch). The remaining gap is Ridge linearity (< 2%).

### Perbandingan Dua Hasil

| Aspek | Prediksi Energi (A) | Streaming Edge-Cloud (B) |
|---|---|---|
| Question | "Seberapa akurat memprediksi daya?" | "Seberapa robust pipeline edge-cloud terhadap drift?" |
| Method | Batch train-test split (80/20) | Online streaming + periodic retrain + drift ablation |
| Best R² | **0.9952** (RF batch) | **0.9128** (Ridge streaming, CONSOLIDATED §2) |
| Insight kunci | 18 fitur + shift(1) = akurasi tinggi | Drift explains 93.5% of streaming-vs-batch gap |
| Validitas ilmiah | Tinggi (clean feature engineering) | Tinggi — drift ablation closed, robustness audited |
