<template>
  <div class="ac-section" :class="{ 'dark': isDarkMode }">
    <!-- Hero Banner -->
    <div class="hero-banner">
      <div class="hero-kicker">AC RECOMMENDATION</div>
      <h2>Rekomendasi Suhu AC</h2>
      <p>Analisis data sensor untuk kenyamanan optimal dengan efisiensi energi</p>
      <div class="hero-meta">
        <span class="meta-badge">Last Update: {{ lastUpdateText }}</span>
        <span class="meta-badge data-count">Confidence: {{ recommendation ? Math.round(recommendation.confidence * 100) + '%' : 'N/A' }}</span>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="isLoading" class="loading-state">
      <div class="spinner"></div>
      <p>Menganalisis data sensor...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="error-state">
      <p>{{ error }}</p>
      <button @click="fetchRecommendation" class="retry-btn">Coba Lagi</button>
    </div>

    <!-- Recommendation Display -->
    <div v-else-if="recommendation" class="recommendation-content">
      <!-- Main Card -->
      <div class="main-card">
        <div class="main-card-header">
          <span class="card-label">Rekomendasi Suhu AC</span>
          <span class="comfort-badge" :class="getComfortClass()">
            {{ recommendation.comfortLevel }}
          </span>
        </div>

        <div class="temp-display">
          <span class="temp-number">{{ Math.round(recommendation.recommendedTemp) }}</span>
          <span class="temp-unit">°C</span>
        </div>

        <div class="main-card-info">
          <p class="reason-text">{{ recommendation.reason }}</p>
        </div>

        <div class="action-buttons">
          <button class="action-btn decrease" @click="adjustTemp(-1)">- 1°C</button>
          <button class="action-btn apply" @click="applyRecommendation">Terapkan</button>
          <button class="action-btn increase" @click="adjustTemp(1)">+ 1°C</button>
        </div>
      </div>

      <!-- Stats Grid -->
      <div class="stats-section">
        <h3 class="section-title">Statistik</h3>
        <div class="stats-grid">
          <div class="stat-card energy-card">
            <div class="stat-card-header">
              <span class="stat-label-lg">Penghematan Energi</span>
              <span class="stat-trend positive">+{{ recommendation.energySavingPercent }}%</span>
            </div>
            <div class="stat-value-lg">{{ recommendation.energySavingPercent }}%</div>
            <div class="stat-subvalue">Perkiraan hemat dibanding 24°C</div>
            <div class="stat-progress">
              <div class="progress-bar">
                <div class="progress-fill energy-fill" :style="{ width: recommendation.energySavingPercent + '%' }"></div>
              </div>
            </div>
          </div>

          <div class="stat-card comfort-card">
            <div class="stat-card-header">
              <span class="stat-label-lg">Tingkat Kenyamanan</span>
            </div>
            <div class="stat-value-lg">{{ getComfortScore() }}/100</div>
            <div class="stat-subvalue">{{ recommendation.comfortLevel }}</div>
            <div class="stat-status" :class="getComfortClass()">
              {{ getComfortLabel() }}
            </div>
          </div>

          <div class="stat-card confidence-card">
            <div class="stat-card-header">
              <span class="stat-label-lg">Akurasi Prediksi</span>
            </div>
            <div class="stat-value-lg">{{ Math.round(recommendation.confidence * 100) }}%</div>
            <div class="stat-subvalue">Tingkat kepercayaan AI</div>
            <div class="stat-progress">
              <div class="progress-bar">
                <div class="progress-fill confidence-fill" :style="{ width: (recommendation.confidence * 100) + '%' }"></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Sensor Factors -->
      <div class="factors-section">
        <h3 class="section-title">Faktor Sensor</h3>
        <div class="factors-grid">
          <div class="factor-item">
            <span class="factor-label">Suhu Ambient</span>
            <span class="factor-value">{{ localSensorData.suhu.toFixed(1) }}°C</span>
          </div>
          <div class="factor-item">
            <span class="factor-label">Kelembaban</span>
            <span class="factor-value">{{ localSensorData.kelembaban.toFixed(1) }}%</span>
          </div>
          <div class="factor-item">
            <span class="factor-label">Jumlah Orang</span>
            <span class="factor-value">{{ localSensorData.jumlahOrang }}</span>
          </div>
          <div class="factor-item">
            <span class="factor-label">Daya Listrik</span>
            <span class="factor-value">{{ localSensorData.daya.toFixed(0) }}W</span>
          </div>
          <div class="factor-item">
            <span class="factor-label">Tegangan</span>
            <span class="factor-value">{{ localSensorData.tegangan.toFixed(0) }}V</span>
          </div>
          <div class="factor-item">
            <span class="factor-label">Waktu</span>
            <span class="factor-value">{{ timeOfDay }}</span>
          </div>
        </div>
      </div>

      <!-- Auto Update Status -->
      <div class="auto-update-status">
        <span class="status-dot"></span>
        <p>Update otomatis saat data sensor berubah</p>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else class="empty-state">
      <p>Tidak ada data rekomendasi</p>
      <button @click="fetchRecommendation" class="fetch-btn">Ambil Rekomendasi</button>
    </div>
  </div>
