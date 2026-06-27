<template>
  <div class="admin" :class="{ dark: isDarkMode }">
    <aside class="sidebar" :class="{ 'mobile-open': isMobileMenuOpen }">
      <div class="sidebar-brand">
        <div class="brand-logo-wrap">
          <img src="/logo.png" alt="Logo" class="brand-logo" />
        </div>
        <div class="brand-text">
          <span class="brand-title">TwinSpace</span>
          <span class="brand-role">ADMIN PANEL</span>
        </div>
        <button class="menu-close-btn" @click="isMobileMenuOpen = false">✕</button>
      </div>

      <nav class="nav">
        <button
          v-for="item in navItems"
          :key="item.id"
          class="nav-item"
          :class="{ active: activeSection === item.id }"
          @click="selectSection(item.id)"
        >
          <span class="nav-icon">{{ item.icon }}</span>
          <span class="nav-label">{{ item.label }}</span>
        </button>
      </nav>

      <div class="sidebar-footer">
        <div class="admin-chip">
          <img v-if="user?.photoURL" :src="user.photoURL" class="admin-avatar" referrerpolicy="no-referrer" />
          <div v-else class="admin-avatar admin-avatar-fallback">{{ userInitials }}</div>
          <div class="admin-info">
            <span class="admin-name">{{ displayName }}</span>
            <span class="admin-email">{{ user?.email || '' }}</span>
          </div>
        </div>
        <div class="sidebar-actions">
          <button class="action-btn logout" @click="$emit('logout')">
            <span>🚪</span> Keluar Panel
          </button>
        </div>
      </div>
    </aside>

    <div v-if="isMobileMenuOpen" class="mobile-overlay" @click="isMobileMenuOpen = false"></div>

    <main class="main-content">
      <header class="topbar">
        <div class="topbar-left">
          <button class="burger-btn" @click="isMobileMenuOpen = true">
            <span></span><span></span><span></span>
          </button>
          <div class="topbar-info">
            <h1 class="page-title">{{ currentPageTitle }}</h1>
            <p class="page-subtitle">{{ currentPageSubtitle }}</p>
          </div>
        </div>
        <div class="topbar-right">
          <div class="status-pill" :class="mqttConnected ? 'online' : 'offline'">
            <span class="status-dot"></span>
            {{ mqttConnected ? 'Azure Terhubung' : 'Simulasi / Offline' }}
          </div>
          <button class="theme-toggle" @click="$emit('toggle-theme')">
            {{ isDarkMode ? '☀️' : '🌙' }}
          </button>
        </div>
      </header>

      <section v-if="activeSection === 'overview'" class="section">
        <div class="overview-head">
          <div class="overview-copy">
            <span class="overview-kicker">Overview</span>
            <h2 class="overview-title">Pusat kontrol untuk memantau kondisi ruang dan sistem Azure.</h2>
            <p class="overview-text">
              Semua indikator utama, shortcut admin, dan aktivitas terbaru dirangkum dalam satu area.
            </p>
          </div>
          <div class="overview-badges">
            <div class="overview-badge" :class="mqttConnected ? 'online' : 'offline'">
              <span class="overview-badge-dot"></span>
              <span>{{ mqttConnected ? 'Azure Live' : 'Offline Mode' }}</span>
            </div>
            <div class="overview-badge neutral">
              <span>{{ onlineDeviceCount }} perangkat aktif</span>
            </div>
          </div>
        </div>

        <div class="stat-grid">
          <div class="stat-card cyan">
            <div class="stat-icon-bg">🌡️</div>
            <div class="stat-body">
              <span class="stat-label">Suhu Saat Ini</span>
              <span class="stat-value">{{ sensorData.temperature.toFixed(1) }}°C</span>
            </div>
          </div>
          <div class="stat-card blue">
            <div class="stat-icon-bg">💧</div>
            <div class="stat-body">
              <span class="stat-label">Kelembaban</span>
              <span class="stat-value">{{ sensorData.humidity.toFixed(1) }}%</span>
            </div>
          </div>
          <div class="stat-card purple">
            <div class="stat-icon-bg">⚡</div>
            <div class="stat-body">
              <span class="stat-label">Daya Listrik</span>
              <span class="stat-value">{{ sensorData.power.toFixed(1) }}W</span>
            </div>
          </div>
          <div class="stat-card green">
            <div class="stat-icon-bg">👥</div>
            <div class="stat-body">
              <span class="stat-label">Jumlah Orang</span>
              <span class="stat-value">{{ sensorData.peopleCount || 0 }}</span>
            </div>
          </div>
          <div class="stat-card orange">
            <div class="stat-icon-bg">🔌</div>
            <div class="stat-body">
              <span class="stat-label">Tegangan</span>
              <span class="stat-value">{{ sensorData.voltage.toFixed(1) }}V</span>
            </div>
          </div>
        </div>

        <div class="panel">
          <h2 class="panel-title">⚡ Quick Actions</h2>
          <div class="action-grid">
            <button class="quick-action" @click="activeSection = 'energy'">
              <span>💰</span> Energy Management
            </button>
            <button class="quick-action" @click="activeSection = 'analytics'">
              <span>📊</span> Historical Analytics
            </button>
            <button class="quick-action" @click="activeSection = 'settings'">
              <span>⚙️</span> Pengaturan Sistem
            </button>
          </div>
        </div>

        <div class="panel">
          <h2 class="panel-title">🕐 Activity Log</h2>
          <div class="log-list">
            <div v-for="(log, i) in activityLog" :key="i" class="log-item">
              <span class="log-icon">{{ log.icon }}</span>
              <div class="log-body">
                <span class="log-msg">{{ log.message }}</span>
                <span class="log-time">{{ log.time }}</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section v-if="activeSection === 'energy'" class="section">
        <EnergyManagement :is-dark-mode="isDarkMode" :current-power="sensorData.power" />
      </section>

      <section v-if="activeSection === 'analytics'" class="section">
        <HistoricalAnalytics :is-dark-mode="isDarkMode" :current-people-count="sensorData.peopleCount || 0" />
      </section>

      <section v-if="activeSection === 'devices'" class="section">
        <div class="panel">
          <h2 class="panel-title">🔧 Manajemen Perangkat IoT</h2>
          <div class="device-grid">
            <div v-for="device in devices" :key="device.id" class="device-card" :class="device.statusClass">
              <div class="device-card-head">
                <div class="device-icon">{{ device.icon }}</div>
                <div class="device-status-wrap" :class="device.statusClass">
                  <span class="device-status-dot" :class="device.statusClass"></span>
                  <span class="device-status-text">{{ device.status }}</span>
                </div>
              </div>
              <div class="device-info">
                <strong>{{ device.name }}</strong>
                <span class="device-id">{{ device.id }}</span>
              </div>
              <span class="device-type">{{ device.type }}</span>
              <div class="device-meta">
                <span class="device-last-label">Update terakhir</span>
                <span class="device-last">{{ device.lastSeen }}</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section v-if="activeSection === 'alerts'" class="section">
        <div class="panel alert-panel">
          <div class="panel-head">
            <div>
              <h2 class="panel-title">🔔 Pengaturan Alert & Threshold</h2>
              <p class="panel-desc">Atur batas aman setiap parameter dan pantau status sensor secara langsung.</p>
            </div>
            <div class="alert-summary" :class="activeAlertCount > 0 ? 'danger' : 'ok'">
              <span class="alert-summary-dot"></span>
              <span>{{ activeAlertCount > 0 ? `${activeAlertCount} alert aktif` : 'Semua parameter normal' }}</span>
            </div>
          </div>
          <div class="alert-grid">
            <div v-for="alert in alertSettings" :key="alert.key" class="alert-card" :class="getAlertStatus(alert)">
              <div class="alert-card-top">
                <div class="alert-header">
                  <span class="alert-icon-wrap">
                    <span class="alert-icon">{{ alert.icon }}</span>
                  </span>
                  <div class="alert-header-copy">
                    <strong>{{ alert.label }}</strong>
                    <span class="alert-current">Saat ini {{ formatAlertValue(alert) }}</span>
                  </div>
                </div>
                <div class="alert-badge" :class="getAlertStatus(alert)">
                  {{ getAlertBadgeText(alert) }}
                </div>
              </div>
              <div class="alert-inputs">
                <div class="input-group">
                  <label>Min</label>
                  <input type="number" v-model.number="alert.min" :step="alert.step" />
                </div>
                <div class="input-group">
                  <label>Max</label>
                  <input type="number" v-model.number="alert.max" :step="alert.step" />
                </div>
              </div>
              <div class="alert-status" :class="getAlertStatus(alert)">
                {{ getAlertStatusText(alert) }}
              </div>
            </div>
          </div>
          <div class="panel-actions alert-actions">
            <span class="panel-note">Threshold ini dipakai sebagai batas visual monitoring di dashboard admin.</span>
            <button class="btn-primary" @click="saveAlertSettings">💾 Simpan Pengaturan</button>
          </div>
        </div>
      </section>

      <section v-if="activeSection === 'settings'" class="section">
        <div class="panel">
          <h2 class="panel-title">⚙️ Pengaturan Sistem</h2>
          <div class="settings-list">
            <div class="setting-row">
              <div class="setting-info">
                <strong>Polling Interval</strong>
                <span>Interval pengambilan data dari Azure (detik)</span>
              </div>
              <input type="number" v-model.number="systemSettings.pollingInterval" min="1" max="60" class="setting-input" />
            </div>
            <div class="setting-row">
              <div class="setting-info">
                <strong>Tarif Listrik</strong>
                <span>Tarif PLN per kWh (Rp)</span>
              </div>
              <input type="number" v-model.number="systemSettings.tariff" min="0" step="0.01" class="setting-input" />
            </div>
            <div class="setting-row">
              <div class="setting-info">
                <strong>Target Bulanan</strong>
                <span>Target konsumsi energi bulanan (kWh)</span>
              </div>
              <input type="number" v-model.number="systemSettings.monthlyTarget" min="0" class="setting-input" />
            </div>
            <div class="setting-row">
              <div class="setting-info">
                <strong>Kapasitas Ruangan</strong>
                <span>Jumlah maksimum orang dalam ruangan</span>
              </div>
              <input type="number" v-model.number="systemSettings.roomCapacity" min="1" class="setting-input" />
            </div>
            <div class="setting-row">
              <div class="setting-info">
                <strong>Azure Function URL</strong>
                <span>Endpoint API untuk Azure Functions</span>
              </div>
              <input type="text" :value="azureFunctionUrl" class="setting-input wide" disabled />
            </div>
            <div class="setting-row">
              <div class="setting-info">
                <strong>Demo Mode</strong>
                <span>Gunakan data dummy jika backend tidak tersedia</span>
              </div>
              <label class="toggle-switch">
                <input type="checkbox" v-model="systemSettings.demoMode" />
                <span class="toggle-slider"></span>
              </label>
            </div>
          </div>
          <div class="panel-actions">
            <button class="btn-primary" @click="saveSystemSettings">💾 Simpan Pengaturan</button>
            <button class="btn-outline" @click="clearLocalCache">🗑️ Clear Cache</button>
          </div>
        </div>

        <div class="panel system-info-panel">
          <div class="panel-head">
            <div>
              <h2 class="panel-title">ℹ️ Informasi Sistem</h2>
              <p class="panel-desc">Ringkasan stack teknologi yang menopang dashboard, data pipeline, dan perangkat IoT.</p>
            </div>
            <div class="system-stack-pill">
              <span class="system-stack-dot"></span>
              <span>{{ systemInfoItems.length }} komponen inti</span>
            </div>
          </div>
          <div class="info-grid">
            <div v-for="item in systemInfoItems" :key="item.label" class="info-item" :class="item.tone">
              <div class="info-item-head">
                <span class="info-icon">{{ item.icon }}</span>
                <span class="info-label">{{ item.label }}</span>
              </div>
              <strong>{{ item.value }}</strong>
              <span class="info-note">{{ item.note }}</span>
            </div>
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import EnergyManagement from './EnergyManagement.vue'
import HistoricalAnalytics from './HistoricalAnalytics.vue'
import { useMQTT } from '../composables/useMQTT'
import { AZURE_FUNCTION_URL } from '../lib/appConfig'

