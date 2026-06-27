<template>
  <div class="energy-section" :class="{ 'dark': isDarkMode }">
    <!-- Hero Banner -->
    <div class="hero-banner">
      <div class="hero-kicker">ENERGY MANAGEMENT</div>
      <h2>Manajemen Energi & AI</h2>
      <p>Monitor konsumsi energi dan rekomendasi AI untuk efisiensi optimal</p>
      <div class="hero-meta">
        <span class="meta-badge">Last Update: {{ lastUpdateText }}</span>
        <span class="meta-badge data-count">{{ efficiencyScore }}/100 Efisiensi</span>
      </div>
    </div>

    <!-- Sensor Status Warning -->
    <div v-if="!hasCurrentSensor" class="sensor-warning">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"/>
        <line x1="12" y1="8" x2="12" y2="12"/>
        <line x1="12" y1="16" x2="12.01" y2="16"/>
      </svg>
      <span><strong>Sensor Arus (ZMPT101B) belum terhubung!</strong> Data daya hanya dari simulasi. Hubungkan sensor ACS712/ACS758 untuk pengukuran aktual.</span>
    </div>

    <!-- Quick Tabs -->
    <div class="quick-tabs">
      <button :class="['tab-btn', { active: activeTab === 'today' }]" @click="setTab('today')">Hari Ini</button>
      <button :class="['tab-btn', { active: activeTab === 'weekly' }]" @click="setTab('weekly')">Mingguan</button>
      <button :class="['tab-btn', { active: activeTab === 'monthly' }]" @click="setTab('monthly')">Bulanan</button>
      <div class="tab-spacer"></div>
      <button class="refresh-btn" @click="refreshData">Refresh</button>
    </div>

    <!-- Stats Grid -->
    <div class="stats-section">
      <h3 class="section-title">Statistik Konsumsi</h3>
      <div class="stats-grid">
        <div class="stat-card today-card">
          <div class="stat-card-header">
            <span class="stat-label-lg">Hari Ini</span>
            <span class="stat-trend positive">{{ todayConsumption > 0 ? '+12.3%' : 'N/A' }}</span>
          </div>
          <div class="stat-value-lg">{{ todayConsumption.toFixed(2) }} kWh</div>
          <div class="stat-subvalue">Rp {{ formatCurrency(todayCost) }}</div>
          <div class="stat-progress">
            <div class="progress-bar">
              <div class="progress-fill" :style="{ width: Math.min(100, (todayConsumption / settings.dailyTarget) * 100) + '%' }"></div>
            </div>
            <span class="progress-text">{{ ((todayConsumption / settings.dailyTarget) * 100).toFixed(0) }}% target harian</span>
          </div>
        </div>

        <div class="stat-card monthly-card">
          <div class="stat-card-header">
            <span class="stat-label-lg">Bulan Ini</span>
            <span class="stat-trend positive">{{ monthlyConsumption > 0 ? '+8.7%' : 'N/A' }}</span>
          </div>
          <div class="stat-value-lg">{{ monthlyConsumption.toFixed(2) }} kWh</div>
          <div class="stat-subvalue">Rp {{ formatCurrency(monthlyCost) }}</div>
          <div class="stat-progress">
            <div class="progress-bar">
              <div class="progress-fill" :style="{ width: Math.min(100, (monthlyConsumption / settings.monthlyTarget) * 100) + '%' }"></div>
            </div>
            <span class="progress-text">{{ ((monthlyConsumption / settings.monthlyTarget) * 100).toFixed(0) }}% target bulanan</span>
          </div>
        </div>

        <div class="stat-card projection-card">
          <div class="stat-card-header">
            <span class="stat-label-lg">Proyeksi Bulan Ini</span>
          </div>
          <div class="stat-value-lg">{{ projectedMonthly.toFixed(2) }} kWh</div>
          <div class="stat-subvalue">Rp {{ formatCurrency(projectedCost) }}</div>
          <div class="stat-status" :class="projectionStatus.class">
            {{ projectionStatus.text }}
          </div>
        </div>

        <div class="stat-card efficiency-card">
          <div class="stat-card-header">
            <span class="stat-label-lg">Skor Efisiensi</span>
          </div>
          <div class="stat-value-lg">{{ efficiencyScore }}/100</div>
          <div class="stat-subvalue">{{ getEfficiencyLabel(efficiencyScore) }}</div>
          <div class="stat-progress">
            <div class="progress-bar">
              <div class="progress-fill efficiency-fill" :style="{ width: efficiencyScore + '%' }"></div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Peak Usage Analysis -->
    <div class="chart-section">
      <h3 class="section-title">Analisis Peak Usage (24 Jam)</h3>
      <div class="chart-container">
        <Bar v-if="peakChartData" :data="peakChartData" :options="peakChartOptions" />
        <div v-else class="chart-placeholder">
          <p>Memuat data...</p>
        </div>
      </div>
      <div class="peak-info-grid">
        <div class="info-item">
          <span class="info-label">Jam Tertinggi</span>
          <span class="info-value">{{ peakHour.hour }}:00 ({{ peakHour.power.toFixed(0) }}W)</span>
        </div>
        <div class="info-item">
          <span class="info-label">Jam Terendah</span>
          <span class="info-value">{{ lowestHour.hour }}:00 ({{ lowestHour.power.toFixed(0) }}W)</span>
        </div>
        <div class="info-item">
          <span class="info-label">Rata-rata Peak Hour</span>
          <span class="info-value">{{ avgPeakHourPower.toFixed(0) }}W</span>
        </div>
      </div>
    </div>

    <!-- AI Recommendations -->
    <div class="recommendations-section">
      <div class="section-header-bar">
        <h3 class="section-title">AI Recommendations</h3>
        <button class="refresh-btn-small" @click="refreshRecommendations">Refresh</button>
      </div>

      <div v-if="recommendations.length > 0" class="recommendations-list">
        <div
          v-for="(rec, index) in recommendations"
          :key="index"
          class="recommendation-card"
          :class="'priority-' + rec.priority"
        >
          <div class="rec-header">
            <h4>{{ rec.title }}</h4>
            <span class="rec-badge" :class="'badge-' + rec.priority">
              {{ rec.priority.toUpperCase() }}
            </span>
          </div>
          <p class="rec-description">{{ rec.description }}</p>
          <div v-if="rec.potentialSaving > 0" class="rec-saving">
            Potensi penghematan: Rp {{ formatCurrency(rec.potentialSaving) }}
          </div>
        </div>
      </div>

      <div v-else class="no-recommendations">
        <p>Belum ada rekomendasi. Sistem sedang mengumpulkan data...</p>
      </div>
    </div>

    <!-- Settings (Admin Only) -->
    <div v-if="isAdmin" class="settings-section">
      <h3 class="section-title">Pengaturan</h3>
      <div class="settings-grid">
        <div class="setting-item">
          <label>Tarif Listrik (Rp/kWh)</label>
          <input
            type="number"
            v-model.number="localTariff"
            @change="handleTariffUpdate"
            step="0.01"
            min="0"
          />
        </div>
        <div class="setting-item">
          <label>Target Konsumsi Bulanan (kWh)</label>
          <input
            type="number"
            v-model.number="localTarget"
            @change="handleTargetUpdate"
            step="1"
            min="0"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { Bar } from 'vue-chartjs'
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend } from 'chart.js'
import { useEnergyManagement } from '../composables/useEnergyManagement'
import { useHistoricalData } from '../composables/useHistoricalData'

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend)

