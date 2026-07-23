# Integrasi Pilar Penelitian — INSTRUMENTASI

**Status:** Tahap A+B+C selesai (commit 94c1d67). Tahap D in-progress.

Dokumen ini menjelaskan bagaimana 4 pilar penelitian
**terintegrasi** dalam satu repo dan bagaimana cara
mereproduksi semua hasil.

## 1. Peta Pilar → Folder

Pilar 1 — **Edge-Cloud Streaming Validation**
* Folder paparan: `Edge_Cloud_Streaming/`
* Folder implementasi: `Digital_Twin/dashboard_digitaltwin/ml_models/`
* Script utama: `Edge_Cloud_Streaming/scripts/streaming_final.py`
  (canonical copy di `Digital_Twin/dashboard_digitaltwin/ml_models/streaming_final.py`)
* Visualisasi: `Edge_Cloud_Streaming/scripts/streaming_visualizations.py`
  (canonical copy di root)
* Hasil: `streaming_metrics_v2.pkl` + `streaming_results_v2.pkl` (288 MB)
  + `figures/01-08_*.png` (8 figure)

Pilar 2 — **Multimodal Sensor Fusion** (ESP32 + Pi Camera)
* Folder paparan: `Multimodal_Fusion/`
* Folder implementasi:
  - ESP32 firmware: `Digital_Twin/dashboard_digitaltwin/sensor_iot/esp32_main.cpp`
  - Pi Camera YOLO: `Digital_Twin/dashboard_digitaltwin/sensor_iot/raspberry_pi/people_counter_yolo.py`
* Fungsi: ESP32 publishes sensor (DHT22, PIR, light, current) ke Azure IoT
  Hub via MQTT. Raspberry Pi menjalankan YOLOv3-tiny people counter.

Pilar 3 — **Digital Twin Dashboard** (Vue 3 + Vite)
* Folder paparan: `Multimodal_Fusion/` (Pilar 2 + 3 share)
* Folder implementasi: `Digital_Twin/dashboard_digitaltwin/view_virtual/`
* Stack: Vue 3 (Composition API), Vite, Three.js (FBX/GltF 3D
  building), Three.js controls, Vercel deployment config
  (`config/vercel.vite.json`).
* Fungsi: Web-based 3D digital twin yang menampilkan sensor
  real-time + AC recommendation overlay.

Pilar 4 — **Prediksi Energi & Rekomendasi AC**
* Folder paparan: `Prediksi_Energi/`
* Folder implementasi: `Digital_Twin/dashboard_digitaltwin/ml_models/`
* Script utama:
  - Training: `train_ac_recommendation.py` (XGBoost regression,
    MAPE 1.45%, R² 0.9580)
  - Prediksi: `predict.py`
  - REST API: `prediction_api.py` (FastAPI, port 8000)
* Model artifacts: `models/ac_recommendation_model.pkl` (110 KB),
  `models/ac_features.pkl`, `models/ac_scaler.pkl`,
  `models/energy_forecast_model.pkl` (30 KB).
* Status training: `models/training_status.json`

## 2. Alur Data End-to-End

```
┌──────────┐  MQTT   ┌──────────────┐  HTTP   ┌──────────────┐
│  ESP32   │────────▶│ Azure IoT    │────────▶│ Azure Func   │
│ sensors  │         │ Hub          │         │ (GetAC)      │
└──────────┘         └──────────────┘         └──────┬───────┘
                                                     │
┌──────────┐  RTSP   ┌──────────────┐                │ JSON
│  Pi Cam  │────────▶│ YOLOv3-tiny  │                │
│          │         │ people count │                │
└──────────┘         └──────┬───────┘                │
                            │ count                  │
                            ▼                        ▼
                     ┌─────────────────────────────────┐
                     │ prediction_api.py (FastAPI)     │
                     │ XGBoost → AC recommendation     │
                     └────────────┬────────────────────┘
                                  │ JSON
                                  ▼
                     ┌─────────────────────────────────┐
                     │ Vue 3 Dashboard (Pilar 3)       │
                     │ Three.js 3D building + overlay  │
                     │  + LSTM R² 0.9464 streaming     │
                     └─────────────────────────────────┘
                                  │
                                  ▼
                     ┌─────────────────────────────────┐
                     │ streaming_final.py (offline)    │
                     │ 2M records, 90 hari, jittered    │
                     │ → 8 figure PDF/SVG               │
                     └─────────────────────────────────┘
```

