# 🖥️ Digital Twin Dashboard - Vue.js Frontend

Dashboard interaktif untuk visualisasi Digital Twin dengan data sensor real-time, grafik historis, dan rekomendasi AC berbasis Machine Learning.

## 📋 Daftar Isi

- [Overview](#overview)
- [Arsitektur](#arsitektur)
- [Tech Stack](#tech-stack)
- [Struktur Folder](#struktur-folder)
- [Fitur](#fitur)
- [Instalasi](#instalasi)
- [Konfigurasi](#konfigurasi)
- [Components](#components)
- [Composables](#composables)
- [API Integration](#api-integration)
- [Testing](#testing)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)

## Overview

Dashboard ini menyediakan:
- **Visualisasi 3D Digital Twin** dengan indikator sensor interaktif
- **Data Real-time** dari ESP32 dan Raspberry Pi via MQTT
- **Grafik Historis** untuk analisis trend
- **Rekomendasi AC** berbasis ML untuk efisiensi energi
- **Video Stream** dari people counter

```
┌─────────────────────────────────────────────────────────────────────┐
│                       DASHBOARD OVERVIEW                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │                    Digital Twin 3D                          │   │
│   │         🌡️ Suhu    💧 Kelembaban    ⚡ Daya    👥 Orang       │   │
│   └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐    │
│   │  📈 Suhu 24jam  │  │  ⚡ Listrik 7hr │   │  👥 Orang RT      │      │
│   │   [Chart]       │  │   [Chart]       │  │   [Chart]       │     │
│   └─────────────────┘  └─────────────────┘  └─────────────────┘    │
│                                                                      │
│   ┌──────────────────────────────────────────────────────────────┐  │
│   │  🤖 Rekomendasi AC: 22°C  │  ❄️ COOL  │  💡 Hemat 5%        │  │
│   └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Arsitektur

### Data Flow

```
┌──────────────┐     ┌──────────────┐     ┌──────────────────┐
│   ESP32      │────►│  Azure IoT   │────►│  Azure Function  │
│   Sensors    │     │    Hub       │     │  (API)           │
└──────────────┘     └──────────────┘     └────────┬─────────┘
                                                   │
┌──────────────┐     ┌──────────────┐              │
│  Raspberry   │────►│  HiveMQ      │──────────────┤
│  Pi Camera   │     │  MQTT        │              │
└──────────────┘     └──────────────┘              │
                                                   ▼
                                          ┌──────────────────┐
                                          │   Vue.js         │
                                          │   Dashboard      │
                                          │                  │
                                          │  ┌────────────┐  │
                                          │  │ useMQTT    │  │ Real-time
                                          │  │ useAPI     │  │ + Historical
                                          │  │ useAlerts  │  │
                                          │  └────────────┘  │
                                          └──────────────────┘
```

## Tech Stack

| Technology | Purpose | Version |
|------------|---------|---------|
| Vue.js 3 | Frontend framework | ^3.4.0 |
| Vite | Build tool | ^6.0.0 |
| Babylon.js | 3D visualization | ^8.43.0 |
| Three.js | 3D alternative | ^0.160.0 |
| Chart.js | Data charting | ^4.4.0 |
| vue-chartjs | Vue Chart.js wrapper | ^5.3.3 |
| MQTT.js | Real-time messaging | ^5.14.1 |
| Axios | HTTP client | ^1.6.0 |
| Vitest | Unit testing | ^4.0.16 |

## Struktur Folder

```
view_virtual/
├── README.md                    # Dokumentasi ini
├── package.json                 # Dependencies & scripts
├── vite.config.js              # Vite configuration
├── vitest.config.js            # Vitest configuration
├── vercel.json                 # Vercel deployment config
├── postcss.config.js           # PostCSS configuration
├── index.html                  # Entry HTML
├── env.example.txt             # Environment variables template
├── 📁 config/
│   └── vercel.vite.json        # Referensi alternatif config Vercel untuk Vite
│
├── 📁 src/
│   ├── App.vue                 # Root component
│   ├── main.js                 # Vue app initialization
│   ├── style.css               # Global styles
│   │
│   ├── 📁 components/          # Vue components
│   │   ├── DigitalTwin3D.vue         # 3D visualization (Three.js)
│   │   ├── DigitalTwin3D_Babylon.vue # 3D visualization (Babylon.js)
│   │   ├── SensorStatus.vue          # Sensor status cards
│   │   ├── TemperatureChart.vue      # Temperature chart
│   │   ├── ElectricityChart.vue      # Power consumption chart
│   │   ├── PeopleChart.vue           # People count chart
│   │   ├── DataTable.vue             # Data table display
│   │   ├── CameraStream.vue          # Video stream dari RPi
│   │   ├── ACRecommendation.vue      # ML-based AC recommendation
│   │   ├── AlertSettings.vue         # Alert configuration
│   │   ├── EnergyManagement.vue      # Energy dashboard
│   │   ├── HistoricalAnalytics.vue   # Historical data analysis
│   │   └── EmptyState.vue            # Empty state display
│   │
│   └── 📁 composables/         # Vue composables (hooks)
│       ├── useMQTT.js                # MQTT connection & data
│       ├── useAPI.js                 # API calls to Azure
│       ├── useAlerts.js              # Alert system
│       ├── useHistoricalData.js      # Historical data fetching
│       ├── useEnergyManagement.js    # Energy calculations
│       └── useMLPrediction.js        # ML prediction calls
│
├── 📁 public/
│   └── 📁 models/              # 3D model files
│       └── 📁 3d twin/         # GLTF/GLB models
│
└── 📁 coverage/                # Test coverage reports
```

## Fitur

### 1. Digital Twin 3D Visualization

- Model 3D ruangan dengan sensor interaktif
- Klik icon sensor untuk melihat detail data
- Indikator warna berdasarkan nilai sensor
- Support Babylon.js dan Three.js

### 2. Real-time Data Display

- Suhu dan kelembaban dari DHT11
- Tegangan, arus, dan daya dari ZMPT101B + SCT013
- Jumlah orang dari YOLO detection
- Auto-update setiap 5 detik

### 3. Grafik Historis

| Chart | Data | Period |
|-------|------|--------|
| Temperature | Suhu °C | 24 jam |
| Electricity | Daya Watt | 7 hari |
| People | Jumlah orang | Real-time |

### 4. AC Recommendation (ML-based)

- Analisis kondisi ruangan (suhu, kelembaban, orang)
- Rekomendasi suhu AC optimal (20-28°C)
- Estimasi penghematan energi
- Comfort level indicator

### 5. Video Stream

- Live feed dari Raspberry Pi
- People count overlay
- Bounding box detection

### 6. Dark/Light Mode

- Toggle theme sesuai preferensi
- Persist di localStorage

## Instalasi

### Prerequisites

- Node.js 18+
- npm atau yarn

### Setup

```bash
# 1. Masuk ke folder view_virtual
cd view_virtual

# 2. Install dependencies
npm install

# 3. Copy environment config
cp env.example.txt .env

# 4. Edit .env dengan kredensial yang benar

# 5. Jalankan development server
npm run dev
```

Server berjalan di http://localhost:3000

## Konfigurasi

### Environment Variables

File `.env`:

```env
# MQTT Broker (HiveMQ Cloud)
VITE_MQTT_BROKER_URL=wss://xxxxx.hivemq.cloud:8884/mqtt
VITE_MQTT_USERNAME=digitaltwin
VITE_MQTT_PASSWORD=Digitaltwin1

# Azure Functions API
VITE_API_BASE_URL=https://func-energymonitor.azurewebsites.net/api
VITE_AZURE_FUNCTION_URL=https://func-energymonitor.azurewebsites.net/api

# Demo Mode (gunakan dummy data)
VITE_DEMO_MODE=false

# Raspberry Pi Stream
VITE_CAMERA_STREAM_URL=http://192.168.1.100:5000/video_feed
```

### Demo Mode

Set `VITE_DEMO_MODE=true` untuk testing tanpa backend:
- Menggunakan dummy data
- MQTT tidak connect
- API calls di-mock

## Components

### DigitalTwin3D_Babylon.vue

Visualisasi 3D menggunakan Babylon.js.

**Props:**
| Prop | Type | Description |
|------|------|-------------|
| `sensorData` | Object | Data sensor real-time |
| `peopleCount` | Number | Jumlah orang |
| `isDarkMode` | Boolean | Theme mode |

**Features:**
- Load GLTF model ruangan
- Sensor markers interaktif
- Color coding berdasarkan nilai

### TemperatureChart.vue

Chart.js line chart untuk suhu.

**Props:**
| Prop | Type | Description |
|------|------|-------------|
| `data` | Object | { labels: [], values: [] } |
| `isDarkMode` | Boolean | Theme mode |

### ACRecommendation.vue

Menampilkan rekomendasi AC dari ML model.

**Logic:**
```javascript
// Fetch dari Azure Function
const response = await axios.post('/api/GetACRecommendation', {
  suhu: sensorData.temperature,
  kelembaban: sensorData.humidity,
  jumlahOrang: peopleCount,
  daya: sensorData.power
})

// Display
recommendedTemp: 22.5,
comfortLevel: "COOL",
energySaving: "5%"
```

### CameraStream.vue

Video stream dari Raspberry Pi.

**Props:**
| Prop | Type | Description |
|------|------|-------------|
| - | - | Uses env VITE_CAMERA_STREAM_URL |

**Events:**
| Event | Payload | Description |
|-------|---------|-------------|
| `people-count-update` | Number | Jumlah orang terdeteksi |

## Composables

### useMQTT.js

Mengelola koneksi MQTT dan data real-time.

```javascript
import { useMQTT } from './composables/useMQTT'

const { mqttConnected, sensorData, connect, disconnect } = useMQTT()

// sensorData structure:
{
  temperature: 27.5,
  humidity: 65,
  voltage: 220,
  current: 1.25,
  power: 275,
  voltageStatus: 'normal',
  currentStatus: 'normal',
  peopleCount: 15,
  lastPeopleUpdate: '2026-01-18T10:30:00Z'
}
```

**MQTT Topics:**
| Topic | Data |
|-------|------|
| `sensor/dht11/data` | ESP32 sensor data |
| `sensor/camera/people` | People count dari RPi |

### useAPI.js

Fetch data dari Azure Functions.

```javascript
import { useAPI } from './composables/useAPI'

const { temperatureData, electricityData, peopleData, fetchHistoricalData } = useAPI()

// Fetch historical data
await fetchHistoricalData()

// Data structure:
temperatureData: {
  labels: ['08:00', '09:00', ...],
  values: [25.5, 26.0, ...]
}
```

**API Endpoints:**
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/GetTelemetryData/latest` | GET | Data terbaru |
| `/GetTelemetryData/history` | GET | Data historis |
| `/GetTelemetryData/stats` | GET | Statistik |
| `/GetACRecommendation` | POST | Rekomendasi AC |

### useAlerts.js

Sistem alert untuk kondisi abnormal.

```javascript
import { useAlerts } from './composables/useAlerts'

const { alerts, addAlert, clearAlerts, checkThresholds } = useAlerts()

// Auto-check thresholds
checkThresholds({
  temperature: 32,  // > 30 = alert
  humidity: 85,     // > 80 = alert
  power: 5000       // > 4000 = alert
})
```

### useHistoricalData.js

Fetch dan manage data historis.

### useEnergyManagement.js

Kalkulasi dan analisis energi.

### useMLPrediction.js

Interface ke ML prediction API.

## API Integration

### Azure Functions API

```javascript
// Base URL from .env
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL

// Get latest data
const latest = await axios.get(`${API_BASE_URL}/GetTelemetryData/latest`)

// Get historical data (24 hours)
const history = await axios.get(`${API_BASE_URL}/GetTelemetryData/history?hours=24`)

// Get AC recommendation
const recommendation = await axios.post(`${API_BASE_URL}/GetACRecommendation`, {
  suhu: 28,
  kelembaban: 70,
  jumlahOrang: 20,
  daya: 1500
})
```

### MQTT Connection

```javascript
// Connect to HiveMQ Cloud
const client = mqtt.connect(MQTT_BROKER_URL, {
  username: MQTT_USERNAME,
  password: MQTT_PASSWORD,
  protocol: 'wss'
})

// Subscribe to topics
client.subscribe('sensor/dht11/data')
client.subscribe('sensor/camera/people')

// Handle messages
client.on('message', (topic, message) => {
  const data = JSON.parse(message.toString())
  // Update sensorData
})
```

## Testing

### Run Tests

```bash
# Run all tests
npm test

# Run with coverage
npm run test:coverage

# Run in watch mode
npm run test:run -- --watch
```

### Test Structure

```
src/
├── components/
│   └── __tests__/
│       ├── TemperatureChart.test.js
│       ├── ElectricityChart.test.js
│       └── ...
└── composables/
    └── __tests__/
        ├── useAPI.test.js
        ├── useMQTT.test.js
        └── ...
```

### Coverage Report

Coverage report tersedia di `coverage/index.html` setelah run `npm run test:coverage`.

## Deployment

### Build Production

```bash
npm run build
```

Output di folder `dist/`.

### Deploy ke Vercel

```bash
# Install Vercel CLI
npm i -g vercel

# Login
vercel login

# Deploy
vercel --prod
```

### Vercel Configuration

File `vercel.json`:
```json
{
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "framework": "vue"
}
```

### Environment Variables di Vercel

Set di Vercel Dashboard > Project Settings > Environment Variables:
- `VITE_MQTT_BROKER_URL`
- `VITE_MQTT_USERNAME`
- `VITE_MQTT_PASSWORD`
- `VITE_API_BASE_URL`
- `VITE_DEMO_MODE`

## Troubleshooting

### MQTT Connection Failed

```
❌ MQTT connection error
```

**Solusi:**
1. Verifikasi credentials di `.env`
2. Pastikan URL menggunakan `wss://` (WebSocket Secure)
3. Cek firewall port 8884

### 3D Model Tidak Muncul

**Solusi:**
1. Pastikan file `.glb` ada di `public/models/`
2. Cek console browser untuk error loading
3. Verify CORS jika menggunakan external URL

### Build Failed

```
❌ Build error: Cannot resolve module
```

**Solusi:**
```bash
# Clear cache dan reinstall
rm -rf node_modules
rm package-lock.json
npm install
npm run build
```

### API Error 404/500

**Solusi:**
1. Verifikasi `VITE_API_BASE_URL` benar
2. Cek Azure Function berjalan
3. Test endpoint langsung dengan curl

### Chart Tidak Render

**Solusi:**
1. Pastikan data format benar: `{ labels: [], values: [] }`
2. Cek apakah ada data (bukan array kosong)
3. Verify Chart.js version compatibility

---

📝 **Development Tips:**
- Gunakan Demo Mode untuk development tanpa backend
- Browser DevTools > Network tab untuk debug API calls
- Vue DevTools extension untuk debug components
