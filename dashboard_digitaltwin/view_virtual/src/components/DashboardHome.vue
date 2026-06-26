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
              {{ isConnected ? 'ONLINE' : 'OFFLINE' }}
            </span>
          </div>
        </div>

        <!-- IOT SENSOR -->
        <div class="section-header">
          <span>IOT SENSOR</span>
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
          <span class="ac-label">Rekomendasi</span>
        </div>

        <!-- STATS -->
        <div class="section-header">
          <span>STATS</span>
        </div>
        <div class="stats-list">
          <div class="stat-item">
            <span class="stat-label">PEOPLE</span>
            <span class="stat-value">{{ peopleCount || sensorData.peopleCount || 0 }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">ENERGY</span>
            <span class="stat-value">{{ totalEnergyWh.toFixed(1) }}Wh</span>
          </div>
        </div>

      </div>
    </aside>

    <!-- ═══ RIGHT SIDEBAR ═══ -->
    <aside class="sidebar sidebar-right">
      <div class="main-card">
        <!-- Time Header -->
        <div class="card-header">
          <span class="time-display">{{ formattedTime }}</span>
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
            Energy
          </button>
          <button class="menu-btn" @click="selectSection('analytics')">
            Analytics
          </button>
          <button class="menu-btn" @click="selectSection('camera')">
            Vision
          </button>
          <button class="menu-btn" @click="selectSection('settings')">
            Settings
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
          <span>-7.7226, 110.5190</span>
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
            <h2>ENERGY MANAGEMENT</h2>
            <EnergyManagement :is-dark-mode="isDarkMode" :current-power="sensorData.power" :is-admin="false" />
          </div>

          <div v-if="activeSection === 'analytics'" class="modal-body">
            <h2>HISTORICAL ANALYTICS</h2>
            <HistoricalAnalytics :is-dark-mode="isDarkMode" :current-people-count="peopleCount" :is-admin="false" />
          </div>

          <div v-if="activeSection === 'camera'" class="modal-body">
            <h2>VISION SYSTEM</h2>
            <CameraStream :is-dark-mode="isDarkMode" @people-count-update="handlePeopleCountUpdate" />
          </div>

          <div v-if="activeSection === 'settings'" class="modal-body">
            <h2>SETTINGS</h2>
            <div class="settings-grid">
              <div class="settings-card">
                <h4>Profile</h4>
                <div class="profile-row">
                  <img v-if="user?.photoURL" :src="user.photoURL" class="profile-avatar" referrerpolicy="no-referrer"/>
                  <div v-else class="profile-avatar fallback">{{ userInitials }}</div>
                  <div>
                    <p class="profile-name">{{ displayName }}</p>
                    <p class="profile-email">{{ user?.email || 'Operator' }}</p>
                  </div>
                </div>
              </div>
              <div class="settings-card">
                <h4>Display</h4>
                <button class="setting-btn" @click="handleThemeToggle">
                  {{ isDarkMode ? 'Light Mode' : 'Dark Mode' }}
                </button>
              </div>
              <div class="settings-card">
                <h4>System</h4>
                <p>Status: <span :class="isConnected ? 'online' : 'offline'">{{ isConnected ? 'Online' : 'Offline' }}</span></p>
                <p>Energy: {{ totalEnergyWh.toFixed(2) }} Wh</p>
              </div>
            </div>
            <button class="logout-btn" @click="handleLogout">LOGOUT</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch, defineAsyncComponent } from 'vue'

// Lazy load heavy 3D components
const CesiumViewer = defineAsyncComponent(() =>
  import('./CesiumViewer.vue')
)
const DigitalTwinBabylon = defineAsyncComponent(() =>
  import('./DigitalTwin3D_Babylon.vue')
)
const CameraStream = defineAsyncComponent(() =>
  import('./CameraStream.vue')
)
const EnergyManagement = defineAsyncComponent(() =>
  import('./EnergyManagement.vue')
)
const HistoricalAnalytics = defineAsyncComponent(() =>
  import('./HistoricalAnalytics.vue')
)

import { useHistoricalData } from '../composables/useHistoricalData'
import { useAzureTelemetry } from '../composables/useAzureTelemetry'
import { useMLPrediction } from '../composables/useMLPrediction'

const props = defineProps({
  isDarkMode: { type: Boolean, default: false },
  user: { type: Object, default: null }
})

const emit = defineEmits(['toggle-theme', 'logout'])

const activeSection = ref('overview')
const current3DView = ref('cesium')

const { isConnected, sensorData, startPolling, stopPolling } = useAzureTelemetry()
const { loadHistoricalData, addDataPoint } = useHistoricalData()
const mlPrediction = useMLPrediction()

const peopleCount = ref(0)
const totalEnergyWh = ref(0)
const currentTime = ref(new Date())
const electricityData = ref({ values: [] })

const SAVE_INTERVAL = 30000
const MAX_POINTS = 60
let lastSaveTimestamp = 0
let timeInterval = null
let lastPowerTimestamp = Date.now()

const displayName = computed(() => props.user?.displayName || props.user?.email || 'Operator')
const userInitials = computed(() => {
  const src = displayName.value.trim()
  if (!src) return 'OP'
  return src.split(' ').map(p => p[0]).join('').slice(0, 2).toUpperCase()
})
const formattedTime = computed(() => {
  return currentTime.value.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
})

const acRecommendedTemp = computed(() => {
  const temp = mlPrediction.acRecommendation.value?.recommendedTemp
  return temp ? Math.round(temp) : '--'
})

