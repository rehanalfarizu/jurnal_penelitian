import { ref, watch, onUnmounted } from 'vue'
import { AZURE_FUNCTION_URL, AZURE_FUNCTION_WRITE_KEY } from '../lib/appConfig'

const STORAGE_KEY = 'sensor_last_data'

// Polling interval in milliseconds (5 seconds to match ESP32 sensor interval)
const POLLING_INTERVAL = 5000

// Convert UTC ISO string to local display string (WIB)
const toLocalDisplay = (utcString) => {
  if (!utcString) return new Date().toLocaleTimeString('id-ID', { timeZone: 'Asia/Jakarta' })
  try {
    const date = new Date(utcString)
    return date.toLocaleString('id-ID', { timeZone: 'Asia/Jakarta' })
  } catch {
    return utcString
  }
}

// Convert UTC ISO string to Date object
const parseTimestamp = (utcString) => {
  if (!utcString) return null
  try {
    return new Date(utcString)
  } catch {
    return null
  }
}

// Simpan data ke localStorage sebagai backup
const saveLastData = (data) => {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data))
  } catch (e) {
    console.error('❌ Gagal menyimpan ke localStorage:', e)
  }
}

// Load data terakhir dari localStorage (sebagai fallback)
const loadLastData = () => {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) {
      return JSON.parse(saved)
    }
  } catch (e) {
    console.error('❌ Gagal memuat dari localStorage:', e)
  }
  return null
}

