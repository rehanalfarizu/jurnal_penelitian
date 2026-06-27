import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import SensorStatus from '../SensorStatus.vue'

describe('SensorStatus.vue', () => {
  const defaultSensorData = {
    temperature: 0,
    humidity: 0,
    voltage: 0,
    current: 0,
    power: 0,
    voltageStatus: 'unknown',
    currentStatus: 'unknown'
  }

  describe('rendering', () => {
    it('renders with default sensor data', () => {
      const wrapper = mount(SensorStatus, {
        props: { sensorData: defaultSensorData }
      })
      
      expect(wrapper.exists()).toBe(true)
    })

    it('renders all sensor cards', () => {
      const wrapper = mount(SensorStatus, {
        props: { sensorData: defaultSensorData }
      })
      
      expect(wrapper.findAll('.sensor-card').length).toBe(5)
    })

    it('renders temperature card with icon', () => {
      const wrapper = mount(SensorStatus, {
        props: { sensorData: defaultSensorData }
      })
      
      expect(wrapper.text()).toContain('🌡️')
      expect(wrapper.text()).toContain('Suhu')
    })

    it('renders humidity card with icon', () => {
      const wrapper = mount(SensorStatus, {
        props: { sensorData: defaultSensorData }
      })
      
      expect(wrapper.text()).toContain('💧')
      expect(wrapper.text()).toContain('Kelembaban')
    })

    it('renders voltage card with icon', () => {
      const wrapper = mount(SensorStatus, {
        props: { sensorData: defaultSensorData }
      })
      
      expect(wrapper.text()).toContain('🔌')
      expect(wrapper.text()).toContain('Tegangan')
    })

    it('renders current card with icon', () => {
      const wrapper = mount(SensorStatus, {
        props: { sensorData: defaultSensorData }
      })
      
      expect(wrapper.text()).toContain('⚡')
      expect(wrapper.text()).toContain('Arus')
    })

    it('renders power card with icon', () => {
      const wrapper = mount(SensorStatus, {
        props: { sensorData: defaultSensorData }
      })
      
      expect(wrapper.text()).toContain('💡')
      expect(wrapper.text()).toContain('Daya')
    })
  })

  describe('value display', () => {
    it('displays temperature value correctly', () => {
      const wrapper = mount(SensorStatus, {
        props: { 
          sensorData: { ...defaultSensorData, temperature: 25.5 }
        }
      })
      
      expect(wrapper.text()).toContain('25.5°C')
    })

    it('displays humidity value correctly', () => {
      const wrapper = mount(SensorStatus, {
        props: { 
          sensorData: { ...defaultSensorData, humidity: 60.2 }
        }
      })
      
      expect(wrapper.text()).toContain('60.2%')
    })

    it('displays voltage value correctly', () => {
      const wrapper = mount(SensorStatus, {
        props: { 
          sensorData: { ...defaultSensorData, voltage: 220.5 }
        }
      })
      
      expect(wrapper.text()).toContain('220.5V')
    })

    it('displays current value correctly', () => {
      const wrapper = mount(SensorStatus, {
        props: { 
          sensorData: { ...defaultSensorData, current: 2.3 }
        }
      })
      
      expect(wrapper.text()).toContain('2.3A')
    })

    it('displays power value correctly', () => {
      const wrapper = mount(SensorStatus, {
        props: { 
          sensorData: { ...defaultSensorData, power: 450.8 }
        }
      })
      
      expect(wrapper.text()).toContain('450.8W')
    })
  })

  describe('sensor descriptions', () => {
    it('displays DHT22 Sensor for temperature and humidity', () => {
      const wrapper = mount(SensorStatus, {
        props: { sensorData: defaultSensorData }
      })
      
      expect(wrapper.text()).toContain('DHT22 Sensor')
    })

    it('displays ZMPT101B Sensor for voltage', () => {
      const wrapper = mount(SensorStatus, {
        props: { sensorData: defaultSensorData }
      })
      
      expect(wrapper.text()).toContain('ZMPT101B Sensor')
    })

    it('displays SCT-013 Sensor for current', () => {
      const wrapper = mount(SensorStatus, {
        props: { sensorData: defaultSensorData }
      })
      
      expect(wrapper.text()).toContain('SCT-013 Sensor')
    })
  })

  describe('zero values', () => {
    it('displays 0.0 for zero temperature', () => {
      const wrapper = mount(SensorStatus, {
        props: { sensorData: defaultSensorData }
      })
      
      expect(wrapper.text()).toContain('0.0°C')
    })

    it('handles undefined values gracefully', () => {
      const wrapper = mount(SensorStatus, {
        props: { sensorData: {} }
      })
      
      expect(wrapper.exists()).toBe(true)
      expect(wrapper.text()).toContain('0.0')
    })
  })
})
