# 🤖 Machine Learning Models - Digital Twin Energy Monitoring

Modul Machine Learning untuk sistem Digital Twin yang menyediakan prediksi konsumsi energi dan rekomendasi pengaturan AC berdasarkan data sensor real-time.

## 📋 Daftar Isi

- [Overview](#overview)
- [Arsitektur](#arsitektur)
- [Struktur Folder](#struktur-folder)
- [Model yang Tersedia](#model-yang-tersedia)
- [Instalasi](#instalasi)
- [Penggunaan](#penggunaan)
- [API Server](#api-server)
- [Auto Training](#auto-training)
- [Konfigurasi](#konfigurasi)
- [Troubleshooting](#troubleshooting)

## Overview

Sistem ML ini dirancang untuk:
1. **Energy Forecasting**: Memprediksi konsumsi daya berdasarkan kondisi lingkungan
2. **AC Recommendation**: Merekomendasikan suhu AC optimal untuk kenyamanan dan efisiensi energi
3. **Auto-Training**: Training ulang otomatis dengan data terbaru dari Azure Storage

```
┌─────────────────────────────────────────────────────────────┐
│                    ML SYSTEM FLOW                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   Azure Storage ──► auto_train.py ──► Models (.pkl)        │
│        │                                    │               │
│        │                                    ▼               │
│        │                            prediction_api.py       │
│        │                                    │               │
│        ▼                                    ▼               │
│   Data Real-time ──────────────────► Dashboard/API         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Arsitektur

### Data Flow

```
┌───────────────┐     ┌────────────────┐     ┌──────────────┐
│ Azure Storage │────►│ auto_train.py  │────►│ Trained      │
│ (Sensor Data) │     │ (Scheduler)    │     │ Models       │
└───────────────┘     └────────────────┘     └──────┬───────┘
                                                    │
                                                    ▼
┌───────────────┐     ┌────────────────┐     ┌──────────────┐
│ Sensor Data   │────►│ prediction_    │────►│ Dashboard    │
│ (Real-time)   │     │ api.py         │     │ Frontend     │
└───────────────┘     └────────────────┘     └──────────────┘
```

### Algoritma yang Digunakan

| Model | Algoritma | Akurasi | Deskripsi |
|-------|-----------|---------|-----------|
| Energy Forecast | Random Forest Regressor | R² ~0.85 | Prediksi konsumsi daya (Watt) |
| AC Recommendation | Gradient Boosting Regressor | R² ~0.96 | Rekomendasi suhu AC optimal |

## Struktur Folder

```
ml_models/
├── README.md                    # Dokumentasi ini
├── requirements.txt             # Python dependencies
│
├── 📊 TRAINING SCRIPTS
├── train_model.py               # Training Energy Forecast Model
├── train_ac_recommendation.py   # Training AC Recommendation Model
├── train_from_azure.py          # Training dengan data dari Azure
├── auto_train.py                # Auto-training dengan scheduler
├── run_auto_train.sh            # Shell script untuk cron job
│
├── 🔮 PREDICTION SCRIPTS
├── predict.py                   # Prediksi standalone
├── predict_ac_recommendation.py # Prediksi AC standalone
├── prediction_api.py            # Flask API Server
├── ml_prediction_api.py         # API alternatif
│
└── 📁 models/                   # Trained models storage
    ├── energy_forecast_model.pkl
    ├── ac_recommendation_model.pkl
    ├── scaler.pkl
    ├── ac_scaler.pkl
    ├── energy_features.pkl
    ├── ac_features.pkl
    ├── model_config.json
    └── training_status.json
```

## Model yang Tersedia

### 1. Energy Forecast Model

Memprediksi konsumsi daya listrik berdasarkan kondisi lingkungan.

**Features Input:**
| Feature | Tipe | Range | Deskripsi |
|---------|------|-------|-----------|
| `suhu` | float | 18-35 | Suhu ruangan (°C) |
| `kelembaban` | float | 40-90 | Kelembaban udara (%) |
| `jumlahOrang` | int | 0-100 | Jumlah orang di ruangan |
| `tegangan` | float | 200-240 | Tegangan listrik (V) |
| `hour` | int | 0-23 | Jam (dari timestamp) |

**Output:**
- `daya`: Prediksi konsumsi daya dalam Watt

**Logic:**
```python
# Faktor yang mempengaruhi konsumsi daya:
# 1. Jumlah orang lebih banyak = AC bekerja lebih keras
# 2. Suhu ambient tinggi = AC bekerja lebih keras
# 3. Jam kerja (8-17) = beban lebih tinggi
# 4. Tegangan mempengaruhi efisiensi
```

### 2. AC Recommendation Model

Merekomendasikan suhu AC optimal untuk kenyamanan dan efisiensi.

**Features Input:**
| Feature | Tipe | Range | Deskripsi |
|---------|------|-------|-----------|
| `suhu` | float | 18-35 | Suhu ruangan saat ini (°C) |
| `kelembaban` | float | 40-90 | Kelembaban udara (%) |
| `jumlahOrang` | int | 0-100 | Jumlah orang di ruangan |
| `daya` | float | 0-5000 | Konsumsi daya saat ini (W) |
| `hour` | int | 0-23 | Jam saat ini |
| `month` | int | 1-12 | Bulan saat ini |

**Output:**
- `recommended_temp`: Suhu AC yang direkomendasikan (20-28°C)

**Logic Rekomendasi:**
```python
def calculate_recommended_temp(data):
    base_temp = 24.0  # Base comfort temperature
    
    # People factor: lebih banyak orang = lebih dingin
    people_factor = -jumlahOrang / 20  # -0.5°C per 10 orang
    
    # Ambient factor: suhu ambient tinggi = AC lebih dingin
    ambient_factor = (suhu - 25) * 0.3 if suhu > 25 else 0
    
    # Humidity factor: kelembaban tinggi = lebih dingin
    humidity_factor = -0.5 if kelembaban > 60 else 0
    
    # Time factor: jam kerja dengan banyak orang
    if 8 <= hour <= 17 and jumlahOrang > 10:
        time_factor = -1.0
    else:
        time_factor = 0
    
    recommended = base_temp + people_factor + ambient_factor + humidity_factor + time_factor
    return np.clip(recommended, 20, 28)  # Range 20-28°C
```

## Instalasi

### Prerequisites

- Python 3.8+
- pip

### Setup

```bash
# 1. Masuk ke folder ml_models
cd ml_models

# 2. Buat virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# atau
venv\Scripts\activate     # Windows

# 3. Install dependencies
pip install -r requirements.txt
```

### Dependencies (requirements.txt)

```
pandas>=2.0.0
numpy>=1.24.0
scikit-learn>=1.3.0
flask>=2.3.0
flask-cors>=4.0.0
azure-data-tables>=12.4.0
python-dotenv>=1.0.0
```

## Penggunaan

### Training Model dari CSV

```bash
# Training Energy Forecast Model
python train_model.py

# Training AC Recommendation Model
python train_ac_recommendation.py
```

### Training dari Azure Storage

```bash
# Training dengan data real dari Azure
python train_from_azure.py
```

### Prediksi Standalone

```bash
# Prediksi konsumsi energi
python predict.py

# Prediksi rekomendasi AC
python predict_ac_recommendation.py
```

### Contoh Penggunaan dalam Code

```python
import pickle
import numpy as np

# Load model
with open('models/energy_forecast_model.pkl', 'rb') as f:
    model = pickle.load(f)
with open('models/scaler.pkl', 'rb') as f:
    scaler = pickle.load(f)

# Prediksi
features = ['suhu', 'kelembaban', 'jumlahOrang', 'tegangan']
data = {
    'suhu': 27.5,
    'kelembaban': 65.0,
    'jumlahOrang': 15,
    'tegangan': 220.0
}

X = np.array([[data[f] for f in features]])
X_scaled = scaler.transform(X)
prediction = model.predict(X_scaled)[0]

print(f"Predicted Power: {prediction:.2f} Watt")
```

## API Server

### Menjalankan API Server

```bash
python prediction_api.py
```

Server berjalan di `http://localhost:5000`

### Endpoints

#### Health Check
```http
GET /api/health
```

Response:
```json
{
  "status": "healthy",
  "models_loaded": true,
  "model_version": 3,
  "last_training": "2026-01-15T10:30:00"
}
```

#### Predict Energy Consumption
```http
POST /api/predict/energy
Content-Type: application/json

{
  "suhu": 27.5,
  "kelembaban": 65,
  "jumlahOrang": 15,
  "tegangan": 220
}
```

Response:
```json
{
  "prediction": 1250.5,
  "unit": "Watt",
  "confidence": 85.2,
  "features_used": ["suhu", "kelembaban", "jumlahOrang", "tegangan", "hour"],
  "model_version": 3
}
```

#### Predict AC Recommendation
```http
POST /api/predict/ac
Content-Type: application/json

{
  "suhu": 28.0,
  "kelembaban": 70,
  "jumlahOrang": 20,
  "daya": 1500
}
```

Response:
```json
{
  "recommended_temp": 22.5,
  "comfort_level": "COOL",
  "reason": "AC lebih dingin karena kondisi ruangan panas dan padat",
  "energy_saving": 0,
  "confidence": 96.0
}
```

#### Reload Models
```http
POST /api/reload
```

## Auto Training

### Cara Kerja

Auto-training system akan:
1. Fetch data terbaru dari Azure Storage
2. Cek apakah ada cukup data baru (>50 records)
3. Training ulang kedua model
4. Simpan model baru dengan versioning
5. Update training status

### Menjalankan Auto-Training

```bash
# Manual
python auto_train.py

# Dengan shell script
./run_auto_train.sh
```

### Setup Cron Job (Linux/Mac)

```bash
# Edit crontab
crontab -e

# Tambahkan untuk run setiap 6 jam
0 */6 * * * cd /path/to/ml_models && ./run_auto_train.sh >> /var/log/ml_auto_train.log 2>&1
```

### Training Status File

File `models/training_status.json`:
```json
{
  "last_training": "2026-01-15T10:30:00",
  "last_record_count": 1500,
  "model_version": 3,
  "accuracy": {
    "energy_model": {"r2": 0.85, "mae": 45.2},
    "ac_model": {"r2": 0.96, "mae": 0.8}
  }
}
```

## Konfigurasi

### Environment Variables

Buat file `.env`:

```env
# Azure Storage
STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=xxx;AccountKey=xxx;EndpointSuffix=core.windows.net

# Training Settings
MIN_RECORDS_FOR_TRAINING=100
RETRAIN_THRESHOLD=50

# API Settings
API_HOST=0.0.0.0
API_PORT=5000
```

### Model Config

File `models/model_config.json`:
```json
{
  "model_version": 3,
  "training_date": "2026-01-15T10:30:00",
  "energy_features": ["suhu", "kelembaban", "jumlahOrang", "tegangan", "hour"],
  "ac_features": ["suhu", "kelembaban", "jumlahOrang", "daya", "hour", "month"],
  "energy_metrics": {"r2": 0.85, "mae": 45.2},
  "ac_metrics": {"r2": 0.96, "mae": 0.8}
}
```

## Troubleshooting

### Model Not Found

```
❌ Model file not found. Please run train_model.py first!
```

**Solusi:** Jalankan training script terlebih dahulu:
```bash
python train_model.py
python train_ac_recommendation.py
```

### Azure Connection Error

```
❌ Gagal fetch data: Connection refused
```

**Solusi:**
1. Cek connection string di `.env`
2. Pastikan Azure Storage accessible
3. Cek firewall/network

### Low Accuracy

**Penyebab:**
- Data training terlalu sedikit
- Data tidak representative

**Solusi:**
1. Tambah data training
2. Cek kualitas data (outliers, missing values)
3. Feature engineering tambahan

### API Server Error

```
❌ Failed to load models
```

**Solusi:**
1. Pastikan semua model files ada di folder `models/`
2. Cek permission file
3. Restart API server setelah training baru

## 📊 Performance Metrics

| Model | R² Score | MAE | Training Time |
|-------|----------|-----|---------------|
| Energy Forecast | 0.85 | 45.2 W | ~5 detik |
| AC Recommendation | 0.96 | 0.8 °C | ~3 detik |

## 🔗 Integrasi

Model ML ini terintegrasi dengan:
- **Azure Functions** (`GetACRecommendation`): Menggunakan logic yang sama untuk API cloud
- **Dashboard Frontend**: Menampilkan prediksi dan rekomendasi real-time
- **Auto-Training**: Update model otomatis dengan data terbaru

---

📝 **Catatan**: Pastikan selalu menjalankan training dengan data yang cukup (minimal 100 records) untuk hasil yang akurat.
