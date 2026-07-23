<template>
  <div class="data-table">
    <EmptyState 
      v-if="!hasData"
      :is-dark-mode="false"
      icon="📋"
      icon-type="info"
      title="Belum Ada Data Sensor"
      description="Dashboard menunggu koneksi dari semua sensor IoT"
      :actions="[
        { icon: '🔌', text: 'Hubungkan ke MQTT broker' },
        { icon: '🌡️', text: 'Sensor suhu dan kelembaban' },
        { icon: '⚡', text: 'Sensor arus dan tegangan' },
        { icon: '📹', text: 'Kamera people counter' }
      ]"
      button-text="Cek Koneksi MQTT"
      @button-click="checkConnection"
      :show-status="true"
      :status-text="connectionStatus"
      :status-class="connectionClass"
    />
    
    <template v-else>
      <div class="table-responsive">
        <table>
          <thead>
            <tr>
              <th>Waktu</th>
              <th>Suhu (°C)</th>
              <th>Kelembaban (%)</th>
              <th>Tegangan (V)</th>
              <th>Arus (A)</th>
              <th>Daya (W)</th>
              <th>Jumlah Orang</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>{{ currentTime }}</td>
              <td>{{ formatValue(sensorData.temperature) }}</td>
              <td>{{ formatValue(sensorData.humidity) }}</td>
              <td>{{ formatValue(sensorData.voltage) }}</td>
              <td>{{ formatValue(sensorData.current) }}</td>
              <td>{{ formatValue(sensorData.power) }}</td>
              <td>{{ peopleCount }}</td>
              <td>
                <span class="status-badge" :class="getOverallStatus()">
                  {{ getOverallStatusText() }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      
      <div class="table-summary">
        <div class="summary-item">
          <div class="summary-label">Rata-rata Suhu</div>
          <div class="summary-value">{{ formatValue(sensorData.temperature) }}°C</div>
        </div>
        <div class="summary-item">
          <div class="summary-label">Total Konsumsi</div>
          <div class="summary-value">{{ formatEnergy(totalEnergy) }}</div>
        </div>
        <div class="summary-item">
          <div class="summary-label">Kapasitas Ruangan</div>
          <div class="summary-value">{{ peopleCount }} / 20</div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import EmptyState from './EmptyState.vue'

const props = defineProps({
  sensorData: {
    type: Object,
    default: () => ({})
  },
  peopleCount: {
    type: Number,
    default: 0
  },
  totalEnergy: {
    type: Number,
    default: 0
  }
})

const currentTime = ref(new Date().toLocaleString('id-ID'))
let timeInterval = null

const hasData = computed(() => {
  const temp = parseFloat(props.sensorData.temperature) || 0
  const humidity = parseFloat(props.sensorData.humidity) || 0
  const voltage = parseFloat(props.sensorData.voltage) || 0
  const current = parseFloat(props.sensorData.current) || 0
  
  // Check if any sensor has valid data
  return (
    (temp > -50 && temp < 100) ||
    (humidity >= 0 && humidity <= 100) ||
    voltage > 0 ||
    current > 0 ||
    props.peopleCount > 0
  )
})

const connectionStatus = computed(() => {
  if (hasData.value) return 'Terhubung'
  return 'Menunggu koneksi...'
})

const connectionClass = computed(() => {
  if (hasData.value) return 'connected'
  return 'waiting'
})

const checkConnection = () => {
  console.log('🔌 Checking MQTT connection...')
  // This can trigger a reconnection attempt if needed
}

// Watch untuk debug
watch(() => props.sensorData, (newData) => {
  console.log('📊 DataTable component received update:', newData)
}, { deep: true, immediate: true })

onMounted(() => {
  timeInterval = setInterval(() => {
    currentTime.value = new Date().toLocaleString('id-ID')
  }, 1000)
})

onUnmounted(() => {
  if (timeInterval) clearInterval(timeInterval)
})

const formatValue = (value) => {
  if (value === null || value === undefined) return '0.00'
  return Number(value).toFixed(2)
}

const formatEnergy = (value) => {
  if (!value || value <= 0) return '0.00 kWh'
  const kWh = value / 1000
  return `${kWh.toFixed(2)} kWh`
}

const getOverallStatus = () => {
  const temp = parseFloat(props.sensorData.temperature) || 0
  const voltage = parseFloat(props.sensorData.voltage) || 0
  const current = parseFloat(props.sensorData.current) || 0
  const humidity = parseFloat(props.sensorData.humidity) || 0
  const voltageStatus = props.sensorData.voltageStatus
  const currentStatus = props.sensorData.currentStatus
  
  const hasValidData = 
    (temp > -50 && temp < 100) ||
    (humidity >= 0 && humidity <= 100) ||
    voltageStatus === 'terhubung' ||
    currentStatus === 'terhubung'
  
  if (!hasValidData) {
    return 'status-offline'
  }
  
  if (
    temp > 30 || temp < 15 ||
    (voltageStatus === 'terhubung' && (voltage > 250 || voltage < 180)) ||
    (currentStatus === 'terhubung' && current > 80) ||
    voltageStatus !== 'terhubung' ||
    currentStatus !== 'terhubung'
  ) {
    return 'status-warning'
  }
  
  return 'status-online'
}

const getOverallStatusText = () => {
  const status = getOverallStatus()
  if (status === 'status-online') return 'Normal'
  if (status === 'status-warning') return 'Perhatian'
  return 'Offline'
}
</script>

<style scoped>
.data-table {
  width: 100%;
}

.table-responsive {
  overflow-x: auto;
  margin-bottom: 24px;
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
}

table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  background: var(--bg-card);
  backdrop-filter: blur(10px);
  border-radius: 16px;
  overflow: hidden;
  transition: background 0.3s ease;
}

