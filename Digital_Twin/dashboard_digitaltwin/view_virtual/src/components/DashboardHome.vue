<template>
  <div class="app">
    <header class="header">
      <div class="header-container">
        <div class="header-left">
          <div class="logo">
            <div class="logo-icon">
              <img src="/logo.png" alt="TwinSpace Logo" class="logo-image" />
            </div>
            <div class="logo-copy">
              <h1 class="logo-text">Twin Space Dashboard</h1>
              <p class="logo-subtitle">Digital Twin edge–cloud · energi, okupansi, dan visual multiskala</p>
            </div>
          </div>
        </div>

        <div class="header-right">
          <div class="header-actions">
            <button class="theme-pill" type="button" @click="handleThemeToggle">
              <span class="theme-pill-icon">{{ isDarkMode ? '☀️' : '🌙' }}</span>
              <span>{{ isDarkMode ? 'Mode Terang' : 'Mode Gelap' }}</span>
            </button>

            <div class="status-badge" :class="telemetryConnected ? 'connected' : 'disconnected'">
              <span class="status-dot"></span>
              <span class="status-text">{{ telemetryConnected ? 'Replay/API terhubung' : 'API tidak tersedia' }}</span>
            </div>

            <div class="timestamp">
              <div class="time-section">
                <span class="time-icon">📅</span>
                <span class="time-text">{{ formattedDate }}</span>
              </div>
              <div class="time-divider"></div>
              <div class="time-section">
                <span class="time-icon">🕐</span>
                <span class="time-text">{{ formattedTime }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </header>

    <main class="main">
      <div class="container">
        <div class="card" style="margin-bottom: 20px;">
          <h2>🎯 Digital Twin Geospasial–Indoor Multiskala</h2>
          <MultiscaleDigitalTwin
            :sensor-data="sensorData"
            :people-count="peopleCount"
            :is-dark-mode="isDarkMode"
          />
        </div>

        <div class="card provenance-card" style="margin-bottom: 20px;">
          <h2>🧭 Provenance Replay Historis</h2>
          <div class="provenance-grid">
            <div><span>Sumber</span><strong>{{ sensorData.sourceType }}</strong></div>
            <div><span>Blok replay</span><strong>{{ sensorData.replayBlockId ?? 'tidak berlaku' }}</strong></div>
            <div><span>Ancestry posisi</span><strong>{{ sensorData.sourceRowId || 'tidak berlaku' }}</strong></div>
            <div><span>Rute</span><strong>{{ sensorData.route }} · {{ sensorData.routeReason }}</strong></div>
            <div><span>Okupansi</span><strong>{{ sensorData.occupancyStatus }} · {{ peopleCount ?? '—' }} orang</strong></div>
            <div><span>Energi legacy satu siklus</span><strong>{{ formatEnergy(sensorData.energyCumulativeWh) }}</strong></div>
            <div><span>Freshness API lokal (proksi)</span><strong>{{ formatLatency(sensorData.freshnessMs) }}</strong></div>
            <div><span>Waktu sumber (lokal)</span><strong>{{ formatTimestamp(sensorData.sourceTimestamp) }}</strong></div>
            <div><span>Waktu replay (lokal)</span><strong>{{ formatTimestamp(sensorData.replayTimestamp) }}</strong></div>
          </div>
          <p class="scope-note">{{ sensorData.scopeNote }}</p>
        </div>

        <div class="grid grid-2" style="margin-bottom: 20px;">
          <div class="card">
            <h2>🌡️ Suhu (maks. 60 sampel · waktu sumber)</h2>
            <TemperatureChart :data="temperatureData" :is-dark-mode="isDarkMode" />
          </div>

          <div class="card">
            <h2>⚡ Daya Legacy (maks. 60 sampel · waktu sumber)</h2>
            <ElectricityChart :data="electricityData" :is-dark-mode="isDarkMode" />
          </div>

          <div class="card">
            <h2>👥 Jumlah Orang (maks. 60 sampel · waktu sumber)</h2>
            <PeopleChart :data="peopleData" :is-dark-mode="isDarkMode" />
          </div>

          <div class="card">
            <h2>🔋 Energi Legacy Kumulatif per Siklus</h2>
            <ElectricityChart
              :data="energyData"
              :is-dark-mode="isDarkMode"
              metric-label="Energi Legacy Kumulatif (Wh)"
              unit-label="Energi (Wh)"
              empty-title="Menunggu Energi Replay"
            />
          </div>
        </div>

        <div class="card" style="margin-top: 20px;">
          <h2>📋 Detail Data Sensor</h2>
          <DataTable
            :sensor-data="sensorData"
            :people-count="peopleCount"
          />
        </div>

      </div>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import DataTable from './DataTable.vue'
import MultiscaleDigitalTwin from './MultiscaleDigitalTwin.vue'
import ElectricityChart from './ElectricityChart.vue'

import PeopleChart from './PeopleChart.vue'
import TemperatureChart from './TemperatureChart.vue'
import { useTelemetry } from '../composables/useTelemetry'

const props = defineProps({
  isDarkMode: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['toggle-theme'])

const {
  telemetryConnected,
  sensorData,
  connectTelemetry,
  disconnectTelemetry
} = useTelemetry()

const temperatureData = ref({ labels: [], values: [] })
const electricityData = ref({ labels: [], values: [] })
const peopleData = ref({ labels: [], values: [] })
const energyData = ref({ labels: [], values: [] })
const peopleCount = ref(null)
const currentTime = ref(new Date())

const MAX_POINTS = 60

let timeInterval = null

const formattedDate = computed(() => {
  const options = { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' }
  return currentTime.value.toLocaleDateString('id-ID', options)
})

const formattedTime = computed(() => {
  const options = { hour: '2-digit', minute: '2-digit', second: '2-digit' }
  return currentTime.value.toLocaleTimeString('id-ID', options)
})

const handleThemeToggle = () => {
  emit('toggle-theme')
}

const formatTimestamp = value => {
  if (!value) return 'tidak tersedia'
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return String(value)
  return parsed.toLocaleString('id-ID', {
    dateStyle: 'short',
    timeStyle: 'medium'
  })
}

const formatLatency = value => {
  const parsed = Number(value)
  return value !== null && value !== undefined && Number.isFinite(parsed)
    ? `${parsed.toFixed(3)} ms`
    : 'tidak tersedia'
}

const formatEnergy = value => {
  const parsed = Number(value)
  return value !== null && value !== undefined && Number.isFinite(parsed)
    ? `${parsed.toFixed(3)} Wh`
    : 'tidak tersedia'
}

const formatChartTimestamp = value => {
  if (!value) return 'tanpa waktu'
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return String(value)
  return parsed.toLocaleString('id-ID', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

const addChartDataPoint = (targetRef, value, timestamp) => {
  if (!Number.isFinite(value)) return

  const labels = [
    ...(targetRef.value.labels || []),
    formatChartTimestamp(timestamp)
  ]
  const values = [...(targetRef.value.values || []), parseFloat(value.toFixed(2))]

  if (labels.length > MAX_POINTS) {
    labels.shift()
    values.shift()
  }

  targetRef.value = { labels, values }
}

watch(
  sensorData,
  newData => {
    if (!newData) return
    const sampleTimestamp =
      newData.sourceTimestamp ||
      newData.replayTimestamp ||
      newData.timestamp

    if (Number.isFinite(newData.temperature)) {
      addChartDataPoint(
        temperatureData,
        newData.temperature,
        sampleTimestamp
      )
    }

    if (Number.isFinite(newData.power)) {
      addChartDataPoint(electricityData, newData.power, sampleTimestamp)
    }

    if (Number.isFinite(newData.peopleCount)) {
      peopleCount.value = newData.peopleCount
      addChartDataPoint(peopleData, newData.peopleCount, sampleTimestamp)
    } else {
      peopleCount.value = null
    }

    if (Number.isFinite(newData.energyCumulativeWh)) {
      addChartDataPoint(
        energyData,
        newData.energyCumulativeWh,
        sampleTimestamp
      )
    }

  },
  { deep: true }
)

onMounted(() => {
  connectTelemetry()

  timeInterval = setInterval(() => {
    currentTime.value = new Date()
  }, 1000)
})

onUnmounted(() => {
  disconnectTelemetry()
  if (timeInterval) clearInterval(timeInterval)
})
</script>

<style scoped>
.app {
  min-height: 100vh;
  position: relative;
}

.header {
  background: var(--bg-header);
  padding: 0;
  box-shadow: 0 2px 12px var(--shadow-sm);
  margin-bottom: 30px;
  border-bottom: 1px solid var(--border-dark);
  position: sticky;
  top: 0;
  z-index: 100;
  animation: slideDown 0.5s ease-out;
  transition: background 0.3s ease, box-shadow 0.3s ease, border-color 0.3s ease;
}

@keyframes slideDown {
  from {
    transform: translateY(-100%);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

.header-container {
  max-width: 1600px;
  margin: 0 auto;
  padding: 16px 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 24px;
}

.header-left {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-icon {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 12px;
  padding: 6px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
  overflow: hidden;
}

.logo-image {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.logo:hover .logo-icon {
  transform: rotate(5deg) scale(1.05);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15);
}

.logo-copy {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.logo-text {
  font-size: 24px;
  color: #ffffff;
  margin: 0;
  font-weight: 800;
  letter-spacing: -0.3px;
  white-space: nowrap;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.logo-subtitle {
  margin: 0;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.8);
  letter-spacing: 0.4px;
}

.header-right {
  display: flex;
  align-items: center;
  flex: 1;
  justify-content: flex-end;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.theme-pill,
.admin-btn {
  border: 1px solid rgba(255, 255, 255, 0.18);
  background: rgba(255, 255, 255, 0.12);
  color: white;
  padding: 10px 16px;
  border-radius: 14px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-weight: 700;
  letter-spacing: 0.2px;
  transition: transform 0.25s ease, box-shadow 0.25s ease, background 0.25s ease;
  backdrop-filter: blur(16px);
}

.theme-pill:hover,
.admin-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 24px rgba(8, 145, 178, 0.2);
  background: rgba(255, 255, 255, 0.2);
}

.admin-btn {
  background: rgba(139, 92, 246, 0.25);
  border-color: rgba(139, 92, 246, 0.35);
}
.admin-btn:hover {
  background: rgba(139, 92, 246, 0.4);
  box-shadow: 0 10px 24px rgba(139, 92, 246, 0.25);
}

.theme-pill-icon {
  font-size: 14px;
}

.status-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 18px;
  border-radius: 12px;
  font-weight: 600;
  font-size: 13px;
  transition: all 0.3s ease;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  white-space: nowrap;
}

.status-badge:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.status-badge.connected {
  background: linear-gradient(135deg, rgba(39, 174, 96, 0.95) 0%, rgba(46, 213, 115, 0.95) 100%);
  color: white;
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.status-badge.disconnected {
  background: linear-gradient(135deg, rgba(231, 76, 60, 0.95) 0%, rgba(235, 77, 75, 0.95) 100%);
  color: white;
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #fff;
  animation: pulseGlow 2s infinite;
  flex-shrink: 0;
}

.status-badge.connected .status-dot {
  box-shadow: 0 0 8px rgba(255, 255, 255, 0.8), 0 0 16px rgba(39, 174, 96, 0.6);
}

.status-badge.disconnected .status-dot {
  box-shadow: 0 0 8px rgba(255, 255, 255, 0.8), 0 0 16px rgba(231, 76, 60, 0.6);
}

.status-text {
  font-weight: 600;
}

@keyframes pulseGlow {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.8;
    transform: scale(1.15);
  }
}

.timestamp {
  display: flex;
  align-items: center;
  gap: 12px;
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 500;
  padding: 8px 16px;
  background: var(--bg-secondary);
  border-radius: 12px;
  border: 1px solid var(--border-dark);
  white-space: nowrap;
  transition: all 0.3s ease;
}

.timestamp:hover {
  background: var(--bg-card);
  border-color: var(--border-color-hover);
}

.time-section {
  display: flex;
  align-items: center;
  gap: 6px;
}

.time-divider {
  width: 1px;
  height: 20px;
  background: var(--border-dark);
  opacity: 0.5;
}

.time-icon {
  font-size: 14px;
  opacity: 0.9;
}

.time-text {
  font-weight: 500;
  letter-spacing: 0.3px;
}

.main {
  padding-bottom: 40px;
  animation: fadeIn 0.6s ease-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.card h2 {
  font-size: 22px;
  margin-bottom: 24px;
  color: var(--text-primary);
  position: relative;
  padding-bottom: 12px;
  font-weight: 700;
  transition: color 0.3s ease;
}

.card h2::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  width: 60px;
  height: 3px;
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
  border-radius: 2px;
  animation: expandLine 0.5s ease-out;
}

.provenance-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.provenance-grid div {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 14px;
  border: 1px solid var(--border-dark);
  border-radius: 12px;
}

.provenance-grid span,
.scope-note {
  color: var(--text-secondary);
  font-size: 12px;
}

.provenance-grid strong {
  overflow-wrap: anywhere;
}

.scope-note {
  margin: 14px 0 0;
}

@keyframes expandLine {
  from {
    width: 0;
  }
  to {
    width: 60px;
  }
}

@media (max-width: 1100px) {
  .header-container {
    flex-direction: column;
    align-items: stretch;
  }

  .header-right {
    justify-content: flex-start;
  }
}

@media (max-width: 768px) {
  .provenance-grid {
    grid-template-columns: 1fr 1fr;
  }

  .header-container {
    gap: 16px;
    padding: 16px 20px;
  }

  .logo-text {
    font-size: 20px;
  }

  .header-actions {
    width: 100%;
    gap: 10px;
    justify-content: stretch;
  }

  .theme-pill,
  .admin-btn,
  .status-badge,
  .timestamp {
    width: 100%;
    justify-content: center;
  }
}

@media (max-width: 480px) {
  .header-container {
    padding: 12px 16px;
  }

  .logo-copy {
    gap: 0;
  }

  .logo-text {
    font-size: 18px;
  }

  .logo-subtitle {
    font-size: 11px;
  }
}
</style>
