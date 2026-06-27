<template>
  <div class="empty-state" :class="{ 'dark': isDarkMode }">
    <div class="empty-state-content">
      <!-- Animated Icon/Illustration -->
      <div class="empty-icon" :class="iconType">
        <div class="icon-wrapper">
          {{ icon }}
        </div>
        <div class="icon-pulse"></div>
      </div>
      
      <!-- Title -->
      <h3 class="empty-title">{{ title }}</h3>
      
      <!-- Description -->
      <p class="empty-description">{{ description }}</p>
      
      <!-- Action Guidance -->
      <div v-if="actions.length > 0" class="empty-actions">
        <div v-for="(action, index) in actions" :key="index" class="action-item">
          <span class="action-icon">{{ action.icon }}</span>
          <span class="action-text">{{ action.text }}</span>
        </div>
      </div>
      
      <!-- Optional Button -->
      <button v-if="buttonText" @click="handleButtonClick" class="empty-button">
        {{ buttonText }}
      </button>
      
      <!-- Status Indicator -->
      <div v-if="showStatus" class="status-indicator">
        <span class="status-dot" :class="statusClass"></span>
        <span class="status-text">{{ statusText }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  isDarkMode: {
    type: Boolean,
    default: false
  },
  icon: {
    type: String,
    default: '📊'
  },
  iconType: {
    type: String,
    default: 'default', // 'default', 'warning', 'error', 'info', 'success'
  },
  title: {
    type: String,
    default: 'Tidak Ada Data'
  },
  description: {
    type: String,
    default: 'Data belum tersedia saat ini'
  },
  actions: {
    type: Array,
    default: () => []
    // Format: [{ icon: '🔌', text: 'Hubungkan ke MQTT broker' }]
  },
  buttonText: {
    type: String,
    default: ''
  },
  showStatus: {
    type: Boolean,
    default: false
  },
  statusText: {
    type: String,
    default: 'Menunggu koneksi...'
  },
  statusClass: {
    type: String,
    default: 'waiting' // 'waiting', 'connected', 'disconnected'
  }
})

const emit = defineEmits(['buttonClick'])

const handleButtonClick = () => {
  emit('buttonClick')
}
</script>

<style scoped>
.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 300px;
  padding: 40px 20px;
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  border-radius: 12px;
  transition: all 0.3s ease;
}

.empty-state.dark {
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
}

.empty-state-content {
  text-align: center;
  max-width: 500px;
  width: 100%;
  animation: fadeInUp 0.6s ease-out;
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Icon Styles */
.empty-icon {
  position: relative;
  display: inline-block;
  margin-bottom: 24px;
}

.icon-wrapper {
  font-size: 5rem;
  position: relative;
  z-index: 2;
  animation: float 3s ease-in-out infinite;
  filter: drop-shadow(0 4px 8px rgba(0, 0, 0, 0.1));
}

@keyframes float {
  0%, 100% {
    transform: translateY(0px);
  }
  50% {
    transform: translateY(-10px);
  }
}

.icon-pulse {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 120px;
  height: 120px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(6, 182, 212, 0.2) 0%, transparent 70%);
  animation: pulse 2s ease-out infinite;
  z-index: 1;
}

@keyframes pulse {
  0% {
    transform: translate(-50%, -50%) scale(0.8);
    opacity: 1;
  }
  100% {
    transform: translate(-50%, -50%) scale(1.5);
    opacity: 0;
  }
}

/* Icon Type Variations */
.empty-icon.warning .icon-pulse {
  background: radial-gradient(circle, rgba(245, 158, 11, 0.2) 0%, transparent 70%);
}

.empty-icon.error .icon-pulse {
  background: radial-gradient(circle, rgba(239, 68, 68, 0.2) 0%, transparent 70%);
}

.empty-icon.info .icon-pulse {
  background: radial-gradient(circle, rgba(59, 130, 246, 0.2) 0%, transparent 70%);
}

.empty-icon.success .icon-pulse {
  background: radial-gradient(circle, rgba(16, 185, 129, 0.2) 0%, transparent 70%);
}

/* Title */
.empty-title {
  margin: 0 0 12px 0;
  font-size: 1.5rem;
  font-weight: 700;
  color: #1e293b;
  animation: fadeIn 0.6s ease-out 0.2s both;
}

.empty-state.dark .empty-title {
  color: #f1f5f9;
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

/* Description */
.empty-description {
  margin: 0 0 24px 0;
  font-size: 1rem;
  line-height: 1.6;
  color: #64748b;
  animation: fadeIn 0.6s ease-out 0.3s both;
}

.empty-state.dark .empty-description {
  color: #94a3b8;
}

/* Actions */
.empty-actions {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 24px;
  animation: fadeIn 0.6s ease-out 0.4s both;
}

.action-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  transition: all 0.3s ease;
  min-height: 44px;
  width: 100%;
}

.empty-state.dark .action-item {
  background: #1e293b;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.action-item:hover {
  transform: translateX(5px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

.action-icon {
  font-size: 1.3rem;
  flex-shrink: 0;
  width: 24px;
  text-align: center;
}

.action-text {
  flex: 1;
  text-align: left;
  font-size: 0.85rem;
  color: #475569;
  font-weight: 500;
  line-height: 1.3;
  word-wrap: break-word;
  overflow-wrap: break-word;
  hyphens: auto;
}

.empty-state.dark .action-text {
  color: #cbd5e1;
}

/* Button */
.empty-button {
  padding: 12px 32px;
  background: linear-gradient(135deg, #06b6d4 0%, #0891b2 100%);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 4px 6px rgba(6, 182, 212, 0.3);
  transition: all 0.3s ease;
  animation: fadeIn 0.6s ease-out 0.5s both;
}

.empty-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 12px rgba(6, 182, 212, 0.4);
}

.empty-button:active {
  transform: translateY(0);
}

/* Status Indicator */
.status-indicator {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin-top: 24px;
  padding: 8px 16px;
  background: rgba(6, 182, 212, 0.1);
  border-radius: 20px;
  animation: fadeIn 0.6s ease-out 0.6s both;
}

.empty-state.dark .status-indicator {
  background: rgba(6, 182, 212, 0.15);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  animation: blink 2s ease-in-out infinite;
}

.status-dot.waiting {
  background: #f59e0b;
}

.status-dot.connected {
  background: #10b981;
}

.status-dot.disconnected {
  background: #ef4444;
}

@keyframes blink {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.3;
  }
}

.status-text {
  font-size: 0.875rem;
  color: #64748b;
  font-weight: 500;
}

.empty-state.dark .status-text {
  color: #94a3b8;
}

/* Responsive */
@media (max-width: 768px) {
  .empty-state {
    min-height: 250px;
    padding: 30px 15px;
  }
  
  .icon-wrapper {
    font-size: 4rem;
  }
  
  .empty-title {
    font-size: 1.25rem;
  }
  
  .empty-description {
    font-size: 0.9rem;
  }
  
  .action-item {
    padding: 10px 15px;
  }
  
  .action-text {
    font-size: 0.875rem;
  }
}
</style>
