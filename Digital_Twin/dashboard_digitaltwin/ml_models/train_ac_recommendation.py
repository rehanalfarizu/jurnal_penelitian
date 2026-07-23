"""
Training script - AC Temperature Recommendation Model
Memprediksi suhu AC optimal berdasarkan kondisi ruangan
(suhu, kelembaban, jumlah orang, waktu, dll)
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import pickle
import os
from datetime import datetime

# ===== CONFIG =====
DATA_PATH = "../sensor_data_sample_2026-01-04.csv"
MODEL_DIR = "./models"
MODEL_NAME = "ac_recommendation_model.pkl"
SCALER_NAME = "ac_scaler.pkl"

# ===== LOAD DATA =====
print("📊 Loading data...")
df = pd.read_csv(DATA_PATH)
df['timestamp'] = pd.to_datetime(df['timestamp'])
df['hour'] = df['timestamp'].dt.hour
df['month'] = df['timestamp'].dt.month

print(f"✓ Loaded {len(df)} records")
print(f"\nFirst rows:\n{df[['timestamp', 'suhu', 'kelembaban', 'jumlahOrang']].head()}")

# ===== FEATURE ENGINEERING =====
print("\n🔧 Feature Engineering...")

# Logic untuk recommended AC temperature:
# - High people count → cooler AC
# - High ambient temp → cooler AC
# - High humidity → cooler AC (untuk comfort)
# - Peak hours (8-17) → cooler
# - Min comfort temperature: 20°C, Max: 28°C

def calculate_recommended_temp(row):
    """
    Hitung suhu AC yang direkomendasikan berdasarkan kondisi ruangan
    
    Logic:
    - Base temperature: 24°C (comfortable middle)
    - People factor: +1°C per 10 orang (max 25°C)
    - Temperature factor: +0.5°C per °C above 25 (cooling needed)
    - Humidity factor: -0.5°C jika humidity > 60% (cooling for comfort)
    - Time factor: -1°C jika peak hours dengan banyak orang
    """
    base_temp = 24.0
    
    # People factor (more people = cooler)
    people_factor = -row['jumlahOrang'] / 20  # -0.5°C per 10 orang
    
    # Ambient temp factor (hotter = cooler AC)
    ambient_factor = (row['suhu'] - 25) * 0.3 if row['suhu'] > 25 else 0
    
    # Humidity factor (higher humidity = cooler for comfort)
    humidity_factor = -0.5 if row['kelembaban'] > 60 else 0
    
    # Time factor (peak hours 8-17)
    if 8 <= row['hour'] <= 17 and row['jumlahOrang'] > 10:
        time_factor = -1.0
    else:
        time_factor = 0
    
    recommended = base_temp + people_factor + ambient_factor + humidity_factor + time_factor
    
    # Clamp between 20-28°C
    return np.clip(recommended, 20, 28)

df['recommended_temp'] = df.apply(calculate_recommended_temp, axis=1)

print(f"Recommended temp range: {df['recommended_temp'].min():.1f}°C - {df['recommended_temp'].max():.1f}°C")
print(f"Mean recommended temp: {df['recommended_temp'].mean():.1f}°C")

# ===== PREPARE FEATURES =====
features = ['suhu', 'kelembaban', 'jumlahOrang', 'daya', 'hour', 'month']
X = df[features].values
y = df['recommended_temp'].values

print(f"\nFeatures: {features}")
print(f"X shape: {X.shape}")
print(f"y shape: {y.shape}")

# ===== SPLIT DATA =====
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# ===== SCALING =====
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

print(f"\nTrain set: {X_train.shape[0]} samples")
print(f"Test set: {X_test.shape[0]} samples")

# ===== TRAINING =====
print("\n🤖 Training model...")
model = GradientBoostingRegressor(
    n_estimators=100,
    learning_rate=0.1,
    max_depth=5,
    random_state=42
)

model.fit(X_train_scaled, y_train)

# ===== EVALUATION =====
print("\n📈 Evaluating model...")
y_pred_train = model.predict(X_train_scaled)
y_pred_test = model.predict(X_test_scaled)

train_mse = mean_squared_error(y_train, y_pred_train)
test_mse = mean_squared_error(y_test, y_pred_test)
train_mae = mean_absolute_error(y_train, y_pred_train)
test_mae = mean_absolute_error(y_test, y_pred_test)
train_r2 = r2_score(y_train, y_pred_train)
test_r2 = r2_score(y_test, y_pred_test)

print(f"\nTrain Metrics:")
print(f"  MAE: {train_mae:.4f}°C (mean absolute error)")
print(f"  R² Score: {train_r2:.4f}")

print(f"\nTest Metrics:")
print(f"  MAE: {test_mae:.4f}°C (mean absolute error)")
print(f"  R² Score: {test_r2:.4f}")

# ===== FEATURE IMPORTANCE =====
print("\n🎯 Feature Importance:")
for feat, importance in zip(features, model.feature_importances_):
    print(f"  {feat}: {importance:.4f}")

# ===== SAVE MODEL =====
print("\n💾 Saving model...")
os.makedirs(MODEL_DIR, exist_ok=True)

model_path = os.path.join(MODEL_DIR, MODEL_NAME)
scaler_path = os.path.join(MODEL_DIR, SCALER_NAME)

with open(model_path, 'wb') as f:
    pickle.dump(model, f)
    
with open(scaler_path, 'wb') as f:
    pickle.dump(scaler, f)

print(f"✓ Model saved: {model_path}")
print(f"✓ Scaler saved: {scaler_path}")

print("\n✅ AC Recommendation Model Training Complete!")
