"""
predict.py — Single-record energy/power prediction (dashboard service).

Fitted model expects the feature list defined in
`models/energy_features.pkl`. As of 2026-07-02 the canonical list is:
    ['suhu', 'kelembaban', 'tegangan', 'arus', 'hour']

This module is a thin runtime wrapper that loads the deployed artifacts
(model + scaler + feature list) and exposes:

    predict_energy(record)  -> float (watt)
    predict_ac(record)     -> float (recommended setpoint °C)

Both functions raise ValueError when a required feature is missing or cannot
be inferred. 'arus' is REQUIRED for an accurate power-state estimate
(the deployed RF model was trained with 'arus' as a feature); if it is
missing we fall back to daya/tegangan, which introduces a small error vs
the trained model.

Jalankan langsung (skrip contoh):
    python predict.py

Atau import dari kode lain:
    from predict import predict_energy, predict_ac
"""
import os
import json
import pickle
import numpy as np
from datetime import datetime

MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
AC_FEATURES = ['suhu', 'kelembaban', 'daya', 'hour', 'month']

_energy_model = None
_energy_scaler = None
_energy_features = None
_ac_model = None
_ac_scaler = None
_model_config = None


def _load_artifacts():
    """Lazy-load model artifacts on first call. Idempotent."""
    global _energy_model, _energy_scaler, _energy_features
    global _ac_model, _ac_scaler, _model_config
    if _energy_model is not None:
        return
    with open(os.path.join(MODEL_DIR, 'energy_forecast_model.pkl'), 'rb') as f:
        _energy_model = pickle.load(f)
    with open(os.path.join(MODEL_DIR, 'scaler.pkl'), 'rb') as f:
        _energy_scaler = pickle.load(f)
    with open(os.path.join(MODEL_DIR, 'energy_features.pkl'), 'rb') as f:
        _energy_features = list(pickle.load(f))
    with open(os.path.join(MODEL_DIR, 'ac_recommendation_model.pkl'), 'rb') as f:
        _ac_model = pickle.load(f)
    with open(os.path.join(MODEL_DIR, 'ac_scaler.pkl'), 'rb') as f:
        _ac_scaler = pickle.load(f)
    cfg_path = os.path.join(MODEL_DIR, 'model_config.json')
    if os.path.exists(cfg_path):
        with open(cfg_path, 'r') as f:
            _model_config = json.load(f)


def get_energy_features():
    """Return the list of feature names the loaded energy model expects."""
    _load_artifacts()
    return list(_energy_features)


def _lookup(d, key, default=None):
    """Lookup key in dict, case-insensitive on common Indonesian/English variants."""
    aliases = {
        'suhu': ('suhu', 'Suhu (C)', 'temperature'),
        'kelembaban': ('kelembaban', 'Kelembaban (%)', 'humidity'),
        'tegangan': ('tegangan', 'Tegangan (V)', 'voltage'),
        'arus': ('arus', 'Arus (A)', 'current'),
        'jumlahOrang': ('jumlahOrang', 'Jumlah Orang', 'jumlah_orang', 'occupancy'),
        'daya': ('daya', 'Daya (W)', 'power'),
        'hour': ('hour', 'jam'),
        'month': ('month', 'bulan'),
    }
    for alias in aliases.get(key, (key,)):
        if alias in d and d[alias] is not None:
            return d[alias]
    return default


def _build_feature_vector(record, features):
    """Resolve each feature name to a numeric value; raise if missing/inferable."""
    values = []
    for feat in features:
        if feat == 'hour':
            v = _lookup(record, 'hour', datetime.now().hour)
        elif feat == 'arus':
            v = _lookup(record, 'arus')
            if v is None:
                tegangan = _lookup(record, 'tegangan', 220.0) or 220.0
                daya = _lookup(record, 'daya')
                if daya is not None and tegangan > 0:
                    v = float(daya) / float(tegangan)
                else:
                    raise ValueError(
                        "Missing 'arus' and cannot infer (need 'daya' or 'tegangan')."
                    )
        else:
            v = _lookup(record, feat)
            if v is None:
                raise ValueError(f"Missing required feature '{feat}' for model.")
        values.append(float(v))
    return np.array([values])


def predict_energy(record: dict) -> float:
    """Predict instantaneous power (W) from a single sensor record.

    Returns predicted wattage. The deployed model was trained on
    daya = V*I (+ injected noise/drift in the streaming pipeline), so this
    is a power-state estimate, not a multi-step energy forecast.

    Required keys for full accuracy: 'suhu', 'kelembaban', 'tegangan', 'arus'.
    'hour' defaults to current hour if missing.
    """
    _load_artifacts()
    X = _build_feature_vector(record, _energy_features)
    X_scaled = _energy_scaler.transform(X)
    return float(_energy_model.predict(X_scaled)[0])


def predict_ac(record: dict) -> float:
    """Predict recommended AC setpoint (°C) from a single record."""
    _load_artifacts()
    X = _build_feature_vector(record, AC_FEATURES)
    X_scaled = _ac_scaler.transform(X)
    return float(np.clip(_ac_model.predict(X_scaled)[0], 16, 30))


if __name__ == "__main__":
    print("Loading model...")
    _load_artifacts()
    print(f"  Energy features: {_energy_features}")
    print(f"  AC features:     {AC_FEATURES}")
    print(f"  Model version:   {_model_config.get('model_version', 'unknown')}")
    print(f"  Training date:   {_model_config.get('training_date', 'unknown')}")

    print("\nMaking predictions...\n")
    test_cases = [
        {"suhu": 22, "kelembaban": 55, "tegangan": 220, "arus": 0.5},
        {"suhu": 25, "kelembaban": 45, "tegangan": 220, "arus": 1.2},
        {"suhu": 18, "kelembaban": 70, "tegangan": 220, "arus": 0.2},
    ]
    for i, tc in enumerate(test_cases, 1):
        pred = predict_energy(tc)
        print(f"  Test {i}: T={tc['suhu']}°C, H={tc['kelembaban']}%, V={tc['tegangan']}V, I={tc['arus']}A")
        print(f"    -> Predicted Power: {pred:.2f} W")
    print("\nPrediction complete.")
