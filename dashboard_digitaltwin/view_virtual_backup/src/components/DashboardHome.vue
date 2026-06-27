<template>
  <div class="dashboard">
    <!-- Full-Screen 3D Background -->
    <div class="viewer-3d">
      <CesiumViewer
        v-if="current3DView === 'cesium'"
        :sensor-data="sensorData"
        :is-dark-mode="isDarkMode"
        :show-info-card="false"
        @toggle-indoor="current3DView = 'babylon'"
        @switch-to-3d="current3DView = 'babylon'"
      />
      <DigitalTwinBabylon
        v-else
        :sensor-data="sensorData"
        :people-count="peopleCount"
        :is-dark-mode="isDarkMode"
      />
    </div>

    <!-- ═══ LEFT SIDEBAR ═══ -->
    <aside class="sidebar sidebar-left">
      <div class="main-card">
        <!-- Header -->
        <div class="card-header">
          <div class="header-row">
            <div class="logo-section">
              <img src="/logo.png" alt="Logo" class="brand-logo" />
              <span class="brand">TWINSPACE</span>
            </div>
            <span class="status-badge" :class="isConnected ? 'online' : 'offline'">
              <span class="dot"></span>
              {{ isConnected ? 'EDGE' : 'OFFLINE' }}
            </span>
          </div>
        </div>

        <!-- PILAR 1: EDGE-CLOUD METRICS -->
        <div class="section-header">
          <span>EDGE-CLOUD ARCHITECTURE</span>
        </div>
        <div class="arch-metrics">
          <div class="metric-row">
            <span class="metric-label">Edge Latency</span>
            <span class="metric-value green">{{ validationMetrics.edgeLatencyMs.toFixed(2) }} ms</span>
          </div>
          <div class="metric-row">
            <span class="metric-label">Cloud Latency</span>
            <span class="metric-value blue">{{ validationMetrics.cloudLatencyMs }} ms</span>
          </div>
          <div class="metric-row">
            <span class="metric-label">SLA (<2ms)</span>
            <span class="metric-value green">PASS ✓</span>
          </div>
          <div class="metric-divider"></div>
          <div class="routing-bar">
            <div class="routing-segment edge" :style="{ width: validationMetrics.edgeRate + '%' }">
              {{ validationMetrics.edgeRate }}% Edge
            </div>
            <div class="routing-segment cloud" :style="{ width: validationMetrics.anomalyRate + '%' }">
              {{ validationMetrics.anomalyRate }}% Cloud
            </div>
          </div>
        </div>

        <!-- PILAR 2: FUSION INDICATOR -->
        <div class="fusion-section">
          <div class="section-header">
            <span>MULTI-MODAL FUSION</span>
          </div>
          <div class="fusion-grid">
            <div class="fusion-source numeric">
              <div class="fusion-icon">📊</div>
              <div class="fusion-label">Numeric</div>
              <div class="fusion-desc">ESP32</div>
            </div>
            <div class="fusion-center">+</div>
            <div class="fusion-source visual">
              <div class="fusion-icon">👁</div>
              <div class="fusion-label">Visual</div>
              <div class="fusion-desc">YOLO</div>
            </div>
          </div>
          <div class="fusion-result">
            <span class="fusion-tag">FUSED → 18 Fitur</span>
          </div>
        </div>

        <!-- IoT SENSOR DATA -->
        <div class="section-header">
          <span>SENSOR DATA</span>
        </div>
        <div class="sensor-list">
          <div class="sensor-item">
            <span class="sensor-label">TEMP</span>
            <span class="sensor-value temp">{{ sensorData.temperature?.toFixed(1) || '--' }}°C</span>
          </div>
          <div class="sensor-item">
            <span class="sensor-label">HUMID</span>
            <span class="sensor-value humid">{{ sensorData.humidity?.toFixed(1) || '--' }}%</span>
          </div>
          <div class="sensor-item">
            <span class="sensor-label">POWER</span>
            <span class="sensor-value power">{{ sensorData.power?.toFixed(0) || '--' }}W</span>
          </div>
          <div class="sensor-item">
            <span class="sensor-label">VOLT</span>
            <span class="sensor-value voltage">{{ sensorData.voltage?.toFixed(0) || '--' }}V</span>
          </div>
        </div>

        <!-- AC RECOMMENDATION -->
        <div class="section-header">
          <span>AC TARGET</span>
        </div>
        <div class="ac-target-card">
          <span class="ac-temp-value">{{ acRecommendedTemp }}°C</span>
          <span class="ac-label">Rekomendasi ML</span>
        </div>

        <!-- STATS -->
        <div class="stats-list">
          <div class="stat-item">
            <span class="stat-label">PEOPLE</span>
            <span class="stat-value">{{ peopleCount || sensorData.peopleCount || 0 }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">TOTAL RECORDS</span>
            <span class="stat-value" style="font-size:11px">{{ validationMetrics.totalRecords }}</span>
          </div>
        </div>
      </div>
    </aside>

    <!-- ═══ RIGHT SIDEBAR ═══ -->
    <aside class="sidebar sidebar-right">
      <div class="main-card">
        <!-- Time Header -->
        <div class="card-header">
          <div class="time-header">
            <span class="time-display">{{ formattedTime }}</span>
            <span class="data-range-label">{{ validationMetrics.dataPeriod }}</span>
          </div>
        </div>

        <!-- 3D VIEW -->
        <div class="section-header">
          <span>3D VIEW</span>
        </div>
        <div class="view-toggle">
          <button
            :class="['view-btn', { active: current3DView === 'cesium' }]"
            @click="current3DView = 'cesium'"
          >
            Map
          </button>
          <button
            :class="['view-btn', { active: current3DView === 'babylon' }]"
            @click="current3DView = 'babylon'"
          >
            Indoor
          </button>
        </div>

        <!-- FEATURES -->
        <div class="section-header">
          <span>FEATURES</span>
        </div>
        <div class="menu-grid">
          <button class="menu-btn" @click="selectSection('energy')">
            <span class="menu-icon">⚡</span>
            <span>Energy</span>
          </button>
          <button class="menu-btn" @click="selectSection('analytics')">
            <span class="menu-icon">📈</span>
            <span>Analytics</span>
          </button>
          <button class="menu-btn" @click="selectSection('camera')">
            <span class="menu-icon">📷</span>
            <span>Vision</span>
          </button>
          <button class="menu-btn" @click="selectSection('settings')">
            <span class="menu-icon">⚙️</span>
            <span>Settings</span>
          </button>
        </div>

        <!-- THEME -->
        <button class="theme-btn" @click="handleThemeToggle">
          <svg v-if="isDarkMode" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="5"/>
            <line x1="12" y1="1" x2="12" y2="3"/>
          </svg>
          <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
          </svg>
          <span>{{ isDarkMode ? 'Light Mode' : 'Dark Mode' }}</span>
        </button>

        <!-- Footer -->
        <div class="card-footer">
          <span>AMIKOM — Digital Twin Lab 2026</span>
        </div>
      </div>
    </aside>

    <!-- ═══ MODAL ═══ -->
    <Teleport to="body">
      <div v-if="activeSection !== 'overview'" class="modal-overlay" @click.self="activeSection = 'overview'">
        <div class="modal-content">
          <button class="modal-close" @click="activeSection = 'overview'">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>

          <div v-if="activeSection === 'energy'" class="modal-body">
            <h2>PILAR 4 — PREDIKSI ENERGI</h2>

            <div class="energy-layout">
              <!-- R² Comparison -->
              <div class="comparison-card">
                <h3>Model Accuracy Comparison</h3>

                <div class="r2-bar-group">
                  <div class="r2-bar-label">
                    <span>Online SGD (4 fitur)</span>
                    <span class="r2-value blue">{{ validationMetrics.onlineR2 }}</span>
                  </div>
                  <div class="r2-track">
                    <div class="r2-fill online" :style="{ width: (validationMetrics.onlineR2 / validationMetrics.batchRR2 * 100) + '%' }"></div>
                  </div>
                </div>

                <div class="r2-bar-group">
                  <div class="r2-bar-label">
                    <span>Batch RF (18 fitur) ★</span>
                    <span class="r2-value green">{{ validationMetrics.batchRR2 }}</span>
                  </div>
                  <div class="r2-track">
                    <div class="r2-fill batch" :style="{ width: (validationMetrics.batchRR2 * 100) + '%' }"></div>
                  </div>
                </div>

                <div class="r2-bar-group">
                  <div class="r2-bar-label">
                    <span>Batch LR (18 fitur)</span>
                    <span class="r2-value blue">{{ validationMetrics.batchLR2 }}</span>
                  </div>
                  <div class="r2-track">
                    <div class="r2-fill lr" :style="{ width: (validationMetrics.batchLR2 * 100) + '%' }"></div>
                  </div>
                </div>

                <div class="improvement-badge">
                  Improvment: +{{ validationMetrics.r2Improvement }} (SGD → RF)
                </div>

                <div class="metric-summary">
                  <div class="metric-cell">
                    <span class="cell-label">RMSE</span>
                    <span class="cell-value">0.2115 W</span>
                  </div>
                  <div class="metric-cell">
                    <span class="cell-label">MAE</span>
                    <span class="cell-value">0.1530 W</span>
                  </div>
                  <div class="metric-cell">
                    <span class="cell-label">MAPE</span>
                    <span class="cell-value">0.42%</span>
                  </div>
                  <div class="metric-cell">
                    <span class="cell-label">Features</span>
                    <span class="cell-value">18</span>
                  </div>
                </div>
              </div>

              <!-- Energy Chart -->
              <div class="chart-card">
                <h3>Power Consumption (Live Simulation)</h3>
                <canvas ref="powerChartCanvas" width="400" height="300"></canvas>
              </div>
            </div>
          </div>

          <div v-if="activeSection === 'analytics'" class="modal-body">
            <h2>HISTORICAL ANALYTICS</h2>
            <HistoricalAnalytics :is-dark-mode="isDarkMode" :current-people-count="peopleCount" :is-admin="false" />
          </div>

          <div v-if="activeSection === 'camera'" class="modal-body">
            <h2>PILAR 2 — VISION SYSTEM (YOLO)</h2>
            <div class="vision-info">
              <div class="vision-card">
                <h3>People Detection</h3>
                <div class="people-display">{{ peopleCount }} orang</div>
                <p class="vision-desc">
                  YOLO v3-tiny digunakan untuk mendeteksi jumlah orang dalam ruangan.
                  Output ini merupakan modalitas visual yang digabungkan dengan data numerik
                  dari ESP32 (DHT11, ZMPT101B, SCT013) untuk membentuk fusi multimodal.
                </p>
              </div>
              <div class="vision-card">
                <h3>YOLO Model Info</h3>
                <table class="vision-table">
                  <tbody>
                    <tr><td>Model</td><td>YOLO v3-tiny</td></tr>
                    <tr><td>Class</td><td>COCO (person)</td></tr>
                    <tr><td>Modalitas</td><td>Visual</td></tr>
                    <tr><td>Fusion Target</td><td>jumlah_orang (fitur ke-5)</td></tr>
                    <tr><td>Total Fitur Fusi</td><td>18 (5 base + 2 interaksi + 3 time + 5 time_period + 3 rolling)</td></tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          <div v-if="activeSection === 'settings'" class="modal-body">
            <h2>SETTINGS</h2>
            <div class="settings-grid">
              <div class="settings-card">
                <h4>Research Info</h4>
                <p style="font-size:0.75rem;color:#94a3b8;line-height:1.6">
                  <strong>Judul:</strong><br>
                  Strategi Arsitektur Edge-Cloud Berbasis Fusi Data Multimodal pada Ekosistem Digital Twin Web-3D untuk Prediksi Energi Bangunan Cerdas
                </p>
                <p style="font-size:0.75rem;color:#94a3b8;margin-top:8px">
                  <strong>Dataset:</strong> 2,027,520 records (sensor_data.csv)<br>
                  <strong>Periode:</strong> 91 hari (Feb–May 2026)<br>
                  <strong>Device:</strong> RASPBERRY_PI_GATEWAY_001
                </p>
              </div>
              <div class="settings-card">
                <h4>Display</h4>
                <button class="setting-btn" @click="handleThemeToggle">
                  {{ isDarkMode ? 'Light Mode' : 'Dark Mode' }}
                </button>
              </div>
              <div class="settings-card">
                <h4>System</h4>
                <p>Status: <span :class="isConnected ? 'online' : 'offline'">{{ isConnected ? 'Edge Connected' : 'Offline' }}</span></p>
                <p>Data Source: <span>CSS-derived (5000 rows sampled)</span></p>
                <p>3D View: <span>{{ current3DView === 'cesium' ? 'Cesium Map' : 'Babylon.js Indoor' }}</span></p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { computed, defineAsyncComponent, onMounted, onUnmounted, ref, watch, nextTick } from 'vue'

// Lazy load heavy components with defineAsyncComponent
const CesiumViewer = defineAsyncComponent(() => import('./CesiumViewer.vue'))
const DigitalTwinBabylon = defineAsyncComponent(() => import('./DigitalTwin3D_Babylon.vue'))
const HistoricalAnalytics = defineAsyncComponent(() => import('./HistoricalAnalytics.vue'))

import { useDummyData } from '../composables/useDummyData'

const props = defineProps({
  isDarkMode: { type: Boolean, default: false }
})

const emit = defineEmits(['toggle-theme'])

const activeSection = ref('overview')
const current3DView = ref('babylon')

const { isConnected, sensorData, validationMetrics, startPlayback } = useDummyData()

const peopleCount = ref(0)
const currentTime = ref(new Date())
let timeInterval = null

// Power history for chart
const powerHistory = ref([])
const maxHistoryPoints = 60
const powerChartCanvas = ref(null)

const displayName = computed(() => 'TwinSpace Demo')
const formattedTime = computed(() => {
  return currentTime.value.toLocaleTimeString('en-ID', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    timeZone: 'Asia/Jakarta'
  })
})

