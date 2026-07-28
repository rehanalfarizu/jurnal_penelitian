import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useMQTT } from '../useMQTT'

const contractRecord = {
  success: true,
  data: {
    timestamp_utc: '2026-06-01T00:00:00Z',
    device_id: 'RASPBERRY_PI_GATEWAY_001',
    source_type: 'synthetic_calibrated',
    scenario_id: 'normal',
    run_id: 'normal_run_00',
    observed: {
      temperature_c: 30.1,
      humidity_pct: 67,
      voltage_v: 227,
      current_a: 0.16,
      power_w: 36.32,
      people_count: 1
    },
    estimate: {
      power_w: 36.8,
      model_name: 'random_forest',
      model_scope: 'synthetic_calibrated_scenarios_only'
    },
    processing: {
      tier: 'replay',
      compute_latency_ms: 0,
      network_latency_ms: null,
      end_to_end_latency_ms: null
    }
  }
}

describe('useMQTT research telemetry contract', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.useRealTimers()
  })

  it('starts disconnected without fabricated demo values', () => {
    const telemetry = useMQTT()
    expect(telemetry.mqttConnected.value).toBe(false)
    expect(telemetry.sensorData.value.sourceType).toBe('unavailable')
    expect(telemetry.sensorData.value.power).toBe(0)
  })

  it('maps observed and estimated power separately', async () => {
    fetch.mockResolvedValue({
      ok: true,
      json: async () => contractRecord
    })
    const telemetry = useMQTT()
    const success = await telemetry.fetchLatestFromAzure()
    expect(success).toBe(true)
    expect(telemetry.sensorData.value.observedPower).toBe(36.32)
    expect(telemetry.sensorData.value.estimatedPower).toBe(36.8)
    expect(telemetry.sensorData.value.power).toBe(36.8)
    expect(telemetry.sensorData.value.sourceType).toBe('synthetic_calibrated')
  })

  it('remains disconnected when the endpoint fails', async () => {
    fetch.mockRejectedValue(new Error('offline'))
    const telemetry = useMQTT()
    expect(await telemetry.fetchLatestFromAzure()).toBe(false)
    expect(telemetry.mqttConnected.value).toBe(false)
    expect(telemetry.connectionError.value).toBe('offline')
  })
})
