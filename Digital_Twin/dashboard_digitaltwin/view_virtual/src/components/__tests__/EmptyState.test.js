import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import EmptyState from '../EmptyState.vue'

describe('EmptyState.vue', () => {
  it('renders with default props', () => {
    const wrapper = mount(EmptyState)
    
    expect(wrapper.exists()).toBe(true)
  })

  it('renders default icon', () => {
    const wrapper = mount(EmptyState)
    
    // Default icon is 📊
    expect(wrapper.text()).toContain('📊')
  })

  it('renders custom icon when provided', () => {
    const wrapper = mount(EmptyState, {
      props: {
        icon: '🌡️'
      }
    })
    
    expect(wrapper.text()).toContain('🌡️')
  })

  it('renders default title', () => {
    const wrapper = mount(EmptyState)
    
    // Default title is 'Tidak Ada Data'
    expect(wrapper.text()).toContain('Tidak Ada Data')
  })

  it('renders custom title when provided', () => {
    const wrapper = mount(EmptyState, {
      props: {
        title: 'Temperature Data'
      }
    })
    
    expect(wrapper.text()).toContain('Temperature Data')
  })

  it('renders default description', () => {
    const wrapper = mount(EmptyState)
    
    // Default description is 'Data belum tersedia saat ini'
    expect(wrapper.text()).toContain('Data belum tersedia saat ini')
  })

  it('renders custom description when provided', () => {
    const wrapper = mount(EmptyState, {
      props: {
        description: 'Waiting for sensor readings'
      }
    })
    
    expect(wrapper.text()).toContain('Waiting for sensor readings')
  })

  it('renders all custom props together', () => {
    const wrapper = mount(EmptyState, {
      props: {
        icon: '🌡️',
        title: 'Temperature Data',
        description: 'Waiting for sensor readings'
      }
    })
    
    expect(wrapper.text()).toContain('🌡️')
    expect(wrapper.text()).toContain('Temperature Data')
    expect(wrapper.text()).toContain('Waiting for sensor readings')
  })
})
