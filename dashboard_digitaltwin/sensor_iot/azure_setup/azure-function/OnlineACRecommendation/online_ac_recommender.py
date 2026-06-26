"""
Online AC Recommendation with River Library
==========================================

Real-time ML inference + online learning for Digital Twin.

Flow:
1. Load pre-trained base model from ml_models
2. Initialize River model
3. Predict AC recommendation
4. Learn from data (online update)
5. Save model state periodically

Usage:
    from online_ac_recommender import OnlineACRecommender
    recommender = OnlineACRecommender()

    # Predict
    recommendation = recommender.predict(suhu=28.5, kelembaban=70, ...)

    # Update with actual
    recommender.update(features, actual_recommended_temp)
"""

import json
import os
import pickle
import base64
import hashlib
from datetime import datetime
from typing import Dict, Optional, Any

# River imports (will be installed in Azure Function)
try:
    from river import linear_model, preprocessing, compose, metrics
    RIVER_AVAILABLE = True
except ImportError:
    RIVER_AVAILABLE = False
    # Fallback to simple model if river not available


class OnlineACRecommender:
    """
    Online AC Recommendation dengan River Library
    - Combine pre-trained model + online learning
    - Save state untuk persistence
    """

    def __init__(self, model_path: str = None):
        self.model_path = model_path or os.environ.get('MODEL_PATH', './python_model')
        self.state_path = os.path.join(self.model_path, 'model_state.json')
        self.data_count = 0
        self.model = None
        self.base_model = None
        self.metrics = None

        # Initialize
        self._initialize()

    def _initialize(self):
        """Initialize model - load pre-trained + River"""

        if RIVER_AVAILABLE:
            # Create River pipeline
            self.model = (
                preprocessing.StandardScaler() |
                linear_model.LinearRegression(
                    optimizer_lr=0.01  # Learning rate untuk online update
                )
            )

            # Metrics untuk tracking akurasi
            self.metrics = metrics.MAE()

            # Load base model if exists
            base_model_path = os.path.join(self.model_path, 'ac_recommendation_model.pkl')
            if os.path.exists(base_model_path):
                with open(base_model_path, 'rb') as f:
                    self.base_model = pickle.load(f)
                print(f"[OnlineAC] Loaded base model from {base_model_path}")

            # Load saved state
            self._load_state()
            print(f"[OnlineAC] Initialized with {self.data_count} data points")
        else:
            print("[OnlineAC] Warning: River not available, using fallback")
            self.model = None

    def _load_state(self):
        """Load model state dari JSON"""
        if os.path.exists(self.state_path):
            try:
                with open(self.state_path, 'r') as f:
                    state = json.load(f)
                self.data_count = state.get('data_count', 0)
                print(f"[OnlineAC] Loaded state: {self.data_count} data points")
            except Exception as e:
                print(f"[OnlineAC] Error loading state: {e}")

    def _save_state(self):
        """Save model state ke JSON (River doesn't support pickle, use config)"""
        state = {
            'data_count': self.data_count,
            'last_update': datetime.now().isoformat(),
            'model_type': 'river_linear_regression',
            'optimizer_lr': 0.01
        }

        os.makedirs(self.model_path, exist_ok=True)
        with open(self.state_path, 'w') as f:
            json.dump(state, f, indent=2)

        print(f"[OnlineAC] State saved: {self.data_count} data points")

    def _create_features(self, suhu: float, kelembaban: float, daya: float,
                        jumlah_orang: int, jam: int) -> Dict[str, float]:
        """Create feature dict untuk prediction"""
        return {
            'suhu': suhu,
            'kelembaban': kelembaban,
            'daya': daya,
            'jumlah_orang': jumlah_orang,
            'jam': jam,
            'is_peak_hour': 1 if 8 <= jam <= 17 else 0
        }

    def predict(self, suhu: float, kelembaban: float, daya: float,
                jumlah_orang: int, jam: int = None) -> Dict[str, Any]:
        """
        Predict AC recommendation dengan online learning
        """
        # Default jam ke jam sekarang
        if jam is None:
            jam = datetime.now().hour

        features = self._create_features(suhu, kelembaban, daya, jumlah_orang, jam)

        if RIVER_AVAILABLE and self.model is not None:
            try:
                # Predict dengan River model
                prediction = self.model.predict_one(features)

                # Combine dengan base model kalau ada
                if self.base_model is not None:
                    try:
                        import numpy as np
                        base_pred = self.base_model.predict([list(features.values())])[0]
                        # Weighted average: base model 70%, online 30%
                        prediction = 0.7 * base_pred + 0.3 * prediction
                    except:
                        pass  # Use River prediction only

                # Clamp ke range comfort
                recommended_temp = max(18.0, min(28.0, float(prediction)))

            except Exception as e:
                print(f"[OnlineAC] Prediction error: {e}")
                # Fallback ke formula
                recommended_temp = self._fallback_predict(suhu, kelembaban, daya, jumlah_orang, jam)
        else:
            # Fallback - formula-based
            recommended_temp = self._fallback_predict(suhu, kelembaban, daya, jumlah_orang, jam)

        return {
            'recommendedTemp': round(recommended_temp, 1),
            'comfortLevel': self._get_comfort_level(recommended_temp),
            'factors': features,
            'confidence': self._get_confidence(),
            'model_info': {
                'online_learning': RIVER_AVAILABLE,
                'data_count': self.data_count,
                'model_type': 'river' if RIVER_AVAILABLE else 'fallback'
            }
        }

    def _fallback_predict(self, suhu, kelembaban, daya, jumlah_orang, jam):
        """Fallback prediction tanpa ML"""
        recommended_temp = 24.0

        # Temperature factor
        if suhu > 25:
            recommended_temp += (suhu - 25) * -0.3

        # Humidity factor
        if kelembaban > 60:
            recommended_temp += (kelembaban - 60) * -0.01

        # Power factor
        if daya > 100:
            recommended_temp += (daya - 100) * -0.001

        # Peak hour
        if 8 <= jam <= 17:
            recommended_temp -= 0.5

        # People factor
        if jumlah_orang > 0:
            recommended_temp -= jumlah_orang / 20

        return max(18.0, min(28.0, recommended_temp))

    def _get_comfort_level(self, temp):
        """Get comfort level based on temperature"""
        if temp <= 21:
            return "COOL"
        elif temp <= 23:
            return "COOL_COMFORTABLE"
        elif temp <= 25:
            return "COMFORTABLE"
        elif temp <= 26:
            return "WARM_COMFORTABLE"
        else:
            return "WARM"

    def _get_confidence(self):
        """Get confidence based on data count"""
        # More data = higher confidence
        if self.data_count < 10:
            return 0.5
        elif self.data_count < 50:
            return 0.7
        elif self.data_count < 100:
            return 0.85
        else:
            return 0.96

    def update(self, suhu: float, kelembaban: float, daya: float,
               jumlah_orang: int, actual_temp: float, jam: int = None):
        """
        Update model dengan data baru (online learning)

        Args:
            suhu, kelembaban, daya, jumlah_orang: input features
            actual_temp: actual AC setting yang dipakai user
            jam: hour (default now)
        """
        if jam is None:
            jam = datetime.now().hour

        features = self._create_features(suhu, kelembaban, daya, jumlah_orang, jam)

        if RIVER_AVAILABLE and self.model is not None:
            try:
                # Learn from new data
                self.model.learn_one(features, actual_temp)
                self.data_count += 1

                # Update confidence metric
                prediction = self.predict(suhu, kelembaban, daya, jumlah_orang, jam)
                self.metrics.update(actual_temp, prediction['recommendedTemp'])

                # Save state every 100 data
                if self.data_count % 100 == 0:
                    self._save_state()

                print(f"[OnlineAC] Learned from data #{self.data_count}")

            except Exception as e:
                print(f"[OnlineAC] Update error: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Get model status"""
        return {
            'status': 'running' if RIVER_AVAILABLE else 'fallback',
            'river_available': RIVER_AVAILABLE,
            'data_count': self.data_count,
            'last_update': datetime.now().isoformat(),
            'mae': float(self.metrics.error) if self.metrics else None,
            'confidence': self._get_confidence()
        }


# Global instance (for Azure Function reuse)
_recommender_instance = None

def get_recommender() -> OnlineACRecommender:
    """Get or create recommender instance"""
    global _recommender_instance
    if _recommender_instance is None:
        model_path = os.environ.get('MODEL_PATH', '/home/site/wwwroot/python_model')
        _recommender_instance = OnlineACRecommender(model_path)
    return _recommender_instance


def predict_ac_recommendation(suhu: float, kelembaban: float, daya: float,
                             jumlah_orang: int, actual_temp: float = None) -> Dict:
    """
    Main prediction function

    Args:
        suhu: temperature (°C)
        kelembaban: humidity (%)
        daya: power consumption (W)
        jumlah_orang: number of people
        actual_temp: actual AC temp (for learning, optional)

    Returns:
        dict with recommendation
    """
    recommender = get_recommender()

    # Predict
    result = recommender.predict(suhu, kelembaban, daya, jumlah_orang)

    # Update model if actual temp provided
    if actual_temp is not None:
        recommender.update(suhu, kelembaban, daya, jumlah_orang, actual_temp)

    return result


if __name__ == '__main__':
    # Test
    recommender = OnlineACRecommender()

    # Simulate data stream
    test_data = [
        {'suhu': 28.5, 'kelembaban': 70, 'daya': 450, 'orang': 3, 'actual': 22.0},
        {'suhu': 27.0, 'kelembaban': 65, 'daya': 350, 'orang': 2, 'actual': 23.0},
        {'suhu': 26.5, 'kelembaban': 60, 'daya': 300, 'orang': 1, 'actual': 24.0},
    ]

    print("=" * 50)
    print("Testing Online AC Recommender")
    print("=" * 50)

    for i, data in enumerate(test_data):
        result = predict_ac_recommendation(
            suhu=data['suhu'],
            kelembaban=data['kelembaban'],
            daya=data['daya'],
            jumlah_orang=data['orang'],
            actual_temp=data['actual']
        )

        print(f"\nData #{i+1}:")
        print(f"  Input: suhu={data['suhu']}, humidity={data['kelembaban']}, "
              f"power={data['daya']}, orang={data['orang']}")
        print(f"  Actual AC: {data['actual']}°C")
        print(f"  Predicted: {result['recommendedTemp']}°C ({result['comfortLevel']})")
        print(f"  Confidence: {result['model_info']['confidence']}")

    print("\n" + "=" * 50)
    print(f"Model status: {recommender.get_status()}")
    print("=" * 50)