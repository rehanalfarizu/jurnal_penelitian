<template>
  <div class="energy-management" :class="{ 'dark': isDarkMode }">
    <div v-if="!isAdmin" class="section-header" @click="isExpanded = !isExpanded">
      <h2>💰 Energy Management & AI Recommendations</h2>
      <button class="toggle-btn">
        {{ isExpanded ? '▼' : '▶' }}
      </button>
    </div>
    
    <div v-if="isExpanded || isAdmin" class="section-content">
      <!-- Settings Section (Admin Only) -->
      <div v-if="isAdmin" class="settings-section">
        <h3>⚙️ Pengaturan</h3>
        <div class="settings-grid">
          <div class="setting-item">
            <label>Tarif Listrik (Rp/kWh):</label>
            <input 
              type="number" 
              v-model.number="localTariff" 
              @change="handleTariffUpdate"
              step="0.01"
              min="0"
            />
          </div>
          <div class="setting-item">
            <label>Target Konsumsi Bulanan (kWh):</label>
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
      
      <!-- Overview Cards -->
      <div class="overview-grid">
        <div class="overview-card today">
          <div class="card-header">
            <span class="card-icon">📅</span>
            <span class="card-title">Hari Ini</span>
          </div>
          <div class="card-value">{{ todayConsumption.toFixed(2) }} kWh</div>
          <div class="card-cost">Rp {{ formatCurrency(todayCost) }}</div>
          <div class="card-progress">
            <div class="progress-bar">
              <div 
                class="progress-fill today-fill" 
                :style="{ width: Math.min(100, (todayConsumption / settings.dailyTarget) * 100) + '%' }"
              ></div>
            </div>
            <span class="progress-text">
              {{ ((todayConsumption / settings.dailyTarget) * 100).toFixed(0) }}% dari target harian
            </span>
          </div>
        </div>
        
        <div class="overview-card monthly">
          <div class="card-header">
            <span class="card-icon">📊</span>
            <span class="card-title">Bulan Ini</span>
          </div>
          <div class="card-value">{{ monthlyConsumption.toFixed(2) }} kWh</div>
          <div class="card-cost">Rp {{ formatCurrency(monthlyCost) }}</div>
          <div class="card-progress">
            <div class="progress-bar">
              <div 
                class="progress-fill monthly-fill" 
                :style="{ width: Math.min(100, (monthlyConsumption / settings.monthlyTarget) * 100) + '%' }"
              ></div>
            </div>
            <span class="progress-text">
              {{ ((monthlyConsumption / settings.monthlyTarget) * 100).toFixed(0) }}% dari target bulanan
            </span>
          </div>
        </div>
        
        <div class="overview-card projection">
          <div class="card-header">
            <span class="card-icon">🔮</span>
            <span class="card-title">Proyeksi Bulan Ini</span>
          </div>
          <div class="card-value">{{ projectedMonthly.toFixed(2) }} kWh</div>
          <div class="card-cost">Rp {{ formatCurrency(projectedCost) }}</div>
          <div class="card-status" :class="projectionStatus.class">
            {{ projectionStatus.text }}
          </div>
        </div>
        
        <div class="overview-card efficiency">
          <div class="card-header">
            <span class="card-icon">⭐</span>
            <span class="card-title">Skor Efisiensi</span>
          </div>
          <div class="efficiency-score" :class="getEfficiencyClass(efficiencyScore)">
            {{ efficiencyScore }}/100
          </div>
          <div class="card-subtitle">{{ getEfficiencyLabel(efficiencyScore) }}</div>
        </div>
      </div>
      
      <!-- Peak Usage Analysis -->
      <div class="peak-analysis-section">
        <h3>📈 Analisis Peak Usage (24 Jam Terakhir)</h3>
        <div class="chart-container">
          <Bar v-if="peakChartData" :data="peakChartData" :options="peakChartOptions" />
        </div>
        <div class="peak-info">
          <div class="info-item">
            <span class="info-label">Jam Tertinggi:</span>
            <span class="info-value">{{ peakHour.hour }}:00 ({{ peakHour.power.toFixed(0) }}W)</span>
          </div>
          <div class="info-item">
            <span class="info-label">Jam Terendah:</span>
            <span class="info-value">{{ lowestHour.hour }}:00 ({{ lowestHour.power.toFixed(0) }}W)</span>
          </div>
          <div class="info-item">
            <span class="info-label">Rata-rata Peak Hour:</span>
            <span class="info-value">{{ avgPeakHourPower.toFixed(0) }}W</span>
          </div>
        </div>
      </div>
      
      <!-- AI Recommendations -->
      <div class="recommendations-section">
        <div class="recommendations-header">
          <h3>🤖 AI Recommendations</h3>
          <button @click="refreshRecommendations" class="refresh-btn">
            🔄 Refresh
          </button>
        </div>
        
        <div v-if="recommendations.length > 0" class="recommendations-list">
          <div 
            v-for="(rec, index) in recommendations" 
            :key="index"
            class="recommendation-card"
            :class="'priority-' + rec.priority"
          >
            <div class="rec-header">
              <span class="rec-icon">{{ rec.icon }}</span>
              <div class="rec-title-section">
                <h4>{{ rec.title }}</h4>
                <span class="rec-badge" :class="'badge-' + rec.priority">
                  {{ rec.priority.toUpperCase() }}
                </span>
              </div>
            </div>
            <p class="rec-description">{{ rec.description }}</p>
            <div v-if="rec.potentialSaving > 0" class="rec-saving">
              💵 Potensi penghematan: <strong>Rp {{ formatCurrency(rec.potentialSaving) }}</strong>
            </div>
          </div>
        </div>
        
        <div v-else class="no-recommendations">
          <p>Belum ada rekomendasi. Sistem sedang mengumpulkan data...</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { Bar } from 'vue-chartjs'
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend } from 'chart.js'
import { useEnergyManagement } from '../composables/useEnergyManagement'

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
  generateRecommendations
} = useEnergyManagement()