const acRecommendedTemp = computed(() => {
  const temp = sensorData.value?.temperature
  if (!temp) return '--'
  // Simple ML-like AC recommendation
  let base = 25
  if (temp > 28) base = 22
  else if (temp > 26) base = 23
  else if (temp < 22) base = 26
  else if (temp > 24) base = 24
  return base
})

const handleThemeToggle = () => emit('toggle-theme')
const selectSection = (id) => { activeSection.value = id }

// Watch sensor data for chart updates
watch(
  () => sensorData.value?.power,
  (newPower) => {
    if (typeof newPower === 'number') {
      const now = new Date()
      powerHistory.value.push({ time: now, power: newPower })
      if (powerHistory.value.length > maxHistoryPoints) {
        powerHistory.value.shift()
      }
      // Sync people count
      peopleCount.value = sensorData.value.peopleCount || 0
    }
  }
)

onMounted(async () => {
  startPlayback()
  timeInterval = setInterval(() => { currentTime.value = new Date() }, 1000)

  // Wait for data to load before drawing chart
  await nextTick()
  drawPowerChart()
})

onUnmounted(() => {
  clearInterval(timeInterval)
})

// Draw simple canvas chart
const drawPowerChart = () => {
  if (!powerChartCanvas.value || powerHistory.value.length < 2) return

  const canvas = powerChartCanvas.value
  const ctx = canvas.getContext('2d')
  const w = canvas.width
  const h = canvas.height

  ctx.clearRect(0, 0, w, h)

  // Background
  ctx.fillStyle = 'rgba(0, 0, 0, 0.3)'
  ctx.fillRect(0, 0, w, h)

  const data = powerHistory.value.map(p => p.power)
  const maxVal = Math.max(...data) * 1.2
  const minVal = Math.min(...data) * 0.8
  const range = maxVal - minVal || 1

  // Grid
  ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)'
  ctx.lineWidth = 1
  for (let y = 0; y < h; y += 40) {
    ctx.beginPath()
    ctx.moveTo(0, y)
    ctx.lineTo(w, y)
    ctx.stroke()
  }

  // Labels
  ctx.fillStyle = '#64748b'
  ctx.font = '10px IBM Plex Sans'
  ctx.fillText(`${maxVal.toFixed(0)}W`, 4, 14)
  ctx.fillText(`${minVal.toFixed(0)}W`, 4, h - 4)

  // Line
  ctx.beginPath()
  ctx.strokeStyle = '#22c55e'
  ctx.lineWidth = 2

  data.forEach((val, i) => {
    const x = (i / (data.length - 1)) * (w - 20) + 10
    const y = h - 20 - ((val - minVal) / range) * (h - 40)

    if (i === 0) ctx.moveTo(x, y)
    else ctx.lineTo(x, y)
  })
  ctx.stroke()

  // Fill area
  ctx.lineTo((data.length - 1) / (data.length - 1) * (w - 20) + 10, h - 20)
  ctx.lineTo(10, h - 20)
  ctx.closePath()
  ctx.fillStyle = 'rgba(34, 197, 94, 0.15)'
  ctx.fill()

  // Average line
  const avg = data.reduce((a, b) => a + b, 0) / data.length
  const avgY = h - 20 - ((avg - minVal) / range) * (h - 40)
  ctx.beginPath()
  ctx.strokeStyle = 'rgba(251, 191, 36, 0.5)'
  ctx.lineWidth = 1
  ctx.setLineDash([4, 4])
  ctx.moveTo(10, avgY)
  ctx.lineTo(w - 10, avgY)
  ctx.stroke()
  ctx.setLineDash([])

  // X-axis label
  ctx.fillStyle = '#64748b'
  ctx.font = '10px IBM Plex Sans'
  ctx.fillText(`${powerHistory.value.length} points`, w - 80, h - 4)
}

