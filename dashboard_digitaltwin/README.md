# Dashboard Digital Twin — Modul Integrasi Jurnal

Sub-modul ini adalah salinan ramping dari proyek **TwinSpace / dashboard_digitaltwin** yang sudah ada di `~/Desktop/dashboard_digitaltwin/`. Disalin ke sini untuk mendukung validasi arsitektur pada jurnal:

> **Strategi Arsitektur Edge-Cloud Berbasis Fusi Data Multimodal pada Ekosistem Digital Twin Web-3D untuk Prediksi Energi Bangunan Cerdas**

---

## Mapping Komponen → Pilar Jurnal

| Pilar Jurnal | File di Sub-modul Ini |
|---|---|
| **Edge-Cloud** | `sensor_iot/esp32_main.cpp` (Edge device), `sensor_iot/azure_setup/azure-function/` (Cloud layer) |
| **Fusi Data Multimodal** | `sensor_iot/raspberry_pi/people_counter_yolo.py` (visual modality) + `sensor_iot/esp32_main.cpp` (sensor numerik) |
| **Digital Twin Web-3D** | `view_virtual/src/components/DigitalTwin3D_Babylon.vue`, `view_virtual/public/models/scene.gltf`, `view_virtual/public/3dhome.fbx` |
| **Prediksi Energi** | `ml_models/train_model.py`, `ml_models/train_ac_recommendation.py`, `ml_models/models/*.pkl` |

---

## Struktur Folder (Total: 2.4 MB, tanpa node_modules)

```
dashboard_digitaltwin/
├── README.md                        # File ini
│
├── view_virtual/                    # Frontend Vue.js + Babylon.js (Web-3D)
│   ├── package.json                 # Dependensi: @babylonjs/core, three, vue, chart.js
│   ├── vite.config.js
│   ├── index.html
│   ├── .env.example
│   ├── public/
│   │   ├── models/scene.gltf        # Model 3D bangunan (354 KB)
│   │   ├── models/license.txt
│   │   └── 3dhome.fbx               # Alternatif model rumah (944 KB)
│   └── src/
│       ├── App.vue, main.js, style.css
│       ├── components/
│       │   ├── DigitalTwin3D_Babylon.vue   # ← Komponen Web-3D utama
│       │   ├── DashboardHome.vue
│       │   ├── EnergyManagement.vue
│       │   ├── SensorStatus.vue
│       │   ├── DataTable.vue
│       │   ├── ACRecommendation.vue
│       │   └── AdminDashboard.vue
│       ├── composables/
│       │   ├── useAzureTelemetry.js         # ← Streaming dari cloud
│       │   ├── useMLPrediction.js           # ← Prediksi ML
│       │   ├── useEnergyManagement.js
│       │   ├── useAPI.js
│       │   └── useHistoricalData.js
│       ├── lib/  (appConfig.js, firebase.js, adminSession.js)
│       └── router/index.js
│
├── sensor_iot/                      # Hardware Edge (IoT + Vision)
│   ├── README.md
│   ├── platformio.ini
│   ├── esp32_main.cpp               # ← Firmware ESP32 (DHT11, ZMPT101B, SCT013)
│   ├── raspberry_pi/
│   │   ├── people_counter_yolo.py   # ← YOLO people detection (multimodal)
│   │   ├── coco.names
│   │   ├── yolov3-tiny.cfg
│   │   ├── download_yolo.py
│   │   └── README.md, SETUP_YOLO.md
│   └── azure_setup/                 # Cloud layer
│       ├── README.md
│       ├── .env.template
│       ├── iot_hub_config.txt
│       └── azure-function/          # Azure Functions
│           ├── host.json, package.json
│           ├── IoTHubToStorage/     # Event Hub → Table Storage
│           ├── GetTelemetryData/    # API: baca telemetri
│           ├── GetACRecommendation/ # API: rekomendasi AC (ML)
│           ├── SaveSensorData/
│           ├── SavePeopleCount/
│           ├── OnlineACRecommendation/
│           ├── MqttToIoTHub/
│           ├── AvroToTable/
│           ├── ExportSensorData/
│           └── OnlineACSimple/
│
└── ml_models/                       # Machine Learning
    ├── README.md
    ├── train_model.py               # ← Training energy forecast
    ├── train_ac_recommendation.py   # ← Training AC recommender
    ├── predict.py
    ├── predict_ac_recommendation.py
    ├── prediction_api.py
    ├── requirements.txt
    └── models/                      # ← Trained models (.pkl)
        ├── energy_forecast_model.pkl
        ├── energy_features.pkl
        ├── scaler.pkl
        ├── ac_recommendation_model.pkl
        ├── ac_features.pkl
        ├── ac_scaler.pkl
        ├── model_config.json
        └── training_status.json
```