const handleThemeToggle = () => emit('toggle-theme')
const handleLogout = () => emit('logout')
const selectSection = (id) => { activeSection.value = id }

const handlePeopleCountUpdate = async count => {
  peopleCount.value = count
  if (sensorData.value) sensorData.value.peopleCount = count
}

onMounted(() => {
  startPolling()
  loadHistoricalData()
  timeInterval = setInterval(() => { currentTime.value = new Date() }, 1000)
  // Trigger initial ML prediction
  triggerMLPrediction()
})

// Watch for sensor data changes and update ML prediction
watch(
  sensorData,
  async (newData) => {
    if (!newData) return

    // Update electricity data
    if (typeof newData.power === 'number') {
      const values = [...electricityData.value.values, parseFloat(newData.power.toFixed(2))]
      if (values.length > MAX_POINTS) values.shift()
      electricityData.value = { ...electricityData.value, values }
      const now = Date.now()
      const deltaHours = (now - lastPowerTimestamp) / 3600000
      if (deltaHours > 0 && deltaHours < 1) {
        totalEnergyWh.value += newData.power * deltaHours
      }
      lastPowerTimestamp = now
    }

    // Update people count
    if (typeof newData.peopleCount === 'number') {
      peopleCount.value = newData.peopleCount
    }

    // Save to historical data
    const now = Date.now()
    if (now - lastSaveTimestamp >= SAVE_INTERVAL) {
      addDataPoint(newData)
      lastSaveTimestamp = now
    }

    // Update ML prediction when sensor data changes significantly
    if (lastSensorSuhu === null || Math.abs(newData.temperature - lastSensorSuhu) >= 1) {
      lastSensorSuhu = newData.temperature
      triggerMLPrediction()
    }
  },
  { deep: true }
)

// Trigger ML prediction with current sensor data
const triggerMLPrediction = async () => {
  try {
    const sensorInput = {
      suhu: sensorData.value?.temperature || sensorData.value?.suhu || 25,
      kelembaban: sensorData.value?.humidity || sensorData.value?.kelembaban || 60,
      daya: sensorData.value?.power || sensorData.value?.daya || 0,
      jumlahOrang: sensorData.value?.peopleCount || peopleCount.value || 0
    }

    console.log('[Dashboard] Triggering ML prediction with:', sensorInput)
    await mlPrediction.getPrediction(sensorInput)
  } catch (err) {
    console.error('[Dashboard] ML prediction error:', err)
  }
}

let lastSensorSuhu = null
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
  width: 220px;
  z-index: 100;
}

.sidebar-left {
  left: 0;
}

.sidebar-right {
  right: 0;
}

/* Main Card - Single unified card */
.main-card {
  background: var(--panel);
  border: none;
  border-radius: 0;
  padding: 16px 12px;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 0;
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

.logo-icon {
  width: 20px;
  height: 20px;
  color: var(--accent);
}

.brand {
  font-family: 'Sora', sans-serif;
  font-size: 13px;
  font-weight: 700;
  color: var(--text);
}

.brand-logo {
  height: 28px;
  width: auto;
  object-fit: contain;
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

.header-row2 {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.version {
  font-size: 10px;
  color: var(--text-3);
}

.time-display {
  font-family: 'Sora', sans-serif;
  font-size: 24px;
  font-weight: 600;
  color: var(--text);
  text-align: center;
  display: block;
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

/* CCTV List */
.cctv-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 10px;
}

.cctv-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  padding: 7px 8px;
  background: transparent;
  border: 1px solid var(--border);
  border-radius: 6px;
  color: var(--text-2);
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: 11px;
  cursor: pointer;
  transition: background-color 0.2s, border-color 0.2s, color 0.2s;
}

.cctv-btn:hover {
  background: rgba(255, 255, 255, 0.05);
  border-color: var(--accent);
}

.cctv-btn.active {
  background: rgba(0, 212, 255, 0.15);
  border-color: var(--accent);
  color: var(--accent);
}

.cam-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--danger);
  flex-shrink: 0;
}

.cctv-btn.active .cam-dot {
  background: var(--success);
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
  cursor: pointer;
  transition: background-color 0.2s, border-color 0.2s, color 0.2s;
}

.menu-btn:hover {
  background: rgba(0, 212, 255, 0.15);
  border-color: var(--accent);
  color: var(--accent);
}

.menu-btn span {
  font-size: 11px;
  font-weight: 600;
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
  font-size: 11px;
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
  max-width: 900px;
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

.settings-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 20px;
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

.profile-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.profile-avatar {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  object-fit: cover;
  border: 2px solid var(--accent);
}

.profile-avatar.fallback {
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 212, 255, 0.2);
  color: var(--accent);
  font-family: 'Sora', sans-serif;
  font-weight: 700;
}

.profile-name {
  font-weight: 600;
  margin: 0;
}

.profile-email {
  font-size: 0.7rem;
  color: var(--text-3);
  margin: 0;
}

.online { color: var(--success); }
.offline { color: var(--danger); }

.logout-btn {
  display: block;
  width: 100%;
  max-width: 150px;
  margin: 0 auto;
  padding: 12px;
  background: transparent;
  border: 1px solid var(--danger);
  border-radius: 6px;
  color: var(--danger);
  font-family: 'Sora', sans-serif;
  font-size: 0.75rem;
  font-weight: 600;
  cursor: pointer;
}

.logout-btn:hover {
  background: var(--danger);
  color: #fff;
}

/* ═══ RESPONSIVE ═══ */
@media (max-width: 768px) {
  .sidebar {
    display: none;
  }
}

@media (max-width: 768px) {
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
