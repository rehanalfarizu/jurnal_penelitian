import { getCurrentInstance, onUnmounted, ref } from 'vue'
import {
  TELEMETRY_API_URL,
  TELEMETRY_POLL_INTERVAL_MS
} from '../lib/appConfig'

const initialSensorData = () => ({
  temperature: null,
  humidity: null,
  voltage: null,
  current: null,
  legacyPower: null,
  formulaPower: null,
  powerConsistencyError: null,
  energyIntervalWh: null,
  energyCumulativeWh: null,
  energyIntegrationStatus: 'unknown',
  power: null,
  peopleCount: null,
  occupancyStatus: 'unknown',
  voltageStatus: 'unknown',
  currentStatus: 'unknown',
  sourceType: 'unavailable',
  lineageClassification: null,
  replayId: null,
  replayBlockId: null,
  sourceRowId: null,
  sourceRowIndex: null,
  route: 'unavailable',
  routeReason: 'unavailable',
  valid: false,
  freshnessMs: null,
  sourceTimestamp: null,
  replayTimestamp: null,
  timestamp: null,
  digitalTwin: null,
  scopeNote: 'Menunggu payload replay historis.'
})

const numberOrNull = value => {
  if (value === null || value === undefined || value === '') return null
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

const nonNegativeIntegerOrNull = value => {
  const parsed = numberOrNull(value)
  return parsed !== null && parsed >= 0 ? Math.trunc(parsed) : null
}

const normalizeRecord = data => {
  if (
    !data ||
    data.source_type !== 'historical_replay' ||
    !data.monitoring ||
    !data.provenance ||
    !data.processing
  ) {
    throw new Error('Payload tidak sesuai kontrak replay historis')
  }

  const temperature = numberOrNull(data.monitoring.temperature_c)
  const humidity = numberOrNull(data.monitoring.humidity_pct)
  const voltage = numberOrNull(data.monitoring.voltage_v)
  const current = numberOrNull(data.monitoring.current_a)
  const legacyPower = numberOrNull(data.monitoring.power_legacy_w)
  return {
    temperature,
    humidity,
    voltage,
    current,
    legacyPower,
    formulaPower: numberOrNull(data.monitoring.power_formula_w),
    powerConsistencyError: numberOrNull(
      data.monitoring.power_consistency_error_w
    ),
    energyIntervalWh: numberOrNull(
      data.monitoring.energy_interval_legacy_wh
    ),
    energyCumulativeWh: numberOrNull(
      data.monitoring.energy_cumulative_legacy_wh
    ),
    energyIntegrationStatus:
      data.monitoring.energy_integration_status || 'unknown',
    power: legacyPower,
    peopleCount: nonNegativeIntegerOrNull(data.monitoring.people_count),
    occupancyStatus: data.monitoring.occupancy_status || 'unknown',
    voltageStatus: data.monitoring.voltage_status || 'unknown',
    currentStatus: data.monitoring.current_status || 'unknown',
    sourceType: data.source_type,
    lineageClassification:
      data.provenance.lineage_classification || null,
    replayId: data.provenance.replay_id || null,
    replayBlockId: data.provenance.replay_block_id ?? null,
    sourceRowId: data.provenance.source_row_id || null,
    sourceRowIndex: data.provenance.source_row_index ?? null,
    route: data.processing.tier || 'unknown',
    routeReason: data.processing.route_reason || 'unknown',
    valid: Boolean(data.processing.valid),
    freshnessMs: numberOrNull(data.processing.freshness_ms),
    sourceTimestamp: data.provenance.source_timestamp_utc || null,
    replayTimestamp: data.provenance.replay_timestamp_utc || null,
    timestamp: data.timestamp_utc || null,
    digitalTwin: data.digital_twin
      ? {
          representationClass: data.digital_twin.representation_class,
          synchronizationMode: data.digital_twin.synchronization_mode,
          supportedViews: data.digital_twin.supported_views,
          applicationLod: data.digital_twin.application_lod,
          lodTransition: data.digital_twin.lod_transition,
          latitude: numberOrNull(
            data.digital_twin.geospatial_reference?.latitude
          ),
          longitude: numberOrNull(
            data.digital_twin.geospatial_reference?.longitude
          ),
          crs: data.digital_twin.geospatial_reference?.crs,
          geospatialVerification:
            data.digital_twin.geospatial_reference?.verification_status,
          scaleSemantics: data.digital_twin.scale_semantics,
          dataDirection: data.digital_twin.data_direction
        }
      : null,
    scopeNote: 'Energi adalah integral dari proksi daya legacy V×I pada replay historis; bukan keluaran model atau pengukuran energi aktif terkalibrasi.'
  }
}

export function useTelemetry() {
  const telemetryConnected = ref(false)
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
      telemetryConnected.value = true
      return true
    } catch (error) {
      telemetryConnected.value = false
      connectionError.value = error.message
      return false
    } finally {
      requestInFlight = false
    }
  }

  const connectTelemetry = () => {
    fetchLatestData()
    if (!pollingTimer) {
      pollingTimer = window.setInterval(
        fetchLatestData,
        TELEMETRY_POLL_INTERVAL_MS
      )
    }
  }

  const disconnectTelemetry = () => {
    if (pollingTimer) window.clearInterval(pollingTimer)
    pollingTimer = null
    telemetryConnected.value = false
  }

  if (getCurrentInstance()) {
    onUnmounted(disconnectTelemetry)
  }

  return {
    telemetryConnected,
    sensorData,
    connectionError,
    connectTelemetry,
    disconnectTelemetry,
    fetchLatestData
  }
}
