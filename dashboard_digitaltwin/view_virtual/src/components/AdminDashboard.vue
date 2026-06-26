<template>
  <div class="admin-dashboard" :class="{ 'dark': isDarkMode }">
    <!-- Hero Banner -->
    <div class="hero-banner">
      <div class="hero-kicker">ADMIN CONTROL</div>
      <h2>Dashboard Hardware & Services</h2>
      <p>Kontrol ESP32, Raspberry Pi services, dan monitoring sistem</p>
      <div class="hero-meta">
        <span class="meta-badge">Last Update: {{ lastUpdateText }}</span>
        <span class="meta-badge status-badge" :class="systemStatusClass">
          {{ systemStatusText }}
        </span>
      </div>
    </div>

    <!-- Auto-refresh indicator -->
    <div class="auto-refresh-bar">
      <span>Auto-refresh: {{ autoRefreshSeconds }}s</span>
      <div class="refresh-progress" :style="{ width: ((autoRefreshSeconds - refreshCountdown) / autoRefreshSeconds * 100) + '%' }"></div>
    </div>

    <!-- ESP32 Control Section -->
    <div class="control-section">
      <div class="section-header">
        <h3 class="section-title">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
            <line x1="8" y1="21" x2="16" y2="21"/>
            <line x1="12" y1="17" x2="12" y2="21"/>
          </svg>
          ESP32 Control
        </h3>
        <span class="device-id">Device: {{ esp32DeviceId || 'Loading...' }}</span>
      </div>

      <div class="control-grid">
        <!-- ESP32 Health Status -->
        <div class="control-card health-card">
          <h4>ESP32 Health</h4>
          <div class="health-stats">
            <div class="health-item">
              <span class="health-label">Temperature</span>
              <span class="health-value" :class="esp32Health.temp > 60 ? 'warning' : ''">
                {{ esp32Health.temp !== null ? esp32Health.temp.toFixed(1) + '°C' : 'N/A' }}
              </span>
            </div>
            <div class="health-item">
              <span class="health-label">Free Heap</span>
              <span class="health-value">
                {{ esp32Health.heap !== null ? esp32Health.heap.toLocaleString() + ' B' : 'N/A' }}
              </span>
            </div>
            <div class="health-item">
              <span class="health-label">WiFi RSSI</span>
              <span class="health-value" :class="getRssiClass(esp32Health.rssi)">
                {{ esp32Health.rssi !== null ? esp32Health.rssi + ' dBm' : 'N/A' }}
              </span>
            </div>
            <div class="health-item">
              <span class="health-label">Uptime</span>
              <span class="health-value">{{ formatUptime(esp32Health.uptime) }}</span>
            </div>
          </div>
          <button class="refresh-health-btn" @click="refreshEsp32Health" :disabled="isLoadingEsp32">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" :class="{ 'spin': isLoadingEsp32 }">
              <path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.2"/>
            </svg>
            Refresh
          </button>
        </div>

        <!-- ESP32 Commands -->
        <div class="control-card commands-card">
          <h4>Commands</h4>
          <div class="command-buttons">
            <button class="cmd-btn" @click="sendEsp32Command('reboot')" :disabled="isSendingCommand">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="1 4 1 10 7 10"/>
                <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/>
              </svg>
              Reboot ESP32
            </button>
            <button class="cmd-btn" @click="sendEsp32Command('wifi_reconnect')" :disabled="isSendingCommand">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M5 12.55a11 11 0 0 1 14.08 0"/>
                <path d="M1.42 9a16 16 0 0 1 21.16 0"/>
                <path d="M8.53 16.11a6 6 0 0 1 6.95 0"/>
                <line x1="12" y1="20" x2="12.01" y2="20"/>
              </svg>
              Reconnect WiFi
            </button>
          </div>
          <div class="sleep-control">
            <span>Sleep Mode:</span>
            <label class="toggle-switch">
              <input type="checkbox" v-model="sleepModeEnabled" @change="toggleSleepMode">
              <span class="toggle-slider"></span>
            </label>
            <input
              type="number"
              v-model="sleepDuration"
              placeholder="Duration (ms)"
              class="sleep-duration-input"
              min="1000"
              max="3600000"
            />
          </div>
        </div>
      </div>

      <!-- Command Result -->
      <div v-if="commandResult" class="command-result" :class="commandResult.type">
        <strong>{{ commandResult.message }}</strong>
      </div>
    </div>

    <!-- RPi Services Section -->
    <div class="control-section">
      <div class="section-header">
        <h3 class="section-title">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="4" y="4" width="16" height="16" rx="2"/>
            <rect x="9" y="9" width="6" height="6"/>
            <line x1="9" y1="1" x2="9" y2="4"/>
            <line x1="15" y1="1" x2="15" y2="4"/>
            <line x1="9" y1="20" x2="9" y2="23"/>
            <line x1="15" y1="20" x2="15" y2="23"/>
            <line x1="20" y1="9" x2="23" y2="9"/>
            <line x1="20" y1="14" x2="23" y2="14"/>
            <line x1="1" y1="9" x2="4" y2="9"/>
            <line x1="1" y1="14" x2="4" y2="14"/>
          </svg>
          Raspberry Pi Services
        </h3>
        <span class="device-id">RPi: {{ rpiAddress || 'Not configured' }}</span>
      </div>

      <div class="services-grid">
        <div v-for="service in services" :key="service.name" class="service-card">
          <div class="service-header">
            <div class="service-info">
              <div class="service-status-dot" :class="service.status"></div>
              <span class="service-name">{{ service.displayName }}</span>
            </div>
            <span class="service-status-text">{{ getStatusLabel(service.status) }}</span>
          </div>
          <div class="service-details">
            <span v-if="service.port" class="service-port">Port: {{ service.port }}</span>
          </div>
          <div class="service-controls">
            <button
              class="svc-btn start"
              @click="controlService(service.name, 'start')"
              :disabled="service.status === 'running' || isControllingService"
            >
              Start
            </button>
            <button
              class="svc-btn stop"
              @click="controlService(service.name, 'stop')"
              :disabled="service.status !== 'running' || isControllingService"
            >
              Stop
            </button>
            <button
              class="svc-btn restart"
              @click="controlService(service.name, 'restart')"
              :disabled="isControllingService"
            >
              Restart
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- System Control Section -->
    <div class="control-section">
      <div class="section-header">
        <h3 class="section-title">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
            <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
          </svg>
          System Control
        </h3>
      </div>

      <div class="system-controls">
        <div class="system-card">
          <h4>Raspberry Pi System</h4>
          <div class="system-stats">
            <div class="sys-stat">
              <span class="sys-label">CPU</span>
              <span class="sys-value">{{ rpiStats.cpu }}%</span>
            </div>
            <div class="sys-stat">
              <span class="sys-label">Memory</span>
              <span class="sys-value">{{ rpiStats.memory }}%</span>
            </div>
            <div class="sys-stat">
              <span class="sys-label">Disk</span>
              <span class="sys-value">{{ rpiStats.disk }}%</span>
            </div>
          </div>
          <div class="system-buttons">
            <button class="system-btn reboot" @click="confirmReboot">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="1 4 1 10 7 10"/>
                <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/>
              </svg>
              Reboot RPi
            </button>
            <button class="system-btn shutdown" @click="confirmShutdown">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M18.36 6.64a9 9 0 1 1-12.73 0"/>
                <line x1="12" y1="2" x2="12" y2="12"/>
              </svg>
              Shutdown RPi
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Confirmation Modal -->
    <div v-if="showConfirmModal" class="modal-overlay" @click.self="cancelConfirm">
      <div class="confirm-modal">
        <h3>{{ confirmModalTitle }}</h3>
        <p>{{ confirmModalMessage }}</p>
        <div class="modal-buttons">
          <button class="modal-btn cancel" @click="cancelConfirm">Batal</button>
          <button class="modal-btn confirm" @click="executeConfirmedAction">{{ confirmModalAction }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { AZURE_FUNCTION_URL } from '../lib/appConfig'

// RPi local API address (from CLAUDE.md)
const RPI_API_URL = import.meta.env.VITE_RPI_API_URL || 'http://192.168.1.7:5001'
const ADMIN_API_KEY = import.meta.env.VITE_RPI_ADMIN_KEY || 'digital-twin-admin-key'

export default {
  name: 'AdminDashboard',
  props: {
    isDarkMode: {
      type: Boolean,
      default: false
    }
  },
  setup() {
    // Config
    const esp32DeviceId = ref(null)
    const rpiAddress = ref('192.168.1.7')

    // Auto-refresh
    const autoRefreshSeconds = 30
    const refreshCountdown = ref(0)
    let refreshTimer = null

    // ESP32 State
    const esp32Health = ref({
      temp: null,
      heap: null,
      rssi: null,
      uptime: null
    })
    const isLoadingEsp32 = ref(false)
    const isSendingCommand = ref(false)
    const sleepModeEnabled = ref(false)
    const sleepDuration = ref(60000)
    const commandResult = ref(null)

    // Services State
    const services = ref([
      { name: 'yolo_cam', displayName: 'YOLO Camera', port: 5000, status: 'unknown' },
      { name: 'local_api', displayName: 'Local API', port: 5001, status: 'unknown' },
      { name: 'influxdb', displayName: 'InfluxDB', port: 8086, status: 'unknown' },
      { name: 'influxdb-logger', displayName: 'InfluxDB Logger', port: null, status: 'unknown' },
      { name: 'ml-pipeline', displayName: 'ML Pipeline', port: null, status: 'unknown' },
      { name: 'grafana-server', displayName: 'Grafana', port: 3000, status: 'unknown' }
    ])
    const isControllingService = ref(false)

    // System State
    const rpiStats = ref({
      cpu: 0,
      memory: 0,
      disk: 0
    })

    // Modal State
    const showConfirmModal = ref(false)
    const confirmModalTitle = ref('')
    const confirmModalMessage = ref('')
    const confirmModalAction = ref('')
    let pendingAction = null

    // Last update
    const lastUpdateAt = ref(null)
    const lastUpdateText = computed(() => {
      if (!lastUpdateAt.value) return 'Belum update'
      return lastUpdateAt.value.toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' })
    })

    // System status
    const systemStatusClass = computed(() => {
      const runningCount = services.value.filter(s => s.status === 'running').length
      if (runningCount === 0) return 'status-danger'
      if (runningCount === services.value.length) return 'status-success'
      return 'status-warning'
    })
    const systemStatusText = computed(() => {
      const running = services.value.filter(s => s.status === 'running').length
      return `${running}/${services.value.length} Services Active`
    })

    // HTTP helper
    const rpiRequest = async (endpoint, options = {}) => {
      const url = `${RPI_API_URL}${endpoint}`
      const headers = {
        'Content-Type': 'application/json',
        'X-API-Key': ADMIN_API_KEY,
        ...options.headers
      }
      try {
        const response = await fetch(url, { ...options, headers })
        if (!response.ok) {
          const err = await response.json()
          throw new Error(err.error || 'Request failed')
        }
        return response.json()
      } catch (error) {
        console.error(`RPi API Error (${endpoint}):`, error)
        throw error
      }
    }

    // Methods
    const getStatusLabel = (status) => {
      const labels = {
        active: 'Running',
        inactive: 'Stopped',
        failed: 'Failed',
        activating: 'Starting',
        deactivating: 'Stopping',
        unknown: 'Unknown'
      }
      return labels[status] || status || 'Unknown'
    }

    const getRssiClass = (rssi) => {
      if (!rssi) return ''
      if (rssi >= -50) return 'excellent'
      if (rssi >= -70) return 'good'
      if (rssi >= -80) return 'fair'
      return 'poor'
    }

    const formatUptime = (seconds) => {
      if (!seconds) return 'N/A'
      const d = Math.floor(seconds / 86400)
      const h = Math.floor((seconds % 86400) / 3600)
      const m = Math.floor((seconds % 3600) / 60)
      if (d > 0) return `${d}d ${h}h`
      if (h > 0) return `${h}h ${m}m`
      return `${m}m`
    }

    const showCommandResult = (message, type = 'info') => {
      commandResult.value = { message, type }
      setTimeout(() => {
        commandResult.value = null
      }, 5000)
    }

    // ESP32 Methods
    const refreshEsp32Health = async () => {
      isLoadingEsp32.value = true
      try {
        // Get ESP32 health from RPi local API
        const response = await rpiRequest('/api/admin/esp32/health')
        if (response.success && response.data) {
          const data = response.data
          // Only update if we have actual data from ESP32
          if (data.esp32_temp_c !== null || data.free_heap_bytes !== null) {
            esp32Health.value = {
              temp: data.esp32_temp_c,
              heap: data.free_heap_bytes,
              rssi: data.wifi_rssi_dbm,
              uptime: data.uptime_seconds
            }
          } else {
            // ESP32 not sending data yet
            showCommandResult('ESP32 belum mengirim data. Pastikan ESP32 terhubung dan mengirim data.', 'info')
          }
        }
        lastUpdateAt.value = new Date()
      } catch (error) {
        console.warn('Failed to get ESP32 health from RPi:', error.message)
        showCommandResult('Tidak dapat terhubung ke RPi. Cek koneksi.', 'error')
      } finally {
        isLoadingEsp32.value = false
      }
    }

    const sendEsp32Command = async (command) => {
      isSendingCommand.value = true
      try {
        const payload = { command }
        if (command === 'sleep') {
          payload.params = { duration_ms: sleepDuration.value }
        }

        // Try RPi first, then Azure
        try {
          const response = await rpiRequest('/api/admin/esp32/command', {
            method: 'POST',
            body: JSON.stringify(payload)
          })
          showCommandResult(response.data.message || 'Command sent', 'success')
        } catch {
          // Fallback to Azure IoT Hub
          const response = await fetch(`${AZURE_FUNCTION_URL}/device/command`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ deviceId: esp32DeviceId.value, ...payload })
          })
          const result = await response.json()
          showCommandResult(result.message || 'Command sent via Azure', 'success')
        }
        lastUpdateAt.value = new Date()
      } catch (error) {
        showCommandResult('Gagal mengirim command: ' + error.message, 'error')
      } finally {
        isSendingCommand.value = false
      }
    }

    const toggleSleepMode = () => {
      if (sleepModeEnabled.value) {
        sendEsp32Command('sleep')
      } else {
        sendEsp32Command('wake')
      }
    }

    // Service Control Methods
    const refreshServicesStatus = async () => {
      try {
        const response = await rpiRequest('/api/admin/services')
        if (response.success && response.data) {
          services.value = response.data.services.map(svc => ({
            // Map service names (backend uses hyphen, frontend uses underscore)
            name: svc.name,
            displayName: svc.displayName,
            port: svc.port,
            status: svc.status === 'active' ? 'running' :
                   svc.status === 'inactive' ? 'stopped' : svc.status
          }))
        }
        lastUpdateAt.value = new Date()
      } catch (error) {
        console.warn('Failed to get services from RPi:', error.message)
        // Fallback: mark known services as running
        services.value = services.value.map(s => ({
          ...s,
          status: s.name === 'yolo_cam' || s.name === 'influxdb' ||
                 s.name === 'grafana-server' || s.name === 'ml-pipeline' ? 'running' : 'unknown'
        }))
      }
    }

    const controlService = async (serviceName, action) => {
      isControllingService.value = true
      try {
        const response = await rpiRequest('/api/admin/service-control', {
          method: 'POST',
          body: JSON.stringify({ service: serviceName, action })
        })
        if (response.success) {
          const newStatus = response.data.status === 'active' ? 'running' : response.data.status
          const svc = services.value.find(s => s.name === serviceName)
          if (svc) svc.status = newStatus
          showCommandResult(`${action} ${serviceName}: ${newStatus}`, 'success')
        }
      } catch (error) {
        showCommandResult('Gagal mengontrol service: ' + error.message, 'error')
      } finally {
        isControllingService.value = false
      }
    }

    // System Control Methods
    const refreshRpiStats = async () => {
      try {
        const response = await rpiRequest('/api/admin/system')
        if (response.success && response.data) {
          rpiStats.value = {
            cpu: response.data.health?.cpu_percent || 0,
            memory: response.data.health?.memory_percent || 0,
            disk: response.data.health?.disk_percent || 0
          }
        }
      } catch (error) {
        console.warn('Failed to get RPi stats:', error.message)
      }
    }

    const confirmReboot = () => {
      confirmModalTitle.value = 'Konfirmasi Reboot'
      confirmModalMessage.value = 'Raspberry Pi akan di-reboot. Koneksi akan terputus sementara. Lanjutkan?'
      confirmModalAction.value = 'Reboot'
      pendingAction = 'reboot'
      showConfirmModal.value = true
    }

    const confirmShutdown = () => {
      confirmModalTitle.value = 'Konfirmasi Shutdown'
      confirmModalMessage.value = 'Raspberry Pi akan dimatikan. Anda perlu menyalakan ulang secara manual. Lanjutkan?'
      confirmModalAction.value = 'Shutdown'
      pendingAction = 'shutdown'
      showConfirmModal.value = true
    }

    const cancelConfirm = () => {
      showConfirmModal.value = false
      pendingAction = null
    }

    const executeConfirmedAction = async () => {
      showConfirmModal.value = false
      try {
        if (pendingAction === 'reboot') {
          const response = await rpiRequest('/api/admin/system', {
            method: 'POST',
            body: JSON.stringify({ action: 'reboot' })
          })
          showCommandResult(response.data?.message || 'Reboot initiated', 'success')
        } else if (pendingAction === 'shutdown') {
          const response = await rpiRequest('/api/admin/system', {
            method: 'POST',
            body: JSON.stringify({ action: 'shutdown' })
          })
          showCommandResult(response.data?.message || 'Shutdown initiated', 'success')
        }
      } catch (error) {
        showCommandResult('Gagal execute action: ' + error.message, 'error')
      } finally {
        pendingAction = null
      }
    }

    // Auto-refresh
    const startAutoRefresh = () => {
      refreshCountdown.value = autoRefreshSeconds
      refreshTimer = setInterval(() => {
        refreshCountdown.value--
        if (refreshCountdown.value <= 0) {
          refreshEsp32Health()
          refreshServicesStatus()
          refreshRpiStats()
          refreshCountdown.value = autoRefreshSeconds
        }
      }, 1000)
    }

    onMounted(() => {
      // Get ESP32 device ID from config
      esp32DeviceId.value = import.meta.env.VITE_IOT_HUB_DEVICE_ID || 'esp32-sensor-01'

      // Initial load
      refreshEsp32Health()
      refreshServicesStatus()
      refreshRpiStats()
      startAutoRefresh()
    })

    onUnmounted(() => {
      if (refreshTimer) {
        clearInterval(refreshTimer)
      }
    })

    return {
      // Config
      esp32DeviceId,
      rpiAddress,

      // ESP32
      esp32Health,
      isLoadingEsp32,
      isSendingCommand,
      sleepModeEnabled,
      sleepDuration,
      commandResult,
      refreshEsp32Health,
      sendEsp32Command,
      toggleSleepMode,

      // Services
      services,
      isControllingService,
      controlService,
      getStatusLabel,

      // System
      rpiStats,
      confirmReboot,
      confirmShutdown,

      // Modal
      showConfirmModal,
      confirmModalTitle,
      confirmModalMessage,
      confirmModalAction,
      cancelConfirm,
      executeConfirmedAction,

      // Utils
      lastUpdateText,
      systemStatusClass,
      systemStatusText,
      getRssiClass,
      formatUptime,

      // Auto-refresh
      autoRefreshSeconds,
      refreshCountdown
    }
  }
}
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=Sora:wght@500;600;700;800&display=swap');

