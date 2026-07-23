# ☁️ Azure Setup - IoT Hub & Functions

Konfigurasi Azure IoT Hub dan Azure Functions untuk backend Digital Twin system.

## 📋 Daftar Isi

- [Overview](#overview)
- [Arsitektur](#arsitektur)
- [Azure Resources](#azure-resources)
- [Struktur Folder](#struktur-folder)
- [Azure Functions](#azure-functions)
- [Setup & Deployment](#setup--deployment)
- [API Reference](#api-reference)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)

## Overview

Azure backend menangani:
1. **Ingestion**: Menerima data dari ESP32 via Azure IoT Hub
2. **Storage**: Menyimpan data ke Azure Storage Table
3. **API**: Menyediakan REST API untuk dashboard
4. **Analytics**: Menyediakan rekomendasi AC berbasis ML

```
┌─────────────────────────────────────────────────────────────────────┐
│                      AZURE ARCHITECTURE                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   ESP32 ────MQTT/TLS────► Azure IoT Hub                             │
│                                │                                     │
│                                ▼ Event Hub Compatible Endpoint       │
│                        ┌───────────────┐                            │
│                        │IoTHubToStorage│ ◄─── Event Hub Trigger     │
│                        │   Function    │                            │
│                        └───────┬───────┘                            │
│                                │                                     │
│                                ▼                                     │
│                     ┌─────────────────────┐                         │
│                     │ Azure Storage Table │                         │
│                     │  (SensorTelemetry)  │                         │
│                     └─────────┬───────────┘                         │
│                               │                                      │
│                    ┌──────────┴──────────┐                          │
│                    │                     │                          │
│                    ▼                     ▼                          │
│           ┌────────────────┐   ┌───────────────────┐               │
│           │GetTelemetryData│   │GetACRecommendation│               │
│           │   (HTTP API)   │   │    (ML-based)     │               │
│           └────────┬───────┘   └─────────┬─────────┘               │
│                    │                     │                          │
│                    └──────────┬──────────┘                          │
│                               │                                      │
│                               ▼                                      │
│                      ┌───────────────┐                              │
│                      │   Dashboard   │                              │
│                      │   Frontend    │                              │
│                      └───────────────┘                              │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Arsitektur

### Data Flow Detail

```
1. ESP32 sends telemetry via MQTT over TLS (port 8883)
   │
   ▼
2. Azure IoT Hub receives & validates SAS token
   │
   ▼
3. Event Hub compatible endpoint triggers Azure Function
   │
   ▼
4. IoTHubToStorage function parses JSON & stores to Table
   │
   ▼
5. GetTelemetryData API returns data to dashboard
   │
   ▼
6. GetACRecommendation calculates optimal AC setting
```

## Azure Resources

### Required Resources

| Resource | Name | SKU/Tier | Purpose |
|----------|------|----------|---------|
| IoT Hub | iothub-energymonitor-* | F1 (Free) | Device connectivity |
| Storage Account | stenergy* | Standard LRS | Data storage |
| Function App | func-energymonitor-* | Consumption | Serverless compute |
| Application Insights | (optional) | - | Monitoring |

### Resource Configuration

#### IoT Hub

```
Name: iothub-energymonitor-ef753d74
Location: Southeast Asia
SKU: F1 (Free)
Units: 1
Daily Message Quota: 8,000 messages/day

Registered Device:
- Device ID: ESP32_ENERGY_MONITOR_001
- Authentication: Symmetric Key
- Connection State: Connected
```

#### Storage Account

```
Name: mlsuhu0426140346
Location: Southeast Asia
Replication: LRS
Tables:
- SensorTelemetry (partition: deviceId)
```

#### Function App

```
Name: func-energymonitor-7d2e5be2
Runtime: Node.js 18
OS: Linux
Plan: Consumption (Serverless)
```

## Struktur Folder

```
azure-setup/
├── README.md                    # Dokumentasi ini
├── iot_hub_config.txt          # IoT Hub connection info
│
├── 📁 azure-function/          # Azure Functions code
│   ├── host.json               # Function host config
│   ├── local.settings.json     # Local dev settings
│   ├── package.json            # Dependencies
│   │
│   ├── 📁 IoTHubToStorage/     # Event Hub trigger
│   │   ├── index.js
│   │   └── function.json
│   │
│   ├── 📁 GetTelemetryData/    # HTTP API
│   │   ├── index.js
│   │   └── function.json
│   │
│   ├── 📁 GetACRecommendation/ # ML Recommendation API
│   │   ├── index.js
│   │   └── function.json
│   │
│   ├── 📁 MqttToIoTHub/        # MQTT Bridge
│   │   ├── index.js
│   │   └── function.json
│   │
│   └── 📁 SaveSensorData/      # Manual data save
│       ├── index.js
│       └── function.json
│
├── 📁 models/                   # Azure Digital Twin models
│   └── EnergyMonitorSensor.json
│
└── 📁 scripts/                  # Deployment scripts
    ├── deploy_azure.sh
    ├── setup_iot_hub.sh
    ├── quick_deploy_function.sh
    └── ...
```

## Azure Functions

### 1. IoTHubToStorage

Menerima data dari IoT Hub dan menyimpan ke Storage Table.

**Trigger:** Event Hub (IoT Hub compatible endpoint)

**Logic:**
```javascript
// Terima message dari IoT Hub
for (const message of eventHubMessages) {
    const sensorData = JSON.parse(message);
    
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
    
    await tableClient.createEntity(entity);
}
```

**Configuration (function.json):**
```json
{
  "bindings": [
    {
      "type": "eventHubTrigger",
      "name": "eventHubMessages",
      "direction": "in",
      "eventHubName": "iothub-energymonitor-xxxxx",
      "connection": "IOT_HUB_CONNECTION_STRING",
      "cardinality": "many",
      "consumerGroup": "$Default"
    }
  ]
}
```

### 2. GetTelemetryData

REST API untuk mengambil data sensor.

**Trigger:** HTTP GET

**Endpoints:**
| Route | Description |
|-------|-------------|
| `/api/GetTelemetryData/latest` | Data terbaru |
| `/api/GetTelemetryData/history?hours=24` | Data historis |
| `/api/GetTelemetryData/stats?hours=24` | Statistik |
| `/api/GetTelemetryData/people?hours=24` | Data jumlah orang |

**Response Example (latest):**
```json
{
  "success": true,
  "data": {
    "timestamp": "2026-01-18 10:30:00 WIB",
    "suhu": 27.5,
    "kelembaban": 65,
    "tegangan": 220.5,
    "arus": 1.25,
    "daya": 275.6,
    "deviceId": "ESP32_ENERGY_MONITOR_001"
  }
}
```

### 3. GetACRecommendation

API untuk mendapatkan rekomendasi AC berbasis ML.

**Trigger:** HTTP POST

**Request:**
```json
{
  "suhu": 28.0,
  "kelembaban": 70,
  "jumlahOrang": 20,
  "daya": 1500
}
```

**Response:**
```json
{
  "recommendedTemp": 22.5,
  "comfortLevel": "COOL",
  "emoji": "COOL",
  "reason": "AC lebih dingin karena kondisi ruangan panas atau padat",
  "energySavingPercent": 0,
  "confidence": 0.96,
  "model_info": {
    "training_records": 1105,
    "training_date": "2026-01-10",
    "accuracy": 0.96
  },
  "factors": {
    "ambient_temp": 28.0,
    "humidity": 70,
    "people_count": 20,
    "power_consumption": 1500,
    "current_hour": 10
  }
}
```

**ML Logic:**
```javascript
function calculateACRecommendation(sensorData) {
    let recommendedTemp = 24.0;  // Base temperature
    
    // Temperature factor
    if (suhu > 25) {
        recommendedTemp += (suhu - 25) * -0.3;
    }
    
    // Humidity factor
    if (kelembaban > 60) {
        recommendedTemp += (kelembaban - 60) * -0.01;
    }
    
    // People factor
    if (jumlahOrang > 0) {
        recommendedTemp -= (jumlahOrang / 20);
    }
    
    // Time factor (peak hours)
    if (hour >= 8 && hour <= 17) {
        recommendedTemp -= 0.5;
    }
    
    return Math.max(18, Math.min(28, recommendedTemp));
}
```

### 4. MqttToIoTHub (Optional)

Bridge data dari MQTT broker ke IoT Hub.

### 5. SaveSensorData (Manual)

Endpoint untuk menyimpan data sensor secara manual.

## Setup & Deployment

### Prerequisites

```bash
# Install Azure CLI
brew install azure-cli

# Install Azure Functions Core Tools
npm install -g azure-functions-core-tools@4

# Login to Azure
az login
```

### Local Development

```bash
cd azure-function

# Install dependencies
npm install

# Create local.settings.json
cat > local.settings.json << EOF
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "node",
    "STORAGE_CONNECTION_STRING": "YOUR_STORAGE_CONNECTION_STRING",
    "IOT_HUB_CONNECTION_STRING": "YOUR_IOT_HUB_CONNECTION_STRING"
  }
}
EOF

# Start local server
func start
```

### Deploy to Azure

```bash
# Create Function App (first time only)
az functionapp create \
    --resource-group YOUR_RESOURCE_GROUP \
    --consumption-plan-location southeastasia \
    --runtime node \
    --runtime-version 18 \
    --functions-version 4 \
    --name func-energymonitor-UNIQUE_ID \
    --storage-account YOUR_STORAGE_ACCOUNT

# Deploy functions
func azure functionapp publish func-energymonitor-UNIQUE_ID

# Set application settings
az functionapp config appsettings set \
    --name func-energymonitor-UNIQUE_ID \
    --resource-group YOUR_RESOURCE_GROUP \
    --settings "STORAGE_CONNECTION_STRING=YOUR_CONNECTION_STRING"
```

### Using Deployment Scripts

```bash
cd scripts

# Quick deploy
./quick_deploy_function.sh

# Full setup (IoT Hub + Functions)
./deploy_azure.sh
```

## API Reference

### Base URL

```
Local: http://localhost:7071/api
Production: https://func-energymonitor-xxxxx.azurewebsites.net/api
```

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/GetTelemetryData/latest` | Get latest sensor data |
| GET | `/GetTelemetryData/history?hours=24&limit=100` | Get historical data |
| GET | `/GetTelemetryData/stats?hours=24` | Get statistics |
| GET | `/GetTelemetryData/people?hours=24` | Get people count data |
| POST | `/GetACRecommendation` | Get AC recommendation |
| POST | `/SaveSensorData` | Save sensor data manually |

### CORS

Semua endpoint sudah dikonfigurasi dengan CORS:
```javascript
headers: {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type'
}
```

## Monitoring

### Application Insights (Recommended)

1. Create Application Insights di Azure Portal
2. Add connection string ke Function App settings
3. View logs dan metrics di Azure Portal

### Manual Logging

```bash
# Stream logs
func azure functionapp logstream func-energymonitor-xxxxx

# Or via Azure CLI
az functionapp log tail --name func-energymonitor-xxxxx --resource-group YOUR_RG
```

### Storage Explorer

1. Download Azure Storage Explorer
2. Connect dengan connection string
3. Browse Tables > SensorTelemetry

## Troubleshooting

### Function Tidak Trigger

**Symptoms:** Data masuk ke IoT Hub tapi tidak tersimpan

**Solutions:**
1. Cek Event Hub connection string di application settings
2. Verify consumer group `$Default` ada
3. Cek logs di Application Insights

```bash
# Check function status
az functionapp show --name func-energymonitor-xxxxx --resource-group YOUR_RG
```

### Storage Connection Error

**Symptoms:** `Error: STORAGE_CONNECTION_STRING not configured`

**Solutions:**
1. Verify connection string di local.settings.json (local)
2. Verify di Application Settings (production)

```bash
# List current settings
az functionapp config appsettings list --name func-energymonitor-xxxxx --resource-group YOUR_RG
```

### CORS Error

**Symptoms:** Dashboard tidak bisa fetch data

**Solutions:**
1. Verify CORS headers di function response
2. Check browser console untuk detail error

### IoT Hub Device Not Found

**Symptoms:** ESP32 tidak bisa connect

**Solutions:**
1. Verify device terdaftar di IoT Hub
2. Check device key di ESP32 code
3. Verify device connection state di Azure Portal

```bash
# List devices
az iot hub device-identity list --hub-name iothub-energymonitor-xxxxx
```

---

📝 **Note:** Selalu gunakan environment variables untuk menyimpan connection strings. Jangan commit credentials ke repository.
```

### Data Tidak Tersimpan

Cek Storage connection string. Verifikasi table SensorTelemetry sudah dibuat.

### API Return Empty

Pastikan parameter query benar (hours, deviceId). Cek apakah ada data di storage table.