const isExpanded = ref(false)
const localTariff = ref(settings.value.tariffPerKwh)
const localTarget = ref(settings.value.monthlyTarget)

const todayConsumption = ref(0)
const monthlyConsumption = ref(0)
const peakAnalysis = ref([])

// Update consumption data
const updateConsumptionData = () => {
  todayConsumption.value = getTodayConsumption()
  monthlyConsumption.value = getMonthlyConsumption()
  peakAnalysis.value = analyzePeakUsage()
}

// Computed values
const todayCost = computed(() => calculateCost(todayConsumption.value))
const monthlyCost = computed(() => calculateCost(monthlyConsumption.value))

const projectedMonthly = computed(() => {
  const now = new Date()
  const dayOfMonth = now.getDate()
  const daysInMonth = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate()
  return (monthlyConsumption.value / dayOfMonth) * daysInMonth
})

const projectedCost = computed(() => calculateCost(projectedMonthly.value))

// Format currency to exactly 2 decimals (e.g., Rp 10.714,29)
const formatCurrency = (value) => {
  const num = Number(value || 0)
  return num.toLocaleString('id-ID', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  })
}

const projectionStatus = computed(() => {
  const ratio = projectedMonthly.value / settings.value.monthlyTarget
  if (ratio > 1.1) {
    return { text: '⚠️ Melebihi Target', class: 'status-danger' }
  } else if (ratio > 0.9) {
    return { text: '✅ Sesuai Target', class: 'status-success' }
  } else {
    return { text: '🎉 Di Bawah Target', class: 'status-excellent' }
  }
})