// Redraw chart when data changes
watch(powerHistory, drawPowerChart, { deep: true })
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=Sora:wght@500;600;700;800&display=swap');

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

.dashboard {
  --accent: #00d4ff;
  --bg: #0a0f1a;
  --panel: rgba(10, 15, 30, 0.95);
  --panel-solid: #0d1117;
  --border: rgba(255, 255, 255, 0.1);
  --text: #f8fafc;
  --text-2: #94a3b8;
  --text-3: #64748b;
  --success: #22c55e;
  --danger: #ef4444;

  min-height: 100vh;
  background: var(--bg);
  color: var(--text);
  font-family: 'IBM Plex Sans', sans-serif;
  overflow: hidden;
}

/* ═══ VIEWER ═══ */
.viewer-3d {
  position: fixed !important;
  top: 0 !important;
  left: 0 !important;
  right: 0 !important;
  bottom: 0 !important;
  width: 100vw !important;
  height: 100vh !important;
  z-index: 1;
}

/* ═══ SIDEBARS ═══ */
.sidebar {
  position: fixed;
  top: 0;
  bottom: 0;
  width: 240px;
  z-index: 100;
}

.sidebar-left { left: 0; }
.sidebar-right { right: 0; }

.main-card {
  background: var(--panel);
  border: none;
  border-radius: 0;
  padding: 16px 12px;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 0;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: var(--text-3) transparent;
}

