<template>
  <div class="ac-recommendation" :class="{ 'dark': isDarkMode }">
    <div class="section-header" @click="isExpanded = !isExpanded">
      <h2>❄️ AC Temperature Recommendation</h2>
      <button class="toggle-btn">
        {{ isExpanded ? '▼' : '▶' }}
      </button>
    </div>

    <div v-if="isExpanded" class="section-content">
      <!-- Loading State -->
      <div v-if="isLoading" class="loading-state">
        <div class="spinner"></div>
        <p>Menganalisis data sensor...</p>
      </div>

      <!-- Error State -->
      <div v-else-if="error" class="error-state">
        <p>❌ {{ error }}</p>
        <button @click="fetchRecommendation" class="retry-btn">Coba Lagi</button>
      </div>

      <!-- Recommendation Display -->
      <div v-else-if="recommendation" class="recommendation-container">
        <!-- Main Recommendation Card -->
        <div class="main-card">
          <div class="card-header">
            <span class="card-icon">{{ recommendation.emoji }}</span>
            <span class="card-title">Rekomendasi Suhu AC</span>
          </div>
          
          <div class="recommendation-value">
            <div class="temp-display">
              <span class="temp-number">{{ Math.round(recommendation.recommendedTemp) }}</span>
              <span class="temp-unit">°C</span>
            </div>
          </div>

          <div class="recommendation-info">
            <p class="comfort-level">{{ recommendation.comfortLevel }}</p>
            <p class="reason">{{ recommendation.reason }}</p>
          </div>

          <!-- Quick Action Buttons -->
          <div class="action-buttons">
            <button 
              class="action-btn decrease" 
              @click="adjustTemp(-1)"
              title="Decrease 1°C"
            >
              ❄️ Lebih Dingin
            </button>
            <button 
              class="action-btn apply" 
              @click="applyRecommendation"
              title="Apply recommended temperature"
            >
              ✓ Terapkan
            </button>
            <button 
              class="action-btn increase" 
              @click="adjustTemp(1)"
              title="Increase 1°C"
            >
              🔥 Lebih Hangat
            </button>
          </div>
        </div>

        <!-- Overview Cards Grid -->
        <div class="overview-grid">
          <div class="overview-card energy">
            <div class="card-header">
              <span class="card-icon">⚡</span>
              <span class="card-title">Penghematan Energi</span>
            </div>
            <div class="card-value">{{ recommendation.energySavingPercent }}%</div>
            <div class="card-subtitle">Perkiraan hemat dibanding 24°C</div>
            <div class="card-progress">
              <div class="progress-bar">
                <div 
                  class="progress-fill energy-fill" 
                  :style="{ width: recommendation.energySavingPercent + '%' }"
                ></div>
              </div>
            </div>
          </div>
          
          <div class="overview-card comfort">
            <div class="card-header">
              <span class="card-icon">😊</span>
              <span class="card-title">Tingkat Kenyamanan</span>
            </div>
            <div class="card-value">{{ getComfortScore() }}/100</div>
            <div class="card-subtitle">{{ recommendation.comfortLevel }}</div>
            <div class="card-status" :class="getComfortClass()">
              {{ getComfortLabel() }}
            </div>
          </div>
          
          <div class="overview-card confidence">
            <div class="card-header">
              <span class="card-icon">🎯</span>
              <span class="card-title">Akurasi Prediksi</span>
            </div>
            <div class="card-value">{{ Math.round(recommendation.confidence * 100) }}%</div>
            <div class="card-subtitle">Tingkat kepercayaan AI</div>
            <div class="card-progress">
              <div class="progress-bar">
                <div 
                  class="progress-fill confidence-fill" 
                  :style="{ width: (recommendation.confidence * 100) + '%' }"
                ></div>
              </div>
            </div>
          </div>
        </div>

        <!-- Refresh Info -->
        <div class="refresh-info">
          <p>Data sensor dianalisis secara real-time untuk memberikan rekomendasi terbaik</p>
          <button @click="fetchRecommendation" class="refresh-btn">🔄 Refresh Sekarang</button>
        </div>
      </div>

      <!-- Empty State -->
      <div v-else class="empty-state">
        <p>Tidak ada data rekomendasi</p>
        <button @click="fetchRecommendation" class="fetch-btn">Ambil Rekomendasi</button>
      </div>
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

    return {
      mlPrediction
    };
  },
  data() {
    return {
      recommendation: null,
      isLoading: false,
      isExpanded: false,
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
      },
      mlModelInfo: null
    };
  },
  computed: {
    adjustedTemp() {
      return this.recommendation?.recommendedTemp || 24;
    }
  },
  watch: {
    // Update local sensor data when props change
    sensorData: {
      handler(newData) {
        if (newData) {
          this.localSensorData = {
            suhu: newData.temperature || newData.suhu || 25,
            kelembaban: newData.humidity || newData.kelembaban || 60,
            tegangan: newData.voltage || newData.tegangan || 220,
            arus: newData.current || newData.arus || 0.5,
            daya: newData.power || newData.daya || 100,
            jumlahOrang: this.peopleCount || 0
          };
          // Auto refresh prediction when sensor data changes significantly
          this.fetchRecommendation();
        }
      },
      deep: true
    },
    peopleCount(newCount) {
      this.localSensorData.jumlahOrang = newCount || 0;
    }
  },
  mounted() {
    // Initialize with props data
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
    this.getMLModelInfo();
    // Auto refresh every 2 minutes untuk update prediction
    this.refreshInterval = setInterval(() => {
      this.fetchRecommendation();
    }, 2 * 60 * 1000);
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

        // PRIORITAS 1: Fetch data sensor terbaru dari Azure
        await this.fetchLatestSensorData();
        
        // PRIORITAS 2: Get ML prediction
        const mlResult = await this.mlPrediction.getPrediction(this.localSensorData);
        
        if (mlResult.success) {
          // Format recommendation dari ML prediction
          const ac = this.mlPrediction.acRecommendation.value;
          const energy = this.mlPrediction.energyPrediction.value;
          const meta = this.mlPrediction.predictionMeta.value || {};
          
          this.recommendation = {
            recommendedTemp: ac.recommendedTemp,
            emoji: this.getEmoji(ac.mode),
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
          console.log('[AC] ML Prediction loaded from:', mlResult.source);
        } else {
          // Fallback ke Azure Function langsung
          await this.fetchFromAzureFunction();
        }
      } catch (err) {
        this.error = `Error: ${err.message || 'Failed to fetch data'}`;
        console.error('AC Recommendation error:', err);
      } finally {
        this.isLoading = false;
      }
    },
    
    async fetchLatestSensorData() {
      try {
        // Ambil data sensor terbaru dari window.latestSensorData (dari MQTT)
        if (window.latestSensorData) {
          this.localSensorData = { ...this.localSensorData, ...window.latestSensorData };
        }
        
        // Atau fetch dari Azure Function
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
              jumlahOrang: parseInt(data.data.jumlahOrang) || 0
            };
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
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({})
        });

        const payload = await response.json();

        if (response.ok && payload.success && payload.data?.recommendation) {
          const recommendation = payload.data.recommendation;
          this.recommendation = {
            recommendedTemp: recommendation.recommendedTemp || recommendation.recommended_temp || 24,
            emoji: recommendation.emoji || this.getEmoji(recommendation.mode),
            comfortLevel: recommendation.comfortLevel || this.getComfortLevel(recommendation.mode),
            reason: recommendation.reason || recommendation.action || 'Pertahankan suhu AC',
            energySavingPercent: recommendation.energySavingPercent || this.calculateSaving(recommendation.recommendedTemp || 24),
            confidence: this.normalizeConfidenceScore(recommendation.confidence),
            factors: recommendation.factors || {
              ambient_temp: this.localSensorData.suhu,
              humidity: this.localSensorData.kelembaban,
              people_count: this.localSensorData.jumlahOrang || 0,
              power_consumption: (this.localSensorData.daya / 1000).toFixed(2),
              current_hour: new Date().getHours()
            },
            mlSource: 'azure_function',
            sourceTag: 'azure_function:prediction',
            fallbackLevel: 0,
            traceId: payload.trace_id || null,
            energyPrediction: {
              watt: this.localSensorData.daya,
              dailyKwh: (this.localSensorData.daya * 24) / 1000,
              monthlyCost: ((this.localSensorData.daya * 24 * 30) / 1000) * 1444.70
            }
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
    
    getEmoji(mode) {
      if (mode === 'cooling') return '❄️';
      if (mode === 'eco') return '🌱';
      return '✅';
    },
    
    getComfortLevel(mode) {
      if (mode === 'cooling') return 'Perlu Pendinginan';
      if (mode === 'eco') return 'Mode Hemat Energi';
      return 'Nyaman';
    },
    
    calculateSaving(temp) {
      // Setiap 1 derajat naik dari 24°C hemat ~6% energi
      const saving = Math.max(0, (temp - 24) * 6);
      return Math.min(30, Math.round(saving));
    },
    
    async getMLModelInfo() {
      const result = await this.mlPrediction.getModelInfo();
      if (result.success) {
        this.mlModelInfo = result.data;
      }
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
      
      // Show confirmation
      alert(`AC temperature set to ${this.recommendation.recommendedTemp}°C (${this.recommendation.comfortLevel})`);
    },
    updateLastUpdateTime() {
      const now = new Date();
      this.lastUpdateTime = now.toLocaleString('id-ID', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      });
    },
    
    // Helper methods untuk status
    getComfortScore() {
      if (!this.recommendation) return 0;
      const temp = this.recommendation.recommendedTemp;
      // Optimal range 24-26°C = 100 points
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
    },
    
    getTempStatus(temp) {
      if (temp < 20) return 'Sangat Dingin';
      if (temp < 24) return 'Dingin';
      if (temp <= 27) return 'Nyaman';
      if (temp <= 30) return 'Hangat';
      return 'Panas';
    },
    
    getHumidityStatus(humidity) {
      if (humidity < 30) return 'Sangat Kering';
      if (humidity < 40) return 'Kering';
      if (humidity <= 60) return 'Optimal';
      if (humidity <= 70) return 'Lembab';
      return 'Sangat Lembab';
    },
    
    getOccupancyLevel(count) {
      if (count === 0) return 'Kosong';
      if (count === 1) return 'Rendah';
      if (count <= 3) return 'Sedang';
      if (count <= 5) return 'Ramai';
      return 'Sangat Ramai';
    },
    
    getPowerStatus(kw) {
      const watt = parseFloat(kw) * 1000;
      if (watt < 100) return 'Sangat Rendah';
      if (watt < 500) return 'Rendah';
      if (watt <= 1500) return 'Normal';
      if (watt <= 2500) return 'Tinggi';
      return 'Sangat Tinggi';
    },
    
    getTimeOfDay(hour) {
      if (hour >= 5 && hour < 12) return 'Pagi';
      if (hour >= 12 && hour < 15) return 'Siang';
      if (hour >= 15 && hour < 18) return 'Sore';
      if (hour >= 18 && hour < 21) return 'Malam';
      return 'Malam Hari';
    },
    
    getTimeAgo() {
      if (!this.lastUpdateTime) return 'Baru saja';
      return 'Baru saja';
    }
  }
};
</script>

