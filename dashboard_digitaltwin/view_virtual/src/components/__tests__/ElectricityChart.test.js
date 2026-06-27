import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import ElectricityChart from '../ElectricityChart.vue'

// Mock vue-chartjs
vi.mock('vue-chartjs', () => ({
  Bar: {
    name: 'Bar',
    template: '<div class="mock-bar-chart"></div>',
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
  BarElement: {},
  Title: {},
  Tooltip: {},
  Legend: {}
}))

describe('ElectricityChart.vue', () => {
  describe('empty state', () => {
    it('shows EmptyState when no data', () => {
      const wrapper = mount(ElectricityChart, {
        props: {
          data: { labels: [], values: [] }
        }
      })
      
      expect(wrapper.text()).toContain('Menunggu Data Listrik')
    })

    it('shows EmptyState with correct icon', () => {
      const wrapper = mount(ElectricityChart, {
        props: {
          data: { labels: [], values: [] }
        }
      })
      
      expect(wrapper.text()).toContain('⚡')
    })
  })

  describe('with data', () => {
    it('shows chart when data is available', () => {
      const wrapper = mount(ElectricityChart, {
        props: {
          data: { 
            labels: ['Mon', 'Tue', 'Wed'], 
            values: [1000, 1100, 1200] 
          }
        }
      })
      
      expect(wrapper.find('.mock-bar-chart').exists()).toBe(true)
    })

    it('does not show EmptyState when data is available', () => {
      const wrapper = mount(ElectricityChart, {
        props: {
          data: { 
            labels: ['Mon', 'Tue', 'Wed'], 
            values: [1000, 1100, 1200] 
          }
        }
      })
      
      expect(wrapper.text()).not.toContain('Menunggu Data Listrik')
    })
  })

  describe('props', () => {
    it('accepts isDarkMode prop', () => {
      const wrapper = mount(ElectricityChart, {
        props: {
          data: { labels: [], values: [] },
          isDarkMode: true
        }
      })
      
      expect(wrapper.exists()).toBe(true)
    })
  })
})