/* Card Header */
.card-header {
  padding-bottom: 10px;
  margin-bottom: 10px;
  border-bottom: 1px solid var(--border);
}

.header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.logo-section {
  display: flex;
  align-items: center;
  gap: 6px;
}

.brand-logo {
  height: 28px;
  width: auto;
  object-fit: contain;
}

.brand {
  font-family: 'Sora', sans-serif;
  font-size: 13px;
  font-weight: 700;
  color: var(--text);
}

.status-badge {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  border-radius: 10px;
  font-size: 9px;
  font-weight: 600;
}

.status-badge.online {
  background: rgba(34, 197, 94, 0.15);
  color: var(--success);
}

.status-badge.offline {
  background: rgba(239, 68, 68, 0.15);
  color: var(--danger);
}

.status-badge .dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: currentColor;
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.time-header {
  text-align: center;
}

.time-display {
  font-family: 'Sora', sans-serif;
  font-size: 24px;
  font-weight: 600;
  color: var(--text);
  display: block;
}

.data-range-label {
  font-size: 9px;
  color: var(--text-3);
  display: block;
  margin-top: 2px;
}

/* Section Header */
.section-header {
  padding: 10px 0 8px 0;
  margin-bottom: 8px;
  border-bottom: 1px solid var(--border);
}