---

## File yang TIDAK Disalin (Di-exclude)

| File/Folder | Alasan | Ukuran Asli |
|---|---|---|
| `node_modules/` (di view_virtual) | Dependensi, install via `npm install` | 758 MB |
| `node_modules/` (di azure-function) | Sama, install via `npm install` | 104 MB |
| `dist/`, `coverage/` | Build artifacts & test artifacts | 145 MB + 344 KB |
| `3d twin/scene.bin` + `Textures/` | Binary 3D besar, `scene.gltf` saja sudah cukup untuk referensi | 97 MB + 14 MB |
| `yolov3-tiny.weights` | Binary model, download via `download_yolo.py` | 35 MB |
| `*.zip` (Azure deployment) | Package deployment | 36 KB |
| `local.settings.json`, `.env` | Kredensial sensitif | - |
| `compile_commands.json` | PlatformIO cache | 3.7 MB |
| `.git/` | Version control | 188 MB |

---

## Bagaimana Sub-modul Ini Dipakai di Jurnal

### 1. Validasi Arsitektur (di `edge_cloud_streaming.ipynb`)
Notebook jurnal sudah memvalidasi pipeline streaming 2.027.520 record. Sub-modul ini menyediakan **bukti implementasi nyata** dari setiap layer arsitektur:

- **Edge layer** → `sensor_iot/esp32_main.cpp` (real firmware, sensor reading + MQTT publish)
- **Multimodal** → `sensor_iot/raspberry_pi/people_counter_yolo.py` (visual modality)
- **Cloud layer** → `sensor_iot/azure_setup/azure-function/` (Azure Functions untuk ingestion + ML inference)
- **ML prediction** → `ml_models/` (RandomForest/GradientBoosting untuk energy forecasting)
- **Web-3D viewer** → `view_virtual/src/components/DigitalTwin3D_Babylon.vue` (Babylon.js untuk visualisasi 3D)

### 2. Tabel Kontribusi per File (untuk paper)

| Layer | File Implementasi | Jurnal yang Bisa Mengutip |
|---|---|---|
| Edge firmware | `sensor_iot/esp32_main.cpp` | #1, #6, #8, #12, #14, #15 |
| Edge AI (vision) | `sensor_iot/raspberry_pi/people_counter_yolo.py` | #5, #9, #11 |
| Cloud ingestion | `azure-function/IoTHubToStorage/`, `MqttToIoTHub/` | #6, #8, #31 |
| Cloud ML inference | `azure-function/GetACRecommendation/`, `OnlineACRecommendation/` | #4, #23, #30 |
| Web-3D viewer | `DigitalTwin3D_Babylon.vue` | #3, #7, #10, #22, #37 |
| ML training | `ml_models/train_model.py` | #21, #26, #28, #34 |

### 3. Saran Pemakaian

Untuk paper, referensi implementasi ini sebagai:
> "The proposed architecture is implemented as TwinSpace (open-source), available at [github.com/your-repo/dashboard_digitaltwin], comprising ESP32 edge sensors, Raspberry Pi vision node, Azure Functions cloud layer, and a Babylon.js Web-3D dashboard."

Atau untuk local development:
```bash
# Cloud-side ML
cd ml_models && pip install -r requirements.txt && python train_model.py

# Frontend (perlu install node_modules dulu)
cd view_virtual && npm install && npm run dev
```

---

## Sumber Asli

Sub-modul ini disalin dari `~/Desktop/dashboard_digitaltwin/` dan `~/Documents/dashboard_digitaltwin/` pada **2026-06-25**. Versi TwinSpace v1.0.0. Repo asli berisi deployment lengkap ke Azure + Vercel + GitHub Actions yang tidak disertakan di sini karena alasan ukuran dan kerahasiaan kredensial.
