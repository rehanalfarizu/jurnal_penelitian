import { ref, watch, onUnmounted } from 'vue'
import { AZURE_FUNCTION_URL, AZURE_FUNCTION_WRITE_KEY } from '../lib/appConfig'

const STORAGE_KEY = 'sensor_last_data'

// Polling interval in milliseconds (5 seconds for near real-time)
const POLLING_INTERVAL = 5000

// Simpan data ke localStorage sebagai backup
const saveLastData = (data) => {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data))
  } catch (e) {
    console.error('❌ Failed to save to localStorage:', e)
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
    console.error('❌ Failed to load from localStorage:', e)
  }
  return null
}

export function useMQTT() {
  // Represents "Azure connected/polling active"
  const mqttConnected = ref(false)
  const sensorData = ref({
    temperature: 0,
    humidity: 0,
    voltage: 0,
    current: 0,
    power: 0,
    voltageStatus: 'unknown',
    currentStatus: 'unknown',
    peopleCount: 0,
    lastPeopleUpdate: null
  })
  
  let pollingTimer = null
  let isPolling = false
  
  // Auto-save ke localStorage setiap ada perubahan data
  watch(sensorData, (newData) => {
    saveLastData(newData)
  }, { deep: true })

  // Fetch latest sensor data from Azure Function
  const fetchLatestData = async () => {
    try {
      const response = await fetch(`${AZURE_FUNCTION_URL}/telemetry/latest`)
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }
      
      const result = await response.json()
      
      if (result.success && result.data) {
        const data = result.data
        const nextData = { ...sensorData.value }
        
        // Update sensor data from Azure Storage
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
        
        // Compute power if not provided
        if (nextData.power === 0 && nextData.voltage > 0 && nextData.current > 0) {
          nextData.power = parseFloat((nextData.voltage * nextData.current).toFixed(1))
        }
        
        sensorData.value = nextData
        
        console.log('🌡️ Data updated from Azure:', {
          temperature: nextData.temperature,
          humidity: nextData.humidity,
          voltage: nextData.voltage,
          current: nextData.current,
          power: nextData.power,
          timestamp: data.timestamp
        })
        
        return true
      }
      
      return false
    } catch (error) {
      console.error('❌ Error fetching from Azure:', error.message)
      return false
    }
  }

  // Fetch people count from Azure Function (PeopleCount table)
  const fetchPeopleCount = async () => {
    try {
      const response = await fetch(`${AZURE_FUNCTION_URL}/telemetry/people?limit=1`)
      
      if (!response.ok) return false
      
      const result = await response.json()
      
      // Use latest from response or data array
      if (result.success) {
        let count = 0
        let timestamp = null
        
        // Check latest field first (new format)
        if (result.latest && result.latest.count !== undefined) {
          count = parseInt(result.latest.count) || 0
          timestamp = result.latest.timestamp
        }
        // Fallback to data array (old format)
        else if (result.data && result.data.length > 0) {
          const latestPeople = result.data[0]
          count = parseInt(latestPeople.count) || 0
          timestamp = latestPeople.timestamp
        }
        
        sensorData.value.peopleCount = count
        sensorData.value.lastPeopleUpdate = timestamp || new Date().toLocaleTimeString()
        
        console.log('👥 People count updated from Azure:', count)
        return true
      }
      
      return false
    } catch (error) {
      console.error('❌ Error fetching people count:', error.message)
      return false
    }
  }

  // Save people count to Azure (called from camera detection)
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
        // Update local state immediately
        sensorData.value.peopleCount = count
        sensorData.value.lastPeopleUpdate = new Date().toLocaleTimeString()
        console.log('✅ People count saved to Azure:', count)
        return true
      }
      
      return false
    } catch (error) {
      console.error('❌ Error saving people count:', error.message)
      return false
    }
  }

  // Start polling for data from Azure
  const connectMQTT = () => {
    console.log('🔌 Starting Azure polling...')
    console.log('📡 Azure Function URL:', AZURE_FUNCTION_URL)
    
    // Load cached data first
    const cached = loadLastData()
    if (cached) {
      sensorData.value = cached
      console.log('💾 Loaded cached data from localStorage')
    }
    
    // Fetch immediately
    fetchLatestData().then(success => {
      if (success) {
        mqttConnected.value = true
        console.log('✅ Connected to Azure!')
      }
    })
    
    fetchPeopleCount()
    
    // Start polling interval
    if (!pollingTimer) {
      isPolling = true
      pollingTimer = setInterval(async () => {
        if (!isPolling) return
        
        const success = await fetchLatestData()
        mqttConnected.value = success
        
        // Fetch people count every poll (5 seconds)
        await fetchPeopleCount()
      }, POLLING_INTERVAL)
      
      console.log(`🔄 Azure polling started (every ${POLLING_INTERVAL / 1000}s)`)
    }
  }

  // Stop polling
  const disconnectMQTT = () => {
    isPolling = false
    if (pollingTimer) {
      clearInterval(pollingTimer)
      pollingTimer = null
    }
    mqttConnected.value = false
    console.log('⚠️ Stopped Azure polling')
  }

  // For compatibility with existing code
  const fetchLatestFromAzure = async () => {
    return await fetchLatestData()
  }

  // Cleanup on unmount
  onUnmounted(() => {
    disconnectMQTT()
  })

  return {
    mqttConnected,
    sensorData,
    connectMQTT,
    disconnectMQTT,
    fetchLatestFromAzure,
    savePeopleCount,
    fetchPeopleCount
  }
}