<style scoped>
.ac-recommendation {
  margin-top: 20px;
  padding: 20px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
}

.ac-recommendation.dark {
  background: #1e293b;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  user-select: none;
}

.section-header h2 {
  margin: 0;
  font-size: 1.5rem;
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.toggle-btn {
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  color: white;
  border: none;
  border-radius: 6px;
  padding: 8px 16px;
  font-size: 1rem;
  cursor: pointer;
  transition: all 0.3s ease;
}

.toggle-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(59, 130, 246, 0.3);
}

.section-content {
  margin-top: 20px;
  animation: slideDown 0.3s ease;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Loading State */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #2196f3;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 20px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.loading-state p {
  font-size: 1em;
  color: #666;
}

/* Error State */
.error-state {
  background: #fee;
  border: 1px solid #fcc;
  border-radius: 8px;
  padding: 20px;
  text-align: center;
}

.ac-recommendation.dark .error-state {
  background: #3c2a2a;
  border-color: #663333;
}

.retry-btn {
  background: #ff6b6b;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 6px;
  cursor: pointer;
  margin-top: 15px;
  font-size: 0.95em;
}

.retry-btn:hover {
  background: #ff5252;
}

/* Recommendation Container */
.recommendation-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* Main Recommendation Card */
.main-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 12px;
  padding: 30px;
  text-align: center;
  box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
}

