import { onUnmounted, ref } from 'vue'
import { TELEMETRY_API_URL } from '../lib/appConfig'

const POLLING_INTERVAL_MS = 5000

const initialSensorData = () => ({
  temperature: 0,
  humidity: 0,
  voltage: 0,
  current: 0,
  observedPower: 0,
  estimatedPower: 0,
  power: 0,
  peopleCount: 0,
  voltageStatus: 'unknown',
  currentStatus: 'unknown',
  sourceType: 'unavailable',
  scenarioId: null,
  runId: null,
  modelName: 'unavailable',
  modelScope: 'unavailable',
  timestamp: null
})

const numberOrZero = value => {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : 0
}

const normalizeRecord = data => {
  // Preferred research contract.
  if (data.observed && data.estimate) {
    const observedPower = numberOrZero(data.observed.power_w)
    const estimatedPower = numberOrZero(data.estimate.power_w)
    return {
      temperature: numberOrZero(data.observed.temperature_c),
      humidity: numberOrZero(data.observed.humidity_pct),
      voltage: numberOrZero(data.observed.voltage_v),
      current: numberOrZero(data.observed.current_a),
      observedPower,
      estimatedPower,
      power: estimatedPower,
      peopleCount: Math.max(0, Math.trunc(numberOrZero(data.observed.people_count))),
      voltageStatus: data.observed.voltage_v > 0 ? 'normal' : 'invalid',
      currentStatus: data.observed.current_a > 0 ? 'normal' : 'below_threshold',
      sourceType: data.source_type || 'unknown',
      scenarioId: data.scenario_id || null,
      runId: data.run_id || null,
      modelName: data.estimate.model_name || 'unknown',
      modelScope: data.estimate.model_scope || 'unknown',
      timestamp: data.timestamp_utc || null
    }
  }

  // Read-only compatibility with the historical Azure response.
  const voltage = numberOrZero(data.tegangan)
  const current = numberOrZero(data.arus)
  const observedPower = numberOrZero(data.daya) || voltage * current
  return {
    temperature: numberOrZero(data.suhu),
    humidity: numberOrZero(data.kelembaban),
    voltage,
    current,
    observedPower,
    estimatedPower: observedPower,
    power: observedPower,
    peopleCount: Math.max(0, Math.trunc(numberOrZero(data.jumlah_orang))),
    voltageStatus: data.status_tegangan || (voltage > 0 ? 'normal' : 'invalid'),
    currentStatus: data.status_arus || (current > 0 ? 'normal' : 'below_threshold'),
    sourceType: 'live_sensor',
    scenarioId: null,
    runId: null,
    modelName: 'firmware_v_times_i',
    modelScope: 'legacy_observation_only',
    timestamp: data.timestamp || null
  }
}

export function useMQTT() {
  const mqttConnected = ref(false)
  const sensorData = ref(initialSensorData())
  const connectionError = ref(null)
  let pollingTimer = null
  let requestInFlight = false

  const fetchLatestData = async () => {
    if (requestInFlight) return false
    requestInFlight = true
    try {
      const response = await fetch(`${TELEMETRY_API_URL}/telemetry/latest`)
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      const result = await response.json()
      if (!result.success || !result.data) throw new Error('Kontrak telemetry tidak valid')
      sensorData.value = normalizeRecord(result.data)
      connectionError.value = null
      mqttConnected.value = true
      return true
    } catch (error) {
      mqttConnected.value = false
      connectionError.value = error.message
      return false
    } finally {
      requestInFlight = false
    }
  }

  const connectMQTT = () => {
    fetchLatestData()
    if (!pollingTimer) {
      pollingTimer = window.setInterval(fetchLatestData, POLLING_INTERVAL_MS)
    }
  }

  const disconnectMQTT = () => {
    if (pollingTimer) window.clearInterval(pollingTimer)
    pollingTimer = null
    mqttConnected.value = false
  }

  onUnmounted(disconnectMQTT)

  return {
    mqttConnected,
    sensorData,
    connectionError,
    connectMQTT,
    disconnectMQTT,
    fetchLatestFromAzure: fetchLatestData
  }
}