export function useAzureTelemetry() {
  // "Azure connected / polling aktif"
  const isConnected = ref(false)
  const sensorData = ref({
    temperature: 0,
    humidity: 0,
    voltage: 0,
    current: 0,
    power: 0,
    voltageStatus: 'unknown',
    currentStatus: 'unknown',
    peopleCount: 0,
    lastPeopleUpdate: null,
    timestamp: null, // UTC ISO dari storage
    timestampDisplay: null // Tampilan lokal (WIB)
  })

  let pollingTimer = null
  let isPolling = false

  // Auto-save ke localStorage setiap ada perubahan data
  watch(sensorData, (newData) => {
    saveLastData(newData)
  }, { deep: true })

  // Fetch latest sensor data dari Azure Function with retry
  const fetchLatestFromAzure = async (retryCount = 0, maxRetries = 3) => {
    try {
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 10000) // 10s timeout

      const response = await fetch(`${AZURE_FUNCTION_URL}/telemetry/latest`, {
        signal: controller.signal
      })
      clearTimeout(timeoutId)

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const result = await response.json()

      if (result.success && result.data) {
        const data = result.data
        const nextData = { ...sensorData.value }

        // Update data sensor dari Azure Storage
        if (data.suhu !== undefined) {
          nextData.temperature = parseFloat(data.suhu) || 0
        }
        if (data.kelembaban !== undefined) {
          nextData.humidity = parseFloat(data.kelembaban) || 0
        }
        if (data.tegangan !== undefined) {
          nextData.voltage = parseFloat(data.tegangan) || 0
        }
        if (data.arus !== undefined) {
          nextData.current = parseFloat(data.arus) || 0
        }
        if (data.daya !== undefined) {
          nextData.power = parseFloat(data.daya) || 0
        }
        if (data.status_tegangan) {
          nextData.voltageStatus = data.status_tegangan
        }
        if (data.status_arus) {
          nextData.currentStatus = data.status_arus
        }

        // Hitung power jika tidak disediakan
        if (nextData.power === 0 && nextData.voltage > 0 && nextData.current > 0) {
          nextData.power = parseFloat((nextData.voltage * nextData.current).toFixed(1))
        }

        sensorData.value = {
          ...nextData,
          timestamp: data.timestamp || new Date().toISOString(),
          timestampDisplay: toLocalDisplay(data.timestamp)
        }

        console.log('📡 Data diperbarui dari Azure:', {
          temperature: nextData.temperature,
          humidity: nextData.humidity,
          voltage: nextData.voltage,
          current: nextData.current,
          power: nextData.power,
          timestamp: data.timestamp,
          timestampDisplay: toLocalDisplay(data.timestamp)
        })

        return true
      }

      return false
    } catch (error) {
      // Retry logic for network errors
      if (retryCount < maxRetries && (error.name === 'AbortError' || error.message.includes('fetch'))) {
        console.log(`🔄 Retry ${retryCount + 1}/${maxRetries} untuk fetch data...`)
        return new Promise(resolve => setTimeout(() => {
          resolve(fetchLatestFromAzure(retryCount + 1, maxRetries))
        }, 1000 * (retryCount + 1))) // Exponential backoff
      }
      console.error('❌ Error fetching dari Azure:', error.message)
      return false
    }
  }

  // Fetch people count dari Azure Function (PeopleCount table)
  const fetchPeopleCount = async () => {
    try {
      const response = await fetch(`${AZURE_FUNCTION_URL}/telemetry/people?limit=1`)

      if (!response.ok) return false

      const result = await response.json()

      // Gunakan latest dari response atau data array
      if (result.success) {
        let count = 0
        let timestamp = null

        // Cek field latest dulu (format baru)
        if (result.latest && result.latest.count !== undefined) {
          count = parseInt(result.latest.count) || 0
          timestamp = result.latest.timestamp
        }
        // Fallback ke data array (format lama)
        else if (result.data && result.data.length > 0) {
          const latestPeople = result.data[0]
          count = parseInt(latestPeople.count) || 0
          timestamp = latestPeople.timestamp
        }

        sensorData.value.peopleCount = count
        sensorData.value.lastPeopleUpdate = timestamp
          ? toLocalDisplay(timestamp)
          : new Date().toLocaleTimeString('id-ID', { timeZone: 'Asia/Jakarta' })

        console.log('👥 Jumlah orang diperbarui dari Azure:', count, 'at', sensorData.value.lastPeopleUpdate)
        return true
      }

      return false
    } catch (error) {
      console.error('❌ Error fetching jumlah orang:', error.message)
      return false
    }
  }

  // Simpan people count ke Azure (dipanggil dari camera detection)
  const savePeopleCount = async (count, location = 'Ruang Utama') => {
    try {
      if (!AZURE_FUNCTION_WRITE_KEY) {
        console.warn('⚠️ VITE_AZURE_FUNCTION_WRITE_KEY belum diisi. Endpoint write Azure Function tidak bisa dipanggil.')
        return false
      }

      const response = await fetch(`${AZURE_FUNCTION_URL}/people/save`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-functions-key': AZURE_FUNCTION_WRITE_KEY
        },
        body: JSON.stringify({
          count: count,
          deviceId: 'WEB_CAMERA_001',
          location: location
        })
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      const result = await response.json()

      if (result.success) {
        // Update state lokal langsung
        sensorData.value.peopleCount = count
        sensorData.value.lastPeopleUpdate = new Date().toLocaleString('id-ID', { timeZone: 'Asia/Jakarta' })
        console.log('👥 Jumlah orang disimpan ke Azure:', count)
        return true
      }

      return false
    } catch (error) {
      console.error('❌ Error menyimpan jumlah orang:', error.message)
      return false
    }
  }

  // Mulai polling data dari Azure
  const startPolling = () => {
    console.log('🔌 Memulai polling Azure...')
    console.log('📡 Azure Function URL:', AZURE_FUNCTION_URL)

    // Muat data cache dulu
    const cached = loadLastData()
    if (cached) {
      sensorData.value = cached
      console.log('💾 Data cache dimuat dari localStorage')
    }

    // Fetch langsung
    fetchLatestFromAzure().then(success => {
      if (success) {
        isConnected.value = true
        console.log('✅ Terhubung ke Azure!')
      }
    })

    fetchPeopleCount()

    // Mulai interval polling
    if (!pollingTimer) {
      isPolling = true
      pollingTimer = setInterval(async () => {
        if (!isPolling) return

        const success = await fetchLatestFromAzure()
        isConnected.value = success

        // Fetch people count setiap poll (5 detik)
        await fetchPeopleCount()
      }, POLLING_INTERVAL)

      console.log(`🔄 Polling Azure dimulai (setiap ${POLLING_INTERVAL / 1000} detik)`)
    }
  }

  // Hentikan polling
  const stopPolling = () => {
    isPolling = false
    if (pollingTimer) {
      clearInterval(pollingTimer)
      pollingTimer = null
    }
    isConnected.value = false
    console.log('⚠️ Polling Azure dihentikan')
  }

  // Cleanup saat unmount
  onUnmounted(() => {
    stopPolling()
  })

  return {
    isConnected,
    sensorData,
    startPolling,
    stopPolling,
    fetchLatestFromAzure,
    fetchPeopleCount,
    savePeopleCount
  }
}