const efficiencyScore = computed(() => {
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

// Peak usage chart
const peakChartData = computed(() => {
  if (peakAnalysis.value.length === 0) return null
  
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

// Handlers
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

const refreshRecommendations = () => {
  generateRecommendations()
}

const getEfficiencyClass = (score) => {
  if (score >= 80) return 'excellent'
  if (score >= 60) return 'good'
  if (score >= 40) return 'fair'
  return 'poor'
}

const getEfficiencyLabel = (score) => {
  if (score >= 80) return 'Sangat Efisien'
  if (score >= 60) return 'Efisien'
  if (score >= 40) return 'Cukup Efisien'
  return 'Perlu Ditingkatkan'
}

// Watch for power changes
watch(() => props.currentPower, (newPower) => {
  if (newPower && newPower > 0) {
    addEnergyDataPoint(newPower)
    updateConsumptionData()
  }
}, { immediate: false })

// Auto-refresh recommendations every 5 minutes
let recommendationInterval = null

onMounted(() => {
  loadSettings()
  localTariff.value = settings.value.tariffPerKwh
  localTarget.value = settings.value.monthlyTarget
  updateConsumptionData()
  generateRecommendations()
  
  recommendationInterval = setInterval(() => {
    updateConsumptionData()
    generateRecommendations()
  }, 5 * 60 * 1000) // 5 minutes
})
</script>

<style scoped>
.energy-management {
  margin-top: 20px;
  padding: 20px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
}

.energy-management.dark {
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
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.toggle-btn {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
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
  box-shadow: 0 4px 8px rgba(245, 158, 11, 0.3);
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

/* Settings Section */
.settings-section {
  background: #f8fafc;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 20px;
}

.dark .settings-section {
  background: #0f172a;
}

.settings-section h3 {
  margin: 0 0 15px 0;
  color: #475569;
}

.dark .settings-section h3 {
  color: #cbd5e1;
}

.settings-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 15px;
}

.setting-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.setting-item label {
  font-weight: 600;
  color: #475569;
  font-size: 0.95rem;
}

.dark .setting-item label {
  color: #cbd5e1;
}

.setting-item input {
  padding: 10px;
  border: 2px solid #e2e8f0;
  border-radius: 6px;
  font-size: 1rem;
  transition: all 0.3s ease;
}

.dark .setting-item input {
  background: #1e293b;
  border-color: #334155;
  color: #e5e7eb;
}

.setting-item input:focus {
  outline: none;
  border-color: #f59e0b;
}

/* Overview Cards */
.overview-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 15px;
  margin-bottom: 20px;
}

.overview-card {
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
}

.overview-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 8px 12px rgba(0, 0, 0, 0.15);
}

.overview-card.today {
  background: linear-gradient(135deg, #06b6d4 0%, #0891b2 100%);
  color: white;
}

.overview-card.monthly {
  background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%);
  color: white;
}

.overview-card.projection {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
  color: white;
}

.overview-card.efficiency {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  color: white;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 15px;
}

.card-icon {
  font-size: 1.8rem;
}

.card-title {
  font-size: 1rem;
  font-weight: 600;
  opacity: 0.9;
}

.card-value {
  font-size: 2rem;
  font-weight: 700;
  margin-bottom: 5px;
}

.card-cost {
  font-size: 1.1rem;
  opacity: 0.9;
  margin-bottom: 15px;
}

.card-progress {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.progress-bar {
  width: 100%;
  height: 8px;
  background: rgba(255, 255, 255, 0.3);
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.5s ease;
}

.today-fill {
  background: rgba(255, 255, 255, 0.9);
}

.monthly-fill {
  background: rgba(255, 255, 255, 0.9);
}

.progress-text {
  font-size: 0.85rem;
  opacity: 0.9;
}

.card-status {
  padding: 8px 12px;
  border-radius: 6px;
  font-weight: 600;
  text-align: center;
  margin-top: 10px;
}

.status-danger {
  background: rgba(239, 68, 68, 0.9);
}

.status-success {
  background: rgba(34, 197, 94, 0.9);
}

.status-excellent {
  background: rgba(59, 130, 246, 0.9);
}

.efficiency-score {
  font-size: 2.5rem;
  font-weight: 700;
  margin-bottom: 10px;
}

.efficiency-score.excellent {
  color: #fff;
  text-shadow: 0 0 10px rgba(255, 255, 255, 0.5);
}

.card-subtitle {
  font-size: 1rem;
  opacity: 0.9;
}

/* Peak Analysis */
.peak-analysis-section {
  background: #f8fafc;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 20px;
}

.dark .peak-analysis-section {
  background: #0f172a;
}

.peak-analysis-section h3 {
  margin: 0 0 15px 0;
  color: #475569;
}

.dark .peak-analysis-section h3 {
  color: #cbd5e1;
}

.chart-container {
  height: 300px;
  margin-bottom: 15px;
}

.peak-info {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 15px;
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: white;
  border-radius: 6px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.dark .info-item {
  background: #1e293b;
}

.info-label {
  font-weight: 600;
  color: #64748b;
  font-size: 0.9rem;
}

.dark .info-label {
  color: #94a3b8;
}

.info-value {
  font-weight: 700;
  color: #0f172a;
  font-size: 1rem;
}

.dark .info-value {
  color: #e5e7eb;
}

/* Recommendations */
.recommendations-section {
  background: #f8fafc;
  padding: 20px;
  border-radius: 8px;
}

.dark .recommendations-section {
  background: #0f172a;
}

.recommendations-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.recommendations-header h3 {
  margin: 0;
  color: #475569;
}

.dark .recommendations-header h3 {
  color: #cbd5e1;
}

.refresh-btn {
  padding: 8px 16px;
  background: linear-gradient(135deg, #06b6d4 0%, #0891b2 100%);
  color: white;
  border: none;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.refresh-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(6, 182, 212, 0.3);
}

.recommendations-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.recommendation-card {
  padding: 20px;
  border-radius: 12px;
  border-left: 5px solid;
  background: white;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  transition: all 0.3s ease;
}

.dark .recommendation-card {
  background: #1e293b;
}

.recommendation-card:hover {
  transform: translateX(5px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

.recommendation-card.priority-high {
  border-left-color: #ef4444;
}

.recommendation-card.priority-medium {
  border-left-color: #f59e0b;
}

.recommendation-card.priority-low {
  border-left-color: #10b981;
}

.rec-header {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 12px;
}

.rec-icon {
  font-size: 2rem;
}

.rec-title-section {
  flex: 1;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 10px;
}

.rec-title-section h4 {
  margin: 0;
  color: #0f172a;
  font-size: 1.1rem;
}

.dark .rec-title-section h4 {
  color: #e5e7eb;
}

.rec-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 700;
  white-space: nowrap;
}

.badge-high {
  background: #fee2e2;
  color: #991b1b;
}

.badge-medium {
  background: #fef3c7;
  color: #92400e;
}

.badge-low {
  background: #d1fae5;
  color: #065f46;
}

.dark .badge-high {
  background: #7f1d1d;
  color: #fca5a5;
}

.dark .badge-medium {
  background: #78350f;
  color: #fcd34d;
}

.dark .badge-low {
  background: #064e3b;
  color: #6ee7b7;
}

.rec-description {
  margin: 0 0 12px 0;
  color: #475569;
  line-height: 1.6;
}

.dark .rec-description {
  color: #cbd5e1;
}

.rec-saving {
  padding: 10px;
  background: linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%);
  border-radius: 6px;
  color: #166534;
  font-size: 0.95rem;
}

.dark .rec-saving {
  background: linear-gradient(135deg, #064e3b 0%, #065f46 100%);
  color: #6ee7b7;
}

.no-recommendations {
  text-align: center;
  padding: 40px;
  color: #94a3b8;
}

@media (max-width: 768px) {
  .energy-management {
    padding: 15px;
  }
  
  .section-header h2 {
    font-size: 1.2rem;
  }
  
  .overview-grid {
    grid-template-columns: 1fr;
  }
  
  .settings-grid {
    grid-template-columns: 1fr;
  }
  
  .peak-info {
    grid-template-columns: 1fr;
  }
  
  .chart-container {
    height: 250px;
  }
  
  .rec-title-section {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