thead {
  background: linear-gradient(135deg, #06b6d4 0%, #0891b2 50%, #0e7490 100%);
  background-size: 200% 200%;
  animation: gradientShift 3s ease infinite;
  color: white;
  position: relative;
}

@keyframes gradientShift {
  0%, 100% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
}

thead::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: rgba(255, 255, 255, 0.3);
}

th {
  padding: 18px 16px;
  text-align: left;
  font-weight: 700;
  font-size: 13px;
  text-transform: uppercase;
  letter-spacing: 1px;
  position: relative;
}

th:not(:last-child)::after {
  content: '';
  position: absolute;
  right: 0;
  top: 20%;
  height: 60%;
  width: 1px;
  background: rgba(255, 255, 255, 0.2);
}

tbody tr {
  border-bottom: 1px solid var(--border-dark);
  transition: all 0.3s ease;
  background: var(--bg-card);
}

tbody tr:nth-child(even) {
  background: var(--bg-secondary);
}

tbody tr:hover {
  background: var(--bg-secondary);
  transform: scale(1.01);
  box-shadow: 0 4px 12px var(--shadow-sm);
}

[data-theme="light"] tbody tr:hover {
  background: linear-gradient(90deg, rgba(6, 182, 212, 0.08) 0%, rgba(8, 145, 178, 0.08) 100%);
}

[data-theme="dark"] tbody tr:hover {
  background: rgba(6, 182, 212, 0.15);
}

tbody tr:last-child {
  border-bottom: none;
}

td {
  padding: 18px 16px;
  font-size: 14px;
  color: var(--text-primary);
  font-weight: 500;
  transition: color 0.3s ease;
}

.status-badge {
  display: inline-block;
  padding: 8px 16px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  transition: all 0.3s ease;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.status-badge:hover {
  transform: scale(1.05);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.status-badge.status-online {
  background: linear-gradient(135deg, #27ae60 0%, #2ecc71 100%);
  color: white;
}

.status-badge.status-warning {
  background: linear-gradient(135deg, #f39c12 0%, #f1c40f 100%);
  color: white;
}

.status-badge.status-offline {
  background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
  color: white;
}

.table-summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 20px;
  margin-top: 24px;
}

.summary-item {
  background: var(--bg-card);
  backdrop-filter: blur(10px);
  padding: 28px 24px;
  border-radius: 20px;
  text-align: center;
  border: 2px solid transparent;
  transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
  box-shadow: 0 8px 24px var(--shadow-sm);
  position: relative;
  overflow: hidden;
  animation: cardSlideIn 0.6s ease-out backwards;
}

.summary-item:nth-child(1) { animation-delay: 0.1s; }
.summary-item:nth-child(2) { animation-delay: 0.2s; }
.summary-item:nth-child(3) { animation-delay: 0.3s; }

@keyframes cardSlideIn {
  from {
    opacity: 0;
    transform: translateX(-30px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.summary-item::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, #06b6d4 0%, #0891b2 50%, #0e7490 100%);
  background-size: 200% 100%;
  animation: gradientShift 3s ease infinite;
}

.summary-item:hover {
  transform: translateY(-6px) scale(1.02);
  border-color: var(--border-color-hover);
  box-shadow: 0 16px 40px var(--shadow-md);
}

.summary-label {
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 12px;
  text-transform: uppercase;
  font-weight: 700;
  letter-spacing: 1px;
  transition: color 0.3s ease;
}

.summary-value {
  font-size: 32px;
  font-weight: 800;
  background: linear-gradient(135deg, #06b6d4 0%, #0891b2 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  line-height: 1.2;
  transition: all 0.3s;
}

.summary-item:hover .summary-value {
  transform: scale(1.1);
}

@media (max-width: 768px) {
  .table-responsive {
    font-size: 12px;
    border-radius: 12px;
  }
  
  th, td {
    padding: 12px 10px;
    font-size: 12px;
  }

  th {
    font-size: 11px;
  }
  
  .table-summary {
    grid-template-columns: 1fr;
    gap: 16px;
  }

  .summary-item {
    padding: 24px 20px;
  }

  .summary-value {
    font-size: 28px;
  }
}
</style>