const props = defineProps({
  isDarkMode: { type: Boolean, default: false },
  user: { type: Object, default: null }
})

const emit = defineEmits(['toggle-theme', 'logout', 'go-dashboard'])

// Data
const { mqttConnected, sensorData, connectMQTT, disconnectMQTT } = useMQTT()

const activeSection = ref('overview')
const isMobileMenuOpen = ref(false)
const azureFunctionUrl = AZURE_FUNCTION_URL

const selectSection = (id) => {
  activeSection.value = id
  isMobileMenuOpen.value = false
}

const navItems = [
  { id: 'overview', icon: '🏠', label: 'Overview' },
  { id: 'energy', icon: '💰', label: 'Energy' },
  { id: 'analytics', icon: '📊', label: 'Analytics' },
  { id: 'devices', icon: '🔧', label: 'Devices' },
  { id: 'alerts', icon: '🔔', label: 'Alerts' },
  { id: 'settings', icon: '⚙️', label: 'Settings' }
]

const currentPageTitle = computed(() => {
  const map = {
    overview: '🏠 Dashboard Overview',
    energy: '💰 Energy Management',
    analytics: '📊 Historical Analytics',
    devices: '🔧 Device Management',
    alerts: '🔔 Alert Settings',
    settings: '⚙️ System Settings'
  }
  return map[activeSection.value] || 'Admin'
})

const currentPageSubtitle = computed(() => {
  const map = {
    overview: 'Ringkasan sistem dan status sensor realtime',
    energy: 'Analisis konsumsi energi & rekomendasi AI',
    analytics: 'Grafik historis dan tren data sensor',
    devices: 'Status dan manajemen perangkat IoT',
    alerts: 'Konfigurasi threshold dan notifikasi',
    settings: 'Pengaturan sistem dan konfigurasi'
  }
  return map[activeSection.value] || ''
})

const displayName = computed(() => props.user?.displayName || props.user?.email || 'Admin')
const userInitials = computed(() => {
  const name = displayName.value.trim()
  if (!name) return 'AD'
  return name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()
})

// Devices (Reactive to MQTT connection)
const devices = computed(() => [
  { id: 'ESP32-001', name: 'ESP32 Sensor Node', type: 'Suhu, Kelembaban, Listrik', icon: '🌡️', status: mqttConnected.value ? 'Online' : 'Offline', statusClass: mqttConnected.value ? 'online' : 'offline', lastSeen: mqttConnected.value ? 'Baru saja' : 'N/A' },
  { id: 'RPi-CAM-001', name: 'Raspberry Pi Camera', type: 'People Counter (YOLO)', icon: '📹', status: 'Online', statusClass: 'online', lastSeen: 'Baru saja' },
  { id: 'AC-UNIT-001', name: 'AC Unit (Smart)', type: 'Pendingin Ruangan', icon: '❄️', status: 'Standby', statusClass: 'warning', lastSeen: '5 menit lalu' },
  { id: 'GW-MQTT-001', name: 'MQTT Gateway', type: 'Azure Cloud Sync', icon: '📡', status: mqttConnected.value ? 'Connected' : 'Disconnected', statusClass: mqttConnected.value ? 'online' : 'offline', lastSeen: 'N/A' }
])

const onlineDeviceCount = computed(() => (
  devices.value.filter(device => device.statusClass === 'online').length
))

const systemInfoItems = [
  { label: 'Frontend', value: 'Vue 3 + Vite', note: 'UI utama dan bundler aplikasi', icon: '🧩', tone: 'cyan' },
  { label: '3D Engine', value: 'Babylon.js', note: 'Render digital twin interaktif', icon: '🧊', tone: 'blue' },
  { label: 'Chart', value: 'Chart.js + vue-chartjs', note: 'Visualisasi histori dan tren', icon: '📈', tone: 'violet' },
  { label: 'Auth', value: 'Firebase Google', note: 'Autentikasi akun operator dan admin', icon: '🔐', tone: 'amber' },
  { label: 'Backend', value: 'Azure Functions', note: 'API telemetry dan pengolahan data', icon: '☁️', tone: 'cyan' },
  { label: 'Storage', value: 'Azure Table Storage', note: 'Penyimpanan histori sensor', icon: '🗄️', tone: 'slate' },
  { label: 'ML', value: 'Python Flask API', note: 'Serving model dan prediksi energi', icon: '🧠', tone: 'rose' },
  { label: 'IoT', value: 'ESP32 + RPi', note: 'Perangkat edge dan kamera lapangan', icon: '📡', tone: 'emerald' }
]

// Alert settings
const alertSettings = ref([
  { key: 'temperature', icon: '🌡️', label: 'Suhu (°C)', min: 15, max: 30, step: 0.5, currentValue: () => sensorData.value.temperature },
  { key: 'humidity', icon: '💧', label: 'Kelembaban (%)', min: 30, max: 80, step: 1, currentValue: () => sensorData.value.humidity },
  { key: 'voltage', icon: '🔌', label: 'Tegangan (V)', min: 180, max: 250, step: 1, currentValue: () => sensorData.value.voltage },
  { key: 'power', icon: '⚡', label: 'Daya (W)', min: 0, max: 4000, step: 10, currentValue: () => sensorData.value.power },
  { key: 'people', icon: '👥', label: 'Jumlah Orang', min: 0, max: 20, step: 1, currentValue: () => sensorData.value.peopleCount || 0 }
])

const activeAlertCount = computed(() => (
  alertSettings.value.filter(alert => getAlertStatus(alert) === 'alert-danger').length
))

const getAlertCurrentValue = (alert) => {
  const value = typeof alert.currentValue === 'function' ? alert.currentValue() : 0
  return typeof value === 'number' && !Number.isNaN(value) ? value : 0
}

