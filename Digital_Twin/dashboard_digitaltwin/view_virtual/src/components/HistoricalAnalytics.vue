<template>
  <div class="historical-section" :class="{ 'dark': isDarkMode }">
    <div v-if="!isAdmin" class="section-header" @click="isExpanded = !isExpanded">
      <h2>📊 Historical Data & Analytics</h2>
      <button class="toggle-btn">
        {{ isExpanded ? '▼' : '▶' }}
      </button>
    </div>
    
    <div v-if="isExpanded || isAdmin" class="section-content">
      <!-- Date Range Picker -->
      <div class="date-range-section">
        <div class="sync-toolbar">
          <div class="sync-meta">
            <span class="sync-label">Last Sync</span>
            <strong class="sync-value">{{ lastSyncText }}</strong>
          </div>
          <button class="btn-refresh" :disabled="isRefreshing || isLoading" @click="refreshHistoricalData()">
            {{ isRefreshing || isLoading ? 'Menyegarkan...' : 'Refresh Data' }}
          </button>
        </div>

        <div class="date-inputs">
          <div class="input-group">
            <label>Dari Tanggal:</label>
            <input type="date" v-model="tempStartDate" :max="tempEndDate" />
          </div>
          <div class="input-group">
            <label>Sampai Tanggal:</label>
            <input type="date" v-model="tempEndDate" :min="tempStartDate" :max="today" />
          </div>
          <div class="input-group action-group">
            <label>&nbsp;</label>
            <button class="btn-apply" @click="applyFilter">🔍 Cari Data</button>
          </div>
        </div>
        
        <div class="quick-selects">
          <button @click="selectToday">Hari Ini</button>
          <button @click="selectYesterday">Kemarin</button>
          <button @click="select7Days">7 Hari</button>
          <button @click="select30Days">30 Hari</button>
          <button @click="select90Days">90 Hari</button>
          <button @click="selectAllTime">All Time</button>
        </div>
      </div>
      
      <!-- Statistics Cards -->
      <div v-if="statistics" class="stats-summary-bar">
        <div class="stats-summary-chip">
          <span class="stats-summary-label">Jumlah Data</span>
          <strong class="stats-summary-value">{{ statistics.totalRecords }}</strong>
          <span class="stats-summary-label">data points</span>
        </div>
      </div>

      <div v-if="statistics" class="stats-grid">
        <div class="stat-card">
          <div class="stat-icon">🌡️</div>
          <div class="stat-info">
            <p class="stat-label">Temperature</p>
            <p class="stat-value">{{ statistics.temperature.avg?.toFixed(1) || 'N/A' }} °C</p>
            <p class="stat-range">{{ statistics.temperature.min?.toFixed(1) }} - {{ statistics.temperature.max?.toFixed(1) }}</p>
          </div>
        </div>
        
        <div class="stat-card">
          <div class="stat-icon">💧</div>
          <div class="stat-info">
            <p class="stat-label">Humidity</p>
            <p class="stat-value">{{ statistics.humidity.avg?.toFixed(1) || 'N/A' }} %</p>
            <p class="stat-range">{{ statistics.humidity.min?.toFixed(1) }} - {{ statistics.humidity.max?.toFixed(1) }}</p>
          </div>
        </div>
        
        <div class="stat-card">
          <div class="stat-icon">⚡</div>
          <div class="stat-info">
            <p class="stat-label">Power</p>
            <p class="stat-value">{{ statistics.power.avg?.toFixed(0) || 'N/A' }} W</p>
            <p class="stat-range">{{ statistics.power.min?.toFixed(0) }} - {{ statistics.power.max?.toFixed(0) }}</p>
          </div>
        </div>
        
        <div class="stat-card">
          <div class="stat-icon">🔋</div>
          <div class="stat-info">
            <p class="stat-label">Total Energy</p>
            <p class="stat-value">{{ formatEnergy(statistics.totalEnergy) }}</p>
            <p class="stat-range">{{ statistics.totalRecords }} records</p>
          </div>
        </div>
        
        <div class="stat-card">
          <div class="stat-icon">👥</div>
          <div class="stat-info">
            <p class="stat-label">People Count</p>
            <p class="stat-value">{{ currentPeopleCount }}</p>
            <p class="stat-range">Real-time dari kamera</p>
          </div>
        </div>
        
        <div class="stat-card">
          <div class="stat-icon">📁</div>
          <div class="stat-info">
            <p class="stat-label">Total Records</p>
            <p class="stat-value">{{ statistics.totalRecords }}</p>
            <p class="stat-range">Data points</p>
          </div>
        </div>
      </div>
      
      <div v-else class="no-data">
        <p>Tidak ada data untuk rentang tanggal yang dipilih</p>
      </div>
      
      <!-- Chart Controls -->
      <div v-if="statistics" class="chart-controls">
        <div class="control-group">
          <label>Interval:</label>
          <select v-model="chartInterval">
            <option value="hourly">Per Jam</option>
            <option value="daily">Per Hari</option>
            <option value="weekly">Per Minggu</option>
          </select>
        </div>
        
        <div class="control-group">
          <label>Metric:</label>
          <select v-model="selectedMetric">
            <option value="temperature">Temperature</option>
            <option value="humidity">Humidity</option>
            <option value="power">Power</option>
            <option value="peopleCount">People Count</option>
          </select>
        </div>
        
        <label class="comparison-toggle">
          <input type="checkbox" v-model="comparisonMode" />
          <span>Comparison Mode</span>
        </label>
      </div>
      
      <!-- Trend Chart -->
      <div v-if="chartData && chartData.labels.length > 0" class="chart-container">
        <Line :data="chartData" :options="chartOptions" />
      </div>
      
      <!-- Data Preview Table (Admin Only) -->
      <div v-if="isAdmin" class="preview-section">
        <h3 class="preview-title">📊 Preview Data Mentah (10 Terakhir)</h3>
        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Suhu (°C)</th>
                <th>Kelembaban (%)</th>
                <th>Tegangan (V)</th>
                <th>Arus (A)</th>
                <th>Daya (W)</th>
                <th>Orang</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, i) in previewData" :key="i">
                <td>{{ formatTimestamp(row.timestamp) }}</td>
                <td>{{ row.temperature?.toFixed(2) || '-' }}</td>
                <td>{{ row.humidity?.toFixed(2) || '-' }}</td>
                <td>{{ row.voltage?.toFixed(2) || '-' }}</td>
                <td>{{ row.current?.toFixed(2) || '-' }}</td>
                <td>{{ row.power?.toFixed(2) || '-' }}</td>
                <td>{{ row.peopleCount ?? '-' }}</td>
              </tr>
              <tr v-if="previewData.length === 0">
                <td colspan="7" class="empty-row" style="text-align:center; padding: 20px;">Tidak ada data untuk rentang tanggal ini</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Export Button (Admin Only) -->
      <div v-if="isAdmin" class="export-section">
        <button @click="handleExport" class="export-btn">
          📥 Export to CSV
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { Line } from 'vue-chartjs'
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler } from 'chart.js'
import { useHistoricalData } from '../composables/useHistoricalData'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler)

