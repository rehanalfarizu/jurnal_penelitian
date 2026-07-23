<template>
  <div class="chart-container">
    <EmptyState 
      v-if="!hasData"
      :is-dark-mode="isDarkMode"
      icon="🌡️"
      icon-type="info"
      title="Menunggu Data Suhu"
      description="Sistem menunggu data dari sensor suhu dan kelembaban"
      :actions="[
        { icon: '🔌', text: 'Pastikan MQTT broker terhubung' },
        { icon: '📡', text: 'Periksa koneksi sensor DHT11' },
        { icon: '⏱️', text: 'Data akan muncul dalam beberapa detik' }
      ]"
      :show-status="true"
      status-text="Menunggu koneksi sensor..."
      status-class="waiting"
    />
    <Line
      v-else
      :data="chartData"
      :options="chartOptions"
    />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Line } from 'vue-chartjs'
import EmptyState from './EmptyState.vue'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
)

const props = defineProps({
  data: {
    type: Object,
    default: () => ({ labels: [], values: [] })
  },
  isDarkMode: {
    type: Boolean,
    default: false
  }
})

const hasData = computed(() => {
  return props.data && props.data.values && props.data.values.length > 0
})

const chartData = computed(() => ({
  labels: props.data.labels || [],
  datasets: [
    {
      label: 'Suhu (°C)',
      data: props.data.values || [],
      borderColor: '#e74c3c',
      backgroundColor: 'rgba(231, 76, 60, 0.15)',
      borderWidth: 3,
      fill: true,
      tension: 0.5,
      pointRadius: 4,
      pointHoverRadius: 7,
      pointBackgroundColor: '#e74c3c',
      pointBorderColor: '#fff',
      pointBorderWidth: 3,
      shadowOffsetX: 0,
      shadowOffsetY: 4,
      shadowBlur: 10,
      shadowColor: 'rgba(231, 76, 60, 0.3)'
    }
  ]
}))

const chartOptions = computed(() => {
  const isDark = props.isDarkMode
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: true,
        position: 'top',
        labels: {
          usePointStyle: true,
          padding: 15,
          font: {
            size: 12,
            weight: '600'
          },
          color: isDark ? '#b8b8c8' : '#7f8c8d'
        }
      },
      tooltip: {
        mode: 'index',
        intersect: false,
        backgroundColor: isDark ? 'rgba(30, 30, 46, 0.95)' : 'rgba(0, 0, 0, 0.8)',
        padding: 12,
        titleFont: {
          size: 13,
          weight: '600'
        },
        bodyFont: {
          size: 12
        },
        borderColor: '#e74c3c',
        borderWidth: 2,
        cornerRadius: 8,
        displayColors: true,
        titleColor: isDark ? '#e8e8e8' : '#ffffff',
        bodyColor: isDark ? '#b8b8c8' : '#ffffff'
      }
    },
    scales: {
      y: {
        beginAtZero: false,
        title: {
          display: true,
          text: 'Suhu (°C)',
          font: {
            size: 12,
            weight: '600'
          },
          color: isDark ? '#b8b8c8' : '#7f8c8d'
        },
        grid: {
          color: isDark ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.06)',
          lineWidth: 1
        },
        ticks: {
          font: {
            size: 11
          },
          color: isDark ? '#b8b8c8' : '#95a5a6'
        }
      },
      x: {
        grid: {
          display: false
        },
        ticks: {
          font: {
            size: 11
          },
          color: isDark ? '#b8b8c8' : '#95a5a6'
        }
      }
    },
    interaction: {
      mode: 'nearest',
      axis: 'x',
      intersect: false
    },
    animation: {
      duration: 1000,
      easing: 'easeInOutQuart'
    }
  }
})
</script>

<style scoped>
.chart-container {
  height: 300px;
  position: relative;
}
</style>





