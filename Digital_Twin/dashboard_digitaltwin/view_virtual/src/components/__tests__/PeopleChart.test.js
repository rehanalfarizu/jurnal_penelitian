import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import PeopleChart from '../PeopleChart.vue'

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

describe('PeopleChart.vue', () => {
  describe('empty state', () => {
    it('shows EmptyState when no data', () => {
      const wrapper = mount(PeopleChart, {
        props: {
          data: { labels: [], values: [] }
        }
      })
      
      expect(wrapper.text()).toContain('Menunggu Data People Counter')
    })

    it('shows EmptyState with correct icon', () => {
      const wrapper = mount(PeopleChart, {
        props: {
          data: { labels: [], values: [] }
        }
      })
      
      expect(wrapper.text()).toContain('👥')
    })
  })

  describe('with data', () => {
    it('shows chart when data is available', () => {
      const wrapper = mount(PeopleChart, {
        props: {
          data: { 
            labels: ['10:00', '10:05', '10:10'], 
            values: [5, 8, 12] 
          }
        }
      })
      
      expect(wrapper.find('.mock-line-chart').exists()).toBe(true)
    })

    it('does not show EmptyState when data is available', () => {
      const wrapper = mount(PeopleChart, {
        props: {
          data: { 
            labels: ['10:00', '10:05', '10:10'], 
            values: [5, 8, 12] 
          }
        }
      })
      
      expect(wrapper.text()).not.toContain('Menunggu Data Orang')
    })
  })

  describe('props', () => {
    it('accepts isDarkMode prop', () => {
      const wrapper = mount(PeopleChart, {
        props: {
          data: { labels: [], values: [] },
          isDarkMode: true
        }
      })
      
      expect(wrapper.exists()).toBe(true)
    })
  })
})