const props = defineProps({
  isDarkMode: Boolean,
  currentPeopleCount: {
    type: Number,
    default: 0
  },
  isAdmin: {
    type: Boolean,
    default: true
  }
})

const {
  historicalData,
  isLoading,
  loadHistoricalData,
  loadHistoricalDataForRange,
  getDataByDateRange,
  getAggregatedData,
  getAvailableDateRange,
  exportToCSV,
  getStatistics
} = useHistoricalData()

const isExpanded = ref(false)
const AUTO_REFRESH_INTERVAL = 30000
let refreshTimer = null
const lastSyncAt = ref(null)
const isRefreshing = ref(false)

function formatDateInput(date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function parseDateInput(value, endOfDay = false) {
  const [year, month, day] = String(value).split('-').map(Number)
  if (!year || !month || !day) return new Date()

  return endOfDay
    ? new Date(year, month - 1, day, 23, 59, 59, 999)
    : new Date(year, month - 1, day, 0, 0, 0, 0)
}

// Load data from Azure Storage when component mounts
onMounted(async () => {
  console.log('🔄 HistoricalAnalytics: Loading data from Azure Storage...')
  await refreshHistoricalData()
  refreshTimer = setInterval(() => {
    refreshHistoricalData(true)
  }, AUTO_REFRESH_INTERVAL)
  console.log('📊 HistoricalAnalytics: Data loaded, total records:', historicalData.value.length)
})

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
})