.ac-recommendation.dark .main-card {
  background: linear-gradient(135deg, #1a365d 0%, #2d1b69 100%);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 20px;
  justify-content: center;
}

.card-icon {
  font-size: 2em;
}

.card-title {
  font-size: 1.2em;
  font-weight: 600;
}

.recommendation-value {
  margin: 20px 0;
}

.emoji {
  font-size: 4em;
}

.temp-display {
  display: flex;
  align-items: flex-start;
  gap: 5px;
  justify-content: center;
}

.temp-number {
  font-size: 5em;
  font-weight: 700;
  line-height: 1;
}

.temp-unit {
  font-size: 2em;
  opacity: 0.9;
  margin-top: 10px;
}

.recommendation-info {
  margin: 20px 0;
}

.comfort-level {
  font-size: 1.3em;
  font-weight: 600;
  margin: 0 0 10px 0;
}

.reason {
  font-size: 1em;
  opacity: 0.9;
  margin: 0;
  line-height: 1.5;
}

/* Action Buttons */
.action-buttons {
  display: flex;
  gap: 10px;
  margin-top: 25px;
  justify-content: center;
  flex-wrap: wrap;
}

.action-btn {
  flex: 1;
  min-width: 120px;
  padding: 12px 20px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.95em;
  font-weight: 600;
  transition: all 0.3s ease;
  background: rgba(255, 255, 255, 0.1);
  color: white;
}

.action-btn:hover {
  background: rgba(255, 255, 255, 0.2);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

.action-btn.apply {
  background: white;
  color: #667eea;
  border-color: white;
}

.action-btn.apply:hover {
  background: #f0f0f0;
}

/* Overview Cards Grid */
.overview-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 20px;
  margin: 20px 0;
}

.overview-card {
  background: white;
  border-radius: 12px;
  padding: 25px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
  border-left: 4px solid #667eea;
}

.ac-recommendation.dark .overview-card {
  background: #2a2a2a;
  border-left-color: #764ba2;
}

.overview-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15);
}

