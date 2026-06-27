import { ref, computed } from 'vue'

const STORAGE_KEY = 'digitaltwin_energy_management'

export function useEnergyManagement() {
  const settings = ref({
    tariffPerKwh: 1444.70, // Default tarif listrik PLN per kWh
    monthlyTarget: 100, // Target konsumsi bulanan dalam kWh
    dailyTarget: 3.33, // Target harian (monthlyTarget / 30)
    peakHourStart: 17, // Jam mulai peak hour (17:00)
    peakHourEnd: 22 // Jam selesai peak hour (22:00)
  })
  
  const energyData = ref([])
  const recommendations = ref([])
  
  // Load settings from localStorage
  const loadSettings = () => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
      if (stored) {
        const data = JSON.parse(stored)
        settings.value = { ...settings.value, ...data.settings }
        energyData.value = data.energyData || []
      }
    } catch (error) {
      console.error('Error loading energy settings:', error)
    }
  }
  
  // Save settings to localStorage
  const saveSettings = () => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({
        settings: settings.value,
        energyData: energyData.value
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
  
  // Add energy data point
  const addEnergyDataPoint = (power, timestamp = new Date()) => {
    const dataPoint = {
      timestamp: timestamp.toISOString(),
      power: power,
      hour: timestamp.getHours(),
      isPeakHour: timestamp.getHours() >= settings.value.peakHourStart && 
                  timestamp.getHours() <= settings.value.peakHourEnd
    }
    
    energyData.value.push(dataPoint)
    
    // Keep only last 7 days of data
    const sevenDaysAgo = new Date()
    sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7)
    energyData.value = energyData.value.filter(d => 
      new Date(d.timestamp) >= sevenDaysAgo
    )
    
    saveSettings()
  }
  
  // Calculate total energy consumption (kWh)
  const calculateTotalEnergy = (startDate, endDate) => {
    const filteredData = energyData.value.filter(d => {
      const timestamp = new Date(d.timestamp)
      return timestamp >= startDate && timestamp <= endDate
    })
    
    if (filteredData.length < 2) return 0
    
    let totalEnergy = 0
    for (let i = 1; i < filteredData.length; i++) {
      const timeDiff = (new Date(filteredData[i].timestamp) - new Date(filteredData[i - 1].timestamp)) / 3600000
      const avgPower = (filteredData[i].power + filteredData[i - 1].power) / 2
      totalEnergy += avgPower * timeDiff
    }
    
    return totalEnergy / 1000 // Convert Wh to kWh
  }
  
  // Calculate cost
  const calculateCost = (energyKwh) => {
    return energyKwh * settings.value.tariffPerKwh
  }
  
  // Get today's consumption
  const getTodayConsumption = () => {
    const today = new Date()
    today.setHours(0, 0, 0, 0)
    const tomorrow = new Date(today)
    tomorrow.setDate(tomorrow.getDate() + 1)
    
    return calculateTotalEnergy(today, tomorrow)
  }
  
  // Get this month's consumption
  const getMonthlyConsumption = () => {
    const now = new Date()
    const startOfMonth = new Date(now.getFullYear(), now.getMonth(), 1)
    const endOfMonth = new Date(now.getFullYear(), now.getMonth() + 1, 0, 23, 59, 59)
    
    return calculateTotalEnergy(startOfMonth, endOfMonth)
  }
  
  // Peak usage analysis
  const analyzePeakUsage = () => {
    const last24Hours = energyData.value.filter(d => {
      const timestamp = new Date(d.timestamp)
      const now = new Date()
      const diff = now - timestamp
      return diff <= 24 * 60 * 60 * 1000
    })
    
    // Group by hour
    const hourlyData = {}
    for (let i = 0; i < 24; i++) {
      hourlyData[i] = []
    }
    
    last24Hours.forEach(d => {
      hourlyData[d.hour].push(d.power)
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
  
  // ML-based recommendations using pattern detection
  const generateRecommendations = () => {
    const recs = []
    const peakAnalysis = analyzePeakUsage()
    const todayConsumption = getTodayConsumption()
    const monthlyConsumption = getMonthlyConsumption()
    const now = new Date()
    const daysInMonth = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate()
    const dayOfMonth = now.getDate()
    
    // 1. Peak hour usage recommendation
    const peakHourUsage = peakAnalysis.filter(h => h.isPeakHour)
    const avgPeakPower = peakHourUsage.reduce((sum, h) => sum + h.avgPower, 0) / peakHourUsage.length
    
    if (avgPeakPower > 500) {
      recs.push({
        type: 'peak-hour',
        priority: 'high',
        title: 'Penggunaan Tinggi saat Peak Hour',
        description: `Rata-rata daya saat peak hour (${settings.value.peakHourStart}:00-${settings.value.peakHourEnd}:00) mencapai ${avgPeakPower.toFixed(0)}W. Pertimbangkan menggeser penggunaan peralatan berdaya tinggi ke luar jam peak.`,
        potentialSaving: (avgPeakPower * 0.3 * 5 * settings.value.tariffPerKwh / 1000).toFixed(0), // 30% reduction, 5 hours
        icon: '⚠️'
      })
    }
    
    // 2. Monthly target tracking
    const projectedMonthly = (monthlyConsumption / dayOfMonth) * daysInMonth
    if (projectedMonthly > settings.value.monthlyTarget * 1.1) {
      const excessPercentage = ((projectedMonthly - settings.value.monthlyTarget) / settings.value.monthlyTarget * 100).toFixed(0)
      recs.push({
        type: 'target-exceeded',
        priority: 'high',
        title: 'Proyeksi Melebihi Target Bulanan',
        description: `Proyeksi konsumsi bulan ini ${projectedMonthly.toFixed(1)} kWh (${excessPercentage}% di atas target ${settings.value.monthlyTarget} kWh). Kurangi penggunaan rata-rata harian menjadi ${((settings.value.monthlyTarget - monthlyConsumption) / (daysInMonth - dayOfMonth)).toFixed(2)} kWh/hari.`,
        potentialSaving: ((projectedMonthly - settings.value.monthlyTarget) * settings.value.tariffPerKwh).toFixed(0),
        icon: '📊'
      })
    } else if (projectedMonthly < settings.value.monthlyTarget * 0.8) {
      recs.push({
        type: 'target-met',
        priority: 'low',
        title: 'Target Tercapai dengan Baik! 🎉',
        description: `Konsumsi Anda ${((1 - projectedMonthly / settings.value.monthlyTarget) * 100).toFixed(0)}% lebih rendah dari target. Pertahankan pola penggunaan ini!`,
        potentialSaving: ((settings.value.monthlyTarget - projectedMonthly) * settings.value.tariffPerKwh).toFixed(0),
        icon: '✅'
      })
    }
    
    // 3. Standby power detection (ML pattern: constant low power)
    const constantLowPower = energyData.value.filter(d => {
      const hour = new Date(d.timestamp).getHours()
      return hour >= 0 && hour <= 5 && d.power > 20 && d.power < 100
    })
    
    if (constantLowPower.length > 10) {
      const avgStandbyPower = constantLowPower.reduce((sum, d) => sum + d.power, 0) / constantLowPower.length
      const dailyStandbyEnergy = avgStandbyPower * 24 / 1000 // kWh
      const monthlyStandbyCost = dailyStandbyEnergy * 30 * settings.value.tariffPerKwh
      
      recs.push({
        type: 'standby-power',
        priority: 'medium',
        title: 'Deteksi Standby Power',
        description: `Terdeteksi daya standby ~${avgStandbyPower.toFixed(0)}W di malam hari. Matikan peralatan yang tidak digunakan untuk menghemat ~${monthlyStandbyCost.toFixed(0)} Rp/bulan.`,
        potentialSaving: monthlyStandbyCost.toFixed(0),
        icon: '🔌'
      })
    }
    
    // 4. Sudden spike detection (ML anomaly detection)
    const last50Points = energyData.value.slice(-50)
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
          potentialSaving: 0,
          icon: '⚡'
        })
      }
    }
    
    // 5. Time-based recommendation (ML pattern: usage patterns)
    const morningUsage = energyData.value.filter(d => {
      const hour = new Date(d.timestamp).getHours()
      return hour >= 6 && hour <= 9
    })
    const afternoonUsage = energyData.value.filter(d => {
      const hour = new Date(d.timestamp).getHours()
      return hour >= 12 && hour <= 15
    })
    
    if (morningUsage.length > 0 && afternoonUsage.length > 0) {
      const avgMorning = morningUsage.reduce((sum, d) => sum + d.power, 0) / morningUsage.length
      const avgAfternoon = afternoonUsage.reduce((sum, d) => sum + d.power, 0) / afternoonUsage.length
      
      if (avgAfternoon > avgMorning * 1.5) {
        recs.push({
          type: 'time-pattern',
          priority: 'low',
          title: 'Pola Penggunaan Siang Hari',
          description: `Penggunaan siang hari (${avgAfternoon.toFixed(0)}W) lebih tinggi dari pagi (${avgMorning.toFixed(0)}W). Manfaatkan cahaya alami untuk mengurangi penggunaan AC dan lampu.`,
          potentialSaving: ((avgAfternoon - avgMorning) * 3 * settings.value.tariffPerKwh / 1000 * 30).toFixed(0),
          icon: '☀️'
        })
      }
    }
    
    // 6. Efficiency score and general recommendation
    const efficiency = Math.max(0, Math.min(100, 100 - (projectedMonthly / settings.value.monthlyTarget - 1) * 100))
    if (efficiency < 70) {
      recs.push({
        type: 'general',
        priority: 'medium',
        title: 'Skor Efisiensi Rendah',
        description: `Skor efisiensi energi Anda: ${efficiency.toFixed(0)}/100. Tips: 1) Gunakan AC pada 25°C, 2) Cabut charger yang tidak digunakan, 3) Ganti ke lampu LED, 4) Bersihkan filter AC rutin.`,
        potentialSaving: ((projectedMonthly - settings.value.monthlyTarget) * settings.value.tariffPerKwh * 0.5).toFixed(0),
        icon: '💡'
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
    energyData,
    recommendations,
    loadSettings,
    saveSettings,
    updateTariff,
    updateMonthlyTarget,
    addEnergyDataPoint,
    calculateTotalEnergy,
    calculateCost,
    getTodayConsumption,
    getMonthlyConsumption,
    analyzePeakUsage,
    generateRecommendations
  }
}