</template>

<script>
import { useMLPrediction } from '../composables/useMLPrediction';
import { AZURE_FUNCTION_URL } from '../lib/appConfig';

export default {
  name: 'ACRecommendation',
  props: {
    sensorData: {
      type: Object,
      default: () => ({
        temperature: 25,
        humidity: 60,
        voltage: 220,
        current: 0.5,
        power: 100
      })
    },
    peopleCount: {
      type: Number,
      default: 0
    },
    isDarkMode: {
      type: Boolean,
      default: false
    }
  },
  setup() {
    const mlPrediction = useMLPrediction();
    return { mlPrediction };
  },
  data() {
    return {
      recommendation: null,
      isLoading: false,
      isExpanded: true,
      error: null,
      lastUpdateTime: null,
      refreshInterval: null,
      localSensorData: {
        suhu: 25,
        kelembaban: 60,
        tegangan: 220,
        arus: 0.5,
        daya: 100,
        jumlahOrang: 0
      }
    };
  },
  computed: {
    lastUpdateText() {
      if (!this.lastUpdateTime) return 'Belum update';
      return this.lastUpdateTime;
    },
    timeOfDay() {
      const hour = new Date().getHours();
      if (hour >= 5 && hour < 12) return 'Pagi';
      if (hour >= 12 && hour < 15) return 'Siang';
      if (hour >= 15 && hour < 18) return 'Sore';
      if (hour >= 18 && hour < 21) return 'Malam';
      return 'Malam Hari';
    }
  },
  watch: {
    sensorData: {
      handler(newData) {
        if (newData) {
          const oldSuhu = this.localSensorData.suhu;
          const newSuhu = newData.temperature || newData.suhu || 25;
          const newKelembaban = newData.humidity || newData.kelembaban || 60;
          const newDaya = newData.power || newData.daya || 100;

          this.localSensorData = {
            suhu: newSuhu,
            kelembaban: newKelembaban,
            tegangan: newData.voltage || newData.tegangan || 220,
            arus: newData.current || newData.arus || 0.5,
            daya: newDaya,
            jumlahOrang: this.peopleCount || 0
          };

          // Auto-update recommendation when sensor data changes significantly
          const suhuDiff = Math.abs(newSuhu - (oldSuhu || 0));
          if (suhuDiff >= 0.5 || this.recommendation === null) {
            this.fetchRecommendation();
          }
        }
      },
      deep: true
    },
    peopleCount(newCount) {
      if (newCount !== this.localSensorData.jumlahOrang) {
        this.localSensorData.jumlahOrang = newCount || 0;
        this.fetchRecommendation();
      }
    }
  },
  mounted() {
    if (this.sensorData) {
      this.localSensorData = {
        suhu: this.sensorData.temperature || this.sensorData.suhu || 25,
        kelembaban: this.sensorData.humidity || this.sensorData.kelembaban || 60,
        tegangan: this.sensorData.voltage || this.sensorData.tegangan || 220,
        arus: this.sensorData.current || this.sensorData.arus || 0.5,
        daya: this.sensorData.power || this.sensorData.daya || 100,
        jumlahOrang: this.peopleCount || 0
      };
    }
    this.fetchRecommendation();
  },
  beforeUnmount() {
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval);
    }
  },
  methods: {
    async fetchRecommendation() {
      try {
        this.isLoading = true;
        this.error = null;

        await this.fetchLatestSensorData();

        // Log data being sent to ML
        console.log('[AC] Calling ML prediction with:', this.localSensorData);

        const mlResult = await this.mlPrediction.getPrediction(this.localSensorData);

        if (mlResult.success) {
          const ac = this.mlPrediction.acRecommendation.value;
          const energy = this.mlPrediction.energyPrediction.value;
          const meta = this.mlPrediction.predictionMeta.value || {};

          console.log('[AC] ML Result from:', mlResult.source, {
            recommendedTemp: ac.recommendedTemp,
            action: ac.action
          });

          this.recommendation = {
            recommendedTemp: ac.recommendedTemp,
            comfortLevel: this.getComfortLevel(ac.mode),
            reason: ac.action,
            energySavingPercent: this.calculateSaving(ac.recommendedTemp),
            confidence: this.normalizeConfidenceScore(ac.confidence),
            factors: {
              ambient_temp: this.localSensorData.suhu,
              humidity: this.localSensorData.kelembaban,
              people_count: this.localSensorData.jumlahOrang || 0,
              power_consumption: (this.localSensorData.daya / 1000).toFixed(2),
              current_hour: new Date().getHours()
            },
            mlSource: mlResult.source,
            sourceTag: meta.source_tag || `${mlResult.source}:prediction`,
            fallbackLevel: meta.fallback_level,
            traceId: meta.trace_id,
            energyPrediction: {
              watt: energy.predictedWatt,
              dailyKwh: energy.dailyKwh,
              monthlyCost: energy.monthlyCostIDR
            }
          };

          this.updateLastUpdateTime();
        } else {
          await this.fetchFromAzureFunction();
        }
      } catch (err) {
        this.error = `Error: ${err.message || 'Failed to fetch data'}`;
      } finally {
        this.isLoading = false;
      }
    },

    async fetchLatestSensorData() {
      try {
        if (window.latestSensorData) {
          this.localSensorData = { ...this.localSensorData, ...window.latestSensorData };
        }

        const response = await fetch(
          `${AZURE_FUNCTION_URL}/telemetry/latest`,
          { timeout: 5000 }
        );

        if (response.ok) {
          const data = await response.json();
          if (data.success && data.data) {
            this.localSensorData = {
              suhu: parseFloat(data.data.suhu) || this.localSensorData.suhu,
              kelembaban: parseFloat(data.data.kelembaban) || this.localSensorData.kelembaban,
              tegangan: parseFloat(data.data.tegangan) || this.localSensorData.tegangan,
              arus: parseFloat(data.data.arus) || this.localSensorData.arus,
              daya: parseFloat(data.data.daya) || this.localSensorData.daya,
              // Support both field names: people_count (API) and jumlahOrang
              jumlahOrang: parseInt(data.data.people_count || data.data.jumlahOrang) || 0
            };

            // Log for debugging
            console.log('[AC] Updated sensor data:', this.localSensorData);
          }
        }
      } catch (err) {
        console.warn('Could not fetch latest sensor data:', err.message);
      }
    },

    async fetchFromAzureFunction() {
      try {
        const response = await fetch(`${AZURE_FUNCTION_URL}/ac-recommendation/latest-with-recommendation`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({})
        });

        const payload = await response.json();

        if (response.ok && payload.success && payload.data?.recommendation) {
          const recommendation = payload.data.recommendation;
          this.recommendation = {
            recommendedTemp: recommendation.recommendedTemp || recommendation.recommended_temp || 24,
            comfortLevel: recommendation.comfortLevel || this.getComfortLevel(recommendation.mode),
            reason: recommendation.reason || recommendation.action || 'Pertahankan suhu AC',
            energySavingPercent: recommendation.energySavingPercent || this.calculateSaving(recommendation.recommendedTemp || 24),
            confidence: this.normalizeConfidenceScore(recommendation.confidence),
            factors: recommendation.factors || {}
          };

          this.updateLastUpdateTime();
        } else {
          this.error = payload.error || 'Failed to fetch recommendation';
        }
      } catch (err) {
        throw err;
      }
    },

    normalizeConfidenceScore(value) {
      const numeric = Number(value) || 0;
      const percent = numeric <= 1 ? numeric * 100 : numeric;
      return Math.max(0, Math.min(1, percent / 100));
    },

    getComfortLevel(mode) {
      if (mode === 'cooling') return 'Perlu Pendinginan';
      if (mode === 'eco') return 'Mode Hemat Energi';
      return 'Nyaman';
    },

    calculateSaving(temp) {
      const saving = Math.max(0, (temp - 24) * 6);
      return Math.min(30, Math.round(saving));
    },

    adjustTemp(delta) {
      const currentTemp = this.recommendation.recommendedTemp;
      const newTemp = Math.max(20, Math.min(28, currentTemp + delta));
      this.$emit('temp-adjusted', {
        original: currentTemp,
        adjusted: newTemp
      });
    },

    applyRecommendation() {
      this.$emit('apply-recommendation', {
        temperature: this.recommendation.recommendedTemp,
        comfortLevel: this.recommendation.comfortLevel
      });
      alert(`AC temperature set to ${this.recommendation.recommendedTemp}°C (${this.recommendation.comfortLevel})`);
    },

    updateLastUpdateTime() {
      const now = new Date();
      this.lastUpdateTime = now.toLocaleTimeString('id-ID', {
        hour: '2-digit',
        minute: '2-digit'
      });
    },

    getComfortScore() {
      if (!this.recommendation) return 0;
      const temp = this.recommendation.recommendedTemp;
      if (temp >= 24 && temp <= 26) return 100;
      if (temp >= 22 && temp < 24) return 85;
      if (temp > 26 && temp <= 27) return 90;
      return 70;
    },

    getComfortClass() {
      const score = this.getComfortScore();
      if (score >= 90) return 'status-excellent';
      if (score >= 75) return 'status-success';
      return 'status-warning';
    },

    getComfortLabel() {
      const score = this.getComfortScore();
      if (score >= 90) return 'Sangat Nyaman';
      if (score >= 75) return 'Nyaman';
      return 'Cukup Nyaman';
    }
  }
};
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=Sora:wght@500;600;700;800&display=swap');

