import { ref, watch, onUnmounted } from 'vue'

// Real CSV-derived data from sensor_data.csv (2,027,520 rows, 91 days)
// Range: Suhu 26-34°C, Daya 25-484W, Orang 0-5
const VALIDATION_METRICS = {
  edgeLatencyMs: 1.49,       // median per-record (SLA <2ms)
  cloudLatencyMs: 196,       // incl network (anomaly only)
  anomalyRate: 3.24,         // % of 2M records routed to cloud
  edgeRate: 96.76,           // % processed at edge
  onlineR2: 0.595,           // SGD 4-feature baseline
  batchRR2: 0.9952,          // RF 18-feature (best)
  batchLR2: 0.9651,          // LR 18-feature
  r2Improvement: '+40pp',
  throughput: 3379,          // records/sec
  totalRecords: '2,027,520',
  dataPeriod: '90 days (91 dates)'
}

export function useDummyData() {
  const isConnected = ref(false)
  const sensorData = ref({
    temperature: 0,
    humidity: 0,
    voltage: 0,
    current: 0,
    power: 0,
    peopleCount: 0,
    timestamp: null,
    timestampDisplay: null
  })

  // Preloaded history data
  const historyData = ref([])
  const statsData = ref({})
  const isLoaded = ref(false)

  // Validation metrics (static, derived from actual experiments)
  const validationMetrics = ref({ ...VALIDATION_METRICS })

  // Current playback position
  let currentIndex = 0
  let playbackTimer = null
  let dataFetchPromise = null

  const STORAGE_KEY = 'dummy_sensor_last_data'

  const saveLastData = (data) => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(data))
    } catch (e) {
      console.error('DummyData: Failed to save to localStorage:', e)
    }
  }

  const loadLastData = () => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY)
      if (saved) return JSON.parse(saved)
    } catch (e) { /* ignore */ }
    return null
  }

  // Fetch and cache history data once
  const loadHistoryData = async () => {
    if (dataFetchPromise) return dataFetchPromise
    dataFetchPromise = (async () => {
      try {
        const [historyRes, statsRes] = await Promise.all([
          fetch('/data/sensor_history.json'),
          fetch('/data/sensor_stats.json')
        ])
        const history = await historyRes.json()
        const stats = await statsRes.json()
        historyData.value = history
        statsData.value = stats
        console.log(`[DummyData] Loaded ${history.length} rows from CSV (${stats.file_size_mb}MB dataset sampled)`)
      } catch (err) {
        console.error('[DummyData] Failed to load CSV data:', err)
      }
    })()
    return dataFetchPromise
  }

  // Generate next sensor data point with smooth interpolation
  const interpolateNextPoint = () => {
    if (!historyData.value.length) return null

    const idx = currentIndex % historyData.value.length
    const current = historyData.value[idx]
    const next = historyData.value[(idx + 1) % historyData.value.length]

    // Smooth transition: interpolate between current and next
    const nextIdx = (currentIndex + 1) % historyData.value.length
    const frac = 0.3 + Math.random() * 0.4 // randomize timing

    if (next) {
      const smooth = (a, b) => {
        const diff = b - a
        const change = diff * frac
        return a + change
      }

      return {
        temperature: smooth(current.suhu, next.suhu),
        humidity: smooth(current.kelembaban, next.kelembaban),
        voltage: smooth(current.tegangan, next.tegangan),
        current: smooth(current.arus, next.arus),
        power: smooth(current.daya, next.daya),
        peopleCount: current.jumlahOrang,
        timestamp: current.timestamp,
        timestampDisplay: new Date(current.timestamp).toLocaleString('id-ID', { timeZone: 'Asia/Jakarta' })
      }
    }

    return {
      temperature: current.suhu,
      humidity: current.kelembaban,
      voltage: current.tegangan,
      current: current.arus,
      power: current.daya,
      peopleCount: current.jumlahOrang,
      timestamp: current.timestamp,
      timestampDisplay: new Date(current.timestamp).toLocaleString('id-ID', { timeZone: 'Asia/Jakarta' })
    }
  }

  // Start playback simulation
  const startPlayback = () => {
    // Try loading cached data first
    const cached = loadLastData()
    if (cached) {
      sensorData.value = { ...cached }
      console.log('[DummyData] Cached data loaded from localStorage')
    }

    loadDataAndStart()
  }

  const loadDataAndStart = async () => {
    const cached = loadLastData()
    await loadHistoryData()

    if (historyData.value.length === 0) {
      // Fallback to synthetic data if CSV load fails
      console.warn('[DummyData] CSV data not available, falling back to synthetic generator')
      isConnected.value = true
      startSyntheticMode()
      return
    }

    // Restore position from cached data or start fresh
    if (cached) {
      // Find matching row in history
      currentIndex = historyData.value.findIndex(row => {
        if (!row.timestamp) return false
        return row.timestamp.split('T')[0] === new Date(cached.timestampDisplay).toISOString().split('T')[0]
      })
      if (currentIndex < 0) currentIndex = 0
    } else {
      currentIndex = 0
    }

    // Start streaming from history
    isConnected.value = true
    startHistoryPlayback()
  }

  const startHistoryPlayback = () => {
    // Update every 5 seconds to match ESP32 polling interval
    playbackTimer = setInterval(() => {
      const point = interpolateNextPoint()
      if (point) {
        sensorData.value = { ...point }
        saveLastData({ ...sensorData.value })
      }
      currentIndex++
    }, 5000)

    console.log(`[DummyData] History playback started (interval: 5s, ${historyData.value.length} rows)`)
  }

  const startSyntheticMode = () => {
    // Fallback: generate realistic random data based on CSV stats
    const base = {
      temperature: 30.19,
      humidity: 66.63,
      voltage: 227.04,
      current: 0.16,
      power: 36.93,
      peopleCount: 3
    }

    playbackTimer = setInterval(() => {
      sensorData.value = {
        temperature: +(base.temperature + (Math.random() - 0.5) * 8).toFixed(1),
        humidity: +(base.humidity + (Math.random() - 0.5) * 20).toFixed(1),
        voltage: +(base.voltage + (Math.random() - 0.5) * 30).toFixed(1),
        current: +(Math.max(0.1, base.current + (Math.random() - 0.5) * 0.2)).toFixed(2),
        power: +Math.max(25, base.power + (Math.random() - 0.5) * 80).toFixed(1),
        peopleCount: Math.floor(Math.random() * 6),
        timestamp: new Date().toISOString(),
        timestampDisplay: new Date().toLocaleString('id-ID', { timeZone: 'Asia/Jakarta' })
      }
      saveLastData({ ...sensorData.value })
    }, 5000)

    console.log('[DummyData] Synthetic mode started (based on CSV stats)')
  }

  const stopPlayback = () => {
    if (playbackTimer) {
      clearInterval(playbackTimer)
      playbackTimer = null
    }
    isConnected.value = false
  }

  // Watch sensor data changes
  watch(sensorData, (newData) => {
    saveLastData(newData)
  }, { deep: true })

  onUnmounted(() => {
    stopPlayback()
  })

  return {
    isConnected,
    sensorData,
    historyData,
    statsData,
    validationMetrics,
    isLoaded,
    startPlayback,
    stopPlayback
  }
}