const today = formatDateInput(new Date())
const endDate = ref(today)
const startDate = ref(getDateDaysAgo(7))

const tempStartDate = ref(startDate.value)
const tempEndDate = ref(endDate.value)

const chartInterval = ref('daily')
const selectedMetric = ref('temperature')
const comparisonMode = ref(false)
const availableDateRange = computed(() => getAvailableDateRange())
const lastSyncText = computed(() => {
  if (!lastSyncAt.value) return 'Belum sinkron'

  return lastSyncAt.value.toLocaleString('id-ID', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
})

function getDateDaysAgo(days) {
  const date = new Date()
  date.setDate(date.getDate() - days)
  return formatDateInput(date)
}

async function applyFilter() {
  startDate.value = tempStartDate.value
  endDate.value = tempEndDate.value
  await refreshHistoricalData()
}

async function selectToday() {
  tempStartDate.value = today
  tempEndDate.value = today
  await applyFilter()
}

async function selectYesterday() {
  const yesterday = getDateDaysAgo(1)
  tempStartDate.value = yesterday
  tempEndDate.value = yesterday
  await applyFilter()
}

async function select7Days() {
  tempStartDate.value = getDateDaysAgo(7)
  tempEndDate.value = today
  await applyFilter()
}

async function select30Days() {
  tempStartDate.value = getDateDaysAgo(30)
  tempEndDate.value = today
  await applyFilter()
}

async function select90Days() {
  tempStartDate.value = getDateDaysAgo(90)
  tempEndDate.value = today
  await applyFilter()
}

async function selectAllTime() {
  await loadHistoricalData({ background: true })

  const range = getAvailableDateRange()
  if (!range) return

  tempStartDate.value = range.startDate
  tempEndDate.value = range.endDate
  await applyFilter()
}

async function refreshHistoricalData(background = false) {
  if (!background) {
    isRefreshing.value = true
  }

  try {
    const start = parseDateInput(startDate.value)
    const end = parseDateInput(endDate.value, true)

    await loadHistoricalDataForRange(start, end, { background })
    lastSyncAt.value = new Date()
  } finally {
    if (!background) {
      isRefreshing.value = false
    }
  }
}

const statistics = computed(() => {
  const start = parseDateInput(startDate.value)
  const end = parseDateInput(endDate.value, true)
  
  return getStatistics(start, end)
})

const chartData = computed(() => {
  const start = parseDateInput(startDate.value)
  const end = parseDateInput(endDate.value, true)
  
  const aggregated = getAggregatedData(start, end, chartInterval.value)
  
  if (aggregated.length === 0) return null
  
  const labels = aggregated.map(item => {
    if (chartInterval.value === 'hourly') {
      return item.timestamp.split(' ')[1]
    } else if (chartInterval.value === 'daily') {
      return item.timestamp
    } else {
      return item.timestamp
    }
  })
  
  const data = aggregated.map(item => item[selectedMetric.value])
  
  return {
    labels,
    datasets: [{
      label: getMetricLabel(selectedMetric.value),
      data,
      borderColor: '#06b6d4',
      backgroundColor: 'rgba(6, 182, 212, 0.1)',
      tension: 0.4,
      fill: true,
      pointRadius: 4,
      pointHoverRadius: 6
    }]
  }
})

const chartOptions = computed(() => ({
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
      mode: 'index',
      intersect: false
    }
  },
  scales: {
    x: {
      ticks: {
        color: props.isDarkMode ? '#9ca3af' : '#6b7280',
        maxRotation: 45,
        minRotation: 0
      },
      grid: {
        color: props.isDarkMode ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)'
      }
    },
    y: {
      ticks: {
        color: props.isDarkMode ? '#9ca3af' : '#6b7280'
      },
      grid: {
        color: props.isDarkMode ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)'
      }
    }
  }
}))

function getMetricLabel(metric) {
  const labels = {
    temperature: 'Temperature (°C)',
    humidity: 'Humidity (%)',
    power: 'Power (W)',
    peopleCount: 'People Count'
  }
  return labels[metric] || metric
}

function formatEnergy(wh) {
  if (wh === null || wh === undefined) return 'N/A'
  if (wh < 0) return '0 Wh' // Prevent negative values
  if (wh >= 1000) {
    return `${(wh / 1000).toFixed(2)} kWh`
  }
  return `${wh.toFixed(2)} Wh`
}

