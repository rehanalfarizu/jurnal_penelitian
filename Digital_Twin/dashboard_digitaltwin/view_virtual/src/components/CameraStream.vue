<template>
  <div class="camera-stream">
    <div class="stream-container">
      <!-- Loading Indicator -->
      <div v-if="isLoading" class="loading-overlay">
        <div class="spinner"></div>
        <p>Connecting to camera...</p>
      </div>

      <!-- Video Stream -->
      <img 
        v-show="!streamError && !isLoading"
        :src="streamUrl" 
        alt="Camera Stream"
        class="stream-image"
        @load="handleLoad"
        @error="handleError"
      />

      <!-- Error State -->
      <div v-if="streamError && !isLoading" class="stream-placeholder">
        <div class="placeholder-content">
          <span class="icon">📹</span>
          <p class="main-message">Camera Stream Unavailable</p>
          <p class="sub-message">{{ errorMessage }}</p>
          <button @click="refreshStream" class="camera-refresh-trigger">
            <span class="btn-icon">🔄</span>
            <span class="btn-text">Muat Ulang Kamera</span>
          </button>
        </div>
      </div>

      <!-- Stream Info Overlay -->
      <div v-if="!streamError && !isLoading" class="stream-overlay">
        <div class="stream-info">
          <div class="status-indicator" :class="{ active: isStreamActive }"></div>
          <span>LIVE</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'

const emit = defineEmits(['peopleCountUpdate'])

// State
const localCameraUrl = ref('http://192.168.137.205:5000')
const streamUrl = ref('')
const isLoading = ref(true)
const streamError = ref(false)
const errorMessage = ref('')
const isStreamActive = ref(false)
const streamKey = ref(0)
let countPollingTimer = null

// Computed
const videoFeedUrl = computed(() => {
  // Add cache busting parameter untuk force reload
  return `${localCameraUrl.value}/video_feed?t=${streamKey.value}`
})

// Fetch people count from Raspberry Pi directly
const fetchPeopleCountFromRaspberryPi = async () => {
  try {
    const response = await fetch(`${localCameraUrl.value}/count`, {
      method: 'GET',
      headers: {
        'ngrok-skip-browser-warning': 'true'
      }
    })
    
    if (!response.ok) {
      console.warn('⚠️ Cannot fetch count from Raspberry Pi')
      return
    }
    
    const data = await response.json()
    const count = data.count || 0
    
    console.log('📷 People count from Raspberry Pi:', count)
    
    // Emit ke parent component
    emit('peopleCountUpdate', count)
    
  } catch (error) {
    console.warn('⚠️ Error fetching from Raspberry Pi:', error.message)
  }
}

const refreshStream = () => {
  console.log('🔄 Refreshing camera stream...')
  isLoading.value = true
  streamError.value = false
  errorMessage.value = ''
  isStreamActive.value = false
  
  // Update stream key untuk force reload
  streamKey.value = Date.now()
  streamUrl.value = videoFeedUrl.value
}

const handleLoad = () => {
  console.log('✅ Stream loaded successfully')
  isLoading.value = false
  streamError.value = false
  isStreamActive.value = true
  
  // Start polling people count saat stream aktif
  startCountPolling()
}

const handleError = (event) => {
  console.error('❌ Stream error:', event)
  isLoading.value = false
  streamError.value = true
  isStreamActive.value = false
  errorMessage.value = 'Kamera sedang tidak dapat diakses saat ini. Silakan coba muat ulang.'
  
  // Stop polling saat error
  stopCountPolling()
}

const startCountPolling = () => {
  // Fetch immediately
  fetchPeopleCountFromRaspberryPi()
  
  // Then poll every 1 second untuk real-time update
  if (!countPollingTimer) {
    countPollingTimer = setInterval(() => {
      fetchPeopleCountFromRaspberryPi()
    }, 1000)
    console.log('🔄 Started people count polling (1s)')
  }
}

const stopCountPolling = () => {
  if (countPollingTimer) {
    clearInterval(countPollingTimer)
    countPollingTimer = null
    console.log('⏹️ Stopped people count polling')
  }
}

onMounted(() => {
  console.log('🎥 CameraStream mounted')
  console.log('📍 Camera URL:', localCameraUrl.value)
  
  // Initialize stream
  setTimeout(() => {
    refreshStream()
  }, 500)
})

