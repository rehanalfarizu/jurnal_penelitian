import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useTelemetry } from '../useTelemetry'

const contractRecord = {
  success: true,
  data: {
    timestamp_utc: '2026-06-01T00:00:00Z',
    device_id: 'RASPBERRY_PI_GATEWAY_001',
    source_type: 'historical_replay',
    provenance: {
      lineage_classification: 'transformed_historical_replay',
      source_timestamp_utc: '2026-05-17T00:00:00Z',
      replay_timestamp_utc: '2026-06-01T00:00:00Z',
      replay_id: 'historical_replay_03',
      replay_block_id: 3,
      source_row_id: 'historical:000042',
      source_row_index: 42
    },
    monitoring: {
      temperature_c: 30.1,
      humidity_pct: 67,
      voltage_v: 227,
      current_a: 0.16,
      power_legacy_w: 36.3,
      power_formula_w: 36.3,
      power_consistency_error_w: 0,
      energy_interval_legacy_wh: 0.05,
      energy_cumulative_legacy_wh: 12.75,
      energy_integration_status: 'integrated',
      people_count: 1,
      occupancy_status: 'occupied',
      voltage_status: 'normal',
      current_status: 'normal'
    },
    digital_twin: {
      representation_class: 'monitoring_oriented_one_way_prototype',
      synchronization_mode: 'request_driven_historical_replay',
      supported_views: ['geospatial_site', 'building', 'indoor'],
      application_lod: [
        { lod_id: 'LoD-A', view: 'geospatial_site', scale: 'site', detail: 'macro context' },
        { lod_id: 'LoD-B', view: 'building', scale: 'building', detail: 'building summary' },
        { lod_id: 'LoD-C', view: 'indoor', scale: 'indoor', detail: 'indoor detail' }
      ],
      lod_transition: 'manual_view_selection',
      geospatial_reference: {
        latitude: -7.723,
        longitude: 110.5187,
        crs: 'EPSG:4326',
        verification_status: 'legacy_coordinate_not_survey_validated'
      },
      scale_semantics: 'application visualization scales',
      data_direction: 'physical_or_replayed_source_to_digital_representation_only'
    },
    processing: {
      tier: 'edge',
      valid: true,
      route_reason: 'normal_local_monitoring',
      compute_latency_ms: 0.02,
      serialization_latency_ms: 0.01,
      network_latency_ms: null,
      end_to_end_latency_ms: 0.03,
      freshness_ms: 0.03
    }
  }
}

describe('useTelemetry research telemetry contract', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.useRealTimers()
  })

  it('starts disconnected without fabricated demo values', () => {
    const telemetry = useTelemetry()
    expect(telemetry.telemetryConnected.value).toBe(false)
    expect(telemetry.sensorData.value.sourceType).toBe('unavailable')
    expect(telemetry.sensorData.value.power).toBeNull()
  })

  it('maps legacy power and replay provenance without an estimate', async () => {
    fetch.mockResolvedValue({
      ok: true,
      json: async () => contractRecord
    })
    const telemetry = useTelemetry()
    const success = await telemetry.fetchLatestData()
    expect(success).toBe(true)
    expect(telemetry.sensorData.value.legacyPower).toBe(36.3)
    expect(telemetry.sensorData.value.formulaPower).toBe(36.3)
    expect(telemetry.sensorData.value.power).toBe(36.3)
    expect(telemetry.sensorData.value.energyCumulativeWh).toBe(12.75)
    expect(telemetry.sensorData.value.occupancyStatus).toBe('occupied')
    expect(telemetry.sensorData.value.digitalTwin.supportedViews).toEqual([
      'geospatial_site',
      'building',
      'indoor'
    ])
    expect(telemetry.sensorData.value.digitalTwin.applicationLod[2].lod_id).toBe(
      'LoD-C'
    )
    expect(telemetry.sensorData.value.digitalTwin.lodTransition).toBe(
      'manual_view_selection'
    )
    expect(telemetry.sensorData.value.sourceType).toBe('historical_replay')
    expect(telemetry.sensorData.value.replayBlockId).toBe(3)
    expect(telemetry.sensorData.value.sourceRowId).toBe('historical:000042')
    expect(telemetry.sensorData.value.route).toBe('edge')
    expect(telemetry.sensorData.value.lineageClassification).toBe(
      'transformed_historical_replay'
    )
  })

  it('keeps missing monitoring values distinct from measured zero', async () => {
    fetch.mockResolvedValue({
      ok: true,
      json: async () => ({
        ...contractRecord,
        data: {
          ...contractRecord.data,
          monitoring: {
            ...contractRecord.data.monitoring,
            current_a: null,
            power_legacy_w: null,
            power_formula_w: 0,
            people_count: null
          },
          processing: {
            ...contractRecord.data.processing,
            freshness_ms: null
          }
        }
      })
    })
    const telemetry = useTelemetry()
    await telemetry.fetchLatestData()
    expect(telemetry.sensorData.value.current).toBeNull()
    expect(telemetry.sensorData.value.power).toBeNull()
    expect(telemetry.sensorData.value.formulaPower).toBe(0)
    expect(telemetry.sensorData.value.peopleCount).toBeNull()
    expect(telemetry.sensorData.value.freshnessMs).toBeNull()
  })

  it('remains disconnected when the endpoint fails', async () => {
    fetch.mockRejectedValue(new Error('offline'))
    const telemetry = useTelemetry()
    expect(await telemetry.fetchLatestData()).toBe(false)
    expect(telemetry.telemetryConnected.value).toBe(false)
    expect(telemetry.connectionError.value).toBe('offline')
  })

  it('rejects a legacy payload outside the research schema', async () => {
    fetch.mockResolvedValue({
      ok: true,
      json: async () => ({
        success: true,
        data: {
          timestamp: '2026-06-01T00:00:00Z',
          tegangan: 220,
          arus: 0.16,
          daya: 35.2
        }
      })
    })
    const telemetry = useTelemetry()
    expect(await telemetry.fetchLatestData()).toBe(false)
    expect(telemetry.telemetryConnected.value).toBe(false)
    expect(telemetry.connectionError.value).toBe(
      'Payload tidak sesuai kontrak replay historis'
    )
  })
})
