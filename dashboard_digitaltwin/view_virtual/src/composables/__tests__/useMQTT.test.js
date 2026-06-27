import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { useMQTT } from '../useMQTT'

// Mock axios
vi.mock('axios', () => ({
  default: {
    get: vi.fn()
  }
}))

// Mock localStorage
const localStorageMock = {
  store: {},
  getItem: vi.fn((key) => localStorageMock.store[key] || null),
  setItem: vi.fn((key, value) => { localStorageMock.store[key] = value }),
  removeItem: vi.fn((key) => { delete localStorageMock.store[key] }),
  clear: vi.fn(() => { localStorageMock.store = {} })
}
Object.defineProperty(global, 'localStorage', { value: localStorageMock })

// Mock import.meta.env
vi.stubGlobal('import.meta', {
  env: {
    VITE_AZURE_FUNCTION_URL: 'https://test-azure-function.azurewebsites.net/api'
  }
})

describe('useMQTT (Azure IoT Hub)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers()
    localStorageMock.clear()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  describe('initialization', () => {
    it('should initialize with disconnected state', () => {
      const mqtt = useMQTT()
      expect(mqtt.mqttConnected.value).toBe(false)
    })

    it('should have default sensor data structure', () => {
      const mqtt = useMQTT()
      expect(mqtt.sensorData.value).toBeDefined()
      expect(mqtt.sensorData.value.temperature).toBe(0)
      expect(mqtt.sensorData.value.humidity).toBe(0)
      expect(mqtt.sensorData.value.power).toBe(0)
    })

    it('should initialize sensorData with all required fields', () => {
      const mqtt = useMQTT()
      
      expect(mqtt.sensorData.value).toHaveProperty('temperature')
      expect(mqtt.sensorData.value).toHaveProperty('humidity')
      expect(mqtt.sensorData.value).toHaveProperty('voltage')
      expect(mqtt.sensorData.value).toHaveProperty('current')
      expect(mqtt.sensorData.value).toHaveProperty('power')
      expect(mqtt.sensorData.value).toHaveProperty('voltageStatus')
      expect(mqtt.sensorData.value).toHaveProperty('currentStatus')
      expect(mqtt.sensorData.value).toHaveProperty('peopleCount')
      expect(mqtt.sensorData.value).toHaveProperty('lastPeopleUpdate')
    })

    it('should initialize with correct default values', () => {
      const mqtt = useMQTT()
      
      expect(mqtt.sensorData.value.temperature).toBe(0)
      expect(mqtt.sensorData.value.humidity).toBe(0)
      expect(mqtt.sensorData.value.voltage).toBe(0)
      expect(mqtt.sensorData.value.current).toBe(0)
      expect(mqtt.sensorData.value.power).toBe(0)
      expect(mqtt.sensorData.value.voltageStatus).toBe('unknown')
      expect(mqtt.sensorData.value.currentStatus).toBe('unknown')
      expect(mqtt.sensorData.value.peopleCount).toBe(0)
      expect(mqtt.sensorData.value.lastPeopleUpdate).toBeNull()
    })
  })

  describe('exported functions', () => {
    it('should have connectMQTT function', () => {
      const mqtt = useMQTT()
      expect(typeof mqtt.connectMQTT).toBe('function')
    })

    it('should have disconnectMQTT function', () => {
      const mqtt = useMQTT()
      expect(typeof mqtt.disconnectMQTT).toBe('function')
    })

    it('should have fetchLatestFromAzure function', () => {
      const mqtt = useMQTT()
      expect(typeof mqtt.fetchLatestFromAzure).toBe('function')
    })
  })

  describe('connectMQTT (Azure Polling)', () => {
    it('should start polling when connectMQTT is called', async () => {
      const axios = await import('axios')
      axios.default.get.mockResolvedValue({
        data: { success: true, data: { suhu: 25, kelembaban: 60 } }
      })
      
      const mqtt = useMQTT()
      mqtt.connectMQTT()
      
      // Should call fetch immediately
      expect(axios.default.get).toHaveBeenCalled()
    })

    it('should poll Azure every 5 seconds', async () => {
      const axios = await import('axios')
      axios.default.get.mockResolvedValue({
        data: { success: true, data: { suhu: 25 } }
      })
      
      const mqtt = useMQTT()
      mqtt.connectMQTT()
      
      // Initial call
      expect(axios.default.get).toHaveBeenCalledTimes(1)
      
      // After 5 seconds
      vi.advanceTimersByTime(5000)
      expect(axios.default.get).toHaveBeenCalledTimes(2)
      
      // After 10 seconds
      vi.advanceTimersByTime(5000)
      expect(axios.default.get).toHaveBeenCalledTimes(3)
      
      mqtt.disconnectMQTT()
    })
  })

  describe('disconnectMQTT', () => {
    it('should stop polling when disconnectMQTT is called', async () => {
      const axios = await import('axios')
      axios.default.get.mockResolvedValue({
        data: { success: true, data: { suhu: 25 } }
      })
      
      const mqtt = useMQTT()
      mqtt.connectMQTT()
      mqtt.disconnectMQTT()
      
      const callCount = axios.default.get.mock.calls.length
      
      // After 10 seconds, should not call again
      vi.advanceTimersByTime(10000)
      expect(axios.default.get).toHaveBeenCalledTimes(callCount)
    })

    it('should set mqttConnected to false on disconnect', () => {
      const mqtt = useMQTT()
      mqtt.connectMQTT()
      mqtt.disconnectMQTT()
      
      expect(mqtt.mqttConnected.value).toBe(false)
    })

    it('should not reset sensor data on disconnect', async () => {
      const axios = await import('axios')
      axios.default.get.mockResolvedValue({
        data: { success: true, data: { suhu: 30, kelembaban: 70 } }
      })
      
      const mqtt = useMQTT()
      mqtt.connectMQTT()
      
      // Wait for initial fetch
      await vi.advanceTimersByTimeAsync(100)
      
      mqtt.disconnectMQTT()
      
      // Data should persist
      expect(mqtt.sensorData.value.temperature).toBe(30)
      expect(mqtt.sensorData.value.humidity).toBe(70)
    })
  })

  describe('fetchLatestFromAzure', () => {
    it('should update sensorData on successful fetch', async () => {
      const axios = await import('axios')
      axios.default.get.mockResolvedValue({
        data: {
          success: true,
          data: {
            suhu: 28.5,
            kelembaban: 65,
            tegangan: 220,
            arus: 1.5,
            daya: 330,
            status_tegangan: 'normal',
            status_arus: 'normal'
          }
        }
      })
      
      const mqtt = useMQTT()
      const result = await mqtt.fetchLatestFromAzure()
      
      expect(result).toBe(true)
      expect(mqtt.sensorData.value.temperature).toBe(28.5)
      expect(mqtt.sensorData.value.humidity).toBe(65)
      expect(mqtt.sensorData.value.voltage).toBe(220)
      expect(mqtt.sensorData.value.current).toBe(1.5)
      expect(mqtt.sensorData.value.power).toBe(330)
      expect(mqtt.mqttConnected.value).toBe(true)
    })

    it('should handle network errors gracefully', async () => {
      const axios = await import('axios')
      axios.default.get.mockRejectedValue(new Error('Network error'))
      
      const mqtt = useMQTT()
      const result = await mqtt.fetchLatestFromAzure()
      
      expect(result).toBe(false)
      expect(mqtt.mqttConnected.value).toBe(false)
    })

    it('should compute power from voltage and current if not provided', async () => {
      const axios = await import('axios')
      axios.default.get.mockResolvedValue({
        data: {
          success: true,
          data: {
            tegangan: 220,
            arus: 2
          }
        }
      })
      
      const mqtt = useMQTT()
      await mqtt.fetchLatestFromAzure()
      
      // Power = 220 * 2 = 440
      expect(mqtt.sensorData.value.power).toBeCloseTo(440, 0)
    })

    it('should handle people counter data', async () => {
      const axios = await import('axios')
      axios.default.get.mockResolvedValue({
        data: {
          success: true,
          data: {
            jumlahOrang: 5,
            timestamp: '2025-12-31T10:00:00Z'
          }
        }
      })
      
      const mqtt = useMQTT()
      await mqtt.fetchLatestFromAzure()
      
      expect(mqtt.sensorData.value.peopleCount).toBe(5)
      expect(mqtt.sensorData.value.lastPeopleUpdate).toBeDefined()
    })

    it('should fallback to localStorage when Azure fails', async () => {
      const axios = await import('axios')
      axios.default.get.mockRejectedValue(new Error('Network error'))
      
      // Set cached data
      localStorageMock.store['sensor_last_data'] = JSON.stringify({
        temperature: 25,
        humidity: 50
      })
      
      const mqtt = useMQTT()
      await mqtt.fetchLatestFromAzure()
      
      expect(mqtt.sensorData.value.temperature).toBe(25)
      expect(mqtt.sensorData.value.humidity).toBe(50)
    })
  })

  describe('reactive refs', () => {
    it('should export mqttConnected as reactive ref', () => {
      const mqtt = useMQTT()
      
      expect(mqtt.mqttConnected).toBeDefined()
      expect(mqtt.mqttConnected.value).toBeDefined()
    })

    it('should export sensorData as reactive ref', () => {
      const mqtt = useMQTT()
      
      expect(mqtt.sensorData).toBeDefined()
      expect(mqtt.sensorData.value).toBeDefined()
    })

    it('should allow updating sensorData', () => {
      const mqtt = useMQTT()
      
      mqtt.sensorData.value.temperature = 25.5
      mqtt.sensorData.value.humidity = 60
      
      expect(mqtt.sensorData.value.temperature).toBe(25.5)
      expect(mqtt.sensorData.value.humidity).toBe(60)
    })
  })

  describe('localStorage integration', () => {
    it('should save data to localStorage on sensorData change', async () => {
      const axios = await import('axios')
      axios.default.get.mockResolvedValue({
        data: {
          success: true,
          data: { suhu: 30 }
        }
      })
      
      const mqtt = useMQTT()
      await mqtt.fetchLatestFromAzure()
      
      // Wait for watch to trigger
      await vi.runAllTimersAsync()
      
      expect(localStorageMock.setItem).toHaveBeenCalled()
    })

    it('should load cached data when Azure URL not configured', async () => {
      const axios = await import('axios')
      axios.default.get.mockRejectedValue(new Error('Network error'))
      
      localStorageMock.store['sensor_last_data'] = JSON.stringify({
        temperature: 22,
        humidity: 55
      })
      
      const mqtt = useMQTT()
      await mqtt.fetchLatestFromAzure()
      
      expect(mqtt.sensorData.value.temperature).toBe(22)
      expect(mqtt.sensorData.value.humidity).toBe(55)
    })
  })

  describe('data persistence', () => {
    it('should not reset sensorData on connection error', async () => {
      const axios = await import('axios')
      
      // First successful fetch
      axios.default.get.mockResolvedValueOnce({
        data: { success: true, data: { suhu: 28 } }
      })
      
      const mqtt = useMQTT()
      await mqtt.fetchLatestFromAzure()
      
      expect(mqtt.sensorData.value.temperature).toBe(28)
      
      // Second fetch fails
      axios.default.get.mockRejectedValueOnce(new Error('Network error'))
      await mqtt.fetchLatestFromAzure()
      
      // Data should persist from localStorage fallback
      expect(mqtt.sensorData.value.temperature).toBe(28)
    })
  })
})