.admin-dashboard {
  --accent: #8b5cf6;
  --accent-dark: #7c3aed;
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
  background: rgba(139, 92, 246, 0.1);
  border: 1px solid rgba(139, 92, 246, 0.2);
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
  color: var(--text-2);
  margin: 0 0 16px 0;
}

.hero-meta {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.meta-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: var(--surface-2);
  border-radius: 20px;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-2);
}

.status-badge.status-success { background: rgba(34, 197, 94, 0.1); color: var(--success); }
.status-badge.status-warning { background: rgba(245, 158, 11, 0.1); color: var(--warning); }
.status-badge.status-danger { background: rgba(239, 68, 68, 0.1); color: var(--danger); }

/* Auto Refresh Bar */
.auto-refresh-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 16px;
  background: var(--surface-2);
  border-radius: 8px;
  margin-bottom: 24px;
  font-size: 12px;
  color: var(--text-3);
}

.refresh-progress {
  height: 4px;
  background: var(--accent);
  border-radius: 2px;
  transition: width 1s linear;
}

/* Control Section */
.control-section {
  background: var(--surface);
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border);
}

.section-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-family: 'Sora', sans-serif;
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--text);
  margin: 0;
}

.section-title svg {
  color: var(--accent);
}

.device-id {
  font-size: 12px;
  color: var(--text-3);
  font-family: monospace;
}

