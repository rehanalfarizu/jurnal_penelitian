<template>
  <div class="chart-container">
    <EmptyState 
      v-if="!hasData"
      :is-dark-mode="isDarkMode"
      icon="⚡"
      icon-type="warning"
      title="Menunggu Data Listrik"
      description="Sistem menunggu data dari sensor arus dan tegangan"
      :actions="[
        { icon: '🔌', text: 'Pastikan MQTT broker terhubung' },
        { icon: '📊', text: 'Periksa koneksi sensor listrik' },
        { icon: '💡', text: 'Hidupkan beban untuk melihat data' }
      ]"
      :show-status="true"
      status-text="Menunggu pembacaan sensor..."
      status-class="waiting"
    />
    <Bar
      v-else
      :data="chartData"
      :options="chartOptions"
    />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Bar } from 'vue-chartjs'
import EmptyState from './EmptyState.vue'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js'

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
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
      label: 'Konsumsi Listrik (W)',
      data: props.data.values || [],
      backgroundColor: 'rgba(52, 152, 219, 0.7)',
      borderColor: '#3498db',
      borderWidth: 2,
      borderRadius: 8,
      borderSkipped: false,
      shadowOffsetX: 0,
      shadowOffsetY: 4,
      shadowBlur: 8,
      shadowColor: 'rgba(52, 152, 219, 0.3)'
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
        borderColor: '#3498db',
        borderWidth: 2,
        cornerRadius: 8,
        displayColors: true,
        titleColor: isDark ? '#e8e8e8' : '#ffffff',
        bodyColor: isDark ? '#b8b8c8' : '#ffffff'
      }
    },
    scales: {
      y: {
        beginAtZero: true,
        title: {
          display: true,
          text: 'Daya (Watt)',
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