const formatAlertValue = (alert) => {
  const value = getAlertCurrentValue(alert)
  return alert.step < 1 ? value.toFixed(1) : value.toFixed(0)
}

const getAlertStatus = (alert) => {
  const val = getAlertCurrentValue(alert)
  if (val < alert.min || val > alert.max) return 'alert-danger'
  return 'alert-ok'
}

const getAlertBadgeText = (alert) => {
  return getAlertStatus(alert) === 'alert-danger' ? 'Perlu perhatian' : 'Stabil'
}

const getAlertStatusText = (alert) => {
  const val = getAlertCurrentValue(alert)
  if (val < alert.min) return `⚠️ Di bawah minimum (${val})`
  if (val > alert.max) return `⚠️ Di atas maximum (${val})`
  return `✅ Normal (${typeof val === 'number' ? val.toFixed(1) : val})`
}

const saveAlertSettings = () => {
  localStorage.setItem('admin_alert_settings', JSON.stringify(alertSettings.value))
  addLog('🔔', 'Alert settings saved')
  alert('Pengaturan alert berhasil disimpan!')
}

// System settings
const systemSettings = ref({
  pollingInterval: 5,
  tariff: 1444.70,
  monthlyTarget: 100,
  roomCapacity: 20,
  demoMode: false
})

const saveSystemSettings = () => {
  localStorage.setItem('admin_system_settings', JSON.stringify(systemSettings.value))
  addLog('⚙️', 'System settings saved')
  alert('Pengaturan sistem berhasil disimpan!')
}

const clearLocalCache = () => {
  if (confirm('Yakin ingin menghapus semua cache lokal?')) {
    localStorage.removeItem('sensor_last_data')
    localStorage.removeItem('digitaltwin_historical_data')
    localStorage.removeItem('digitaltwin_energy_management')
    addLog('🗑️', 'Local cache cleared')
    alert('Cache lokal berhasil dihapus!')
  }
}

// Activity log
const activityLog = ref([])
const addLog = (icon, message) => {
  activityLog.value.unshift({
    icon,
    message,
    time: new Date().toLocaleTimeString('id-ID')
  })
  if (activityLog.value.length > 50) activityLog.value.pop()
}

// Lifecycle
onMounted(() => {
  connectMQTT()
  addLog('🟢', 'Admin panel opened')
  addLog('📡', `Azure polling started`)

  // Load saved settings
  try {
    const savedSystem = localStorage.getItem('admin_system_settings')
    if (savedSystem) systemSettings.value = { ...systemSettings.value, ...JSON.parse(savedSystem) }

    const savedAlerts = localStorage.getItem('admin_alert_settings')
    if (savedAlerts) alertSettings.value = JSON.parse(savedAlerts)
  } catch (e) { /* ignore */ }
})

onUnmounted(() => {
  disconnectMQTT()
})
</script>

<style scoped>
/* ===== Layout ===== */
.admin {
  display: flex;
  min-height: 100vh;
  background: #f1f5f9;
  color: #1e293b;
  transition: background 0.3s, color 0.3s;
}
.admin.dark {
  background: #0b0f19;
  color: #e2e8f0;
}

/* ===== Sidebar ===== */
.sidebar {
  width: 260px;
  flex-shrink: 0;
  background: #fff;
  border-right: 1px solid rgba(0,0,0,0.06);
  display: flex;
  flex-direction: column;
  position: sticky;
  top: 0;
  height: 100vh;
  overflow-y: auto;
  transition: background 0.3s, border-color 0.3s;
}
.dark .sidebar {
  background: #111827;
  border-right-color: rgba(255,255,255,0.06);
}

/* ===== Sidebar Brand Custom (Mirip Screenshot) ===== */
.sidebar-brand {
  position: relative;
  display: flex;
  align-items: center;
  gap: 14px;
  margin: 16px 14px 10px;
  padding: 16px 18px;
  border-radius: 24px;
  background: linear-gradient(135deg, #f4faff, #e6f4fe);
  border: 1px solid rgba(186, 230, 253, 0.4);
  box-shadow: 0 4px 15px rgba(14, 116, 144, 0.03);
}
.dark .sidebar-brand {
  background: linear-gradient(145deg, rgba(8,47,73,0.38), rgba(15,23,42,0.96));
  border-color: rgba(34,211,238,0.16);
  box-shadow: 0 16px 30px rgba(0,0,0,0.28);
}

.brand-logo-wrap {
  position: relative;
  width: 52px;
  height: 52px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 16px;
  background: #ffffff;
  border: 2px solid #eef7ff;
  box-shadow: 0 0 0 2px #e0f2fe, 0 4px 12px rgba(186, 230, 253, 0.4);
  flex-shrink: 0;
}
.dark .brand-logo-wrap {
  background: #0f172a;
  border-color: #1e293b;
  box-shadow: 0 4px 12px rgba(0,0,0,0.3);
}

.brand-logo {
  width: 26px;
  height: 26px;
  object-fit: contain;
}

.brand-text {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
  min-width: 0;
  flex: 1;
}

.brand-title {
  font-weight: 900;
  font-size: 1.45rem;
  line-height: 1;
  letter-spacing: -0.02em;
  color: #0f172a; /* Warna teks biru super gelap (slate) */
  /* Shadow disesuaikan dengan warna aksen cyan tema Anda */
  text-shadow: 1.5px 1.5px 0px rgba(6, 182, 212, 0.3); 
}

.dark .brand-title {
  color: #f8fafc;
  /* Shadow cyan yang lebih terang untuk dark mode */
  text-shadow: 1.5px 1.5px 0px rgba(34, 211, 238, 0.4);
}

.brand-role {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 6px 14px;
  border-radius: 999px;
  font-size: 0.65rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 0.18em;
  white-space: nowrap;
  color: #0091a1;
  background: #daf1fd;
  border: 1px solid #bce6fd;
}
.dark .brand-role {
  color: #67e8f9;
  background: rgba(8,47,73,0.76);
  border-color: rgba(34,211,238,0.22);
}

.menu-close-btn {
  display: none;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  flex-shrink: 0;
  border: 1px solid rgba(15,23,42,0.08);
  border-radius: 12px;
  background: rgba(255,255,255,0.76);
  color: #334155;
  cursor: pointer;
  transition: transform 0.2s ease, background 0.2s ease, color 0.2s ease, box-shadow 0.2s ease;
}
.menu-close-btn:hover {
  transform: translateY(-1px);
  background: rgba(239,68,68,0.08);
  color: #ef4444;
  box-shadow: 0 8px 16px rgba(239,68,68,0.12);
}
.dark .menu-close-btn {
  border-color: rgba(255,255,255,0.08);
  background: rgba(15,23,42,0.85);
  color: #e2e8f0;
}
.menu-close-btn span {
  font-size: 1.35rem;
  line-height: 1;
}

.nav {
  flex: 1;
  padding: 14px 14px 18px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.nav-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px 14px;
  border: 1px solid transparent;
  border-radius: 18px;
  background: rgba(255,255,255,0.72);
  color: #0f172a;
  cursor: pointer;
  font-size: 0.95rem;
  font-weight: 700;
  letter-spacing: -0.01em;
  transition: transform 0.22s ease, box-shadow 0.22s ease, border-color 0.22s ease, background 0.22s ease, color 0.22s ease;
  text-align: left;
  box-shadow: 0 6px 14px rgba(15, 23, 42, 0.04);
}
.dark .nav-item {
  background: rgba(15,23,42,0.42);
  color: #e5eef9;
  border-color: rgba(255,255,255,0.03);
}
.nav-item:hover {
  transform: translateY(-1px);
  background: linear-gradient(135deg, rgba(6,182,212,0.1), rgba(255,255,255,0.95));
  border-color: rgba(6,182,212,0.14);
  box-shadow: 0 12px 24px rgba(6,182,212,0.1);
}
.dark .nav-item:hover {
  background: linear-gradient(135deg, rgba(34,211,238,0.12), rgba(15,23,42,0.9));
  border-color: rgba(34,211,238,0.14);
  box-shadow: 0 14px 24px rgba(0,0,0,0.2);
}
.nav-item.active {
  background: linear-gradient(135deg, rgba(6,182,212,0.16), rgba(99,102,241,0.08), rgba(255,255,255,0.9));
  border-color: rgba(6,182,212,0.18);
  color: #06b6d4;
  box-shadow: 0 16px 28px rgba(6,182,212,0.14);
}
.dark .nav-item.active {
  color: #67e8f9;
  background: linear-gradient(135deg, rgba(34,211,238,0.14), rgba(99,102,241,0.08), rgba(15,23,42,0.9));
  border-color: rgba(34,211,238,0.18);
}
.nav-item.active::after {
  content: '';
  position: absolute;
  right: 14px;
  top: 50%;
  width: 7px;
  height: 7px;
  border-radius: 999px;
  background: currentColor;
  transform: translateY(-50%);
  box-shadow: 0 0 0 6px rgba(6,182,212,0.08);
}
.dark .nav-item.active::after {
  box-shadow: 0 0 0 6px rgba(34,211,238,0.08);
}
.nav-icon {
  width: 40px;
  height: 40px;
  border-radius: 14px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: 1.2rem;
  background: linear-gradient(145deg, rgba(255,255,255,0.92), rgba(240,249,255,0.96));
  border: 1px solid rgba(6,182,212,0.12);
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.9), 0 8px 16px rgba(15,23,42,0.05);
}
.dark .nav-icon {
  background: linear-gradient(145deg, rgba(15,23,42,0.95), rgba(17,24,39,0.9));
  border-color: rgba(34,211,238,0.1);
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.03), 0 8px 16px rgba(0,0,0,0.18);
}
.nav-label {
  flex: 1;
}