## 3. Cara Reproduksi

**Setup** (sekali):
```bash
git clone <repo>
cd jurnal_penelitian
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt   # atau pip install pandas numpy
                                # scikit-learn xgboost matplotlib
                                # fastapi uvicorn
```

**Pilar 1 — Streaming validation** (5-7 menit):
```bash
cd Edge_Cloud_Streaming/scripts
python streaming_final.py        # menghasilkan streaming_*_v2.pkl
python streaming_visualizations.py  # menghasilkan figures/01-08 PNG
```

**Pilar 2 — ESP32 firmware** (perlu hardware):
```bash
cd Digital_Twin/dashboard_digitaltwin/sensor_iot
# Edit platformio.ini: upload_port = /dev/cu.usbserial-*
pio run --target upload
```

**Pilar 3 — Digital Twin dashboard** (web, port 5173):
```bash
cd Digital_Twin/dashboard_digitaltwin/view_virtual
npm install
npm run dev          # development
npm run build        # production → dist/
```

**Pilar 4 — AC prediction API** (port 8000):
```bash
cd Digital_Twin/dashboard_digitaltwin/ml_models
uvicorn prediction_api:app --reload --port 8000
# Swagger: http://localhost:8000/docs
```

**Atau jalankan semuanya berurutan** (run_all_integrated.py — Tahap D):
```bash
python run_all_integrated.py --skip-hardware  # tanpa ESP32
```

## 4. File Konfigurasi Bersama

* `Edge_Cloud_Streaming/scripts/streaming_final.py` ↔
  `Digital_Twin/dashboard_digitaltwin/ml_models/streaming_final.py`:
  symlink untuk konsistensi. Patch selalu di symlink, real
  path auto-terupdate.
* `Edge_Cloud_Streaming/scripts/streaming_visualizations.py` ↔
  `Digital_Twin/dashboard_digitaltwin/ml_models/streaming_visualizations.py`:
  sama, symlink.
* `Multimodal_Fusion/visual/*` ↔
  `Digital_Twin/dashboard_digitaltwin/sensor_iot/raspberry_pi/*`:
  symlink. Visual folder adalah paparan.
* `Multimodal_Fusion/numerical/esp32_main.cpp` ↔
  `Digital_Twin/dashboard_digitaltwin/sensor_iot/esp32_main.cpp`:
  symlink.
* `Prediksi_Energi/scripts/*` ↔
  `Digital_Twin/dashboard_digitaltwin/ml_models/*`:
  symlink.

## 5. Backup & Recovery

* `streaming_*_v2.pkl.bak.pre_jitter` (di .gitignore):
  snapshot data sebelum Tahap B jitter. Bisa dipulihkan
  dengan rename → `streaming_*_v2.pkl`.
* `arsip/` (di .gitignore): 565 MB file archive
  (historical run, tidak untuk paper). Preserve di luar git.
* `Digital_Twin/dashboard_digitaltwin/view_virtual/node_modules/`:
  732 MB, di-exclude. Re-install via `npm install`.
* `Digital_Twin/dashboard_digitaltwin/view_virtual/dist/`:
  116 MB, di-exclude. Regenerate via `npm run build`.

## 6. Audit Trail

| Tahap | Commit   | Isi |
|-------|----------|-----|
| A     | 94c1d67  | Pilar folder reorg + symlink |
| B     | 94c1d67  | Latency jitter + 3 throughput |
| C     | 94c1d67  | 8 figure regenerate |
| D     | pending  | INTEGRATION.md (this file) + track Digital_Twin/ |
| E     | pending  | Paper draf (8 section) |

Lihat `AUDIT_RESULTS.md` untuk angka performa final
(R², MAPE, throughput, latency, energy, anomaly).