.ac-section {
  --accent: #3b82f6;
  --accent-dark: #2563eb;
  --bg: #f8fafc;
  --surface: #ffffff;
  --surface-2: #f1f5f9;
  --border: #e2e8f0;
  --text: #0f172a;
  --text-2: #475569;
  --text-3: #94a3b8;
  --success: #22c55e;
  --danger: #ef4444;
  --warning: #f59e0b;
  --purple: #a855f7;

  font-family: 'IBM Plex Sans', sans-serif;
  padding: 24px;
  animation: fadeUp 0.4s ease;
}

@keyframes fadeUp {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.hero-banner { margin-bottom: 24px; }

.hero-kicker {
  display: inline-block;
  padding: 6px 12px;
  background: rgba(59, 130, 246, 0.1);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 20px;
  font-family: 'Sora', sans-serif;
  font-size: 11px;
  font-weight: 600;
  color: var(--accent);
  letter-spacing: 0.05em;
  margin-bottom: 12px;
}

.hero-banner h2 {
  font-family: 'Sora', sans-serif;
  font-size: 1.8rem;
  font-weight: 700;
  color: var(--text);
  margin: 0 0 6px 0;
}

.hero-banner p {
  font-size: 0.95rem;
  color: var(--text-2);
  margin: 0 0 16px 0;
}

.hero-meta {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.meta-badge {
  display: inline-block;
  padding: 8px 14px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: 0.82rem;
  color: var(--text-2);
}

.meta-badge.data-count {
  background: rgba(59, 130, 246, 0.1);
  border-color: rgba(59, 130, 246, 0.2);
  color: var(--accent);
}

.section-title {
  font-family: 'Sora', sans-serif;
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--text);
  margin: 0 0 16px 0;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 16px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.error-state {
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.2);
  border-radius: 12px;
  padding: 24px;
  text-align: center;
  color: var(--danger);
}

.retry-btn {
  margin-top: 12px;
  padding: 10px 20px;
  background: var(--danger);
  color: white;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
}

.main-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 16px;
  padding: 32px;
  text-align: center;
  margin-bottom: 24px;
}