.section-header span {
  font-family: 'Sora', sans-serif;
  font-size: 10px;
  font-weight: 600;
  color: var(--accent);
  letter-spacing: 0.05em;
}

/* ═══ PILAR 1: ARCHITECTURE METRICS ═══ */
.arch-metrics {
  margin-bottom: 10px;
}

.metric-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 5px 8px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 4px;
  margin-bottom: 3px;
}

.metric-label {
  font-size: 10px;
  color: var(--text-3);
  font-weight: 500;
}

.metric-value {
  font-family: 'Sora', sans-serif;
  font-size: 11px;
  font-weight: 600;
}

.metric-value.green { color: var(--success); }
.metric-value.blue { color: var(--accent); }

.metric-divider {
  height: 1px;
  background: var(--border);
  margin: 8px 0;
}

.routing-bar {
  display: flex;
  border-radius: 4px;
  overflow: hidden;
  height: 24px;
}

.routing-segment {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 8px;
  font-weight: 600;
  color: white;
  font-family: 'Sora', sans-serif;
}

.routing-segment.edge {
  background: var(--success);
}

.routing-segment.cloud {
  background: var(--danger);
}

/* ═══ PILAR 2: FUSION INDICATOR ═══ */
.fusion-section {
  margin-bottom: 10px;
}