const props = defineProps({
  isDarkMode: Boolean,
  currentPower: Number,
  isAdmin: {
    type: Boolean,
    default: true
  }
})

const {
  settings,
  recommendations,
  loadSettings,
  updateTariff,
  updateMonthlyTarget,
  addEnergyDataPoint,
  getTodayConsumption,
  getMonthlyConsumption,
  analyzePeakUsage,
  calculateCost,
  generateRecommendations,
  getPowerData,
  historicalData,
  isValidPower
} = useEnergyManagement()

// Get direct access to getStatistics from useHistoricalData
const { getStatistics } = useHistoricalData()

const localTariff = ref(1444.70)
const localTarget = ref(100)
const activeTab = ref('monthly')
const lastUpdateAt = ref(null)
const hasCurrentSensor = ref(false)

// Reactive consumption data
// NOTE: getStatistics returns totalEnergy in Wh, need to divide by 1000 for kWh
const todayConsumption = computed(() => {
  const stats = getStatistics(new Date(new Date().setHours(0, 0, 0, 0)), new Date())
  const valWh = stats?.totalEnergy || 0
  const valKwh = valWh / 1000 // Convert Wh to kWh

  // Check if we have valid current/power data (sensor connected)
  hasCurrentSensor.value = (stats?.validPowerRecords || 0) > 0

  console.log('[EnergyManagement] Today:', {
    totalEnergyWh: valWh,
    totalEnergyKwh: valKwh,
    totalRecords: stats?.totalRecords,
    validPowerRecords: stats?.validPowerRecords,
    avgPower: stats?.power?.avg
  })
  return valKwh
})