function handleExport() {
  const start = parseDateInput(startDate.value)
  const end = parseDateInput(endDate.value, true)
  
  exportToCSV(start, end)
}

const previewData = computed(() => {
  const start = parseDateInput(startDate.value)
  const end = parseDateInput(endDate.value, true)
  
  const rangeData = getDataByDateRange(start, end)
  if (!rangeData || rangeData.length === 0) return []
  return [...rangeData].reverse().slice(0, 10)
})

const formatTimestamp = (ts) => {
  if (!ts) return '-'
  const d = new Date(ts)
  return `${d.toLocaleDateString('id-ID')} ${d.toLocaleTimeString('id-ID')}`
}
</script>

<style scoped>
.historical-section {
  margin-top: 20px;
  padding: 20px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
}

.preview-section {
  margin-top: 30px;
  border-top: 1px solid rgba(0,0,0,0.1);
  padding-top: 20px;
}

.dark .preview-section {
  border-top-color: rgba(255,255,255,0.1);
}

.preview-title {
  font-size: 1.1rem;
  font-weight: 600;
  margin-bottom: 15px;
  color: #1f2937;
}

.dark .preview-title {
  color: #e5e7eb;
}

.table-wrap {
  width: 100%;
  overflow-x: auto;
  border-radius: 8px;
  border: 1px solid rgba(0,0,0,0.05);
  margin-bottom: 20px;
}

.dark .table-wrap {
  border-color: rgba(255,255,255,0.05);
  background: rgba(0,0,0,0.2);
}