.fusion-grid {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  margin-bottom: 6px;
}

.fusion-source {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 8px 6px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border);
  border-radius: 6px;
  flex: 1;
}

.fusion-source.numeric {
  border-color: rgba(0, 212, 255, 0.3);
}

.fusion-source.visual {
  border-color: rgba(168, 85, 247, 0.3);
}

.fusion-icon {
  font-size: 18px;
  line-height: 1;
}

.fusion-label {
  font-size: 9px;
  font-weight: 600;
  color: var(--text-2);
  margin-top: 4px;
}

.fusion-desc {
  font-size: 8px;
  color: var(--text-3);
}

.fusion-center {
  font-size: 14px;
  font-weight: 700;
  color: var(--accent);
}

.fusion-result {
  text-align: center;
}

.fusion-tag {
  display: inline-block;
  padding: 4px 10px;
  background: linear-gradient(135deg, rgba(0, 212, 255, 0.15), rgba(168, 85, 247, 0.15));
  border: 1px solid rgba(0, 212, 255, 0.3);
  border-radius: 12px;
  font-size: 9px;
  font-weight: 600;
  color: var(--accent);
  font-family: 'Sora', sans-serif;
}

/* Sensor List */
.sensor-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 12px;
}

.sensor-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 10px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 6px;
}

