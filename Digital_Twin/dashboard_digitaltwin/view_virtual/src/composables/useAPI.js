import { ref } from 'vue'
import axios from 'axios'
import { API_BASE_URL, AZURE_FUNCTION_URL } from '../lib/appConfig'

export function useAPI() {
  const temperatureData = ref({
    labels: [],
    values: []
  })
  
  const electricityData = ref({
    labels: [],
    values: []
  })
  
  const peopleData = ref({
    labels: [],
    values: []
  })

  const fetchHistoricalData = async () => {
    // PRIORITAS 1: Selalu coba fetch dari Azure Storage terlebih dahulu
    if (AZURE_FUNCTION_URL) {
      try {
        const azureSuccess = await fetchFromAzure()
        if (azureSuccess) {
          console.log('✅ Data historis berhasil dimuat dari Azure Storage')
          return
        }
      } catch (azureError) {
        console.warn('⚠️ Azure Storage tidak tersedia:', azureError.message)
      }
    }

    // PRIORITAS 2: Fallback ke API lokal (jika ada)
    try {
      // Fetch data suhu 24 jam
      try {
        const tempResponse = await axios.get(`${API_BASE_URL}/data/suhu/24jam`)
        const tempData = Array.isArray(tempResponse.data) 
          ? tempResponse.data 
          : (tempResponse.data?.data || [])
        
        if (Array.isArray(tempData) && tempData.length > 0) {
          temperatureData.value = {
            labels: tempData.map(d => {
              const timestamp = d.timestamp || d.time || d.date
              return timestamp ? new Date(timestamp).toLocaleTimeString('id-ID') : ''
            }).filter(Boolean),
            values: tempData.map(d => d.temperature || d.temp || d.suhu || 0)
          }
        } else {
          throw new Error('No temperature data available')
        }
      } catch (tempError) {
        // Hanya log jika bukan network error (API belum tersedia adalah normal)
        if (!tempError.message.includes('Network Error') && !tempError.message.includes('No temperature')) {
          console.warn('⚠️ Failed to fetch temperature data:', tempError.message)
        }
        // Will use dummy data
      }

      // Fetch data listrik 7 hari
      try {
        const elecResponse = await axios.get(`${API_BASE_URL}/data/listrik/7hari`)
        const elecData = Array.isArray(elecResponse.data) 
          ? elecResponse.data 
          : (elecResponse.data?.data || [])
        
        if (Array.isArray(elecData) && elecData.length > 0) {
          electricityData.value = {
            labels: elecData.map(d => {
              const timestamp = d.timestamp || d.time || d.date
              return timestamp ? new Date(timestamp).toLocaleDateString('id-ID') : ''
            }).filter(Boolean),
            values: elecData.map(d => d.power || d.daya || 0)
          }
        } else {
          throw new Error('No electricity data available')
        }
      } catch (elecError) {
        // Hanya log jika bukan network error (API belum tersedia adalah normal)
        if (!elecError.message.includes('Network Error') && !elecError.message.includes('No electricity')) {
          console.warn('⚠️ Failed to fetch electricity data:', elecError.message)
        }
        // Will use dummy data
      }

      // Fetch data orang real-time
      try {
        const peopleResponse = await axios.get(`${API_BASE_URL}/data/orang/realtime`)
        const peopleDataArray = Array.isArray(peopleResponse.data) 
          ? peopleResponse.data 
          : (peopleResponse.data?.data || [])
        
        if (Array.isArray(peopleDataArray) && peopleDataArray.length > 0) {
          peopleData.value = {
            labels: peopleDataArray.map(d => {
              const timestamp = d.timestamp || d.time || d.date
              return timestamp ? new Date(timestamp).toLocaleTimeString('id-ID') : ''
            }).filter(Boolean),
            values: peopleDataArray.map(d => d.count || d.people || d.orang || 0)
          }
        } else {
          throw new Error('No people data available')
        }
      } catch (peopleError) {
        // Hanya log jika bukan network error (API belum tersedia adalah normal)
        if (!peopleError.message.includes('Network Error') && !peopleError.message.includes('No people')) {
          console.warn('⚠️ Failed to fetch people data:', peopleError.message)
        }
        // Will use dummy data
      }
      
      // Jika semua fetch gagal, gunakan dummy data (normal jika API belum tersedia)
      if (temperatureData.value.labels.length === 0 && 
          electricityData.value.labels.length === 0 && 
          peopleData.value.labels.length === 0) {
        console.log('📊 Using demo data for charts (API backend not available)')
        generateDummyData()
      } else {
        console.log('✅ Historical data loaded successfully')
      }
    } catch (error) {
      console.error('❌ Error fetching historical data:', error)
      // Generate dummy data untuk demo jika API belum tersedia
      generateDummyData()
    }
  }

  const generateDummyData = () => {
    // Dummy data suhu (24 jam terakhir, setiap jam)
    const now = new Date()
    temperatureData.value = {
      labels: Array.from({ length: 24 }, (_, i) => {
        const date = new Date(now)
        date.setHours(date.getHours() - (23 - i))
        return date.toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' })
      }),
      values: Array.from({ length: 24 }, () => 20 + Math.random() * 10)
    }

    // Dummy data listrik (7 hari terakhir)
    electricityData.value = {
      labels: Array.from({ length: 7 }, (_, i) => {
        const date = new Date(now)
        date.setDate(date.getDate() - (6 - i))
        return date.toLocaleDateString('id-ID', { day: '2-digit', month: 'short' })
      }),
      values: Array.from({ length: 7 }, () => 1000 + Math.random() * 500)
    }

    // Dummy data orang (10 data terakhir)
    peopleData.value = {
      labels: Array.from({ length: 10 }, (_, i) => {
        const date = new Date(now)
        date.setMinutes(date.getMinutes() - (9 - i) * 5)
        return date.toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' })
      }),
      values: Array.from({ length: 10 }, () => Math.floor(Math.random() * 20))
    }
  }

  const fetchFromAzure = async () => {
    console.log('🔵 Mengambil data dari Azure Storage (stordigitaltwin2026)...')
    
    try {
      // Ambil data dari Azure Storage Table melalui Azure Function
      const response = await axios.get(`${AZURE_FUNCTION_URL}/telemetry/history?hours=168&limit=500`, {
        timeout: 10000 // 10 detik timeout
      })
      
      console.log('📊 Response dari Azure:', response.data)
      
      if (response.data.success) {
        const data = response.data.data || []
        
        if (data.length > 0) {
          console.log(`✅ Ditemukan ${data.length} data dari Azure Storage Table`)
          
          // Process temperature data (24 jam terakhir)
          temperatureData.value = {
            labels: data.slice(-24).map(d => new Date(d.timestamp).toLocaleTimeString('id-ID', { 
              hour: '2-digit', 
              minute: '2-digit' 
            })),
            values: data.slice(-24).map(d => parseFloat(d.suhu) || 0)
          }
          
          // Process electricity data (aggregate by day)
          const dayData = {}
          data.forEach(d => {
            const day = new Date(d.timestamp).toLocaleDateString('id-ID', { day: '2-digit', month: 'short' })
            if (!dayData[day]) {
              dayData[day] = { total: 0, count: 0 }
            }
            dayData[day].total += (parseFloat(d.daya) || 0)
            dayData[day].count++
          })
          
          electricityData.value = {
            labels: Object.keys(dayData),
            values: Object.values(dayData).map(v => v.total / v.count)
          }
          
          // Process people count data (jika ada)
          try {
            const peopleResponse = await axios.get(`${AZURE_FUNCTION_URL}/telemetry/people?hours=24`, {
              timeout: 5000
            })
            if (peopleResponse.data.success && peopleResponse.data.data?.length > 0) {
              const pData = peopleResponse.data.data
              peopleData.value = {
                labels: pData.map(d => new Date(d.timestamp).toLocaleTimeString('id-ID', { 
                  hour: '2-digit', 
                  minute: '2-digit' 
                })),
                values: pData.map(d => parseInt(d.count) || 0)
              }
              console.log(`   - People Count: ${peopleData.value.values.length} points`)
            }
          } catch (peopleError) {
            console.log('   - People Count: Data tidak tersedia')
          }
          
          console.log(`   ✓ Suhu: ${temperatureData.value.values.length} data point`)
          console.log(`   ✓ Listrik: ${electricityData.value.values.length} hari`)
          console.log('   📍 Sumber: Azure Storage Table (stordigitaltwin2026)')
          
          return true
        } else {
          console.log('⚠️ Azure Storage Table kosong atau belum ada data')
          console.log('   Pastikan ESP32 sudah mengirim data ke Azure Storage')
          return false
        }
      } else {
        console.warn('⚠️ Response dari Azure tidak valid')
        return false
      }
    } catch (error) {
      if (error.code === 'ECONNABORTED') {
        console.error('❌ Timeout connecting to Azure Storage')
      } else if (error.response) {
        console.error('❌ Azure Function error:', error.response.status, error.response.data)
      } else {
        console.error('❌ Network error:', error.message)
      }
      return false
    }
  }

  return {
    temperatureData,
    electricityData,
    peopleData,
    fetchHistoricalData,
    fetchFromAzure
  }
}





