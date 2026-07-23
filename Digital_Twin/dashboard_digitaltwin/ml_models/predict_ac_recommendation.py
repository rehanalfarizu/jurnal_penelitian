"""
AC Temperature Recommendation - Prediksi suhu AC optimal
"""

import pickle
import numpy as np
import os
from datetime import datetime

# ===== CONFIG =====
MODEL_DIR = "./models"
MODEL_NAME = "ac_recommendation_model.pkl"
SCALER_NAME = "ac_scaler.pkl"

# ===== LOAD MODEL =====
print("📂 Loading AC Recommendation Model...")
model_path = os.path.join(MODEL_DIR, MODEL_NAME)
scaler_path = os.path.join(MODEL_DIR, SCALER_NAME)

try:
    with open(model_path, 'rb') as f:
        model = pickle.load(f)
    with open(scaler_path, 'rb') as f:
        scaler = pickle.load(f)
    print("✓ Model loaded successfully\n")
except FileNotFoundError:
    print("❌ Model file not found. Please run train_ac_recommendation.py first!")
    exit(1)

# ===== EXAMPLE RECOMMENDATIONS =====
print("❄️ AC Temperature Recommendations\n")
print("=" * 70)

# Example scenarios
test_cases = [
    {
        "name": "Morning - Few people, Cool ambient",
        "suhu": 20,
        "kelembaban": 55,
        "jumlahOrang": 5,
        "daya": 1.2,
        "hour": 8,
        "month": 1
    },
    {
        "name": "Peak hours - Many people, Warm ambient",
        "suhu": 26,
        "kelembaban": 65,
        "jumlahOrang": 30,
        "daya": 4.5,
        "hour": 14,
        "month": 1
    },
    {
        "name": "Afternoon - Medium people, Hot & Humid",
        "suhu": 28,
        "kelembaban": 75,
        "jumlahOrang": 20,
        "daya": 3.8,
        "hour": 15,
        "month": 1
    },
    {
        "name": "Evening - Few people, Cool",
        "suhu": 22,
        "kelembaban": 50,
        "jumlahOrang": 3,
        "daya": 1.0,
        "hour": 18,
        "month": 1
    },
]

features = ['suhu', 'kelembaban', 'jumlahOrang', 'daya', 'hour', 'month']

for test_case in test_cases:
    X = np.array([[test_case[f] for f in features]])
    X_scaled = scaler.transform(X)
    recommendation = model.predict(X_scaled)[0]
    
    print(f"\n📍 {test_case['name']}")
    print(f"   Ambient Temp: {test_case['suhu']}°C")
    print(f"   Humidity: {test_case['kelembaban']}%")
    print(f"   People: {test_case['jumlahOrang']}")
    print(f"   Power: {test_case['daya']} kW")
    print(f"   Time: {test_case['hour']:02d}:00")
    print(f"\n   🎯 Recommended AC Temp: {recommendation:.1f}°C")
    
    # Comfort recommendation
    if recommendation <= 21:
        comfort = "❄️ COOL (for high occupancy/hot ambient)"
    elif recommendation <= 23:
        comfort = "🌬️ COOL-COMFORTABLE"
    elif recommendation <= 25:
        comfort = "😊 COMFORTABLE (standard setting)"
    elif recommendation <= 26:
        comfort = "🌡️ WARM-COMFORTABLE"
    else:
        comfort = "🔥 WARM (energy saving)"
    
    print(f"   {comfort}")
    print("-" * 70)

print("\n✅ Recommendations Complete!")
print("\nTips:")
print("• Set AC to recommended temperature for optimal comfort & energy savings")
print("• More people in room = cooler AC recommended")
print("• Higher humidity = cooler AC for comfort")
print("• Peak hours with many people = maximum cooling")