.main-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.card-label {
  font-size: 0.9rem;
  opacity: 0.9;
}

.comfort-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
  background: rgba(255, 255, 255, 0.2);
}

.temp-display {
  display: flex;
  align-items: flex-start;
  justify-content: center;
  gap: 4px;
  margin-bottom: 16px;
}

.temp-number {
  font-family: 'Sora', sans-serif;
  font-size: 5rem;
  font-weight: 700;
  line-height: 1;
}

.temp-unit {
  font-size: 2rem;
  opacity: 0.9;
  margin-top: 12px;
}

.main-card-info {
  margin-bottom: 24px;
}

.reason-text {
  font-size: 1rem;
  opacity: 0.9;
  line-height: 1.5;
  margin: 0;
}

.action-buttons {
  display: flex;
  gap: 12px;
  justify-content: center;
}

.action-btn {
  flex: 1;
  max-width: 140px;
  padding: 12px 20px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-radius: 8px;
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.2s, border-color 0.2s, color 0.2s;
  background: rgba(255, 255, 255, 0.1);
  color: white;
}

.action-btn:hover {
  background: rgba(255, 255, 255, 0.2);
}

.action-btn.apply {
  background: white;
  color: #667eea;
  border-color: white;
}

.action-btn.apply:hover {
  background: #f0f0f0;
}