.overview-card.energy {
  border-left-color: #4caf50;
}

.overview-card.comfort {
  border-left-color: #2196f3;
}

.overview-card.confidence {
  border-left-color: #ff9800;
}

.overview-card .card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 15px;
  justify-content: flex-start;
}

.overview-card .card-icon {
  font-size: 1.8em;
}

.overview-card .card-title {
  font-size: 1em;
  font-weight: 600;
  color: #666;
}

.ac-recommendation.dark .overview-card .card-title {
  color: #aaa;
}

.overview-card .card-value {
  font-size: 2.5em;
  font-weight: 700;
  margin: 10px 0;
  color: #667eea;
}

.ac-recommendation.dark .overview-card .card-value {
  color: #8b9dff;
}

.overview-card .card-subtitle {
  font-size: 0.9em;
  color: #888;
  margin-bottom: 15px;
}

.ac-recommendation.dark .overview-card .card-subtitle {
  color: #999;
}

.overview-card .card-status {
  display: inline-block;
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 0.85em;
  font-weight: 600;
  margin-top: 10px;
}

.card-status.status-excellent {
  background: rgba(76, 175, 80, 0.2);
  color: #4caf50;
}

.card-status.status-success {
  background: rgba(33, 150, 243, 0.2);
  color: #2196f3;
}

