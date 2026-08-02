import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import MultiscaleDigitalTwin from '../MultiscaleDigitalTwin.vue'

vi.mock('../DigitalTwin3D_Babylon.vue', () => ({
  default: {
    name: 'DigitalTwin3D',
    template: '<div data-test="indoor-3d">Indoor 3D</div>'
  }
}))

const sensorData = {
  power: 36.3,
  energyCumulativeWh: 12.75,
  occupancyStatus: 'occupied',
  route: 'edge',
  digitalTwin: {
    latitude: -7.723,
    longitude: 110.5187,
    crs: 'EPSG:4326',
    geospatialVerification: 'legacy_coordinate_not_survey_validated',
    scaleSemantics: 'application visualization scales',
    synchronizationMode: 'request_driven_historical_replay'
  }
}

describe('MultiscaleDigitalTwin', () => {
  it('starts at geospatial scale with explicit coordinate status', () => {
    const wrapper = mount(MultiscaleDigitalTwin, {
      props: { sensorData, peopleCount: 2 }
    })

    expect(wrapper.text()).toContain('-7.7230, 110.5187 · EPSG:4326')
    expect(wrapper.text()).toContain('legacy_coordinate_not_survey_validated')
    expect(wrapper.text()).toContain('application visualization scales')
    expect(wrapper.text()).toContain('LoD-A · Tapak geospasial')
    expect(wrapper.text()).toContain('LoD-B · Bangunan')
    expect(wrapper.text()).toContain('LoD-C · Indoor 3D')
  })

  it('links building energy and occupancy and exposes indoor 3D', async () => {
    const wrapper = mount(MultiscaleDigitalTwin, {
      props: { sensorData, peopleCount: 2 }
    })

    await wrapper.get('button:nth-child(2)').trigger('click')
    expect(wrapper.text()).toContain('2 orang · occupied')
    expect(wrapper.text()).toContain('12.750 Wh')

    await wrapper.get('button:nth-child(3)').trigger('click')
    expect(wrapper.get('[data-test="indoor-3d"]').exists()).toBe(true)
  })
})
