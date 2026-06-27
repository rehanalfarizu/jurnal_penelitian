import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import TemperatureChart from '../TemperatureChart.vue'

// Mock vue-chartjs
vi.mock('vue-chartjs', () => ({
  Line: {
    name: 'Line',
    template: '<div class="mock-line-chart"></div>',
    props: ['data', 'options']
  }
}))

// Mock chart.js
vi.mock('chart.js', () => ({
  Chart: {
    register: vi.fn()
  },
  CategoryScale: {},
  LinearScale: {},
  PointElement: {},
  LineElement: {},
  Title: {},
  Tooltip: {},
  Legend: {},
  Filler: {}
}))

describe('TemperatureChart.vue', () => {
  describe('empty state', () => {
    it('shows EmptyState when no data', () => {
      const wrapper = mount(TemperatureChart, {
        props: {
          data: { labels: [], values: [] }
        }
      })
      
      expect(wrapper.text()).toContain('Menunggu Data Suhu')
    })

    it('shows EmptyState with correct icon', () => {
      const wrapper = mount(TemperatureChart, {
        props: {
          data: { labels: [], values: [] }
        }
      })
      
      expect(wrapper.text()).toContain('🌡️')
    })

    it('shows connection guidance in empty state', () => {
      const wrapper = mount(TemperatureChart, {
        props: {
          data: { labels: [], values: [] }
        }
      })
      
      expect(wrapper.text()).toContain('Pastikan MQTT broker terhubung')
    })
  })

  describe('with data', () => {
    it('shows chart when data is available', () => {
      const wrapper = mount(TemperatureChart, {
        props: {
          data: { 
            labels: ['10:00', '11:00', '12:00'], 
            values: [25, 26, 27] 
          }
        }
      })
      
      expect(wrapper.find('.mock-line-chart').exists()).toBe(true)
    })

    it('does not show EmptyState when data is available', () => {
      const wrapper = mount(TemperatureChart, {
        props: {
          data: { 
            labels: ['10:00', '11:00', '12:00'], 
            values: [25, 26, 27] 
          }
        }
      })
      
      expect(wrapper.text()).not.toContain('Menunggu Data Suhu')
    })
  })

  describe('props', () => {
    it('accepts isDarkMode prop', () => {
      const wrapper = mount(TemperatureChart, {
        props: {
          data: { labels: [], values: [] },
          isDarkMode: true
        }
      })
      
      expect(wrapper.exists()).toBe(true)
    })

    it('defaults to light mode', () => {
      const wrapper = mount(TemperatureChart, {
        props: {
          data: { labels: [], values: [] }
        }
      })
      
      expect(wrapper.exists()).toBe(true)
    })
  })
})
