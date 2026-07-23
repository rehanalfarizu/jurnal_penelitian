import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useAPI } from '../useAPI'

// Mock axios
vi.mock('axios', () => ({
  default: {
    get: vi.fn()
  }
}))

describe('useAPI', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('initialization', () => {
    it('should initialize with empty temperature data', () => {
      const api = useAPI()
      
      expect(api.temperatureData.value.labels).toEqual([])
      expect(api.temperatureData.value.values).toEqual([])
    })

    it('should initialize with empty electricity data', () => {
      const api = useAPI()
      
      expect(api.electricityData.value.labels).toEqual([])
      expect(api.electricityData.value.values).toEqual([])
    })

    it('should initialize with empty people data', () => {
      const api = useAPI()
      
      expect(api.peopleData.value.labels).toEqual([])
      expect(api.peopleData.value.values).toEqual([])
    })
  })

  describe('exported functions', () => {
    it('should have fetchHistoricalData function', () => {
      const api = useAPI()
      expect(typeof api.fetchHistoricalData).toBe('function')
    })

    it('should have fetchFromAzure function', () => {
      const api = useAPI()
      expect(typeof api.fetchFromAzure).toBe('function')
    })
  })

  describe('exported refs', () => {
    it('should export temperatureData ref', () => {
      const api = useAPI()
      
      expect(api.temperatureData).toBeDefined()
      expect(api.temperatureData.value).toBeDefined()
    })

    it('should export electricityData ref', () => {
      const api = useAPI()
      
      expect(api.electricityData).toBeDefined()
      expect(api.electricityData.value).toBeDefined()
    })

    it('should export peopleData ref', () => {
      const api = useAPI()
      
      expect(api.peopleData).toBeDefined()
      expect(api.peopleData.value).toBeDefined()
    })
  })

  describe('dummy data generation', () => {
    it('should generate dummy data when API is not available', async () => {
      const api = useAPI()
      
      // Trigger fetch which will fail and generate dummy data
      await api.fetchHistoricalData()
      
      // Should have 24 hours of temperature data
      expect(api.temperatureData.value.labels.length).toBe(24)
      expect(api.temperatureData.value.values.length).toBe(24)
      
      // Should have 7 days of electricity data
      expect(api.electricityData.value.labels.length).toBe(7)
      expect(api.electricityData.value.values.length).toBe(7)
    })

    it('should have valid temperature values in range (20-30)', async () => {
      const api = useAPI()
      
      await api.fetchHistoricalData()
      
      // Temperature should be between 20-30°C for dummy data
      api.temperatureData.value.values.forEach(temp => {
        expect(temp).toBeGreaterThanOrEqual(20)
        expect(temp).toBeLessThanOrEqual(30)
      })
    })

    it('should have valid electricity values in range (1000-1500)', async () => {
      const api = useAPI()
      
      await api.fetchHistoricalData()
      
      // Electricity should be between 1000-1500 for dummy data
      api.electricityData.value.values.forEach(elec => {
        expect(elec).toBeGreaterThanOrEqual(1000)
        expect(elec).toBeLessThanOrEqual(1500)
      })
    })

    it('should generate people data with 10 entries', async () => {
      const api = useAPI()
      
      await api.fetchHistoricalData()
      
      expect(api.peopleData.value.labels.length).toBe(10)
      expect(api.peopleData.value.values.length).toBe(10)
    })

    it('should have valid people count values (0-20)', async () => {
      const api = useAPI()
      
      await api.fetchHistoricalData()
      
      api.peopleData.value.values.forEach(count => {
        expect(count).toBeGreaterThanOrEqual(0)
        expect(count).toBeLessThan(20)
      })
    })
  })

  describe('data structure', () => {
    it('should have labels and values arrays in temperatureData', () => {
      const api = useAPI()
      
      expect(Array.isArray(api.temperatureData.value.labels)).toBe(true)
      expect(Array.isArray(api.temperatureData.value.values)).toBe(true)
    })

    it('should have labels and values arrays in electricityData', () => {
      const api = useAPI()
      
      expect(Array.isArray(api.electricityData.value.labels)).toBe(true)
      expect(Array.isArray(api.electricityData.value.values)).toBe(true)
    })

    it('should have labels and values arrays in peopleData', () => {
      const api = useAPI()
      
      expect(Array.isArray(api.peopleData.value.labels)).toBe(true)
      expect(Array.isArray(api.peopleData.value.values)).toBe(true)
    })
  })

  describe('reactive updates', () => {
    it('should allow manual updates to temperatureData', () => {
      const api = useAPI()
      
      api.temperatureData.value = {
        labels: ['10:00', '11:00', '12:00'],
        values: [25, 26, 27]
      }
      
      expect(api.temperatureData.value.labels).toEqual(['10:00', '11:00', '12:00'])
      expect(api.temperatureData.value.values).toEqual([25, 26, 27])
    })

    it('should allow manual updates to electricityData', () => {
      const api = useAPI()
      
      api.electricityData.value = {
        labels: ['Mon', 'Tue', 'Wed'],
        values: [1000, 1100, 1200]
      }
      
      expect(api.electricityData.value.labels).toEqual(['Mon', 'Tue', 'Wed'])
      expect(api.electricityData.value.values).toEqual([1000, 1100, 1200])
    })
  })

  describe('fetchFromAzure', () => {
    it('should return a boolean value', async () => {
      const api = useAPI()
      const result = await api.fetchFromAzure()
      expect(typeof result).toBe('boolean')
    })

    it('should handle network errors gracefully', async () => {
      const api = useAPI()
      
      // Should not throw on network error
      await expect(api.fetchFromAzure()).resolves.toBe(false)
    })

    it('should log fetch attempt', async () => {
      const consoleSpy = vi.spyOn(console, 'log')
      const api = useAPI()
      
      await api.fetchFromAzure()
      
      expect(consoleSpy).toHaveBeenCalledWith(expect.stringContaining('Azure'))
    })
  })

  describe('fetchHistoricalData', () => {
    it('should populate all data arrays on fetch', async () => {
      const api = useAPI()
      
      await api.fetchHistoricalData()
      
      // All data should be populated (from dummy data fallback)
      expect(api.temperatureData.value.labels.length).toBeGreaterThan(0)
      expect(api.electricityData.value.labels.length).toBeGreaterThan(0)
      expect(api.peopleData.value.labels.length).toBeGreaterThan(0)
    })

    it('should handle errors and fallback to dummy data', async () => {
      const api = useAPI()
      
      // This should not throw
      await expect(api.fetchHistoricalData()).resolves.not.toThrow()
      
      // Should have dummy data
      expect(api.temperatureData.value.labels.length).toBe(24)
    })

    it('should generate time labels for temperature data', async () => {
      const api = useAPI()
      
      await api.fetchHistoricalData()
      
      // Labels should be in time format (HH:mm)
      api.temperatureData.value.labels.forEach(label => {
        expect(label).toMatch(/^\d{2}[:.]\d{2}$/)
      })
    })

    it('should generate date labels for electricity data', async () => {
      const api = useAPI()
      
      await api.fetchHistoricalData()
      
      // Labels should contain date info
      api.electricityData.value.labels.forEach(label => {
        expect(typeof label).toBe('string')
        expect(label.length).toBeGreaterThan(0)
      })
    })
  })

  describe('data validation', () => {
    it('should have numeric temperature values', async () => {
      const api = useAPI()
      
      await api.fetchHistoricalData()
      
      api.temperatureData.value.values.forEach(val => {
        expect(typeof val).toBe('number')
        expect(isNaN(val)).toBe(false)
      })
    })

    it('should have numeric electricity values', async () => {
      const api = useAPI()
      
      await api.fetchHistoricalData()
      
      api.electricityData.value.values.forEach(val => {
        expect(typeof val).toBe('number')
        expect(isNaN(val)).toBe(false)
      })
    })

    it('should have integer people count values', async () => {
      const api = useAPI()
      
      await api.fetchHistoricalData()
      
      api.peopleData.value.values.forEach(val => {
        expect(typeof val).toBe('number')
        expect(Number.isInteger(val)).toBe(true)
      })
    })

    it('should have string labels in all data', async () => {
      const api = useAPI()
      
      await api.fetchHistoricalData()
      
      api.temperatureData.value.labels.forEach(label => {
        expect(typeof label).toBe('string')
      })
      
      api.electricityData.value.labels.forEach(label => {
        expect(typeof label).toBe('string')
      })
      
      api.peopleData.value.labels.forEach(label => {
        expect(typeof label).toBe('string')
      })
    })
  })

  describe('edge cases', () => {
    it('should handle empty data gracefully', () => {
      const api = useAPI()
      
      api.temperatureData.value = { labels: [], values: [] }
      
      expect(api.temperatureData.value.labels.length).toBe(0)
      expect(api.temperatureData.value.values.length).toBe(0)
    })

    it('should maintain data consistency after multiple fetches', async () => {
      const api = useAPI()
      
      await api.fetchHistoricalData()
      const firstLength = api.temperatureData.value.labels.length
      
      await api.fetchHistoricalData()
      const secondLength = api.temperatureData.value.labels.length
      
      expect(firstLength).toBe(secondLength)
    })

    it('should not share state between multiple useAPI calls', () => {
      const api1 = useAPI()
      const api2 = useAPI()
      
      api1.temperatureData.value = { labels: ['test'], values: [100] }
      
      // api2 should have its own state
      expect(api2.temperatureData.value.labels).not.toEqual(['test'])
    })
  })
})
