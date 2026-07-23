# Pilar 4 — Prediksi Energi

Modul ini adalah **delegasi** ke sub-modul di bawah
`../Digital_Twin/dashboard_digitaltwin/ml_models/`. Tidak berdiri
sendiri — kode training, model `.pkl`, dan prediction API tinggal
di sana.

## Lokasi Kode Asli

| Komponen | Path |
|---|---|
| Model energi (R² 0.9687) | `../Digital_Twin/dashboard_digitaltwin/ml_models/models/energy_forecast_model.pkl` |
| Model rekomendasi AC (R² 0.8629) | `../Digital_Twin/dashboard_digitaltwin/ml_models/models/ac_recommendation_model.pkl` |
| Scaler + features | `../Digital_Twin/dashboard_digitaltwin/ml_models/models/*.pkl` |
| Train energi | `../Digital_Twin/dashboard_digitaltwin/ml_models/train_*.py` (lihat symlink) |
| Predict | `../Digital_Twin/dashboard_digitaltwin/ml_models/predict.py` |
| API service | `../Digital_Twin/dashboard_digitaltwin/ml_models/prediction_api.py` |
- Model config (JSON) | `../Digital_Twin/dashboard_digitaltwin/ml_models/models/model_config.json` |

## Dual-Experiment Design (penting untuk paper)

Pilar 4 di repo ini menjalankan **dua eksperimen paralel**:

### Eksperimen A — Small Window (Snapshot Azure)

- Snapshot dari Azure `stordigitaltwin2026`, tanggal training
  `2026-01-10`.
- 2.121 records, 5 fitur (suhu, kelembaban, tegangan, arus, hour).
- Model: ensemble regresi (lihat `train_*.py`).
- **R² energi = 0.9687**, **R² AC rec = 0.8629**.
- Model ini yang di-deploy ke Azure Function
  `OnlineACRecommendation` dan dipakai di Digital Twin (Layer 5).
- Latency inferensi cloud ≈ 8-10 ms per request.

### Eksperimen B — Large Corpus (Batch)

- Dataset `../Data/sensor_data.csv` 2.027.520 × 8, periode 89 hari.
- Augmentasi dari Azure feed (lihat `../arsip/2026-07-23/CONSOLIDATED_RESULTS.md`
  §"Dataset provenance").
- Hasil: Ridge R² = 0.9597 (test), RF R² = 0.9933.
- Dipakai untuk **benchmark pilar 1 (streaming)** di edge.

Dua eksperimen ini **tidak kontradiktif**. Yang A adalah
*deployment-grade* (production, stabil, real-time inference),
yang B adalah *batch-validated* (paper-grade, stress-test pada
korpus besar). Paper akan menjelaskan keduanya.

## Cara Reproduksi

```bash
# Snapshot (Eksperimen A, butuh Azure snapshot CSV)
CONDA_NO_PLUGINS=true ../.venv/bin/python ../Digital_Twin/dashboard_digitaltwin/ml_models/train_ac_recommendation.py

# Batch (Eksperimen B, butuh sensor_data.csv — sudah otomatis)
CONDA_NO_PLUGINS=true ../.venv/bin/python -u ../streaming_final.py
```

Output `streaming_metrics_v2.pkl` memuat metrik Pilar 1 yang
juga mencakup hasil regresi dari Pilar 4 (batch path).

---
*Pemeliharaan: perubahan pada Pilar 4 dilakukan di
`../Digital_Twin/dashboard_digitaltwin/ml_models/`.*