.sensor-label {
  font-size: 11px;
  color: var(--text-3);
  font-weight: 500;
}

.sensor-value {
  font-family: 'Sora', sans-serif;
  font-size: 14px;
  font-weight: 600;
}

.sensor-value.temp { color: #00d4ff; }
.sensor-value.humid { color: #a855f7; }
.sensor-value.power { color: #22c55e; }
.sensor-value.voltage { color: #f59e0b; }

/* AC Target Card */
.ac-target-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 16px 12px;
  background: linear-gradient(135deg, rgba(0, 212, 255, 0.15) 0%, rgba(168, 85, 247, 0.15) 100%);
  border: 1px solid rgba(0, 212, 255, 0.3);
  border-radius: 10px;
  margin-bottom: 12px;
}

.ac-temp-value {
  font-family: 'Sora', sans-serif;
  font-size: 28px;
  font-weight: 700;
  color: #00d4ff;
}

.ac-label {
  font-size: 10px;
  color: var(--text-3);
}

/* Stats List */
.stats-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 10px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 6px;
}

.stat-label {
  font-size: 11px;
  color: var(--text-3);
  font-weight: 500;
}

.stat-value {
  font-family: 'Sora', sans-serif;
  font-size: 14px;
  font-weight: 600;
  color: var(--accent);
}

/* View Toggle */
.view-toggle {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.view-btn {
  flex: 1;
  padding: 10px 8px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border);
  border-radius: 8px;
  color: var(--text-2);
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: 11px;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.2s, border-color 0.2s, color 0.2s;
}

.view-btn:hover {
  background: rgba(255, 255, 255, 0.08);
}

.view-btn.active {
  background: rgba(0, 212, 255, 0.15);
  border-color: var(--accent);
  color: var(--accent);
  font-weight: 600;
}

/* Menu Grid */
.menu-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-bottom: 12px;
}

.menu-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 12px 8px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border);
  border-radius: 8px;
  color: var(--text-2);
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.2s, border-color 0.2s, color 0.2s;
}

.menu-btn:hover {
  background: rgba(0, 212, 255, 0.15);
  border-color: var(--accent);
  color: var(--accent);
}

.menu-icon {
  font-size: 16px;
}

/* Theme Button */
.theme-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
  padding: 12px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border);
  border-radius: 8px;
  color: var(--text-2);
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: 12px;
  cursor: pointer;
  transition: background-color 0.2s, border-color 0.2s, color 0.2s;
  margin-bottom: 12px;
}

.theme-btn:hover {
  border-color: var(--accent);
  color: var(--accent);
}

.theme-btn svg {
  width: 18px;
  height: 18px;
}

/* Footer */
.card-footer {
  text-align: center;
  padding-top: 12px;
  margin-top: auto;
  border-top: 1px solid var(--border);
}

.card-footer span {
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: 9px;
  color: var(--text-3);
}

/* ═══ MODAL ═══ */
.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 200;
  background: rgba(0, 0, 0, 0.85);
  backdrop-filter: blur(5px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 30px;
}

.modal-content {
  position: relative;
  width: 100%;
  max-width: 1000px;
  max-height: calc(100vh - 60px);
  background: var(--panel-solid);
  border: 1px solid var(--border);
  border-radius: 12px;
  overflow: hidden;
}

.modal-close {
  position: absolute;
  top: 12px;
  right: 12px;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.1);
  border: none;
  border-radius: 6px;
  color: var(--text-2);
  cursor: pointer;
  z-index: 10;
}

.modal-close:hover {
  background: var(--danger);
  color: #fff;
}

.modal-close svg {
  width: 16px;
  height: 16px;
}

.modal-body {
  padding: 30px;
  max-height: calc(100vh - 100px);
  overflow-y: auto;
}

.modal-body h2 {
  font-family: 'Sora', sans-serif;
  font-size: 1.2rem;
  font-weight: 700;
  margin-bottom: 20px;
  color: var(--accent);
}