.sidebar-footer {
  padding: 18px 14px 16px;
  border-top: 1px solid rgba(0,0,0,0.06);
  background: linear-gradient(180deg, rgba(248,250,252,0.82), rgba(255,255,255,0.96));
}
.dark .sidebar-footer { 
  border-top-color: rgba(255,255,255,0.06);
  background: linear-gradient(180deg, rgba(15,23,42,0.5), rgba(17,24,39,0.82));
}

.admin-chip {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
  padding: 12px;
  border-radius: 18px;
  background: linear-gradient(145deg, rgba(255,255,255,0.92), rgba(248,250,252,0.95));
  border: 1px solid rgba(6,182,212,0.12);
  box-shadow: 0 10px 24px rgba(15,23,42,0.06);
}
.dark .admin-chip {
  background: linear-gradient(145deg, rgba(15,23,42,0.9), rgba(17,24,39,0.92));
  border-color: rgba(34,211,238,0.1);
  box-shadow: 0 12px 24px rgba(0,0,0,0.2);
}
.admin-avatar {
  width: 48px; height: 48px;
  border-radius: 16px;
  object-fit: cover;
  border: 2px solid rgba(6,182,212,0.2);
  flex-shrink: 0;
  box-shadow: 0 8px 18px rgba(15,23,42,0.08);
}
.admin-avatar-fallback {
  display: flex; align-items: center; justify-content: center;
  background: linear-gradient(135deg, rgba(6,182,212,0.16), rgba(99,102,241,0.14));
  font-weight: 800;
  font-size: 1rem;
  color: #06b6d4;
  letter-spacing: 0.05em;
}
.admin-info { display: flex; flex-direction: column; min-width: 0; }
.admin-name { font-weight: 900; font-size: 1rem; color: var(--text-primary); line-height: 1.15; }
.admin-email { font-size: 0.8rem; color: #94a3b8; margin-top: 4px; }

.sidebar-actions {
  display: flex;
}
.action-btn {
  flex: 1;
  padding: 12px 16px;
  border: 1px solid rgba(0,0,0,0.08);
  border-radius: 16px;
  background: linear-gradient(145deg, rgba(255,255,255,0.95), rgba(248,250,252,0.92));
  color: #475569;
  cursor: pointer;
  font-size: 0.95rem;
  font-weight: 800;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  box-shadow: 0 10px 22px rgba(15,23,42,0.06);
}
.dark .action-btn { 
  background: linear-gradient(145deg, rgba(15,23,42,0.92), rgba(17,24,39,0.9)); 
  border-color: rgba(255,255,255,0.1);
  color: #cbd5e1;
}
.action-btn:hover { 
  background: linear-gradient(145deg, rgba(255,255,255,1), rgba(240,249,255,0.96));
  color: #06b6d4;
  border-color: #06b6d4;
  transform: translateY(-1px);
  box-shadow: 0 14px 28px rgba(6,182,212,0.14);
}
.dark .action-btn:hover {
  background: linear-gradient(145deg, rgba(6,182,212,0.12), rgba(15,23,42,0.92));
}
.action-btn.logout:hover { 
  background: linear-gradient(145deg, rgba(254,242,242,0.96), rgba(255,255,255,0.96)); 
  border-color: rgba(239,68,68,0.4); 
  color: #ef4444; 
  box-shadow: 0 14px 28px rgba(239,68,68,0.14);
}
.dark .action-btn.logout:hover {
  background: linear-gradient(145deg, rgba(127,29,29,0.26), rgba(15,23,42,0.94));
}
.action-btn span {
  width: 28px;
  height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  background: rgba(6,182,212,0.08);
}
.dark .action-btn span {
  background: rgba(34,211,238,0.1);
}

/* ===== Main Content ===== */
.main-content {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 32px;
  background: #fff;
  border-bottom: 1px solid rgba(0,0,0,0.06);
  position: sticky;
  top: 0;
  z-index: 50;
  gap: 16px;
  flex-wrap: wrap;
}
.dark .topbar { background: #111827; border-bottom-color: rgba(255,255,255,0.06); }
.page-title { font-size: 1.35rem; font-weight: 800; margin: 0; }
.page-subtitle { font-size: 0.85rem; color: #94a3b8; margin: 0; }

.topbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}
.status-pill {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 16px; border-radius: 999px;
  font-size: 0.82rem; font-weight: 700;
}
.status-pill.online { background: rgba(16,185,129,0.12); color: #059669; }
.status-pill.offline { background: rgba(239,68,68,0.12); color: #ef4444; }
.dark .status-pill.online { color: #34d399; }
.dark .status-pill.offline { color: #fca5a5; }
.status-dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: currentColor;
  animation: pulse 2s infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.theme-toggle {
  width: 40px; height: 40px;
  border: 1px solid rgba(0,0,0,0.08);
  border-radius: 12px;
  background: transparent;
  cursor: pointer;
  font-size: 1.1rem;
  display: flex; align-items: center; justify-content: center;
  transition: all 0.2s;
}
.dark .theme-toggle { border-color: rgba(255,255,255,0.08); }
.theme-toggle:hover { background: rgba(6,182,212,0.08); }

/* ===== Sections ===== */
.section {
  padding: 24px 32px 40px;
  animation: fadeUp 0.3s ease;
}
@keyframes fadeUp {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}

/* ===== Overview ===== */
.overview-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
  padding: 24px 28px;
  margin-bottom: 24px;
  border-radius: 24px;
  border: 1px solid rgba(6,182,212,0.12);
  background:
    radial-gradient(circle at top right, rgba(56,189,248,0.16), transparent 34%),
    linear-gradient(145deg, rgba(255,255,255,0.98), rgba(240,249,255,0.92));
  box-shadow: 0 18px 40px rgba(14,116,144,0.08);
}
.dark .overview-head {
  border-color: rgba(103,232,249,0.12);
  background:
    radial-gradient(circle at top right, rgba(34,211,238,0.14), transparent 36%),
    linear-gradient(145deg, rgba(15,23,42,0.96), rgba(15,23,42,0.88));
  box-shadow: 0 18px 40px rgba(2,6,23,0.32);
}
.overview-copy {
  max-width: 760px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.overview-kicker {
  display: inline-flex;
  align-items: center;
  width: fit-content;
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(6,182,212,0.1);
  color: #0891b2;
  font-size: 0.74rem;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}
.dark .overview-kicker {
  background: rgba(34,211,238,0.16);
  color: #67e8f9;
}
.overview-title {
  margin: 0;
  font-size: clamp(1.35rem, 2vw, 2rem);
  line-height: 1.15;
  font-weight: 900;
}
.overview-text {
  margin: 0;
  max-width: 58ch;
  color: #64748b;
  font-size: 0.98rem;
  line-height: 1.7;
}
.dark .overview-text {
  color: #94a3b8;
}
.overview-badges {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 10px;
}
.overview-badge {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  min-height: 46px;
  padding: 0 16px;
  border-radius: 14px;
  border: 1px solid rgba(15,23,42,0.06);
  background: rgba(255,255,255,0.82);
  color: #0f172a;
  font-size: 0.88rem;
  font-weight: 700;
  box-shadow: 0 10px 22px rgba(15,23,42,0.06);
}
.dark .overview-badge {
  border-color: rgba(255,255,255,0.08);
  background: rgba(15,23,42,0.72);
  color: #e2e8f0;
}
.overview-badge.online {
  color: #047857;
}
.overview-badge.offline {
  color: #dc2626;
}
.overview-badge.neutral {
  color: #0369a1;
}
.dark .overview-badge.online {
  color: #6ee7b7;
}
.dark .overview-badge.offline {
  color: #fda4af;
}
.dark .overview-badge.neutral {
  color: #7dd3fc;
}
.overview-badge-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: currentColor;
  box-shadow: 0 0 0 6px rgba(16,185,129,0.12);
}
.overview-badge.offline .overview-badge-dot {
  box-shadow: 0 0 0 6px rgba(239,68,68,0.12);
}
.overview-badge.neutral .overview-badge-dot {
  box-shadow: 0 0 0 6px rgba(14,165,233,0.12);
}

/* ===== Stat Grid ===== */
.stat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 18px;
  margin-bottom: 28px;
}
.stat-card {
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: center;
  gap: 16px;
  min-height: 126px;
  padding: 20px 22px;
  border-radius: 22px;
  background:
    linear-gradient(160deg, rgba(255,255,255,0.98), rgba(248,250,252,0.92));
  border: 1px solid rgba(15,23,42,0.06);
  box-shadow: 0 16px 36px rgba(15,23,42,0.06);
  transition: transform 0.28s ease, box-shadow 0.28s ease, border-color 0.28s ease;
}
.stat-card::before {
  content: "";
  position: absolute;
  inset: 0 0 auto;
  height: 4px;
  background: linear-gradient(90deg, rgba(6,182,212,0.82), rgba(99,102,241,0.8));
}
.dark .stat-card {
  background:
    linear-gradient(160deg, rgba(15,23,42,0.98), rgba(30,41,59,0.92));
  border-color: rgba(255,255,255,0.06);
  box-shadow: 0 18px 40px rgba(2,6,23,0.28);
}
.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 20px 44px rgba(15,23,42,0.12);
  border-color: rgba(6,182,212,0.24);
}
.stat-icon-bg {
  width: 58px;
  height: 58px;
  border-radius: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.4rem;
  flex-shrink: 0;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.5);
}
.stat-card.cyan::before { background: linear-gradient(90deg, #06b6d4, #22d3ee); }
.stat-card.blue::before { background: linear-gradient(90deg, #3b82f6, #60a5fa); }
.stat-card.purple::before { background: linear-gradient(90deg, #8b5cf6, #a78bfa); }
.stat-card.green::before { background: linear-gradient(90deg, #10b981, #34d399); }
.stat-card.orange::before { background: linear-gradient(90deg, #f59e0b, #fbbf24); }
.stat-card.pink::before { background: linear-gradient(90deg, #ec4899, #f472b6); }
.stat-card.cyan .stat-icon-bg { background: linear-gradient(145deg, rgba(6,182,212,0.16), rgba(207,250,254,0.96)); }
.stat-card.blue .stat-icon-bg { background: linear-gradient(145deg, rgba(59,130,246,0.16), rgba(219,234,254,0.96)); }
.stat-card.purple .stat-icon-bg { background: linear-gradient(145deg, rgba(139,92,246,0.16), rgba(237,233,254,0.96)); }
.stat-card.green .stat-icon-bg { background: linear-gradient(145deg, rgba(16,185,129,0.16), rgba(209,250,229,0.96)); }
.stat-card.orange .stat-icon-bg { background: linear-gradient(145deg, rgba(245,158,11,0.16), rgba(254,243,199,0.96)); }
.stat-card.pink .stat-icon-bg { background: linear-gradient(145deg, rgba(236,72,153,0.16), rgba(252,231,243,0.96)); }
.dark .stat-card.cyan .stat-icon-bg { background: linear-gradient(145deg, rgba(6,182,212,0.18), rgba(8,47,73,0.92)); }
.dark .stat-card.blue .stat-icon-bg { background: linear-gradient(145deg, rgba(59,130,246,0.18), rgba(30,41,59,0.96)); }
.dark .stat-card.purple .stat-icon-bg { background: linear-gradient(145deg, rgba(139,92,246,0.18), rgba(49,46,129,0.88)); }
.dark .stat-card.green .stat-icon-bg { background: linear-gradient(145deg, rgba(16,185,129,0.18), rgba(6,78,59,0.9)); }
.dark .stat-card.orange .stat-icon-bg { background: linear-gradient(145deg, rgba(245,158,11,0.18), rgba(120,53,15,0.9)); }
.dark .stat-card.pink .stat-icon-bg { background: linear-gradient(145deg, rgba(236,72,153,0.18), rgba(80,7,36,0.88)); }
.stat-body {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}
.stat-label {
  font-size: 0.78rem;
  font-weight: 700;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.12em;
}
.stat-value {
  font-size: clamp(1.4rem, 2vw, 2rem);
  font-weight: 900;
  line-height: 1.05;
}
.stat-meta {
  font-size: 0.84rem;
  color: #64748b;
}
.dark .stat-meta {
  color: #94a3b8;
}

/* ===== Panel ===== */
.panel {
  position: relative;
  overflow: hidden;
  background: linear-gradient(160deg, rgba(255,255,255,0.98), rgba(248,250,252,0.92));
  border: 1px solid rgba(15,23,42,0.06);
  border-radius: 24px;
  padding: 24px;
  margin-bottom: 20px;
  box-shadow: 0 16px 36px rgba(15,23,42,0.06);
  transition: background 0.3s, border-color 0.3s, box-shadow 0.3s;
}
.panel::before {
  content: "";
  position: absolute;
  inset: 0 0 auto;
  height: 1px;
  background: linear-gradient(90deg, rgba(6,182,212,0.45), transparent 82%);
}
.dark .panel {
  background: linear-gradient(160deg, rgba(15,23,42,0.98), rgba(30,41,59,0.92));
  border-color: rgba(255,255,255,0.06);
  box-shadow: 0 18px 40px rgba(2,6,23,0.26);
}
.panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}
.panel-title {
  font-size: 1.15rem;
  font-weight: 800;
  margin: 0;
}
.panel > .panel-title {
  margin-bottom: 16px;
}
.panel-desc {
  color: #94a3b8;
  margin: 6px 0 0;
  font-size: 0.92rem;
  line-height: 1.6;
}
.panel > .panel-desc {
  margin: 0 0 20px;
}
.panel-actions {
  display: flex;
  gap: 12px;
  margin-top: 20px;
  flex-wrap: wrap;
}
.panel-note {
  font-size: 0.88rem;
  color: #64748b;
  line-height: 1.5;
}
.dark .panel-note {
  color: #94a3b8;
}

/* ===== Buttons ===== */
.btn-primary {
  padding: 12px 24px;
  border: none;
  border-radius: 12px;
  background: linear-gradient(135deg, #06b6d4, #6366f1);
  color: #fff;
  font-weight: 700;
  font-size: 0.95rem;
  cursor: pointer;
  transition: all 0.3s;
}
.btn-primary:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(6,182,212,0.25); }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-lg { padding: 14px 32px; font-size: 1rem; }
.btn-outline {
  padding: 12px 24px;
  border: 2px solid rgba(0,0,0,0.1);
  border-radius: 12px;
  background: transparent;
  color: inherit;
  font-weight: 700;
  font-size: 0.95rem;
  cursor: pointer;
  transition: all 0.3s;
}
.dark .btn-outline { border-color: rgba(255,255,255,0.1); }
.btn-outline:hover { border-color: #ef4444; color: #ef4444; }

/* ===== Quick Actions ===== */
.action-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 14px;
}
.quick-action {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 18px;
  min-height: 92px;
  border: 1px solid rgba(15,23,42,0.06);
  border-radius: 18px;
  background: linear-gradient(160deg, rgba(255,255,255,0.92), rgba(240,249,255,0.86));
  color: inherit;
  cursor: pointer;
  font-weight: 700;
  font-size: 0.94rem;
  text-align: left;
  transition: all 0.25s ease;
  box-shadow: 0 10px 22px rgba(15,23,42,0.05);
}
.dark .quick-action {
  border-color: rgba(255,255,255,0.06);
  background: linear-gradient(160deg, rgba(15,23,42,0.86), rgba(17,24,39,0.9));
}
.quick-action:hover {
  background: linear-gradient(160deg, rgba(236,254,255,0.96), rgba(224,242,254,0.92));
  border-color: rgba(6,182,212,0.32);
  transform: translateY(-3px);
  box-shadow: 0 16px 30px rgba(6,182,212,0.12);
}
.dark .quick-action:hover {
  background: linear-gradient(160deg, rgba(8,47,73,0.52), rgba(15,23,42,0.94));
}
.quick-action > span {
  font-size: 1.25rem;
}

/* ===== Log ===== */
.log-list {
  max-height: 320px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.log-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 16px;
  border: 1px solid rgba(15,23,42,0.06);
  border-radius: 16px;
  background: rgba(248,250,252,0.78);
}
.dark .log-item {
  border-color: rgba(255,255,255,0.06);
  background: rgba(15,23,42,0.6);
}
.log-icon {
  width: 42px;
  height: 42px;
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 14px;
  background: rgba(6,182,212,0.1);
  font-size: 1.1rem;
}
.dark .log-icon {
  background: rgba(34,211,238,0.14);
}
.log-body {
  flex: 1;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}
.log-msg {
  font-size: 0.92rem;
  font-weight: 600;
}
.log-time {
  font-size: 0.8rem;
  color: #94a3b8;
  white-space: nowrap;
}

/* ===== Export Controls ===== */
.export-controls { display: flex; flex-direction: column; gap: 16px; }
.input-row { display: flex; gap: 16px; flex-wrap: wrap; }
.input-group {
  display: flex; flex-direction: column; gap: 6px; flex: 1; min-width: 120px;
}
.input-group label { font-size: 0.82rem; font-weight: 700; color: #64748b; }
.dark .input-group label { color: #94a3b8; }
.input-group input, .setting-input {
  width: 100%;
  box-sizing: border-box;
  padding: 10px 14px;
  border: 2px solid rgba(0,0,0,0.08);
  border-radius: 10px;
  font-size: 0.95rem;
  background: transparent;
  color: inherit;
  transition: border-color 0.2s;
}
.dark .input-group input, .dark .setting-input { border-color: rgba(255,255,255,0.1); }
.input-group input:focus, .setting-input:focus { outline: none; border-color: #06b6d4; }

.quick-range-btns { display: flex; gap: 8px; flex-wrap: wrap; }
.quick-range-btns button {
  padding: 8px 16px;
  border: 2px solid rgba(6,182,212,0.3);
  border-radius: 10px;
  background: transparent;
  color: #06b6d4;
  font-weight: 700;
  font-size: 0.85rem;
  cursor: pointer;
  transition: all 0.2s;
}
.quick-range-btns button:hover { background: #06b6d4; color: #fff; }
.export-info { font-size: 0.9rem; color: #64748b; }
.dark .export-info { color: #94a3b8; }

/* ===== Data Table ===== */
.table-wrap { overflow-x: auto; border-radius: 12px; }
.data-table { width: 100%; border-collapse: collapse; font-size: 0.88rem; }
.data-table th {
  padding: 12px 14px;
  background: linear-gradient(135deg, #06b6d4, #0891b2);
  color: #fff;
  text-align: left;
  font-weight: 700;
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  white-space: nowrap;
}
.data-table td {
  padding: 10px 14px;
  border-bottom: 1px solid rgba(0,0,0,0.05);
}
.dark .data-table td { border-bottom-color: rgba(255,255,255,0.05); }
.data-table tbody tr:hover { background: rgba(6,182,212,0.04); }
.empty-row { text-align: center; color: #94a3b8; padding: 24px !important; }

/* ===== Devices ===== */
.device-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(280px, 1fr));
  gap: 18px;
  align-items: stretch;
}
.device-card {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 14px;
  padding: 20px;
  min-height: 228px;
  border-radius: 18px;
  border: 1px solid rgba(15,23,42,0.06);
  background: linear-gradient(160deg, rgba(255,255,255,0.98), rgba(248,250,252,0.92));
  box-shadow: 0 14px 30px rgba(15,23,42,0.05);
  transition: transform 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease;
}
.device-card::before {
  content: "";
  position: absolute;
  inset: 0 0 auto;
  height: 4px;
  border-radius: 18px 18px 0 0;
  background: linear-gradient(90deg, rgba(6,182,212,0.82), rgba(99,102,241,0.78));
}
.device-card.online::before {
  background: linear-gradient(90deg, #10b981, #34d399);
}
.device-card.warning::before {
  background: linear-gradient(90deg, #f59e0b, #fbbf24);
}
.device-card.offline::before {
  background: linear-gradient(90deg, #ef4444, #f87171);
}
.dark .device-card {
  border-color: rgba(255,255,255,0.06);
  background: linear-gradient(160deg, rgba(15,23,42,0.96), rgba(30,41,59,0.9));
  box-shadow: 0 18px 38px rgba(2,6,23,0.28);
}
.device-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 18px 34px rgba(15,23,42,0.1);
  border-color: rgba(6,182,212,0.2);
}
.device-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
}
.device-icon {
  width: 58px;
  height: 58px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 1.75rem;
  border-radius: 18px;
  background: linear-gradient(145deg, rgba(6,182,212,0.16), rgba(224,242,254,0.95));
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.55);
}
.dark .device-icon {
  background: linear-gradient(145deg, rgba(34,211,238,0.14), rgba(8,47,73,0.92));
}
.device-info {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-height: 72px;
}
.device-info strong {
  display: block;
  width: 100%;
  font-size: 1rem;
  line-height: 1.22;
  font-weight: 800;
  letter-spacing: -0.01em;
  text-wrap: balance;
  word-break: normal;
  overflow-wrap: normal;
}
.device-id {
  display: block;
  width: 100%;
  font-size: 0.76rem;
  color: #64748b;
  font-family: monospace;
  line-height: 1.35;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.device-type {
  display: -webkit-box;
  overflow: hidden;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  font-size: 0.88rem;
  color: #94a3b8;
  line-height: 1.5;
  min-height: calc(1.5em * 2);
}
.device-status-wrap {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 9px 14px;
  border-radius: 999px;
  white-space: nowrap;
  border: 1px solid rgba(15,23,42,0.06);
  background: rgba(248,250,252,0.86);
  flex-shrink: 0;
}
.dark .device-status-wrap {
  border-color: rgba(255,255,255,0.08);
  background: rgba(15,23,42,0.68);
}
.device-status-wrap.online {
  color: #047857;
  background: rgba(16,185,129,0.1);
}
.device-status-wrap.warning {
  color: #b45309;
  background: rgba(245,158,11,0.12);
}
.device-status-wrap.offline {
  color: #b91c1c;
  background: rgba(239,68,68,0.1);
}
.dark .device-status-wrap.online {
  color: #6ee7b7;
}
.dark .device-status-wrap.warning {
  color: #fcd34d;
}
.dark .device-status-wrap.offline {
  color: #fca5a5;
}
.device-status-dot { width: 8px; height: 8px; border-radius: 50%; }
.device-status-dot.online { background: #10b981; box-shadow: 0 0 8px rgba(16,185,129,0.4); }
.device-status-dot.warning { background: #f59e0b; box-shadow: 0 0 8px rgba(245,158,11,0.4); }
.device-status-dot.offline { background: #ef4444; box-shadow: 0 0 8px rgba(239,68,68,0.4); }
.device-status-text { font-size: 0.82rem; font-weight: 700; }
.device-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding-top: 10px;
  border-top: 1px solid rgba(15,23,42,0.06);
  margin-top: auto;
}
.dark .device-meta {
  border-top-color: rgba(255,255,255,0.06);
}
.device-last-label {
  font-size: 0.74rem;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  line-height: 1.35;
}
.device-last {
  font-size: 0.8rem;
  color: #64748b;
  white-space: nowrap;
  font-weight: 600;
  line-height: 1.35;
}
.dark .device-last {
  color: #cbd5e1;
}

/* ===== Alerts ===== */
.alert-panel {
  overflow: hidden;
}
.alert-summary {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 11px 16px;
  border-radius: 999px;
  border: 1px solid rgba(15,23,42,0.08);
  background: rgba(248,250,252,0.86);
  font-size: 0.88rem;
  font-weight: 700;
  color: #0f172a;
}
.alert-summary.ok {
  color: #0f766e;
  background: linear-gradient(135deg, rgba(209,250,229,0.92), rgba(204,251,241,0.92));
  border-color: rgba(45,212,191,0.24);
  box-shadow: 0 10px 20px rgba(20,184,166,0.1);
}
.alert-summary.danger {
  color: #be123c;
  background: linear-gradient(135deg, rgba(255,228,230,0.94), rgba(255,241,242,0.92));
  border-color: rgba(251,113,133,0.22);
  box-shadow: 0 10px 20px rgba(244,63,94,0.08);
}
.dark .alert-summary {
  border-color: rgba(255,255,255,0.08);
  background: rgba(15,23,42,0.72);
  color: #e2e8f0;
}
.dark .alert-summary.ok {
  color: #5eead4;
}
.dark .alert-summary.danger {
  color: #fda4af;
}
.alert-summary-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: currentColor;
  box-shadow: 0 0 0 5px rgba(255,255,255,0.24);
}
.dark .alert-summary-dot {
  box-shadow: 0 0 0 5px rgba(15,23,42,0.45);
}
.alert-grid {
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  gap: 18px;
  align-items: stretch;
}
.alert-card {
  position: relative;
  grid-column: span 4;
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 20px;
  min-height: 236px;
  border-radius: 20px;
  border: 1px solid rgba(0,0,0,0.06);
  background: linear-gradient(160deg, rgba(255,255,255,0.98), rgba(248,250,252,0.94));
  box-shadow: 0 14px 28px rgba(15,23,42,0.05);
  transition: transform 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease;
}
.alert-card::before {
  content: "";
  position: absolute;
  inset: 0 0 auto;
  height: 4px;
  border-radius: 20px 20px 0 0;
  background: linear-gradient(90deg, rgba(6,182,212,0.8), rgba(99,102,241,0.72));
}
.alert-card.alert-danger::before {
  background: linear-gradient(90deg, #f43f5e, #fb7185);
}
.alert-card.alert-ok::before {
  background: linear-gradient(90deg, #14b8a6, #2dd4bf);
}
.alert-card.alert-ok {
  border-color: rgba(45,212,191,0.22);
  background:
    radial-gradient(circle at top right, rgba(153,246,228,0.32), transparent 42%),
    linear-gradient(160deg, rgba(245,255,252,0.98), rgba(236,253,245,0.92));
  box-shadow: 0 16px 32px rgba(20,184,166,0.09);
}
.alert-card.alert-danger {
  border-color: rgba(251,113,133,0.2);
  background:
    radial-gradient(circle at top right, rgba(254,205,211,0.34), transparent 42%),
    linear-gradient(160deg, rgba(255,251,252,0.98), rgba(255,241,242,0.92));
  box-shadow: 0 16px 32px rgba(244,63,94,0.08);
}
.alert-card:nth-last-child(2),
.alert-card:last-child {
  grid-column: span 6;
}
.dark .alert-card {
  border-color: rgba(255,255,255,0.06);
  background: linear-gradient(160deg, rgba(15,23,42,0.96), rgba(30,41,59,0.9));
  box-shadow: 0 18px 34px rgba(2,6,23,0.28);
}
.dark .alert-card.alert-ok {
  border-color: rgba(45,212,191,0.18);
  background:
    radial-gradient(circle at top right, rgba(20,184,166,0.18), transparent 42%),
    linear-gradient(160deg, rgba(15,23,42,0.96), rgba(12,74,64,0.62));
}
.dark .alert-card.alert-danger {
  border-color: rgba(251,113,133,0.16);
  background:
    radial-gradient(circle at top right, rgba(244,63,94,0.16), transparent 42%),
    linear-gradient(160deg, rgba(15,23,42,0.96), rgba(76,5,25,0.5));
}
.alert-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 18px 34px rgba(15,23,42,0.1);
  border-color: rgba(6,182,212,0.2);
}
.alert-card.alert-ok:hover {
  box-shadow: 0 20px 38px rgba(20,184,166,0.16);
  border-color: rgba(45,212,191,0.32);
}
.alert-card.alert-danger:hover {
  box-shadow: 0 20px 38px rgba(244,63,94,0.14);
  border-color: rgba(251,113,133,0.28);
}
.alert-card-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}
.alert-header {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  margin-bottom: 0;
  min-width: 0;
  flex: 1;
}
.alert-icon-wrap {
  width: 54px;
  height: 54px;
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 16px;
  background: linear-gradient(145deg, rgba(6,182,212,0.16), rgba(224,242,254,0.95));
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.55);
}
.dark .alert-icon-wrap {
  background: linear-gradient(145deg, rgba(34,211,238,0.14), rgba(8,47,73,0.92));
}
.alert-card.alert-ok .alert-icon-wrap {
  background: linear-gradient(145deg, rgba(153,246,228,0.62), rgba(236,253,245,0.98));
}
.alert-card.alert-danger .alert-icon-wrap {
  background: linear-gradient(145deg, rgba(255,228,230,0.96), rgba(255,241,242,0.98));
}
.dark .alert-card.alert-ok .alert-icon-wrap {
  background: linear-gradient(145deg, rgba(45,212,191,0.18), rgba(15,118,110,0.42));
}
.dark .alert-card.alert-danger .alert-icon-wrap {
  background: linear-gradient(145deg, rgba(251,113,133,0.18), rgba(136,19,55,0.38));
}
.alert-icon {
  font-size: 1.6rem;
}
.alert-header-copy {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.alert-header-copy strong {
  font-size: 1rem;
  line-height: 1.28;
}
.alert-card.alert-ok .alert-header-copy strong {
  color: #0f766e;
}
.alert-card.alert-danger .alert-header-copy strong {
  color: #e11d48;
}
.dark .alert-card.alert-ok .alert-header-copy strong {
  color: #5eead4;
}
.dark .alert-card.alert-danger .alert-header-copy strong {
  color: #fda4af;
}
.alert-current {
  font-size: 0.85rem;
  color: #64748b;
}
.dark .alert-current {
  color: #94a3b8;
}
.alert-badge {
  display: inline-flex;
  align-items: center;
  padding: 8px 12px;
  border-radius: 999px;
  font-size: 0.76rem;
  font-weight: 800;
  white-space: nowrap;
  border: 1px solid rgba(15,23,42,0.06);
  background: rgba(248,250,252,0.86);
}
.dark .alert-badge {
  border-color: rgba(255,255,255,0.08);
  background: rgba(15,23,42,0.68);
}
.alert-badge.alert-ok {
  color: #0f766e;
  background: linear-gradient(135deg, rgba(209,250,229,0.92), rgba(204,251,241,0.92));
  border-color: rgba(45,212,191,0.2);
}
.alert-badge.alert-danger {
  color: #be123c;
  background: linear-gradient(135deg, rgba(255,228,230,0.94), rgba(255,241,242,0.92));
  border-color: rgba(251,113,133,0.2);
}
.dark .alert-badge.alert-ok {
  color: #5eead4;
}
.dark .alert-badge.alert-danger {
  color: #fda4af;
}
.alert-inputs {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}
.alert-inputs .input-group { flex: 1; }
.alert-status {
  margin-top: auto;
  min-height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 10px 14px;
  border-radius: 14px;
  font-size: 0.84rem;
  font-weight: 700;
  text-align: center;
  border: 1px solid transparent;
}
.alert-ok {
  background: linear-gradient(135deg, rgba(209,250,229,0.92), rgba(204,251,241,0.92));
  color: #0f766e;
  border-color: rgba(45,212,191,0.18);
}
.dark .alert-ok {
  color: #5eead4;
  background: linear-gradient(135deg, rgba(20,83,45,0.32), rgba(17,94,89,0.3));
  border-color: rgba(45,212,191,0.14);
}
.alert-danger {
  background: linear-gradient(135deg, rgba(255,228,230,0.96), rgba(255,241,242,0.94));
  color: #e11d48;
  border-color: rgba(251,113,133,0.16);
}
.dark .alert-danger {
  color: #fda4af;
  background: linear-gradient(135deg, rgba(127,29,29,0.3), rgba(136,19,55,0.28));
  border-color: rgba(251,113,133,0.14);
}
.alert-actions {
  align-items: center;
  justify-content: space-between;
}

/* ===== Settings ===== */
.settings-list { display: flex; flex-direction: column; gap: 4px; }
.setting-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 0;
  border-bottom: 1px solid rgba(0,0,0,0.05);
  flex-wrap: wrap;
}
.dark .setting-row { border-bottom-color: rgba(255,255,255,0.05); }
.setting-info { flex: 1; min-width: 200px; }
.setting-info strong { display: block; font-size: 0.92rem; }
.setting-info span { font-size: 0.82rem; color: #94a3b8; }
.setting-input { width: 150px; text-align: right; }
.setting-input.wide { width: 300px; text-align: left; font-family: monospace; font-size: 0.82rem; }

/* Toggle Switch */
.toggle-switch { position: relative; display: inline-block; width: 50px; height: 28px; cursor: pointer; }
.toggle-switch input { opacity: 0; width: 0; height: 0; }
.toggle-slider {
  position: absolute; inset: 0;
  background: rgba(0,0,0,0.15);
  border-radius: 28px;
  transition: 0.3s;
}
.dark .toggle-slider { background: rgba(255,255,255,0.12); }
.toggle-slider::before {
  content: '';
  position: absolute;
  height: 22px; width: 22px;
  left: 3px; bottom: 3px;
  background: white;
  border-radius: 50%;
  transition: 0.3s;
}
.toggle-switch input:checked + .toggle-slider { background: #06b6d4; }
.toggle-switch input:checked + .toggle-slider::before { transform: translateX(22px); }

/* ===== Info Grid ===== */
.system-info-panel {
  overflow: hidden;
}
.system-stack-pill {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 11px 16px;
  border-radius: 999px;
  border: 1px solid rgba(6,182,212,0.16);
  background: linear-gradient(135deg, rgba(236,254,255,0.96), rgba(224,242,254,0.92));
  color: #0f766e;
  font-size: 0.88rem;
  font-weight: 700;
  box-shadow: 0 10px 20px rgba(14,165,233,0.08);
}
.dark .system-stack-pill {
  border-color: rgba(34,211,238,0.14);
  background: linear-gradient(135deg, rgba(8,47,73,0.64), rgba(15,23,42,0.82));
  color: #67e8f9;
}
.system-stack-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: currentColor;
  box-shadow: 0 0 0 5px rgba(255,255,255,0.24);
}
.dark .system-stack-dot {
  box-shadow: 0 0 0 5px rgba(15,23,42,0.45);
}
.info-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}
.info-item {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 18px;
  min-height: 160px;
  border-radius: 20px;
  border: 1px solid rgba(15,23,42,0.06);
  background: linear-gradient(160deg, rgba(255,255,255,0.98), rgba(248,250,252,0.92));
  box-shadow: 0 14px 28px rgba(15,23,42,0.05);
  transition: transform 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease;
}
.info-item::before {
  content: "";
  position: absolute;
  inset: 0 0 auto;
  height: 4px;
  border-radius: 20px 20px 0 0;
  background: linear-gradient(90deg, rgba(6,182,212,0.8), rgba(99,102,241,0.72));
}
.info-item:hover {
  transform: translateY(-4px);
  box-shadow: 0 18px 34px rgba(15,23,42,0.09);
}
.dark .info-item {
  border-color: rgba(255,255,255,0.06);
  background: linear-gradient(160deg, rgba(15,23,42,0.96), rgba(30,41,59,0.9));
  box-shadow: 0 18px 34px rgba(2,6,23,0.28);
}
.info-item-head {
  display: flex;
  align-items: center;
  gap: 12px;
}
.info-icon {
  width: 46px;
  height: 46px;
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 1.3rem;
  border-radius: 15px;
  background: linear-gradient(145deg, rgba(6,182,212,0.16), rgba(224,242,254,0.95));
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.55);
}
.dark .info-icon {
  background: linear-gradient(145deg, rgba(34,211,238,0.14), rgba(8,47,73,0.92));
}
.info-label {
  font-size: 0.8rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: #64748b;
}
.dark .info-label {
  color: #94a3b8;
}
.info-item strong {
  font-size: 1.06rem;
  line-height: 1.35;
  font-weight: 800;
  color: #1e293b;
}
.dark .info-item strong {
  color: #f8fafc;
}
.info-note {
  margin-top: auto;
  font-size: 0.85rem;
  line-height: 1.55;
  color: #64748b;
}
.dark .info-note {
  color: #94a3b8;
}
.info-item.cyan::before { background: linear-gradient(90deg, #06b6d4, #38bdf8); }
.info-item.blue::before { background: linear-gradient(90deg, #3b82f6, #60a5fa); }
.info-item.violet::before { background: linear-gradient(90deg, #8b5cf6, #a78bfa); }
.info-item.amber::before { background: linear-gradient(90deg, #f59e0b, #fbbf24); }
.info-item.slate::before { background: linear-gradient(90deg, #64748b, #94a3b8); }
.info-item.rose::before { background: linear-gradient(90deg, #f43f5e, #fb7185); }
.info-item.emerald::before { background: linear-gradient(90deg, #10b981, #34d399); }
.info-item.cyan .info-icon {
  background: linear-gradient(145deg, rgba(207,250,254,0.92), rgba(224,242,254,0.98));
}
.info-item.blue .info-icon {
  background: linear-gradient(145deg, rgba(219,234,254,0.94), rgba(239,246,255,0.98));
}
.info-item.violet .info-icon {
  background: linear-gradient(145deg, rgba(237,233,254,0.94), rgba(245,243,255,0.98));
}
.info-item.amber .info-icon {
  background: linear-gradient(145deg, rgba(254,243,199,0.94), rgba(255,251,235,0.98));
}
.info-item.slate .info-icon {
  background: linear-gradient(145deg, rgba(226,232,240,0.94), rgba(248,250,252,0.98));
}
.info-item.rose .info-icon {
  background: linear-gradient(145deg, rgba(255,228,230,0.94), rgba(255,241,242,0.98));
}
.info-item.emerald .info-icon {
  background: linear-gradient(145deg, rgba(209,250,229,0.94), rgba(236,253,245,0.98));
}
.dark .info-item.cyan .info-icon {
  background: linear-gradient(145deg, rgba(8,145,178,0.22), rgba(12,74,110,0.42));
}
.dark .info-item.blue .info-icon {
  background: linear-gradient(145deg, rgba(59,130,246,0.2), rgba(30,64,175,0.38));
}
.dark .info-item.violet .info-icon {
  background: linear-gradient(145deg, rgba(139,92,246,0.2), rgba(91,33,182,0.38));
}
.dark .info-item.amber .info-icon {
  background: linear-gradient(145deg, rgba(245,158,11,0.2), rgba(146,64,14,0.38));
}
.dark .info-item.slate .info-icon {
  background: linear-gradient(145deg, rgba(100,116,139,0.22), rgba(51,65,85,0.44));
}
.dark .info-item.rose .info-icon {
  background: linear-gradient(145deg, rgba(244,63,94,0.2), rgba(136,19,55,0.38));
}
.dark .info-item.emerald .info-icon {
  background: linear-gradient(145deg, rgba(16,185,129,0.2), rgba(6,95,70,0.38));
}

/* ===== Responsive ===== */
@media (max-width: 1440px) {
  .device-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 1180px) {
  .info-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .alert-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .alert-card,
  .alert-card:nth-last-child(2),
  .alert-card:last-child {
    grid-column: span 1;
  }
  .device-card {
    min-height: 0;
  }
  .device-card-head {
    align-items: flex-start;
  }
  .device-status-wrap {
    align-self: flex-start;
  }
  .device-type {
    min-height: 0;
  }
  .device-meta {
    flex-direction: column;
    align-items: flex-start;
  }
}

@media (max-width: 900px) {
  .admin { flex-direction: column; }
  
  /* Sidebar as Drawer */
  .sidebar {
    position: fixed;
    top: 0;
    left: -280px;
    width: 280px;
    height: 100vh;
    z-index: 200;
    transition: transform 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    background: #fff;
    box-shadow: 10px 0 30px rgba(0,0,0,0.1);
    overflow-y: auto;
    border-right: none;
  }
  .dark .sidebar { background: #111827; box-shadow: 10px 0 30px rgba(0,0,0,0.4); }
  .sidebar.mobile-open { transform: translateX(280px); }

  .sidebar-brand { 
    margin: 14px 14px 10px;
    padding: 16px;
    justify-content: space-between;
  }
  .brand-logo-wrap { width: 48px; height: 48px; border-radius: 16px; }
  .brand-logo { width: 28px; height: 28px; }
  .brand-title { font-size: 1.14rem; }
  .brand-role { width: 146px; font-size: 0.64rem; letter-spacing: 0.14em; padding: 7px 10px; }
  
  .menu-close-btn {
    display: flex;
  }

  .nav { padding: 16px 12px 18px; gap: 10px; flex-direction: column; }
  .nav-item { padding: 14px 16px; width: 100%; border-radius: 18px; }
  .nav-label { display: block; }
  .nav-icon { width: 42px; height: 42px; font-size: 1.25rem; }

  .sidebar-footer { 
    display: block; 
    margin-top: auto; 
    padding: 20px 14px 18px;
    border-top: 1px solid rgba(0,0,0,0.06);
  }
  .dark .sidebar-footer { border-top-color: rgba(255,255,255,0.08); }

  .mobile-overlay {
    position: fixed; inset: 0;
    background: rgba(0, 0, 0, 0.4);
    backdrop-filter: blur(4px);
    z-index: 150;
    animation: fadeIn 0.3s ease;
  }
  @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }

  /* Top Bar & Burger */
  .topbar {
    padding: 14px 20px;
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    background: #fff;
    border-bottom: 1px solid rgba(0,0,0,0.06);
    position: sticky; top: 0; z-index: 100;
  }
  .dark .topbar { background: #111827; border-bottom-color: rgba(255,255,255,0.06); }
  
  .topbar-left { display: flex; align-items: center; gap: 16px; }
  .topbar-info { display: flex; flex-direction: column; }
  
  .burger-btn {
    display: flex; flex-direction: column; gap: 4px;
    width: 42px; height: 42px;
    padding: 10px;
    border: 1px solid rgba(0,0,0,0.08); border-radius: 10px;
    background: transparent; cursor: pointer;
    transition: 0.2s;
  }
  .dark .burger-btn { border-color: rgba(255,255,255,0.08); }
  .burger-btn span {
    display: block; width: 100%; height: 2px;
    background: var(--text-primary);
    border-radius: 4px; transition: 0.3s;
  }
  .burger-btn:hover { background: rgba(6,182,212,0.08); border-color: #06b6d4; }
  
  .page-title { font-size: 1rem; text-align: left; }
  .page-subtitle { font-size: 0.7rem; text-align: left; }
  
  .topbar-right { width: auto; justify-content: flex-end; }
  .status-pill { padding: 6px 12px; font-size: 0.7rem; }
  
  .overview-head {
    flex-direction: column;
    align-items: flex-start;
    padding: 22px;
  }
  .overview-badges {
    justify-content: flex-start;
  }

  .section { padding: 20px 16px 40px; }
  .device-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 600px) {
  .overview-head {
    padding: 20px 18px;
  }
  .overview-title {
    font-size: 1.2rem;
  }
  .overview-badges {
    width: 100%;
  }
  .stat-grid { grid-template-columns: 1fr; }
  .stat-card {
    min-height: 112px;
    padding: 18px;
  }
  .panel { padding: 20px 16px; }
  .log-body {
    flex-direction: column;
    align-items: flex-start;
  }
  .input-row { flex-direction: column; }
  .system-stack-pill {
    width: 100%;
    justify-content: center;
  }
  .info-grid {
    grid-template-columns: 1fr;
  }
  .info-item {
    min-height: 0;
  }
  .alert-grid {
    grid-template-columns: 1fr;
  }
  .alert-card {
    min-height: 0;
  }
  .alert-card-top {
    flex-direction: column;
  }
  .alert-badge {
    align-self: flex-start;
  }
  .alert-inputs {
    grid-template-columns: 1fr;
  }
  .setting-row { flex-direction: column; align-items: flex-start; gap: 8px; }
  .setting-input { width: 100% !important; text-align: left; }
  .panel-actions { flex-direction: column; }
  .btn-primary, .btn-outline { width: 100%; justify-content: center; }
}
</style>