.card-status.status-warning {
  background: rgba(255, 152, 0, 0.2);
  color: #ff9800;
}

.card-progress {
  margin-top: 15px;
}

.progress-bar {
  height: 8px;
  background: #e0e0e0;
  border-radius: 4px;
  overflow: hidden;
}

.ac-recommendation.dark .progress-bar {
  background: #404040;
}

.progress-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.5s ease;
}

.energy-fill {
  background: linear-gradient(90deg, #4caf50, #66bb6a);
}

.confidence-fill {
  background: linear-gradient(90deg, #ff9800, #ffa726);
}

/* Stats Section */
.stats-section {
  margin: 30px 0;
}

.stats-section h3 {
  font-size: 1.3em;
  margin-bottom: 20px;
  font-weight: 600;
  color: #333;
}

.ac-recommendation.dark .stats-section h3 {
  color: #e0e0e0;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 15px;
}

.stat-card {
  background: white;
  border-radius: 10px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 15px;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);
  transition: all 0.3s ease;
  border: 1px solid #f0f0f0;
}

.ac-recommendation.dark .stat-card {
  background: #2a2a2a;
  border-color: #404040;
}

.stat-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
}

.stat-icon {
  font-size: 2.5em;
  flex-shrink: 0;
}

.stat-info {
  flex: 1;
}

.stat-label {
  margin: 0 0 5px 0;
  font-size: 0.85em;
  color: #888;
  font-weight: 500;
}

.ac-recommendation.dark .stat-label {
  color: #aaa;
}

.stat-value {
  margin: 0 0 5px 0;
  font-size: 1.5em;
  font-weight: 700;
  color: #333;
}

.ac-recommendation.dark .stat-value {
  color: #e0e0e0;
}

.stat-range {
  margin: 0;
  font-size: 0.8em;
  color: #2196f3;
  font-weight: 500;
}

.ac-recommendation.dark .stat-range {
  color: #64b5f6;
}

/* Refresh Info */
.refresh-info {
  text-align: center;
  padding: 20px 0;
  border-top: 2px solid #f0f0f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 20px;
}

.ac-recommendation.dark .refresh-info {
  border-top-color: #404040;
}

.refresh-info p {
  margin: 0;
  font-size: 0.95em;
  color: #666;
}

.ac-recommendation.dark .refresh-info p {
  color: #aaa;
}

.refresh-btn {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.95em;
  font-weight: 600;
  transition: all 0.3s ease;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
}

.refresh-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.refresh-btn:active {
  transform: translateY(0);
}

/* Empty State */
.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #666;
}

.ac-recommendation.dark .empty-state {
  color: #aaa;
}

.fetch-btn {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  padding: 12px 24px;
  border-radius: 8px;
  cursor: pointer;
  margin-top: 20px;
  font-size: 1em;
  font-weight: 600;
  transition: all 0.3s ease;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
}

.fetch-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

/* Responsive */
@media (max-width: 768px) {
  .overview-grid {
    grid-template-columns: 1fr;
  }
  
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .action-buttons {
    flex-direction: column;
  }
  
  .action-btn {
    width: 100%;
  }

  .refresh-info {
    flex-direction: column;
    gap: 15px;
  }
  
  .main-card {
    padding: 20px;
  }
  
  .temp-number {
    font-size: 4em;
  }
}
</style>
