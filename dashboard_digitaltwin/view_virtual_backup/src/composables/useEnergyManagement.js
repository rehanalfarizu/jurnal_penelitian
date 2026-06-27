import { ref, computed, watch } from 'vue'
import { useHistoricalData } from './useHistoricalData'

const STORAGE_KEY = 'digitaltwin_energy_settings'

export function useEnergyManagement() {
  const { historicalData, getStatistics, isValidPower, loadHistoricalData } = useHistoricalData()

  const settings = ref({
    tariffPerKwh: 1444.70, // Default tarif listrik PLN per kWh
    monthlyTarget: 300, // Target konsumsi bulanan dalam kWh (cukup untuk AC + equipment)
    dailyTarget: 10, // Target harian (monthlyTarget / 30)
    peakHourStart: 17, // Jam mulai peak hour (17:00)
    peakHourEnd: 22 // Jam selesai peak hour (22:00)
  })

  const recommendations = ref([])
  const isLoading = ref(false)

  // Load settings from localStorage
  const loadSettings = () => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
      if (stored) {
        const data = JSON.parse(stored)
        settings.value = { ...settings.value, ...data.settings }
      }
    } catch (error) {
      console.error('Error loading energy settings:', error)
    }
  }

  // Save settings to localStorage
  const saveSettings = () => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({
        settings: settings.value
      }))
    } catch (error) {
      console.error('Error saving energy settings:', error)
    }
  }

  // Update tariff
  const updateTariff = (newTariff) => {
    settings.value.tariffPerKwh = parseFloat(newTariff)
    saveSettings()
  }

  // Update monthly target
  const updateMonthlyTarget = (newTarget) => {
    settings.value.monthlyTarget = parseFloat(newTarget)
    settings.value.dailyTarget = newTarget / 30
    saveSettings()
  }

  // Calculate cost
  const calculateCost = (energyKwh) => {
    return energyKwh * settings.value.tariffPerKwh
  }

  // Get stats from historical data
  const getEnergyStats = computed(() => {
    return getStatistics(new Date(new Date().setHours(0, 0, 0, 0)), new Date())
  })

  // Get today's consumption from historical data (kWh)
  const getTodayConsumption = () => {
    const stats = getStatistics(
      new Date(new Date().setHours(0, 0, 0, 0)),
      new Date()
    )
    return stats?.totalEnergy || 0
  }

  // Get this month's consumption from historical data (kWh)
  const getMonthlyConsumption = () => {
    const now = new Date()
    const startOfMonth = new Date(now.getFullYear(), now.getMonth(), 1)
    const stats = getStatistics(startOfMonth, now)
    return stats?.totalEnergy || 0
  }

  // Get power data from historical
  const getPowerData = () => {
    if (historicalData.value.length === 0) return []

    return historicalData.value
      .filter(d => isValidPower(d.power))
      .map(d => ({
        timestamp: d.timestamp,
        power: d.power,
        hour: new Date(d.timestamp).getHours()
      }))
      .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp))
  }

  // Peak usage analysis from historical data
  const analyzePeakUsage = () => {
    const powerData = getPowerData()

    if (powerData.length === 0) {
      // Return empty 24-hour data if no data
      return Array.from({ length: 24 }, (_, i) => ({
        hour: i,
        avgPower: 0,
        isPeakHour: i >= settings.value.peakHourStart && i <= settings.value.peakHourEnd
      }))
    }

    // Group by hour
    const hourlyData = {}
    for (let i = 0; i < 24; i++) {
      hourlyData[i] = []
    }

    // Filter last 24 hours
    const now = new Date()
    const last24h = new Date(now.getTime() - 24 * 60 * 60 * 1000)

    powerData
      .filter(d => new Date(d.timestamp) >= last24h)
      .forEach(d => {
        const hour = new Date(d.timestamp).getHours()
        hourlyData[hour].push(d.power)
      })

    // Calculate average for each hour
    const hourlyAverage = Object.keys(hourlyData).map(hour => ({
      hour: parseInt(hour),
      avgPower: hourlyData[hour].length > 0
        ? hourlyData[hour].reduce((sum, p) => sum + p, 0) / hourlyData[hour].length
        : 0,
      isPeakHour: parseInt(hour) >= settings.value.peakHourStart &&
                  parseInt(hour) <= settings.value.peakHourEnd
    }))

    return hourlyAverage.sort((a, b) => b.avgPower - a.avgPower)
  }

  // Add energy data point (compatibility)
  const addEnergyDataPoint = (power, timestamp = new Date()) => {
    // No-op: data comes from historicalData now
    console.log('[EnergyManagement] Data point received (ignored, using historicalData)')
  }

  // ML-based recommendations using pattern detection
  const generateRecommendations = () => {
    const recs = []
    const peakAnalysis = analyzePeakUsage()
    const todayConsumption = getTodayConsumption()
    const monthlyConsumption = getMonthlyConsumption()
    const now = new Date()
    const daysInMonth = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate()
    const dayOfMonth = now.getDate()
    const projectedMonthly = (monthlyConsumption / dayOfMonth) * daysInMonth

    // 1. Peak hour usage recommendation
    const peakHourUsage = peakAnalysis.filter(h => h.isPeakHour)
    const avgPeakPower = peakHourUsage.length > 0
      ? peakHourUsage.reduce((sum, h) => sum + h.avgPower, 0) / peakHourUsage.length
      : 0

    if (avgPeakPower > 100) { // Lower threshold
      recs.push({
        type: 'peak-hour',
        priority: avgPeakPower > 500 ? 'high' : 'medium',
        title: 'Penggunaan Tinggi saat Peak Hour',
        description: `Rata-rata daya saat peak hour (${settings.value.peakHourStart}:00-${settings.value.peakHourEnd}:00) mencapai ${avgPeakPower.toFixed(0)}W. Pertimbangkan menggeser penggunaan peralatan berdaya tinggi ke luar jam peak.`,
        potentialSaving: (avgPeakPower * 0.3 * 5 * settings.value.tariffPerKwh / 1000).toFixed(0)
      })
    }

    // 2. Monthly target tracking
    if (projectedMonthly > settings.value.monthlyTarget * 1.1 && monthlyConsumption > 0) {
      const excessPercentage = ((projectedMonthly - settings.value.monthlyTarget) / settings.value.monthlyTarget * 100).toFixed(0)
      recs.push({
        type: 'target-exceeded',
        priority: 'high',
        title: 'Proyeksi Melebihi Target Bulanan',
        description: `Proyeksi konsumsi bulan ini ${projectedMonthly.toFixed(1)} kWh (${excessPercentage}% di atas target ${settings.value.monthlyTarget} kWh). Kurangi penggunaan rata-rata harian menjadi ${((settings.value.monthlyTarget - monthlyConsumption) / Math.max(1, daysInMonth - dayOfMonth)).toFixed(2)} kWh/hari.`,
        potentialSaving: ((projectedMonthly - settings.value.monthlyTarget) * settings.value.tariffPerKwh).toFixed(0)
      })
    } else if (projectedMonthly < settings.value.monthlyTarget * 0.8 && monthlyConsumption > 0) {
      recs.push({
        type: 'target-met',
        priority: 'low',
        title: 'Target Tercapai dengan Baik!',
        description: `Konsumsi Anda ${((1 - projectedMonthly / settings.value.monthlyTarget) * 100).toFixed(0)}% lebih rendah dari target. Pertahankan pola penggunaan ini!`,
        potentialSaving: ((settings.value.monthlyTarget - projectedMonthly) * settings.value.tariffPerKwh).toFixed(0)
      })
    }

    // 3. Standby power detection (night hours)
    const powerData = getPowerData()
    if (powerData.length > 10) {
      const nightData = powerData.filter(d => {
        const hour = new Date(d.timestamp).getHours()
        return hour >= 0 && hour <= 5
      })

      if (nightData.length > 5) {
        const avgNightPower = nightData.reduce((sum, d) => sum + d.power, 0) / nightData.length
        if (avgNightPower > 20) {
          const monthlyStandbyCost = avgNightPower * 24 / 1000 * 30 * settings.value.tariffPerKwh
          recs.push({
            type: 'standby-power',
            priority: 'medium',
            title: 'Deteksi Standby Power',
            description: `Terdeteksi daya standby ~${avgNightPower.toFixed(0)}W di malam hari. Matikan peralatan yang tidak digunakan untuk menghemat ~${monthlyStandbyCost.toFixed(0)} Rp/bulan.`,
            potentialSaving: monthlyStandbyCost.toFixed(0)
          })
        }
      }

      // 4. Sudden spike detection (ML anomaly detection)
      const last50Points = powerData.slice(-50)
      if (last50Points.length > 10) {
        const avgPower = last50Points.reduce((sum, d) => sum + d.power, 0) / last50Points.length
        const stdDev = Math.sqrt(
          last50Points.reduce((sum, d) => sum + Math.pow(d.power - avgPower, 2), 0) / last50Points.length
        )

        const anomalies = last50Points.filter(d => d.power > avgPower + 2 * stdDev)
        if (anomalies.length > 0) {
          const maxAnomaly = Math.max(...anomalies.map(a => a.power))
          recs.push({
            type: 'anomaly',
            priority: 'medium',
            title: 'Deteksi Lonjakan Daya',
            description: `Terdeteksi lonjakan daya hingga ${maxAnomaly.toFixed(0)}W (${((maxAnomaly - avgPower) / avgPower * 100).toFixed(0)}% di atas rata-rata). Periksa peralatan yang baru dihidupkan.`,
            potentialSaving: 0
          })
        }
      }
    }

    // 5. Efficiency score
    if (monthlyConsumption > 0) {
      const efficiency = Math.max(0, Math.min(100, 100 - Math.max(0, (projectedMonthly / settings.value.monthlyTarget - 1) * 100)))
      if (efficiency < 60) {
        recs.push({
          type: 'general',
          priority: 'medium',
          title: 'Skor Efisiensi Rendah',
          description: `Skor efisiensi energi Anda: ${efficiency.toFixed(0)}/100. Tips: 1) Gunakan AC pada 25C, 2) Cabut charger yang tidak digunakan, 3) Ganti ke lampu LED, 4) Bersihkan filter AC rutin.`,
          potentialSaving: ((projectedMonthly - settings.value.monthlyTarget) * settings.value.tariffPerKwh * 0.3).toFixed(0)
        })
      }
    }

    // 6. No data warning
    if (historicalData.value.length === 0) {
      recs.push({
        type: 'info',
        priority: 'low',
        title: 'Menunggu Data Sensor',
        description: 'Sistem sedang menunggu data dari sensor. Pastikan ESP32 dan RPi gateway berjalan dengan baik.',
        potentialSaving: 0
      })
    }

    recommendations.value = recs.sort((a, b) => {
      const priorityOrder = { high: 3, medium: 2, low: 1 }
      return priorityOrder[b.priority] - priorityOrder[a.priority]
    })

    return recommendations.value
  }

  return {
    settings,
    recommendations,
    isLoading,
    loadSettings,
    saveSettings,
    updateTariff,
    updateMonthlyTarget,
    addEnergyDataPoint,
    calculateCost,
    getTodayConsumption,
    getMonthlyConsumption,
    analyzePeakUsage,
    generateRecommendations,
    getPowerData,
    historicalData,
    isValidPower
  }
}
