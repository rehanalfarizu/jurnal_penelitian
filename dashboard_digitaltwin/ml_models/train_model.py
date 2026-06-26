"""
Training script untuk ML Model - Energy Consumption Forecasting
Memprediksi konsumsi daya berdasarkan suhu, kelembaban, dan jumlah orang
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import pickle
import os
from pathlib import Path

# ===== CONFIG =====
DATA_PATH = "../sensor_data_sample_2026-01-04.csv"
MODEL_DIR = "./models"
MODEL_NAME = "energy_forecast_model.pkl"
SCALER_NAME = "scaler.pkl"

# ===== LOAD DATA =====
print("📊 Loading data...")
df = pd.read_csv(DATA_PATH)

print(f"✓ Loaded {len(df)} records")
print(f"\nColumns: {df.columns.tolist()}")
print(f"\nFirst rows:\n{df.head()}")

# ===== PREPROCESSING =====
print("\n🔧 Preprocessing data...")

# Features (X) dan Target (y)
features = ['suhu', 'kelembaban', 'jumlahOrang', 'tegangan']
X = df[features].values
y = df['daya'].values

print(f"Features shape: {X.shape}")
print(f"Target shape: {y.shape}")

# Split data
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# Scaling
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

print(f"Training set: {X_train.shape[0]} samples")
print(f"Test set: {X_test.shape[0]} samples")

# ===== TRAINING =====
print("\n🤖 Training model...")
model = RandomForestRegressor(
    n_estimators=100,
    max_depth=20,
    random_state=42,
    n_jobs=-1
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
print(f"  MSE: {train_mse:.4f}")
print(f"  MAE: {train_mae:.4f}")
print(f"  R² Score: {train_r2:.4f}")

print(f"\nTest Metrics:")
print(f"  MSE: {test_mse:.4f}")
print(f"  MAE: {test_mae:.4f}")
print(f"  R² Score: {test_r2:.4f}")

# Feature importance
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

print("\n✅ Training complete!")