.stats-section { margin-bottom: 24px; }

.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.stat-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 20px;
  transition: background-color 0.2s, border-color 0.2s, color 0.2s;
}

.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 24px rgba(0, 0, 0, 0.08);
}

.stat-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.energy-card { border-top: 3px solid var(--success); }
.comfort-card { border-top: 3px solid var(--accent); }
.confidence-card { border-top: 3px solid var(--warning); }

.stat-label-lg {
  font-size: 0.85rem;
  color: var(--text-2);
  font-weight: 600;
}

.stat-trend {
  padding: 4px 8px;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 600;
}

.stat-trend.positive {
  background: rgba(34, 197, 94, 0.15);
  color: var(--success);
}

.stat-value-lg {
  font-family: 'Sora', sans-serif;
  font-size: 1.8rem;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 4px;
}

.stat-subvalue {
  font-size: 0.85rem;
  color: var(--text-3);
  margin-bottom: 12px;
}

.stat-progress { margin-top: auto; }

.progress-bar {
  width: 100%;
  height: 6px;
  background: var(--surface-2);
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 6px;
}

.progress-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.5s ease;
}

.energy-fill {
  background: linear-gradient(90deg, var(--success), #059669);
}

.confidence-fill {
  background: linear-gradient(90deg, var(--warning), #d97706);
}

.stat-status {
  display: inline-block;
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 600;
}

.status-excellent {
  background: rgba(34, 197, 94, 0.15);
  color: var(--success);
}

.status-success {
  background: rgba(59, 130, 246, 0.15);
  color: var(--accent);
}

.status-warning {
  background: rgba(245, 158, 11, 0.15);
  color: var(--warning);
}

.factors-section {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 24px;
  margin-bottom: 24px;
}

.factors-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.factor-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px;
  background: var(--surface-2);
  border-radius: 8px;
}

.factor-label {
  font-size: 0.78rem;
  color: var(--text-3);
  font-weight: 500;
}

.factor-value {
  font-size: 1rem;
  color: var(--text);
  font-weight: 600;
}

.auto-update-status {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 0;
  border-top: 1px solid var(--border);
}

.auto-update-status .status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--success);
  animation: pulse-dot 2s infinite;
}

@keyframes pulse-dot {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.auto-update-status p {
  margin: 0;
  font-size: 0.85rem;
  color: var(--text-3);
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: var(--text-2);
}

.fetch-btn {
  margin-top: 16px;
  padding: 12px 24px;
  background: linear-gradient(135deg, var(--accent), var(--accent-dark));
  border: none;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 600;
  color: white;
  cursor: pointer;
}

.dark {
  --bg: #0f172a;
  --surface: #1e293b;
  --surface-2: #334155;
  --border: rgba(255, 255, 255, 0.1);
  --text: #f1f5f9;
  --text-2: #cbd5e1;
  --text-3: #94a3b8;
}

@media (max-width: 900px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 640px) {
  .ac-section {
    padding: 16px;
  }

  .stats-grid {
    grid-template-columns: 1fr;
  }

  .factors-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .action-buttons {
    flex-direction: column;
  }

  .action-btn {
    max-width: 100%;
  }

  .temp-number {
    font-size: 4rem;
  }
}
</style>