.data-table { width: 100%; border-collapse: collapse; font-size: 0.88rem; white-space: nowrap; }
.data-table th {
  background: rgba(243,244,246,1);
  color: #374151;
  font-weight: 600;
  padding: 12px 16px;
  text-align: left;
}
.dark .data-table th { background: rgba(255,255,255,0.05); color: #e5e7eb; }
.data-table td {
  padding: 12px 16px;
  border-bottom: 1px solid rgba(0,0,0,0.05);
  color: #4b5563;
}
.dark .data-table td { border-bottom-color: rgba(255,255,255,0.05); color: #d1d5db; }
.data-table tbody tr:hover { background: rgba(6,182,212,0.04); }

.historical-section.dark {
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
  color: #06b6d4;
}

.toggle-btn {
  background: #06b6d4;
  color: white;
  border: none;
  border-radius: 6px;
  padding: 8px 16px;
  font-size: 1rem;
  cursor: pointer;
  transition: all 0.3s ease;
}

.toggle-btn:hover {
  background: #0891b2;
  transform: translateY(-2px);
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

.date-range-section {
  background: #f8fafc;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 20px;
}

.dark .date-range-section {
  background: #0f172a;
}

.sync-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.sync-meta {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.sync-label {
  font-size: 0.78rem;
  font-weight: 700;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.dark .sync-label {
  color: #94a3b8;
}

.sync-value {
  color: #0f172a;
  font-size: 0.95rem;
}

.dark .sync-value {
  color: #e2e8f0;
}

.btn-refresh {
  border: none;
  background: linear-gradient(135deg, #0ea5e9, #06b6d4);
  color: white;
  padding: 10px 16px;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 700;
  transition: transform 0.2s ease, box-shadow 0.2s ease, opacity 0.2s ease;
  box-shadow: 0 6px 14px rgba(14, 165, 233, 0.2);
}

.btn-refresh:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 10px 18px rgba(14, 165, 233, 0.25);
}

.btn-refresh:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.date-inputs {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 15px;
  margin-bottom: 15px;
}

.input-group {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.input-group label {
  font-weight: 600;
  color: #475569;
}

.dark .input-group label {
  color: #cbd5e1;
}

.input-group input {
  padding: 10px;
  border: 2px solid #e2e8f0;
  border-radius: 6px;
  font-size: 1rem;
  transition: all 0.3s ease;
}

.dark .input-group input {
  background: #1e293b;
  border-color: #334155;
  color: #e5e7eb;
}

.input-group input:focus {
  outline: none;
  border-color: #06b6d4;
}

.quick-selects {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.quick-selects button {
  padding: 8px 16px;
  background: white;
  border: 2px solid #06b6d4;
  color: #06b6d4;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.dark .quick-selects button {
  background: #1e293b;
  border-color: #0891b2;
  color: #06b6d4;
}

.quick-selects button:hover {
  background: #06b6d4;
  color: white;
}

.stats-summary-bar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 12px;
}

.stats-summary-chip {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-radius: 999px;
  background: rgba(6, 182, 212, 0.12);
  border: 1px solid rgba(6, 182, 212, 0.2);
  color: #0f172a;
}

.dark .stats-summary-chip {
  background: rgba(34, 211, 238, 0.12);
  border-color: rgba(34, 211, 238, 0.24);
  color: #e2e8f0;
}

.stats-summary-label {
  font-size: 0.82rem;
  font-weight: 600;
  color: #475569;
}

.dark .stats-summary-label {
  color: #cbd5e1;
}

.stats-summary-value {
  font-size: 1rem;
  font-weight: 800;
  color: #0891b2;
}

.dark .stats-summary-value {
  color: #67e8f9;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 15px;
  margin-bottom: 20px;
}

.stats-grid .stat-card:last-child {
  display: none;
}

.stat-card {
  background: linear-gradient(135deg, #06b6d4 0%, #0891b2 100%);
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 4px 6px rgba(6, 182, 212, 0.2);
  display: flex;
  gap: 15px;
  align-items: center;
  transition: all 0.3s ease;
}

.stat-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 8px 12px rgba(6, 182, 212, 0.3);
}

.stat-icon {
  font-size: 2.5rem;
}

.stat-info {
  flex: 1;
}

.stat-label {
  margin: 0;
  color: rgba(255, 255, 255, 0.9);
  font-size: 0.9rem;
  font-weight: 500;
}

.stat-value {
  margin: 5px 0;
  color: white;
  font-size: 1.5rem;
  font-weight: 700;
}

.stat-range {
  margin: 0;
  color: rgba(255, 255, 255, 0.8);
  font-size: 0.85rem;
}

.no-data {
  text-align: center;
  padding: 40px;
  color: #94a3b8;
  font-size: 1.1rem;
}

.chart-controls {
  display: flex;
  gap: 20px;
  margin-bottom: 20px;
  flex-wrap: wrap;
  align-items: center;
}

.control-group {
  display: flex;
  align-items: center;
  gap: 10px;
}

.control-group label {
  font-weight: 600;
  color: #475569;
}

.dark .control-group label {
  color: #cbd5e1;
}

.control-group select {
  padding: 8px 12px;
  border: 2px solid #e2e8f0;
  border-radius: 6px;
  font-size: 1rem;
  cursor: pointer;
  transition: all 0.3s ease;
}

.dark .control-group select {
  background: #1e293b;
  border-color: #334155;
  color: #e5e7eb;
}

.control-group select:focus {
  outline: none;
  border-color: #06b6d4;
}

.comparison-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  color: #475569;
  cursor: pointer;
  user-select: none;
}

.dark .comparison-toggle {
  color: #cbd5e1;
}

.comparison-toggle input[type="checkbox"] {
  width: 20px;
  height: 20px;
  cursor: pointer;
}

.chart-container {
  height: 400px;
  margin-bottom: 20px;
  padding: 15px;
  background: #f8fafc;
  border-radius: 8px;
}

.dark .chart-container {
  background: #0f172a;
}

.export-section {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}

.export-btn {
  padding: 12px 30px;
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 1.1rem;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 4px 6px rgba(16, 185, 129, 0.3);
  transition: all 0.3s ease;
}

.export-btn:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 12px rgba(16, 185, 129, 0.4);
}

@media (max-width: 1280px) {
  .stats-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 1024px) {
  .stats-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .historical-section {
    padding: 15px;
  }
  
  .section-header h2 {
    font-size: 1.2rem;
  }

  .stats-summary-bar {
    justify-content: flex-start;
  }
  
  .stats-grid {
    grid-template-columns: 1fr;
  }
  
  .chart-controls {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .chart-container {
    height: 300px;
  }
}
.btn-apply {
  background: var(--primary, #06b6d4);
  color: white;
  border: none;
  padding: 10px 16px;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.2s;
  height: 42px; /* Matches input height roughly */
  display: flex;
  align-items: center;
  gap: 6px;
}
.btn-apply:hover {
  background: var(--primary-dark, #0891b2);
  transform: translateY(-1px);
}
.action-group {
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
}
</style>