onUnmounted(() => {
  console.log('CameraStream unmounted')
  stopCountPolling()
})
</script>

<style scoped>
.camera-stream {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.stream-container {
  position: relative;
  width: 100%;
  aspect-ratio: 4/3;
  background: var(--bg-secondary);
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 8px var(--shadow-sm);
}

.stream-image {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
  background: #000;
}

.stream-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-card);
  border: 2px dashed var(--border);
}

.placeholder-content {
  text-align: center;
  color: var(--text-secondary);
  padding: 20px;
}

.placeholder-content .icon {
  font-size: 48px;
  display: block;
  margin-bottom: 12px;
}

.placeholder-content .main-message {
  font-size: 18px;
  font-weight: 600;
  margin: 8px 0;
  color: var(--text-primary);
}

.placeholder-content .sub-message {
  font-size: 14px;
  margin: 4px 0 16px 0;
  opacity: 0.7;
}

.placeholder-content .offline-info {
  text-align: left;
  background: var(--bg-secondary);
  padding: 12px 16px;
  border-radius: 8px;
  font-size: 13px;
  margin-top: 12px;
}

.placeholder-content .offline-info p {
  margin: 0 0 8px 0;
  font-weight: 500;
}

.placeholder-content .offline-info ul {
  margin: 0;
  padding-left: 20px;
}

.placeholder-content .offline-info li {
  margin: 4px 0;
  opacity: 0.8;
}

.url-hint {
  font-size: 12px;
  opacity: 0.7;
}

.stream-overlay {
  position: absolute;
  top: 12px;
  right: 12px;
  background: rgba(0, 0, 0, 0.7);
  padding: 6px 12px;
  border-radius: 4px;
  backdrop-filter: blur(8px);
}

.error-overlay {
  position: absolute;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(220, 38, 38, 0.9);
  color: white;
  padding: 12px 24px;
  border-radius: 8px;
  backdrop-filter: blur(8px);
  font-size: 14px;
  font-weight: 500;
}

.stream-info {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  color: white;
}

.status-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #666;
}

.status-indicator.active {
  background: #00ff00;
  box-shadow: 0 0 8px #00ff00;
  animation: pulse 2s infinite;
}

.fps-text {
  margin-left: 8px;
  font-size: 11px;
  opacity: 0.8;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: white;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 12px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.stream-controls {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.debug-info {
  margin-top: 8px;
  padding: 8px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 4px;
  font-family: monospace;
  font-size: 11px;
  color: #aaa;
  word-break: break-all;
}

.ip-input {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid var(--border);
  border-radius: 4px;
  background: var(--bg-card);
  color: var(--text-primary);
  font-size: 14px;
}

.ip-input:focus {
  outline: none;
  border-color: var(--primary);
}

.btn-update,
.btn-refresh {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  background: var(--primary);
  color: white;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-update:hover,
.btn-refresh:hover {
  background: var(--primary-dark);
  transform: translateY(-1px);
}

.btn-refresh {
  background: var(--success);
}

.btn-refresh:hover {
  background: var(--success-dark);
}

.btn-refresh:disabled {
  background: var(--border);
  cursor: not-allowed;
  transform: none;
}

.camera-refresh-trigger {
  margin-top: 20px;
  padding: 12px 24px;
  background: var(--primary, #0284c7);
  color: #ffffff;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  display: inline-flex !important;
  align-items: center !important;
  gap: 10px !important;
  justify-content: center !important;
  width: auto !important;
  height: auto !important;
  white-space: nowrap !important;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

.camera-refresh-trigger:hover {
  background: var(--primary-dark, #0369a1);
  transform: translateY(-2px);
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
}

.camera-refresh-trigger .btn-icon {
  font-size: 16px;
  line-height: 1;
}

.camera-refresh-trigger .btn-text {
  font-size: 14px;
  line-height: 1;
  color: #ffffff;
}

.btn-open-local,
.btn-refresh {
  margin-top: 12px;
  padding: 10px 20px;
  border: none;
  border-radius: 6px;
  background: var(--primary);
  color: white;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-open-local:hover,
.btn-refresh:hover {
  background: var(--primary-dark);
  transform: translateY(-1px);
}

.note {
  margin-top: 12px;
  font-size: 12px;
  opacity: 0.7;
  font-style: italic;
}
</style>