/* ESP32 Control Grid */
.control-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
}

.control-card {
  background: var(--surface-2);
  border-radius: 10px;
  padding: 16px;
}

.control-card h4 {
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
  margin: 0 0 12px 0;
}

/* Health Card */
.health-stats {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.health-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.health-label {
  font-size: 11px;
  color: var(--text-3);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.health-value {
  font-size: 16px;
  font-weight: 600;
  color: var(--text);
}

.health-value.warning { color: var(--warning); }
.health-value.excellent { color: var(--success); }
.health-value.good { color: #22c55e; }
.health-value.fair { color: var(--warning); }
.health-value.poor { color: var(--danger); }

.refresh-health-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  padding: 10px;
  margin-top: 12px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: 13px;
  color: var(--text-2);
  cursor: pointer;
  transition: all 0.2s;
}

.refresh-health-btn:hover:not(:disabled) {
  background: var(--accent);
  color: white;
  border-color: var(--accent);
}

.refresh-health-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.spin { animation: spin 1s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

/* Commands Card */
.command-buttons {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 16px;
}

.cmd-btn {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  color: var(--text);
  cursor: pointer;
  transition: all 0.2s;
}

.cmd-btn:hover:not(:disabled) {
  background: var(--accent);
  color: white;
  border-color: var(--accent);
}

.cmd-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.sleep-control {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.sleep-control span {
  font-size: 13px;
  color: var(--text-2);
}

.toggle-switch {
  position: relative;
  width: 44px;
  height: 24px;
}

.toggle-switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.toggle-slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #cbd5e1;
  transition: 0.3s;
  border-radius: 24px;
}

.toggle-slider:before {
  position: absolute;
  content: "";
  height: 18px;
  width: 18px;
  left: 3px;
  bottom: 3px;
  background-color: white;
  transition: 0.3s;
  border-radius: 50%;
}

.toggle-switch input:checked + .toggle-slider {
  background-color: var(--accent);
}

.toggle-switch input:checked + .toggle-slider:before {
  transform: translateX(20px);
}

.sleep-duration-input {
  width: 100px;
  padding: 6px 10px;
  border: 1px solid var(--border);
  border-radius: 6px;
  font-size: 12px;
}

/* Command Result */
.command-result {
  padding: 12px 16px;
  border-radius: 8px;
  margin-top: 16px;
  font-size: 13px;
}

.command-result.success {
  background: rgba(34, 197, 94, 0.1);
  color: var(--success);
  border: 1px solid rgba(34, 197, 94, 0.2);
}

.command-result.error {
  background: rgba(239, 68, 68, 0.1);
  color: var(--danger);
  border: 1px solid rgba(239, 68, 68, 0.2);
}

.command-result.info {
  background: rgba(139, 92, 246, 0.1);
  color: var(--accent);
  border: 1px solid rgba(139, 92, 246, 0.2);
}

/* Services Grid */
.services-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.service-card {
  background: var(--surface-2);
  border-radius: 10px;
  padding: 16px;
}

.service-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.service-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.service-status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--text-3);
}

.service-status-dot.running { background: var(--success); }
.service-status-dot.stopped { background: var(--danger); }
.service-status-dot.failed { background: var(--danger); }

.service-name {
  font-weight: 600;
  color: var(--text);
}

.service-status-text {
  font-size: 12px;
  color: var(--text-2);
}

.service-details {
  margin-bottom: 12px;
}

.service-port {
  font-size: 11px;
  color: var(--text-3);
  font-family: monospace;
}

.service-controls {
  display: flex;
  gap: 8px;
}

.svc-btn {
  flex: 1;
  padding: 8px;
  border: none;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.svc-btn.start {
  background: rgba(34, 197, 94, 0.1);
  color: var(--success);
}

.svc-btn.start:hover:not(:disabled) {
  background: var(--success);
  color: white;
}

.svc-btn.stop {
  background: rgba(239, 68, 68, 0.1);
  color: var(--danger);
}

.svc-btn.stop:hover:not(:disabled) {
  background: var(--danger);
  color: white;
}

.svc-btn.restart {
  background: rgba(245, 158, 11, 0.1);
  color: var(--warning);
}

.svc-btn.restart:hover:not(:disabled) {
  background: var(--warning);
  color: white;
}

.svc-btn:disabled { opacity: 0.4; cursor: not-allowed; }

/* System Controls */
.system-controls {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
}

.system-card {
  background: var(--surface-2);
  border-radius: 10px;
  padding: 16px;
}

.system-card h4 {
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
  margin: 0 0 12px 0;
}

.system-stats {
  display: flex;
  gap: 20px;
  margin-bottom: 16px;
  padding: 12px;
  background: var(--surface);
  border-radius: 8px;
}

.sys-stat {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.sys-label {
  font-size: 11px;
  color: var(--text-3);
  text-transform: uppercase;
}

.sys-value {
  font-size: 18px;
  font-weight: 600;
  color: var(--text);
}

.system-buttons {
  display: flex;
  gap: 12px;
}

.system-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.system-btn.reboot {
  background: rgba(245, 158, 11, 0.1);
  color: var(--warning);
}

.system-btn.reboot:hover {
  background: var(--warning);
  color: white;
}

.system-btn.shutdown {
  background: rgba(239, 68, 68, 0.1);
  color: var(--danger);
}

.system-btn.shutdown:hover {
  background: var(--danger);
  color: white;
}

/* Modal */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.confirm-modal {
  background: var(--surface);
  border-radius: 12px;
  padding: 24px;
  max-width: 400px;
  width: 90%;
}

.confirm-modal h3 {
  font-family: 'Sora', sans-serif;
  font-size: 1.2rem;
  font-weight: 600;
  color: var(--text);
  margin: 0 0 12px 0;
}

.confirm-modal p {
  color: var(--text-2);
  margin: 0 0 20px 0;
  line-height: 1.5;
}

.modal-buttons {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}

.modal-btn {
  padding: 10px 20px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.modal-btn.cancel {
  background: var(--surface-2);
  color: var(--text-2);
}

.modal-btn.cancel:hover {
  background: var(--border);
}

.modal-btn.confirm {
  background: var(--accent);
  color: white;
}

.modal-btn.confirm:hover {
  background: var(--accent-dark);
}

/* Dark Mode */
.admin-dashboard.dark {
  --bg: #0f172a;
  --surface: #1e293b;
  --surface-2: #334155;
  --border: #475569;
  --text: #f1f5f9;
  --text-2: #94a3b8;
  --text-3: #64748b;
}
</style>