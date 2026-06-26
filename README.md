# Jurnal Penelitian

## Strategi Arsitektur Edge-Cloud Berbasis Fusi Data Multimodal pada Ekosistem Digital Twin Web-3D untuk Prediksi Energi Bangunan Cerdas

### Files

| File | Deskripsi |
|---|---|
| `edge_cloud_streaming.ipynb` | **Notebook utama** — Streaming 2M records, validasi arsitektur Edge-Cloud |
| `energy_prediction_models.ipynb` | **Validasi akurasi** — Feature engineering + 2 model (LR/RF) pada 2M records |
| `streaming_edge_cloud.py` | Engine streaming Edge-Cloud (2.027.520 records, per-record) |
| `sensor_data.csv` | Dataset sensor IoT (154.7 MB, 2.027.520 baris, 8 kolom) |
| `dashboard_digitaltwin/` | Sub-modul TwinSpace (Vue.js + Babylon.js + ESP32 + YOLO + Azure) |
| `streaming_summary.json` | Ringkasan metrik streaming |
| `streaming_results.csv` | Hasil simulasi batch (dari notebook lama) |
| `best_energy_model.joblib` | Model Random Forest terlatih (R² = 0.9952 pada 2M records, 18 fitur) |
| `energy_scaler.joblib` | StandardScaler untuk 18 fitur input |
| `energy_feature_columns.joblib` | Daftar 18 fitur input model |
| `energy_model_results.json` | Ringkasan metrik akurasi model |

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
- **R² prediksi online (SGD, 4 fitur)**: 0.5950 (baseline, untuk validasi streaming)
- **R² prediksi batch (RF, 18 fitur, anti-leakage)**: **0.9952** (lihat `energy_prediction_models.ipynb`)
- **R² prediksi batch (LR, 18 fitur, anti-leakage)**: 0.9651
- **RF MAPE**: 0.42% — error prediksi < 1% dari nilai aktual
- **Anti-leakage**: Rolling means dihitung independen per train/test set untuk deployment real-time yang valid
- **Data path**: ESP32 + Camera → RPi Gateway (RASPBERRY_PI_GATEWAY_001) → Azure Function `SaveSensorData` → Table Storage → CSV
