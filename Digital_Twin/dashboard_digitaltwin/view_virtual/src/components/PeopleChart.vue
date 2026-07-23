<template>
  <div class="chart-container">
    <EmptyState 
      v-if="!hasData"
      :is-dark-mode="isDarkMode"
      icon="👥"
      icon-type="info"
      title="Menunggu Data People Counter"
      description="Sistem menunggu data dari kamera penghitung orang"
      :actions="[
        { icon: '⏳', text: 'Menunggu koneksi ke data sensor' }
      ]"
      :show-status="true"
      status-text="Menunggu deteksi kamera..."
      status-class="waiting"
    />
    <template v-else>
      <div class="people-count-display">
        <div class="count-value">{{ currentCount }}</div>
        <div class="count-label">Orang di Ruangan</div>
      </div>
      <Line
        :data="chartData"
        :options="chartOptions"
      />
    </template>
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
const currentCount = computed(() => {
  const values = props.data.values || []
  return values.length > 0 ? values[values.length - 1] : 0
})

const chartData = computed(() => ({
  labels: props.data.labels || [],
  datasets: [
    {
      label: 'Jumlah Orang',
      data: props.data.values || [],
      borderColor: '#06b6d4',
      backgroundColor: 'rgba(6, 182, 212, 0.15)',
      borderWidth: 3,
      fill: true,
      tension: 0.4,
      pointRadius: 3,
      pointHoverRadius: 6,
      pointBackgroundColor: '#06b6d4',
      pointBorderColor: '#fff',
      pointBorderWidth: 2,
      stepped: false
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
        display: false
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
        borderColor: '#06b6d4',
        borderWidth: 2,
        cornerRadius: 8,
        displayColors: true,
        titleColor: isDark ? '#e8e8e8' : '#ffffff',
        bodyColor: isDark ? '#b8b8c8' : '#ffffff'
      }
    },
    scales: {
      y: {
        min: 0,
        max: 5,
        ticks: {
          stepSize: 1,
          precision: 0,
          font: {
            size: 11
          },
          color: isDark ? '#b8b8c8' : '#95a5a6'
        },
        title: {
          display: false
        },
        grid: {
          color: isDark ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.06)',
          lineWidth: 1
        }
      },
      x: {
        grid: {
          display: false
        },
        ticks: {
          font: {
            size: 10
          },
          color: isDark ? '#b8b8c8' : '#95a5a6',
          maxRotation: 45,
          autoSkip: true,
          maxTicksLimit: 10
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
  height: 180px;
  position: relative;
}

.people-count-display {
  text-align: center;
  margin-bottom: 24px;
  padding: 28px 24px;
  background: linear-gradient(135deg, #06b6d4 0%, #0891b2 50%, #0e7490 100%);
  background-size: 200% 200%;
  animation: gradientShift 3s ease infinite;
  border-radius: 20px;
  color: white;
  box-shadow: 0 8px 24px rgba(6, 182, 212, 0.3);
  position: relative;
  overflow: hidden;
  transition: all 0.3s ease;
}

.people-count-display::before {
  content: '';
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.1) 0%, transparent 70%);
  animation: rotate 10s linear infinite;
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@keyframes gradientShift {
  0%, 100% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
}

.people-count-display:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 32px rgba(6, 182, 212, 0.4);
}

.count-value {
  font-size: 56px;
  font-weight: 800;
  margin-bottom: 8px;
  text-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
  position: relative;
  z-index: 1;
  animation: countPulse 2s ease-in-out infinite;
}

@keyframes countPulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.05); }
}

.count-label {
  font-size: 14px;
  opacity: 0.95;
  text-transform: uppercase;
  letter-spacing: 2px;
  font-weight: 600;
  position: relative;
  z-index: 1;
}
</style>