/* Energy Layout */
.energy-layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.comparison-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 16px;
}

.comparison-card h3 {
  font-family: 'Sora', sans-serif;
  font-size: 0.85rem;
  color: var(--text-2);
  margin-bottom: 16px;
}

.chart-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 16px;
}

.chart-card h3 {
  font-family: 'Sora', sans-serif;
  font-size: 0.85rem;
  color: var(--text-2);
  margin-bottom: 12px;
}

.chart-card canvas {
  border-radius: 6px;
  border: 1px solid var(--border);
}

/* R2 Bars */
.r2-bar-group {
  margin-bottom: 14px;
}

.r2-bar-label {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.r2-bar-label span:first-child {
  font-size: 11px;
  color: var(--text-2);
}

.r2-value {
  font-family: 'Sora', sans-serif;
  font-size: 12px;
  font-weight: 700;
}

.r2-value.green { color: var(--success); }
.r2-value.blue { color: var(--accent); }

.r2-track {
  height: 12px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 6px;
  overflow: hidden;
}

.r2-fill {
  height: 100%;
  border-radius: 6px;
  transition: width 0.5s ease;
}

.r2-fill.online { background: var(--accent); }
.r2-fill.batch { background: var(--success); }
.r2-fill.lr { background: #a855f7; }

.improvement-badge {
  display: inline-block;
  padding: 4px 12px;
  background: rgba(34, 197, 94, 0.15);
  border: 1px solid rgba(34, 197, 94, 0.3);
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
  color: var(--success);
  font-family: 'Sora', sans-serif;
  margin: 12px 0;
}

.metric-summary {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  margin-top: 16px;
}

.metric-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 10px 6px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 6px;
  border: 1px solid var(--border);
}

.cell-label {
  font-size: 9px;
  color: var(--text-3);
  font-weight: 500;
  text-transform: uppercase;
}

.cell-value {
  font-family: 'Sora', sans-serif;
  font-size: 14px;
  font-weight: 700;
  color: var(--success);
  margin-top: 2px;
}

/* Vision Info */
.vision-info {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.vision-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 16px;
}

.vision-card h3 {
  font-family: 'Sora', sans-serif;
  font-size: 0.85rem;
  color: var(--accent);
  margin-bottom: 12px;
}

.people-display {
  font-family: 'Sora', sans-serif;
  font-size: 2.5rem;
  font-weight: 700;
  color: var(--accent);
  text-align: center;
  margin: 16px 0;
}

.vision-desc {
  font-size: 0.8rem;
  color: var(--text-2);
  line-height: 1.6;
}

.vision-table {
  width: 100%;
  font-size: 0.8rem;
  color: var(--text-2);
  border-collapse: collapse;
}

.vision-table td {
  padding: 6px 0;
  border-bottom: 1px solid var(--border);
}

.vision-table td:first-child {
  color: var(--text-3);
  font-weight: 500;
  width: 120px;
}

/* Settings Grid */
.settings-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.settings-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 14px;
}

.settings-card h4 {
  font-family: 'Sora', sans-serif;
  font-size: 0.65rem;
  color: var(--accent);
  margin-bottom: 10px;
}

.settings-card p {
  font-size: 0.8rem;
  color: var(--text-2);
  margin-bottom: 4px;
}

.setting-btn {
  width: 100%;
  padding: 8px;
  background: var(--accent);
  border: none;
  border-radius: 4px;
  color: #000;
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: 0.75rem;
  font-weight: 600;
  cursor: pointer;
}

/* Responsive */
@media (max-width: 1200px) {
  .energy-layout,
  .vision-info {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .sidebar {
    display: none;
  }

  .modal-overlay {
    padding: 16px;
  }

  .modal-body {
    padding: 20px;
  }

  .settings-grid {
    grid-template-columns: 1fr;
  }
}
</style>
