# 📡 Sensor IoT - ESP32 & Raspberry Pi

Modul sensor IoT untuk Digital Twin Dashboard yang menghubungkan hardware sensor fisik ke cloud Azure dan dashboard visualisasi.

## 📋 Daftar Isi

- [Overview](#overview)
- [Arsitektur Sistem](#arsitektur-sistem)
- [Struktur Folder](#struktur-folder)
- [Komponen Hardware](#komponen-hardware)
- [ESP32 - Sensor Suhu & Listrik](#esp32---sensor-suhu--listrik)
- [Raspberry Pi - People Counter](#raspberry-pi---people-counter)
- [Azure Functions](#azure-functions)
- [Instalasi & Setup](#instalasi--setup)
- [Testing](#testing)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)

## Overview

Sistem IoT ini terdiri dari dua komponen utama:

1. **ESP32**: Mengumpulkan data sensor lingkungan (suhu, kelembaban, tegangan, arus, daya) dan mengirim ke Azure IoT Hub
2. **Raspberry Pi**: Mendeteksi jumlah orang menggunakan webcam + YOLO dan mengirim ke MQTT broker

```
┌──────────────────────────────────────────────────────────────────────┐
│                      SYSTEM ARCHITECTURE                             │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   ┌──────────────┐                        ┌──────────────────┐       │
│   │    ESP32     │                        │  Raspberry Pi    │       │
│   │  ┌────────┐  │                        │  ┌────────────┐  │       │
│   │  │ DHT11  │  │                        │  │   Webcam   │  │       │
│   │  │ZMPT101B│  │                        │  │   + YOLO   │  │       │
│   │  │ SCT013 │  │                        │  └─────┬──────┘  │       │
│   │  └────┬───┘  │                        │        │         │       │
│   │       │      │                        │        │         │       │
│   └───────┼──────┘                        └────────┼─────────┘       │
│           │                                        │                 │
│           ▼                                        ▼                 │
│   ┌───────────────┐                        ┌──────────────┐          │
│   │ Azure IoT Hub │                        │ MQTT Broker  │          │
│   │               │                        │  (HiveMQ)    │          │
│   └───────┬───────┘                        └──────┬───────┘          │
│           │                                        │                 │
│           ▼                                        │                 │
│   ┌───────────────────┐                           │                  │
│   │  Azure Functions  │◄──────────────────────────┘                  │
│   │  ┌─────────────┐  │                                              │
│   │  │IoTHubTo     │  │                                              │
│   │  │Storage      │  │                                              │
│   │  └─────────────┘  │                                              │
│   └─────────┬─────────┘                                              │
│             │                                                        │
│             ▼                                                        │
│   ┌───────────────────┐     ┌──────────────────┐                     │
│   │  Azure Storage    │────►│    Dashboard     │                     │
│   │  (Table Storage)  │     │    (Vue.js)      │                     │
│   └───────────────────┘     └──────────────────┘                     │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

## Arsitektur Sistem

### Data Flow ESP32

```
ESP32 (Sensors) ──MQTT/TLS──► Azure IoT Hub ──EventHub──► Azure Function ──► Storage Table ──► Dashboard API
```

### Data Flow Raspberry Pi

```
Webcam ──OpenCV──► YOLO Detection ──► People Count ──MQTT──► HiveMQ ──► Dashboard (Direct)
                                                         └──► Azure Function ──► Storage
```

## Struktur Folder

```
sensor iot/
├── README.md                    # Dokumentasi ini
├── platformio.ini               # Konfigurasi PlatformIO (ESP32)
│
├── 📁 src/                      # Source code ESP32
│   └── main.cpp                 # Program utama ESP32
│
├── 📁 include/                  # Header files ESP32
│   └── README
│
├── 📁 lib/                      # Library ESP32
│   └── README
│
├── 📁 test/                     # Test files ESP32
│   └── README
│
├── 📁 raspberry-pi/             # People detection system
│   ├── README.md                # Dokumentasi Raspberry Pi
│   ├── requirements.txt         # Python dependencies
│   └── people_counter_yolo.py   # Script people detection
│
└── 📁 azure-setup/              # Azure configuration & functions
    ├── README.md                # Dokumentasi Azure Setup
    ├── iot_hub_config.txt       # Konfigurasi IoT Hub
    │
    ├── 📁 azure-function/       # Azure Functions code
    │   ├── host.json
    │   ├── local.settings.json
    │   ├── package.json
    │   ├── IoTHubToStorage/     # Simpan data ke Storage
    │   ├── GetTelemetryData/    # API get data sensor
    │   ├── GetACRecommendation/ # API rekomendasi AC
    │   ├── MqttToIoTHub/        # Bridge MQTT ke IoT Hub
    │   └── SaveSensorData/      # Save manual sensor data
    │
    ├── 📁 models/               # Azure Digital Twin models
    │   └── EnergyMonitorSensor.json
    │
    └── 📁 scripts/              # Deployment scripts
        ├── deploy_azure.sh
        ├── setup_iot_hub.sh
        ├── quick_deploy_function.sh
        └── ...
```

## Komponen Hardware

### Bill of Materials

| Komponen | Fungsi | Spesifikasi |
|----------|--------|-------------|
| ESP32 DevKit | Microcontroller | 240MHz, WiFi, Bluetooth |
| DHT11 | Sensor suhu & kelembaban | Range: 0-50°C, 20-90% RH |
| ZMPT101B | Sensor tegangan AC | 0-250V AC, output 0-5V |
| SCT013-000 | Sensor arus AC | 0-100A, output 0-50mA |
| Raspberry Pi 3/4/5 | People detection | 2GB+ RAM |
| USB Webcam | Video capture | V4L2 compatible |

### Wiring Diagram ESP32

```
ESP32 Pin Configuration:
┌──────────────────────────────────────┐
│            ESP32 DevKit              │
│                                      │
│  GPIO 4  ◄── DHT11 Data              │
│  GPIO 35 ◄── ZMPT101B Vout           │
│  GPIO 32 ◄── SCT013 (via 1kΩ)        │
│  3.3V    ──► DHT11 VCC, ZMPT101B     │
│  GND     ──► DHT11 GND, SCT013       │
│                                      │
└──────────────────────────────────────┘

DHT11 Wiring:
┌─────┐
│DHT11│
│     │
│ VCC ├──► 3.3V
│ Data├──► GPIO 4 (dengan 10kΩ pull-up)
│ GND ├──► GND
└─────┘

ZMPT101B Wiring:
┌────────┐
│ZMPT101B│
│        │
│ VCC    ├──► 5V (atau 3.3V)
│ GND    ├──► GND
│ Vout   ├──► GPIO 35
│ AC In  ├──► Kabel fase (HATI-HATI!)
└────────┘

SCT013 Wiring (Tanpa Bias):
┌──────┐
│SCT013│
│      │
│ Red  ├──┬──► GPIO 32
│      │  │
│      │  └──[1kΩ]──┐
│ Black├────────────┴──► GND
└──────┘
```

## ESP32 - Sensor Suhu & Listrik

### Fitur Utama

- Pembacaan DHT11 (suhu & kelembaban) setiap 5 detik
- Pengukuran tegangan AC dengan RMS calculation
- Pengukuran arus AC dengan burden resistor
- Kalkulasi daya (P = V × I)
- Koneksi WiFi dengan auto-reconnect
- Koneksi Azure IoT Hub via MQTT over TLS
- SAS Token generation untuk autentikasi

### Konfigurasi WiFi & Azure

Edit `src/main.cpp`:

```cpp
// WiFi Configuration
const char* ssid = "NAMA_WIFI";
const char* password = "PASSWORD_WIFI";

// Azure IoT Hub Configuration
const char* iotHubName = "iothub-energymonitor-xxxxx";
const char* deviceId = "ESP32_ENERGY_MONITOR_001";
const char* deviceKey = "PRIMARY_KEY_DARI_AZURE";
```

### Data Format yang Dikirim

```json
{
  "deviceId": "ESP32_ENERGY_MONITOR_001",
  "timestamp": "2026-01-18T10:30:00.000Z",
  "suhu": 27.5,
  "kelembaban": 65.0,
  "tegangan": 220.5,
  "arus": 1.25,
  "daya": 275.6,
  "status_tegangan": "normal",
  "status_arus": "normal"
}
```

### Logic Pembacaan Sensor

```cpp
// === Pembacaan Tegangan AC (RMS) ===
// 1. Sample 2000 kali untuk ~10 cycle AC (50Hz)
// 2. Kuadratkan setiap nilai
// 3. Hitung rata-rata (Mean Square)
// 4. Akar kuadrat (Root) untuk RMS
// 5. Kalibrasi dengan faktor VOLTAGE_CALIBRATION

float readACVoltage() {
    float sumSquares = 0;
    for (int i = 0; i < 2000; i++) {
        int adc = analogRead(ZMPT101B_PIN);
        float voltage = (adc * 3.3) / 4096;
        float voltageAC = voltage - 1.65;  // Remove DC offset
        sumSquares += (voltageAC * voltageAC);
    }
    float rms = sqrt(sumSquares / 2000);
    return rms * VOLTAGE_CALIBRATION;
}

// === Pembacaan Arus AC (RMS) ===
// Sama seperti tegangan, tapi dengan burden resistor
// SCT013-000: 100A input = 50mA output
// Dengan 1kΩ burden: 50mA × 1000Ω = 50mV

// === Kalkulasi Daya ===
float power = voltage * current;  // Watt
```

### Build & Upload

```bash
# Menggunakan PlatformIO CLI
cd "sensor iot"
platformio run --target upload

# Monitor Serial
platformio device monitor --baud 115200
```

### Expected Serial Output

```
[INFO] WiFi connecting...
[OK] WiFi connected: 192.168.1.100
[INFO] Connecting to Azure IoT Hub...
[OK] Connected to Azure IoT Hub

📊 Sensor Reading:
   Suhu: 27.5°C
   Kelembaban: 65%
   Tegangan: 220.5V (normal)
   Arus: 1.25A (normal)
   Daya: 275.6W

✅ Telemetry sent successfully
```

## Raspberry Pi - People Counter

### Fitur Utama

- Deteksi orang menggunakan YOLO v3-tiny
- Video streaming via Flask web server
- Publish jumlah orang ke MQTT
- Optimasi untuk Raspberry Pi (resolusi rendah, skip frames)

### Konfigurasi

Edit `raspberry-pi/people_counter_yolo.py`:

```python
# Webcam
WEBCAM_PORT = 0
FRAME_WIDTH = 320
FRAME_HEIGHT = 240

# MQTT Broker (HiveMQ Cloud)
MQTT_BROKER = "xxxxx.hivemq.cloud"
MQTT_PORT = 8883
MQTT_USERNAME = "username"
MQTT_PASSWORD = "password"
MQTT_TOPIC = "sensor/camera/people"

# Detection
CONFIDENCE_THRESHOLD = 0.5
SKIP_FRAMES = 5  # Process YOLO setiap 5 frame
```

### Data Format yang Dikirim

```json
{
  "deviceId": "RASPBERRY_PI_CAMERA_001",
  "jumlahOrang": 15,
  "timestamp": "2026-01-18T10:30:00.000Z",
  "location": "Ruang Server"
}
```

### Logic Deteksi

```python
def detect_people_yolo(frame):
    # 1. Prepare blob input untuk YOLO
    blob = cv2.dnn.blobFromImage(frame, 1/255.0, (160, 160), swapRB=True)
    
    # 2. Forward pass melalui network
    net.setInput(blob)
    outputs = net.forward(output_layers)
    
    # 3. Filter deteksi dengan confidence > threshold
    # 4. Non-Maximum Suppression untuk remove duplicates
    # 5. Hitung jumlah orang (class_id == 0)
    
    people_count = len([c for c in class_ids if c == 0])
    return people_count
```

### Menjalankan

```bash
# SSH ke Raspberry Pi
ssh user@raspberry-pi-ip

# Install dependencies
pip3 install -r requirements.txt

# Jalankan
python3 people_counter_yolo.py

# Akses video stream
# Browser: http://raspberry-pi-ip:5000/
```

## Azure Functions

### Daftar Functions

| Function | Trigger | Deskripsi |
|----------|---------|-----------|
| `IoTHubToStorage` | EventHub | Terima data dari IoT Hub, simpan ke Storage Table |
| `GetTelemetryData` | HTTP | API untuk ambil data sensor (latest, history, stats) |
| `GetACRecommendation` | HTTP | API untuk rekomendasi suhu AC |
| `MqttToIoTHub` | HTTP/Timer | Bridge data MQTT ke IoT Hub |
| `SaveSensorData` | HTTP | Simpan data sensor manual |

### IoTHubToStorage Logic

```javascript
// Terima message dari IoT Hub Event Hub
module.exports = async function (context, eventHubMessages) {
    for (const message of eventHubMessages) {
        // Parse data sensor
        const sensorData = JSON.parse(message);
        
        // Prepare entity untuk Storage Table
        const entity = {
            partitionKey: sensorData.deviceId,
            rowKey: Date.now().toString(),
            timestamp: sensorData.timestamp,
            suhu: sensorData.suhu,
            kelembaban: sensorData.kelembaban,
            tegangan: sensorData.tegangan,
            arus: sensorData.arus,
            daya: sensorData.daya
        };
        
        // Insert ke Azure Storage Table
        await tableClient.createEntity(entity);
    }
};
```

### GetTelemetryData API

```
GET /api/GetTelemetryData/{action}

Actions:
- latest      : Data terbaru
- history     : Data historis (query: ?hours=24&limit=100)
- stats       : Statistik (min, max, avg)
- people      : Data jumlah orang
```

### GetACRecommendation API

```
POST /api/GetACRecommendation

Request:
{
  "suhu": 28.0,
  "kelembaban": 70,
  "jumlahOrang": 20,
  "daya": 1500
}

Response:
{
  "recommendedTemp": 22.5,
  "comfortLevel": "COOL",
  "reason": "AC lebih dingin karena kondisi ruangan panas dan padat",
  "energySavingPercent": 0,
  "confidence": 0.96
}
```

## Instalasi & Setup

### 1. Setup ESP32

```bash
# Install PlatformIO extension di VS Code
# Buka folder "sensor iot"
# Edit src/main.cpp dengan kredensial WiFi & Azure
# Upload ke ESP32

cd "sensor iot"
platformio run --target upload
```

### 2. Setup Raspberry Pi

```bash
# Copy files ke Raspberry Pi
scp -r raspberry-pi/* user@raspberry-pi:~/

# SSH ke Raspberry Pi
ssh user@raspberry-pi

# Install dependencies
pip3 install -r requirements.txt

# Jalankan
python3 people_counter_yolo.py
```

### 3. Setup Azure Functions

```bash
# Install Azure Functions Core Tools
npm install -g azure-functions-core-tools@4

# Deploy
cd "sensor iot/azure-setup/azure-function"
npm install
func azure functionapp publish FUNCTION_APP_NAME
```

### 4. Konfigurasi Azure IoT Hub

1. Buat IoT Hub di Azure Portal
2. Buat Device dengan ID: `ESP32_ENERGY_MONITOR_001`
3. Copy Primary Key ke `src/main.cpp`
4. Setup routing ke Event Hub / Storage

## Testing

### Test ESP32 (Lokal)

```bash
cd "sensor iot"
platformio device monitor --baud 115200
```

### Test Raspberry Pi (Lokal)

```bash
python3 people_counter_yolo.py
# Buka browser: http://localhost:5000/
```

### Test Azure Functions (Lokal)

```bash
cd "sensor iot/azure-setup/azure-function"
npm install
func start

# Test endpoints
curl http://localhost:7071/api/GetTelemetryData/latest
curl -X POST http://localhost:7071/api/GetACRecommendation \
  -H "Content-Type: application/json" \
  -d '{"suhu":28,"kelembaban":70,"jumlahOrang":20,"daya":1500}'
```

### Test Azure Functions (Cloud)

```bash
curl https://FUNCTION_APP.azurewebsites.net/api/GetTelemetryData/latest
```

## Deployment

### Deploy ESP32

1. Edit kredensial di `src/main.cpp`
2. Build dan upload via PlatformIO
3. Monitor serial untuk verifikasi

### Deploy Raspberry Pi

1. Setup sebagai systemd service untuk autostart
2. Lihat `raspberry-pi/README.md` untuk detail

### Deploy Azure Functions

```bash
cd "sensor iot/azure-setup/azure-function"
func azure functionapp publish FUNCTION_APP_NAME --javascript
```

## Troubleshooting

### ESP32 Tidak Konek WiFi

```
[ERROR] WiFi connection failed
```

**Solusi:**
1. Cek SSID dan password
2. Pastikan 2.4GHz (ESP32 tidak support 5GHz)
3. Cek jarak ke router

### ESP32 Tidak Konek Azure

```
[ERROR] MQTT connection failed
```

**Solusi:**
1. Cek IoT Hub name dan device key
2. Pastikan NTP time sync (SAS token butuh waktu akurat)
3. Cek firewall port 8883

### Tegangan/Arus Tidak Terbaca

```
Tegangan: 0V (disconnected)
```

**Solusi:**
1. Cek wiring sensor
2. Kalibrasi faktor `VOLTAGE_CALIBRATION`
3. Pastikan sensor terhubung ke sumber AC

### Raspberry Pi YOLO Lambat

**Solusi:**
1. Kurangi resolusi (`FRAME_WIDTH`, `FRAME_HEIGHT`)
2. Naikkan `SKIP_FRAMES`
3. Gunakan `INPUT_SIZE` lebih kecil

### Azure Function Tidak Trigger

**Solusi:**
1. Cek Event Hub connection string
2. Verifikasi IoT Hub routing
3. Cek logs di Azure Portal

---

📝 **Catatan Keamanan**: Jangan pernah commit kredensial (WiFi password, Azure keys) ke repository. Gunakan environment variables atau file konfigurasi terpisah.

### Upload ESP32

```bash
cd "sensor iot"
platformio run --target upload
```

### Setup Raspberry Pi

Copy file ke Raspberry Pi:

```bash
scp "sensor iot/raspberry-pi/people_counter_yolo.py" [user]@[raspi_ip]:~/
scp "sensor iot/raspberry-pi/requirements.txt" [user]@[raspi_ip]:~/
```

Di Raspberry Pi:

```bash
pip3 install -r requirements.txt
python3 people_counter_yolo.py
```