const monthlyConsumption = computed(() => {
  const now = new Date()
  const startOfMonth = new Date(now.getFullYear(), now.getMonth(), 1)
  const stats = getStatistics(startOfMonth, now)
  const valWh = stats?.totalEnergy || 0
  const valKwh = valWh / 1000 // Convert Wh to kWh
  return valKwh
})

const peakAnalysis = ref([])

const updateConsumptionData = () => {
  peakAnalysis.value = analyzePeakUsage()
  lastUpdateAt.value = new Date()
  console.log('[EnergyManagement] Peak analysis:', peakAnalysis.value.length, 'hours')
}

const todayCost = computed(() => calculateCost(todayConsumption.value))
const monthlyCost = computed(() => calculateCost(monthlyConsumption.value))

const projectedMonthly = computed(() => {
  const now = new Date()
  const dayOfMonth = now.getDate()
  const daysInMonth = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate()
  if (dayOfMonth === 0) return 0
  return (monthlyConsumption.value / dayOfMonth) * daysInMonth
})

const projectedCost = computed(() => calculateCost(projectedMonthly.value))

const formatCurrency = (value) => {
  const num = Number(value || 0)
  return num.toLocaleString('id-ID', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  })
}

const lastUpdateText = computed(() => {
  if (!lastUpdateAt.value) return 'Belum update'
  return lastUpdateAt.value.toLocaleTimeString('id-ID', {
    hour: '2-digit',
    minute: '2-digit'
  })
})

const projectionStatus = computed(() => {
  const ratio = projectedMonthly.value / settings.value.monthlyTarget
  if (ratio > 1.1) {
    return { text: 'Melebihi Target', class: 'status-danger' }
  } else if (ratio > 0.9) {
    return { text: 'Sesuai Target', class: 'status-success' }
  } else {
    return { text: 'Di Bawah Target', class: 'status-excellent' }
  }
})

const efficiencyScore = computed(() => {
  // If no consumption data, score is undefined
  if (monthlyConsumption.value <= 0) return 0
  const ratio = projectedMonthly.value / settings.value.monthlyTarget
  return Math.max(0, Math.min(100, Math.round(100 - (ratio - 1) * 100)))
})

const peakHour = computed(() => {
  if (peakAnalysis.value.length === 0) return { hour: 0, power: 0 }
  return {
    hour: peakAnalysis.value[0].hour,
    power: peakAnalysis.value[0].avgPower
  }
})

const lowestHour = computed(() => {
  if (peakAnalysis.value.length === 0) return { hour: 0, power: 0 }
  const lowest = [...peakAnalysis.value].sort((a, b) => a.avgPower - b.avgPower)[0]
  return {
    hour: lowest.hour,
    power: lowest.avgPower
  }
})

const avgPeakHourPower = computed(() => {
  const peakHours = peakAnalysis.value.filter(h => h.isPeakHour)
  if (peakHours.length === 0) return 0
  return peakHours.reduce((sum, h) => sum + h.avgPower, 0) / peakHours.length
})

const peakChartData = computed(() => {
  if (peakAnalysis.value.length === 0) {
    return {
      labels: Array.from({ length: 24 }, (_, i) => `${i}:00`),
      datasets: [{
        label: 'Daya Rata-rata (W)',
        data: Array(24).fill(0),
        backgroundColor: 'rgba(6, 182, 212, 0.3)',
        borderColor: 'rgba(6, 182, 212, 0.8)',
        borderWidth: 2
      }]
    }
  }

  const sortedData = [...peakAnalysis.value].sort((a, b) => a.hour - b.hour)
  return {
    labels: sortedData.map(d => `${d.hour}:00`),
    datasets: [{
      label: 'Daya Rata-rata (W)',
      data: sortedData.map(d => d.avgPower),
      backgroundColor: sortedData.map(d =>
        d.isPeakHour ? 'rgba(239, 68, 68, 0.6)' : 'rgba(6, 182, 212, 0.6)'
      ),
      borderColor: sortedData.map(d =>
        d.isPeakHour ? 'rgba(239, 68, 68, 1)' : 'rgba(6, 182, 212, 1)'
      ),
      borderWidth: 2
    }]
  }
})

const peakChartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      display: true,
      labels: {
        color: props.isDarkMode ? '#e5e7eb' : '#374151'
      }
    },
    tooltip: {
      callbacks: {
        label: (context) => `${context.parsed.y.toFixed(0)}W`
      }
    }
  },
  scales: {
    x: {
      ticks: {
        color: props.isDarkMode ? '#9ca3af' : '#6b7280'
      },
      grid: {
        color: props.isDarkMode ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)'
      }
    },
    y: {
      beginAtZero: true,
      ticks: {
        color: props.isDarkMode ? '#9ca3af' : '#6b7280',
        callback: (value) => `${value}W`
      },
      grid: {
        color: props.isDarkMode ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)'
      }
    }
  }
}))

const setTab = (tab) => {
  activeTab.value = tab
}

const refreshData = () => {
  updateConsumptionData()
  generateRecommendations()
}

const refreshRecommendations = () => {
  generateRecommendations()
}

const handleTariffUpdate = () => {
  updateTariff(localTariff.value)
  updateConsumptionData()
  generateRecommendations()
}

const handleTargetUpdate = () => {
  updateMonthlyTarget(localTarget.value)
  updateConsumptionData()
  generateRecommendations()
}

const getEfficiencyLabel = (score) => {
  if (score >= 80) return 'Sangat Efisien'
  if (score >= 60) return 'Efisien'
  if (score >= 40) return 'Cukup Efisien'
  return 'Perlu Ditingkatkan'
}

watch(() => props.currentPower, (newPower) => {
  if (newPower && newPower > 0) {
    addEnergyDataPoint(newPower)
  }
}, { immediate: false })

// Watch historical data changes
watch(() => historicalData.value.length, (newLength, oldLength) => {
  console.log('[EnergyManagement] Historical data changed:', oldLength, '->', newLength, 'records')
  console.log('[EnergyManagement] Sample data:', historicalData.value.slice(0, 3).map(d => ({
    timestamp: d.timestamp,
    power: d.power,
    valid: isValidPower(d.power)
  })))
  updateConsumptionData()
  generateRecommendations()
}, { immediate: true })

let recommendationInterval = null
let updateInterval = null

onMounted(() => {
  loadSettings()
  localTariff.value = settings.value.tariffPerKwh
  localTarget.value = settings.value.monthlyTarget
  updateConsumptionData()
  generateRecommendations()

  // Refresh data periodically
  recommendationInterval = setInterval(() => {
    updateConsumptionData()
    generateRecommendations()
  }, 5 * 60 * 1000)

  updateInterval = setInterval(() => {
    updateConsumptionData()
  }, 30 * 1000)
})

onUnmounted(() => {
  if (recommendationInterval) clearInterval(recommendationInterval)
  if (updateInterval) clearInterval(updateInterval)
})
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=Sora:wght@500;600;700;800&display=swap');

.energy-section {
  --accent: #f59e0b;
  --accent-dark: #d97706;
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

.sensor-warning {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: #fef3c7;
  border: 1px solid #f59e0b;
  border-radius: 8px;
  margin-bottom: 16px;
  color: #92400e;
  font-size: 13px;
}

.sensor-warning svg {
  flex-shrink: 0;
  color: #f59e0b;
}

.hero-banner { margin-bottom: 24px; }

.hero-kicker {
  display: inline-block;
  padding: 6px 12px;
  background: rgba(245, 158, 11, 0.1);
  border: 1px solid rgba(245, 158, 11, 0.2);
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
  background: rgba(245, 158, 11, 0.1);
  border-color: rgba(245, 158, 11, 0.2);
  color: var(--accent);
}

.quick-tabs {
  display: flex;
  gap: 8px;
  align-items: center;
  padding: 8px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.tab-btn {
  padding: 10px 16px;
  background: transparent;
  border: none;
  border-radius: 8px;
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--text-2);
  cursor: pointer;
  transition: background-color 0.2s, border-color 0.2s, color 0.2s;
}

.tab-btn:hover {
  background: var(--surface-2);
  color: var(--text);
}

.tab-btn.active {
  background: var(--accent);
  color: white;
  font-weight: 600;
}

.tab-spacer { flex: 1; }

.refresh-btn {
  padding: 10px 16px;
  background: linear-gradient(135deg, var(--accent), var(--accent-dark));
  border: none;
  border-radius: 8px;
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: 0.85rem;
  font-weight: 600;
  color: white;
  cursor: pointer;
  transition: background-color 0.2s, border-color 0.2s, color 0.2s;
}

.refresh-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(245, 158, 11, 0.3);
}

.refresh-btn-small {
  padding: 8px 14px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 6px;
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: 0.8rem;
  font-weight: 500;
  color: var(--text-2);
  cursor: pointer;
  transition: background-color 0.2s, border-color 0.2s, color 0.2s;
}

