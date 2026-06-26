"""
Prediction script - Gunakan trained model untuk prediksi
"""

import pandas as pd
import pickle
import numpy as np
import os

# ===== CONFIG =====
MODEL_DIR = "./models"
MODEL_NAME = "energy_forecast_model.pkl"
SCALER_NAME = "scaler.pkl"

# ===== LOAD MODEL =====
print("📂 Loading model...")
model_path = os.path.join(MODEL_DIR, MODEL_NAME)
scaler_path = os.path.join(MODEL_DIR, SCALER_NAME)

try:
    with open(model_path, 'rb') as f:
        model = pickle.load(f)
    with open(scaler_path, 'rb') as f:
        scaler = pickle.load(f)
    print("✓ Model loaded successfully")
except FileNotFoundError:
    print("❌ Model file not found. Please run train_model.py first!")
    exit(1)

# ===== EXAMPLE PREDICTIONS =====
print("\n🔮 Making predictions...\n")

# Example data: suhu, kelembaban, jumlahOrang, tegangan
test_cases = [
    {"suhu": 22, "kelembaban": 55, "jumlahOrang": 10, "tegangan": 220},
    {"suhu": 25, "kelembaban": 45, "jumlahOrang": 30, "tegangan": 220},
    {"suhu": 18, "kelembaban": 70, "jumlahOrang": 5, "tegangan": 220},
]

features = ['suhu', 'kelembaban', 'jumlahOrang', 'tegangan']

for i, test_case in enumerate(test_cases, 1):
    X = np.array([[test_case[f] for f in features]])
    X_scaled = scaler.transform(X)
    prediction = model.predict(X_scaled)[0]
    
    print(f"Test Case {i}:")
    print(f"  Input: Suhu={test_case['suhu']}°C, Kelembaban={test_case['kelembaban']}%, Orang={test_case['jumlahOrang']}, Tegangan={test_case['tegangan']}V")
    print(f"  Predicted Power: {prediction:.2f} kW")
    print()

print("✅ Prediction complete!")
