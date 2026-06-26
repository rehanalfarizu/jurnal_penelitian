"""
ML Prediction API Server
Flask API untuk serving ML predictions ke dashboard

Jalankan: python prediction_api.py
Endpoint: http://localhost:5000/api/predict
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import pickle
import numpy as np
import os
import json
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Enable CORS untuk dashboard

MODEL_DIR = "./models"

# ===== LOAD MODELS =====
def load_models():
    """Load semua model dari file"""
    global energy_model, energy_scaler, energy_features
    global ac_model, ac_scaler, ac_features
    global model_config
    
    try:
        # Load Energy Model
        with open(os.path.join(MODEL_DIR, 'energy_forecast_model.pkl'), 'rb') as f:
            energy_model = pickle.load(f)
        with open(os.path.join(MODEL_DIR, 'scaler.pkl'), 'rb') as f:
            energy_scaler = pickle.load(f)
        with open(os.path.join(MODEL_DIR, 'energy_features.pkl'), 'rb') as f:
            energy_features = pickle.load(f)
            
        # Load AC Model
        with open(os.path.join(MODEL_DIR, 'ac_recommendation_model.pkl'), 'rb') as f:
            ac_model = pickle.load(f)
        with open(os.path.join(MODEL_DIR, 'ac_scaler.pkl'), 'rb') as f:
            ac_scaler = pickle.load(f)
        with open(os.path.join(MODEL_DIR, 'ac_features.pkl'), 'rb') as f:
            ac_features = pickle.load(f)
            
        # Load config
        config_path = os.path.join(MODEL_DIR, 'model_config.json')
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                model_config = json.load(f)
        else:
            model_config = {}
            
        print("[OK] Models loaded successfully")
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to load models: {e}")
        return False

# Load models on startup
models_loaded = load_models()

# ===== API ENDPOINTS =====

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "models_loaded": models_loaded,
        "model_version": model_config.get('model_version', 'unknown'),
        "last_training": model_config.get('training_date', 'unknown')
    })

@app.route('/api/reload', methods=['POST'])
def reload_models():
    """Reload models setelah training baru"""
    global models_loaded
    models_loaded = load_models()
    return jsonify({
        "success": models_loaded,
        "message": "Models reloaded" if models_loaded else "Failed to reload models"
    })

@app.route('/api/predict/energy', methods=['POST'])
def predict_energy():
    """Predict energy consumption"""
    if not models_loaded:
        return jsonify({"error": "Models not loaded"}), 500
    
    try:
        data = request.json
        
        # Prepare features
        feature_values = []
        for feat in energy_features:
            if feat in data:
                feature_values.append(float(data[feat]))
            elif feat == 'hour':
                feature_values.append(datetime.now().hour)
            else:
                return jsonify({"error": f"Missing feature: {feat}"}), 400
        
        # Predict
        X = np.array([feature_values])
        X_scaled = energy_scaler.transform(X)
        prediction = energy_model.predict(X_scaled)[0]
        
        # Calculate confidence based on R2
        r2 = model_config.get('energy_metrics', {}).get('r2', 0.8)
        confidence = min(95, r2 * 100)
        
        return jsonify({
            "prediction": round(prediction, 2),
            "unit": "Watt",
            "confidence": round(confidence, 1),
            "features_used": energy_features,
            "model_version": model_config.get('model_version', 1)
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/predict/ac', methods=['POST'])
def predict_ac():
    """Predict AC recommendation"""
    if not models_loaded:
        return jsonify({"error": "Models not loaded"}), 500
    
    try:
        data = request.json
        
        # Prepare features
        feature_values = []
        for feat in ac_features:
            if feat in data:
                feature_values.append(float(data[feat]))
            elif feat == 'hour':
                feature_values.append(datetime.now().hour)
            elif feat == 'month':
                feature_values.append(datetime.now().month)
            else:
                # Default value for missing optional features
                if feat == 'jumlahOrang':
                    feature_values.append(0)
                else:
                    return jsonify({"error": f"Missing feature: {feat}"}), 400
        
        # Predict
        X = np.array([feature_values])
        X_scaled = ac_scaler.transform(X)
        recommended_temp = ac_model.predict(X_scaled)[0]
        
        # Clip to valid range
        recommended_temp = np.clip(recommended_temp, 16, 30)
        
        # Calculate confidence based on R2
        r2 = model_config.get('ac_metrics', {}).get('r2', 0.8)
        confidence = min(95, r2 * 100)
        
        # Generate recommendation text
        current_temp = data.get('suhu', 25)
        if recommended_temp < current_temp - 2:
            action = "AC perlu diturunkan"
            mode = "cooling"
        elif recommended_temp > current_temp + 2:
            action = "AC bisa dinaikkan untuk hemat energi"
            mode = "eco"
        else:
            action = "Suhu AC optimal"
            mode = "maintain"
        
        return jsonify({
            "recommended_temp": round(recommended_temp, 1),
            "confidence": round(confidence, 1),
            "action": action,
            "mode": mode,
            "current_conditions": {
                "suhu": data.get('suhu'),
                "kelembaban": data.get('kelembaban'),
                "daya": data.get('daya')
            },
            "features_used": ac_features,
            "model_version": model_config.get('model_version', 1)
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/predict/all', methods=['POST'])
def predict_all():
    """Predict both energy and AC in one call"""
    if not models_loaded:
        return jsonify({"error": "Models not loaded"}), 500
    
    try:
        data = request.json
        now = datetime.now()
        
        # Prepare common values
        suhu = float(data.get('suhu', 25))
        kelembaban = float(data.get('kelembaban', 60))
        tegangan = float(data.get('tegangan', 220))
        arus = float(data.get('arus', 0.5))
        daya = float(data.get('daya', tegangan * arus))
        jumlahOrang = float(data.get('jumlahOrang', 0))
        hour = data.get('hour', now.hour)
        month = data.get('month', now.month)
        
        # Energy prediction
        energy_values = []
        for feat in energy_features:
            if feat == 'suhu': energy_values.append(suhu)
            elif feat == 'kelembaban': energy_values.append(kelembaban)
            elif feat == 'tegangan': energy_values.append(tegangan)
            elif feat == 'arus': energy_values.append(arus)
            elif feat == 'hour': energy_values.append(hour)
            elif feat == 'jumlahOrang': energy_values.append(jumlahOrang)
        
        X_energy = np.array([energy_values])
        X_energy_scaled = energy_scaler.transform(X_energy)
        energy_pred = energy_model.predict(X_energy_scaled)[0]
        
        # AC prediction
        ac_values = []
        for feat in ac_features:
            if feat == 'suhu': ac_values.append(suhu)
            elif feat == 'kelembaban': ac_values.append(kelembaban)
            elif feat == 'daya': ac_values.append(daya)
            elif feat == 'hour': ac_values.append(hour)
            elif feat == 'month': ac_values.append(month)
            elif feat == 'jumlahOrang': ac_values.append(jumlahOrang)
        
        X_ac = np.array([ac_values])
        X_ac_scaled = ac_scaler.transform(X_ac)
        ac_temp = np.clip(ac_model.predict(X_ac_scaled)[0], 16, 30)
        
        # Generate recommendation
        if ac_temp < suhu - 2:
            ac_action = "Turunkan suhu AC"
            ac_mode = "cooling"
        elif ac_temp > suhu + 2:
            ac_action = "Naikkan suhu AC untuk hemat energi"
            ac_mode = "eco"
        else:
            ac_action = "Pertahankan suhu AC"
            ac_mode = "maintain"
        
        # Energy efficiency
        daily_kwh = (energy_pred * 24) / 1000
        monthly_kwh = daily_kwh * 30
        monthly_cost = monthly_kwh * 1444.70  # Tarif listrik
        
        return jsonify({
            "timestamp": now.isoformat(),
            "model_version": model_config.get('model_version', 1),
            "energy": {
                "predicted_watt": round(energy_pred, 2),
                "daily_kwh": round(daily_kwh, 2),
                "monthly_kwh": round(monthly_kwh, 2),
                "monthly_cost_idr": round(monthly_cost, 0),
                "confidence": round(model_config.get('energy_metrics', {}).get('r2', 0.8) * 100, 1)
            },
            "ac": {
                "recommended_temp": round(ac_temp, 1),
                "action": ac_action,
                "mode": ac_mode,
                "confidence": round(model_config.get('ac_metrics', {}).get('r2', 0.8) * 100, 1)
            },
            "input": {
                "suhu": suhu,
                "kelembaban": kelembaban,
                "tegangan": tegangan,
                "arus": arus,
                "daya": daya,
                "jumlahOrang": jumlahOrang
            }
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/model/info', methods=['GET'])
def model_info():
    """Get model information"""
    status_file = os.path.join(MODEL_DIR, 'training_status.json')
    status = {}
    if os.path.exists(status_file):
        with open(status_file, 'r') as f:
            status = json.load(f)
    
    return jsonify({
        "model_version": model_config.get('model_version', 'unknown'),
        "training_date": model_config.get('training_date', 'unknown'),
        "energy": {
            "features": energy_features if models_loaded else [],
            "r2": model_config.get('energy_metrics', {}).get('r2', 'unknown'),
            "mae": model_config.get('energy_metrics', {}).get('mae', 'unknown')
        },
        "ac": {
            "features": ac_features if models_loaded else [],
            "r2": model_config.get('ac_metrics', {}).get('r2', 'unknown'),
            "mae": model_config.get('ac_metrics', {}).get('mae', 'unknown')
        },
        "training_status": status
    })

if __name__ == '__main__':
    print("\n" + "=" * 50)
    print("   ML PREDICTION API SERVER")
    print("=" * 50)
    print(f"Starting server at http://localhost:5000")
    print("Endpoints:")
    print("  GET  /api/health        - Health check")
    print("  GET  /api/model/info    - Model information")
    print("  POST /api/predict/energy - Energy prediction")
    print("  POST /api/predict/ac     - AC recommendation")
    print("  POST /api/predict/all    - All predictions")
    print("  POST /api/reload         - Reload models")
    print("=" * 50 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
