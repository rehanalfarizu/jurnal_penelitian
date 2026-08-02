import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import DataTable from '../DataTable.vue'

const replayRecord = {
  temperature: 30.1,
  humidity: 67,
  voltage: 227,
  current: 0.16,
  legacyPower: 36.3,
  formulaPower: 36.3,
  powerConsistencyError: 0,
  energyCumulativeWh: 12.75,
  occupancyStatus: 'occupied',
  sourceType: 'historical_replay',
  replayId: 'historical_replay_03',
  route: 'edge',
  valid: true,
  sourceTimestamp: '2026-05-17T00:00:00Z'
}

describe('DataTable replay semantics', () => {
  it('shows replay guidance while telemetry is unavailable', () => {
    const wrapper = mount(DataTable, {
      props: { sensorData: { sourceType: 'unavailable' } }
    })

    expect(wrapper.text()).toContain('Belum Ada Payload Replay')
    expect(wrapper.text()).not.toContain('MQTT')
  })

  it('labels a single payload as latest rather than an average', () => {
    const wrapper = mount(DataTable, {
      props: { sensorData: replayRecord, peopleCount: 1 }
    })

    expect(wrapper.text()).toContain('Suhu Payload Terbaru')
    expect(wrapper.text()).not.toContain('Rata-rata')
    expect(wrapper.text()).toContain('Energi Siklus')
    expect(wrapper.text()).toContain('Valid · Edge')
  })

  it('renders missing values as an em dash instead of fabricated zero', () => {
    const wrapper = mount(DataTable, {
      props: {
        sensorData: {
          ...replayRecord,
          temperature: null,
          current: null,
          legacyPower: null,
          formulaPower: null,
          powerConsistencyError: null,
          valid: false
        },
        peopleCount: null
      }
    })

    const cells = wrapper.findAll('tbody td')
    expect(cells[1].text()).toBe('—')
    expect(cells[4].text()).toBe('—')
    expect(cells[5].text()).toBe('—')
    expect(cells[6].text()).toBe('—')
    expect(cells[7].text()).toBe('—')
    expect(cells[9].text()).toBe('—')
    expect(wrapper.text()).toContain('Payload Tidak Valid')
  })
})
