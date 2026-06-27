<template>
  <div class="cesium-viewer" :class="{ 'dark-mode': isDarkMode }">
    <div id="cesium-container" class="cesium-container"></div>

    <!-- Overlay controls -->
    <div class="cesium-overlay">
      <button class="switch-btn" @click="$emit('switch-to-3d')">
        Beralih ke Babylon.js 3D
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'

defineProps({
  sensorData: { type: Object, default: () => ({ temperature: 25, humidity: 60, power: 0, voltage: 220 }) },
  isDarkMode: { type: Boolean, default: false }
})

const emit = defineEmits(['toggle-indoor', 'switch-to-3d'])

let viewer = null

onMounted(() => {
  initCesium()
})

onBeforeUnmount(() => {
  if (viewer) {
    viewer.destroy()
    viewer = null
  }
})

async function initCesium() {
  // Try loading Cesium dynamically
  try {
    const CesiumModule = await import('cesium')
    const Cesium = CesiumModule.default || CesiumModule

    // Token setup
    const token = import.meta.env.VITE_CESIUM_ION_TOKEN || ''
    if (token) {
      Cesium.Ion.defaultAccessToken = token
    }

    viewer = new Cesium.Viewer('cesium-container', {
      baseLayerPicker: false,
      geocoder: false,
      homeButton: false,
      sceneModePicker: false,
      navigationHelpButton: false,
      fullscreenButton: false,
      animation: false,
      timeline: false,
      infoBox: false,
      selectionIndicator: false,
      shouldAnimate: true
    })

    // Disable atmosphere for cleaner look
    viewer.scene.globe.enableLighting = false

    // Try adding a building outline (fallback to plain map)
    if (token) {
      try {
        viewer.scene.primitives.add(
          new Cesium.BoxOutlineEntity({
            position: Cesium.Cartesian3.fromDegrees(-75.165, 39.953),
            dimensions: new Cesium.Cartesian3(400, 400, 200),
            material: Cesium.Color.fromCssColorString('#4A90A4')
          })
        )
      } catch {}
    }

  } catch (err) {
    // Cesium failed to initialize — show fallback placeholder
    console.warn('[Cesium] Could not initialize Cesium viewer:', err.message)

    // Create placeholder
    const container = document.getElementById('cesium-container')
    if (container) {
      container.innerHTML = `
        <div style="display:flex;align-items:center;justify-content:center;height:100%;background:linear-gradient(135deg,#0a1628 0%,#1a2940 100%);flex-direction:column;gap:12px;">
          <div style="font-size:64px;opacity:0.3">🌍</div>
          <div style="color:#64748b;font-size:14px;font-family:sans-serif">Cesium requires API token</div>
          <div style="color:#475569;font-size:12px;font-family:sans-serif">Switch to Indoor (Babylon.js) view for 3D visualization</div>
        </div>
      `
    }
  }
}
</script>

<style scoped>
.cesium-viewer {
  position: absolute;
  inset: 0;
  overflow: hidden;
}

.cesium-container {
  width: 100%;
  height: 100%;
}

.cesium-overlay {
  position: absolute;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 100;
}

.switch-btn {
  background: rgba(74, 144, 164, 0.9);
  color: #fff;
  border: none;
  padding: 12px 24px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  backdrop-filter: blur(4px);
}

.switch-btn:hover {
  background: rgba(74, 144, 164, 1);
}
</style>