.refresh-btn-small:hover {
  border-color: var(--accent);
  color: var(--accent);
}

.section-title {
  font-family: 'Sora', sans-serif;
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--text);
  margin: 0 0 16px 0;
}

.section-header-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.stats-section { margin-bottom: 24px; }

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
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

.today-card { border-top: 3px solid var(--accent); }
.monthly-card { border-top: 3px solid var(--purple); }
.projection-card { border-top: 3px solid var(--warning); }
.efficiency-card { border-top: 3px solid var(--success); }

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

.stat-trend.negative {
  background: rgba(239, 68, 68, 0.15);
  color: var(--danger);
}

.stat-value-lg {
  font-family: 'Sora', sans-serif;
  font-size: 1.8rem;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 4px;
}

.stat-subvalue {
  font-size: 0.9rem;
  color: var(--text-2);
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
  background: linear-gradient(90deg, var(--accent), var(--accent-dark));
  border-radius: 3px;
  transition: width 0.5s ease;
}

.efficiency-fill {
  background: linear-gradient(90deg, var(--success), #059669);
}

.progress-text {
  font-size: 0.75rem;
  color: var(--text-3);
}

.stat-status {
  display: inline-block;
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 600;
}

.status-danger {
  background: rgba(239, 68, 68, 0.15);
  color: var(--danger);
}

.status-success {
  background: rgba(34, 197, 94, 0.15);
  color: var(--success);
}

.status-excellent {
  background: rgba(34, 211, 238, 0.15);
  color: #22c11e;
}

.chart-section {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 24px;
  margin-bottom: 24px;
}

.chart-container {
  height: 300px;
  margin-bottom: 16px;
}

.peak-info-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px;
  background: var(--surface-2);
  border-radius: 8px;
}

.info-label {
  font-size: 0.78rem;
  color: var(--text-3);
  font-weight: 500;
}

.info-value {
  font-size: 0.95rem;
  color: var(--text);
  font-weight: 600;
}

.recommendations-section {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 24px;
  margin-bottom: 24px;
}

.recommendations-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.recommendation-card {
  padding: 16px;
  border-radius: 12px;
  border-left: 4px solid;
  background: var(--surface-2);
  transition: background-color 0.2s, border-color 0.2s, color 0.2s;
}

.recommendation-card:hover {
  transform: translateX(4px);
}

.recommendation-card.priority-high {
  border-left-color: var(--danger);
}

.recommendation-card.priority-medium {
  border-left-color: var(--warning);
}

.recommendation-card.priority-low {
  border-left-color: var(--success);
}

.rec-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  gap: 12px;
}

.rec-header h4 {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: var(--text);
}

.rec-badge {
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 0.7rem;
  font-weight: 700;
  white-space: nowrap;
}

.badge-high {
  background: rgba(239, 68, 68, 0.15);
  color: var(--danger);
}

.badge-medium {
  background: rgba(245, 158, 11, 0.15);
  color: var(--warning);
}

.badge-low {
  background: rgba(34, 197, 94, 0.15);
  color: var(--success);
}

.rec-description {
  margin: 0 0 12px 0;
  font-size: 0.9rem;
  color: var(--text-2);
  line-height: 1.5;
}

.rec-saving {
  padding: 10px 12px;
  background: rgba(34, 197, 94, 0.1);
  border-radius: 6px;
  color: var(--success);
  font-size: 0.85rem;
  font-weight: 500;
}

.no-recommendations {
  text-align: center;
  padding: 40px;
  color: var(--text-3);
}

.settings-section {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 24px;
}

.settings-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.setting-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.setting-item label {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text-2);
}

.setting-item input {
  padding: 12px 14px;
  border: 2px solid var(--border);
  border-radius: 8px;
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: 0.9rem;
  color: var(--text);
  background: var(--surface);
  transition: background-color 0.2s, border-color 0.2s, color 0.2s;
}

.setting-item input:focus {
  outline: none;
  border-color: var(--accent);
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

@media (max-width: 1200px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .energy-section {
    padding: 16px;
  }

  .stats-grid {
    grid-template-columns: 1fr;
  }

  .peak-info-grid {
    grid-template-columns: 1fr;
  }

  .settings-grid {
    grid-template-columns: 1fr;
  }

  .quick-tabs {
    flex-direction: column;
  }

  .tab-spacer {
    display: none;
  }

  .refresh-btn {
    width: 100%;
    justify-content: center;
  }
}
</style>
