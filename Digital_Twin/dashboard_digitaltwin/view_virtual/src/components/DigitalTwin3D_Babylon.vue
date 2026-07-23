<template>
  <div class="digital-twin-3d">
    <div class="canvas-wrapper">
      <canvas ref="canvas" class="canvas-container"></canvas>
      
      <!-- Sensor Icons Overlay - Inside 3D View -->
      <div class="sensor-icons-overlay">
        <div 
          v-for="icon in sensorIcons" 
          :key="icon.id"
          class="sensor-icon"
          @click="showSensorData(icon)"
          :title="icon.label"
        >
          <div class="icon-emoji">{{ icon.emoji }}</div>
          <div class="icon-label">{{ icon.label }}</div>
          <div class="icon-value">{{ icon.value }}</div>
        </div>
      </div>
    </div>
    
    <!-- Loading Indicator -->
    <div v-if="!modelLoaded" class="loading-overlay">
      <div class="loading-spinner">
        <div class="spinner"></div>
        <p class="loading-text">{{ loadingStatus }}</p>
        <div class="progress-bar-container">
          <div class="progress-bar" :style="{ width: loadingProgress + '%' }"></div>
        </div>
        <p class="loading-details">{{ loadingDetails }}</p>
        <p v-if="loadingProgress > 0 && loadingProgress < 100" class="loading-tip">
          💡 Loading 3D apartment model...
        </p>
      </div>
    </div>
    
    <div class="controls">
      <button @click="resetCamera" class="btn btn-primary">🔄 Reset Kamera</button>
      <button @click="toggleAnimation" class="btn btn-primary">
        {{ isAnimating ? '⏸️ Pause' : '▶️ Play' }}
      </button>
    </div>
    
    <!-- Hover Tooltip -->
    <div v-if="hoveredMesh && !selectedItem" class="hover-tooltip">
      <span class="tooltip-icon">{{ hoveredMesh.info?.icon || '📍' }}</span>
      <span class="tooltip-text">{{ hoveredMesh.info?.name || hoveredMesh.name }}</span>
      <span class="tooltip-hint">Klik untuk detail</span>
    </div>
    
    <!-- Popup Detail Item -->
    <div v-if="selectedItem" class="item-popup" @click="closePopup">
      <div class="popup-content" @click.stop>
        <button class="close-btn" @click="closePopup">×</button>
        <h3>{{ selectedItem.name }}</h3>
        <div class="popup-details">
          <div v-for="(value, key) in selectedItem.data" :key="key" class="detail-row">
            <span class="detail-label">{{ formatLabel(key) }}:</span>
            <span class="detail-value">{{ formatValue(key, value) }}</span>
          </div>
        </div>
        <div class="popup-status">
          <span class="status-indicator" :class="selectedItem.status"></span>
          {{ selectedItem.statusText }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'
import * as BABYLON from '@babylonjs/core'
import '@babylonjs/loaders/glTF'

const props = defineProps({
  sensorData: {
    type: Object,
    default: () => ({ temperature: 0, voltage: 0, current: 0, humidity: 0, power: 0 })
  },
  peopleCount: {
    type: Number,
    default: 0
  },
  isDarkMode: {
    type: Boolean,
    default: false
  }
})

const canvas = ref(null)
const isAnimating = ref(true)
const selectedItem = ref(null)
const hoveredMesh = ref(null)

// Sensor Icons Configuration
const sensorIcons = computed(() => [
  {
    id: 'temperature',
    emoji: '🌡️',
    label: 'Suhu',
    value: `${props.sensorData.temperature.toFixed(1)}°C`,
    gradient: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
    data: {
      temperature: props.sensorData.temperature,
      sensor: 'DHT22 Sensor'
    }
  },
  {
    id: 'humidity',
    emoji: '💧',
    label: 'Kelembaban',
    value: `${props.sensorData.humidity.toFixed(1)}%`,
    gradient: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
    data: {
      humidity: props.sensorData.humidity,
      sensor: 'DHT22 Sensor'
    }
  },
  {
    id: 'voltage',
    emoji: '🔌',
    label: 'Tegangan',
    value: `${props.sensorData.voltage.toFixed(1)}V`,
    gradient: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
    data: {
      voltage: props.sensorData.voltage,
      sensor: 'ZMPT101B Sensor'
    }
  },
  {
    id: 'current',
    emoji: '⚡',
    label: 'Arus',
    value: `${props.sensorData.current.toFixed(2)}A`,
    gradient: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
    data: {
      current: props.sensorData.current,
      sensor: 'SCT-013 Sensor'
    }
  },
  {
    id: 'power',
    emoji: '💡',
    label: 'Daya',
    value: `${props.sensorData.power.toFixed(1)}W`,
    gradient: 'linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%)',
    data: {
      power: props.sensorData.power,
      sensor: 'Konsumsi Listrik'
    }
  }
])

let engine = null
let scene = null
let camera = null
let blenderModel = null
let highlightLayer = null
const modelLoaded = ref(false)
const loadingProgress = ref(0)
const loadingStatus = ref('Initializing 3D Engine...')
const loadingDetails = ref('')
let loadStartTime = null
let lastLoadedBytes = 0
let downloadSpeed = 0

// Mapping nama mesh ke informasi ruangan (sesuai scene.gltf)
const roomMapping = {
  // Ruangan utama dari scene.gltf
  'LivingRoomWallper': { name: 'Living Room', type: 'living', icon: '🛋️' },
  'KitchenTiles': { name: 'Kitchen', type: 'kitchen', icon: '🍳' },
  'ToiletTiles': { name: 'Toilet', type: 'toilet', icon: '🚻' },
  'ToiletFloorTiles': { name: 'Toilet Floor', type: 'toilet', icon: '🚻' },
  'BedRoomWallper': { name: 'Bedroom', type: 'bedroom', icon: '🛏️' },
  'DoorMaterial': { name: 'Pintu', type: 'structure', icon: '🚪' },
  'WoodenFloor': { name: 'Lantai Kayu', type: 'structure', icon: '🪵' },
  'JustWhite': { name: 'Dinding', type: 'structure', icon: '🧱' },
  'Brick': { name: 'Dinding Bata', type: 'structure', icon: '🧱' },
  // Fallback untuk mesh lain
  'wall': { name: 'Dinding', type: 'structure', icon: '🧱' },
  'floor': { name: 'Lantai', type: 'structure', icon: '⬛' },
  'door': { name: 'Pintu', type: 'structure', icon: '🚪' },
  'window': { name: 'Jendela', type: 'structure', icon: '🪟' },
  'acBody': { name: 'AC Unit', type: 'equipment', icon: '❄️' },
}

onMounted(() => {
  setTimeout(() => {
    if (canvas.value) {
      initBabylonJS()
    } else {
      console.error('Canvas element not found')
    }
  }, 100)
})

onUnmounted(() => {
  cleanup()
})

watch(() => props.sensorData, (newData) => {
  updateSensorVisualization(newData)
  if (selectedItem.value) {
    updateSelectedItem()
  }
}, { deep: true })

watch(() => props.peopleCount, (count) => {
  updatePeopleVisualization(count)
  if (selectedItem.value) {
    updateSelectedItem()
  }
})

watch(() => props.isDarkMode, () => {
  updateSceneTheme()
})

const updateSceneTheme = () => {
  if (!scene) return
  
  if (props.isDarkMode) {
    scene.clearColor = new BABYLON.Color4(0.06, 0.09, 0.16, 1)
  } else {
    scene.clearColor = new BABYLON.Color4(0.94, 0.97, 1, 1)
  }
}

const initBabylonJS = () => {
  if (!canvas.value) {
    console.error('Canvas not found')
    return
  }

  try {
    // Create engine
    engine = new BABYLON.Engine(canvas.value, true, {
      preserveDrawingBuffer: true,
      stencil: true,
      antialias: true
    })

    // Create scene
    scene = new BABYLON.Scene(engine)
    updateSceneTheme()
    
    // Enable fog
    scene.fogMode = BABYLON.Scene.FOGMODE_EXP2
    scene.fogDensity = 0.015
    scene.fogColor = props.isDarkMode 
      ? new BABYLON.Color3(0.06, 0.09, 0.16) 
      : new BABYLON.Color3(0.94, 0.97, 1)

    // Create camera
    camera = new BABYLON.ArcRotateCamera(
      "camera",
      Math.PI / 4,
      Math.PI / 3,
      15,
      new BABYLON.Vector3(0, 2, 0),
      scene
    )
    camera.attachControl(canvas.value, true)
    camera.lowerRadiusLimit = 5
    camera.upperRadiusLimit = 30
    camera.wheelPrecision = 50

    // Enhanced lighting
    const ambientLight = new BABYLON.HemisphericLight(
      "ambientLight",
      new BABYLON.Vector3(0, 1, 0),
      scene
    )
    ambientLight.intensity = 0.5

    // Main directional light
    const mainLight = new BABYLON.DirectionalLight(
      "mainLight",
      new BABYLON.Vector3(-1, -2, -1),
      scene
    )
    mainLight.intensity = 0.8
    mainLight.position = new BABYLON.Vector3(10, 15, 10)

    // Enable shadows
    const shadowGenerator = new BABYLON.ShadowGenerator(1024, mainLight)
    shadowGenerator.useBlurExponentialShadowMap = true
    shadowGenerator.blurScale = 2

    // Point lights
    const pointLight1 = new BABYLON.PointLight(
      "pointLight1",
      new BABYLON.Vector3(-3, 3, -3),
      scene
    )
    pointLight1.intensity = 0.6
    pointLight1.diffuse = new BABYLON.Color3(1, 0.9, 0.8)

    const pointLight2 = new BABYLON.PointLight(
      "pointLight2",
      new BABYLON.Vector3(3, 3, 3),
      scene
    )
    pointLight2.intensity = 0.6
    pointLight2.diffuse = new BABYLON.Color3(0.8, 0.9, 1)

    console.log('✅ Babylon.js initialized')

    // Setup mesh click detection (disabled for now)
    // setupMeshInteraction()

    // Prevent page scroll/zoom when scrolling on canvas - only zoom 3D view
    canvas.value.addEventListener('wheel', (event) => {
      event.preventDefault()
    }, { passive: false })

    // Load model
    loadModel(shadowGenerator)

    // Render loop
    engine.runRenderLoop(() => {
      if (scene && isAnimating.value) {
        scene.render()
      }
    })

    // Handle resize
    window.addEventListener('resize', () => {
      engine.resize()
    })

  } catch (error) {
    console.error('Error initializing Babylon.js:', error)
  }
}

const formatBytes = (bytes) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const formatTime = (seconds) => {
  if (seconds < 60) return `${Math.round(seconds)}s`
  const mins = Math.floor(seconds / 60)
  const secs = Math.round(seconds % 60)
  return `${mins}m ${secs}s`
}

// Setup interaksi klik dan hover pada mesh
const setupMeshInteraction = () => {
  // Create highlight layer untuk efek hover
  highlightLayer = new BABYLON.HighlightLayer("highlightLayer", scene)
  highlightLayer.innerGlow = false
  highlightLayer.outerGlow = true
  
  // Hover - highlight mesh saat mouse over
  scene.onPointerMove = (evt, pickInfo) => {
    // Remove previous highlight
    if (hoveredMesh.value && hoveredMesh.value.mesh) {
      highlightLayer.removeMesh(hoveredMesh.value.mesh)
      hoveredMesh.value = null
    }
    
    if (pickInfo.hit && pickInfo.pickedMesh) {
      const mesh = pickInfo.pickedMesh
      const meshName = mesh.name || ''
      
      // Skip jika mesh adalah particle atau effect
      if (meshName.includes('particle') || meshName.includes('Particle')) return
      
      // Highlight mesh
      highlightLayer.addMesh(mesh, new BABYLON.Color3(0.2, 0.6, 1)) // Blue highlight
      
      // Get room info
      const roomInfo = getRoomInfo(meshName)
      hoveredMesh.value = {
        mesh: mesh,
        name: meshName,
        info: roomInfo
      }
      
      // Change cursor
      canvas.value.style.cursor = 'pointer'
    } else {
      canvas.value.style.cursor = 'grab'
    }
  }
  
  // Click - show popup with details
  scene.onPointerDown = (evt, pickInfo) => {
    if (pickInfo.hit && pickInfo.pickedMesh && evt.button === 0) {
      const mesh = pickInfo.pickedMesh
      const meshName = mesh.name || ''
      
      // Skip particle meshes
      if (meshName.includes('particle') || meshName.includes('Particle')) return
      
      console.log('🖱️ Clicked mesh:', meshName)
      
      // Get room info and show popup
      const roomInfo = getRoomInfo(meshName)
      showMeshPopup(mesh, roomInfo)
    }
  }
  
  console.log('✅ Mesh interaction setup complete')
}

// Get room info based on mesh name
const getRoomInfo = (meshName) => {
  // Check exact match first
  if (roomMapping[meshName]) {
    return roomMapping[meshName]
  }
  
  // Check partial match
  const lowerName = meshName.toLowerCase()
  for (const [key, value] of Object.entries(roomMapping)) {
    if (lowerName.includes(key.toLowerCase())) {
      return value
    }
  }
  
  // Default for unknown mesh
  return {
    name: meshName || 'Unknown Object',
    type: 'other',
    icon: '📍'
  }
}

// Show popup when mesh is clicked
const showMeshPopup = (mesh, roomInfo) => {
  // Get sensor data based on room type
  let sensorData = {}
  let status = 'normal'
  let statusText = 'Status Normal'
  
  switch (roomInfo.type) {
    case 'living':
    case 'bedroom':
      sensorData = {
        temperature: props.sensorData.temperature,
        humidity: props.sensorData.humidity,
        peopleCount: props.peopleCount
      }
      if (props.sensorData.temperature > 28) {
        status = 'warning'
        statusText = '⚠️ Suhu Tinggi'
      }
      break
    case 'kitchen':
      sensorData = {
        temperature: props.sensorData.temperature,
        humidity: props.sensorData.humidity,
        power: props.sensorData.power
      }
      break
    case 'toilet':
      sensorData = {
        humidity: props.sensorData.humidity,
        status: 'Available'
      }
      break
    case 'equipment':
      sensorData = {
        temperature: props.sensorData.temperature,
        power: props.sensorData.power,
        status: 'Active'
      }
      break
    case 'structure':
      sensorData = {
        condition: 'Good',
        lastCheck: new Date().toLocaleDateString('id-ID')
      }
      break
    default:
      sensorData = {
        temperature: props.sensorData.temperature,
        humidity: props.sensorData.humidity
      }
  }
  
  selectedItem.value = {
    name: `${roomInfo.icon} ${roomInfo.name}`,
    meshName: mesh.name,
    type: roomInfo.type,
    data: sensorData,
    status: status,
    statusText: statusText,
    position: {
      x: mesh.position?.x?.toFixed(2) || 0,
      y: mesh.position?.y?.toFixed(2) || 0,
      z: mesh.position?.z?.toFixed(2) || 0
    }
  }
  
  console.log('📊 Showing popup for:', roomInfo.name)
}

const loadModel = (shadowGenerator) => {
  console.log('🏠 Loading apartment model from local...')
  loadingStatus.value = 'Loading 3D Model...'
  loadStartTime = Date.now()
  lastLoadedBytes = 0
  
  // Local model path - using 3d twin folder
  const modelPath = "/models/3d twin/"
  const modelFileName = "scene.gltf"
  
  BABYLON.SceneLoader.ImportMesh(
    "",
    modelPath,
    modelFileName,
    scene,
    (meshes) => {
      console.log('✅ Model loaded successfully!')
      console.log('📦 Meshes loaded:', meshes.length)
      loadingStatus.value = 'Processing 3D Model...'
      
      blenderModel = meshes[0]
      
      // Enable shadows for all meshes and change wall colors
      meshes.forEach((mesh) => {
        if (mesh) {
          mesh.receiveShadows = true
          shadowGenerator.addShadowCaster(mesh)
          
          // Change wall color to light beige/cream
          if (mesh.name && (mesh.name.includes('wall') || mesh.name.includes('Wall') || mesh.name.includes('WALL'))) {
            const wallMaterial = new BABYLON.StandardMaterial("wallMaterial_" + mesh.name, scene)
            wallMaterial.diffuseColor = new BABYLON.Color3(0.95, 0.92, 0.85) // Light cream/beige
            wallMaterial.specularColor = new BABYLON.Color3(0.1, 0.1, 0.1)
            mesh.material = wallMaterial
            console.log('🎨 Wall color changed:', mesh.name)
          }
          
          // Log mesh info
          if (mesh.name) {
            console.log('📦 Mesh:', mesh.name)
          }
        }
      })
      
      // Tambahkan AC unit di atas pintu
      createACUnit(shadowGenerator)
      
      loadingStatus.value = '✅ Model Loaded!'
      modelLoaded.value = true
      loadingProgress.value = 100
      loadingDetails.value = ''
      
      const totalTime = (Date.now() - loadStartTime) / 1000
      console.log(`📊 Model loaded in ${formatTime(totalTime)}`)
      console.log('📊 Model info:', {
        meshes: meshes.length,
        position: blenderModel.position
      })
    },
    (event) => {
      if (event.lengthComputable) {
        const loaded = event.loaded
        const total = event.total
        loadingProgress.value = (loaded / total) * 100
        
        // Calculate download speed
        const currentTime = Date.now()
        const elapsedTime = (currentTime - loadStartTime) / 1000
        
        if (elapsedTime > 0) {
          downloadSpeed = loaded / elapsedTime // bytes per second
          const remainingBytes = total - loaded
          const estimatedTimeRemaining = remainingBytes / downloadSpeed
          
          loadingStatus.value = `Downloading 3D Model... ${loadingProgress.value.toFixed(0)}%`
          loadingDetails.value = `${formatBytes(loaded)} / ${formatBytes(total)} • ${formatBytes(downloadSpeed)}/s • ~${formatTime(estimatedTimeRemaining)} remaining`
        }
        
        console.log(`⏳ Loading: ${loadingProgress.value.toFixed(1)}%`)
      } else {
        // If total size is unknown, show indeterminate progress
        loadingStatus.value = 'Downloading 3D Model...'
        loadingDetails.value = `${formatBytes(event.loaded)} downloaded`
      }
    },
    (scene, message, exception) => {
      console.error('❌ Error loading model:', message, exception)
      console.error('⚠️ Pastikan file ada di: /models/floor_plan.glb')
      loadingStatus.value = '❌ Error loading model'
      loadingDetails.value = 'Check console for details'
      modelLoaded.value = true
    }
  )
}

const createACUnit = (shadowGenerator) => {
  console.log('🌬️ Creating AC unit...')
  
  // AC Body (main unit) - dipasang MENEMPEL di dinding
  const acBody = BABYLON.MeshBuilder.CreateBox("acBody", {
    width: 1.2,
    height: 0.25,
    depth: 0.35
  }, scene)
  
  // Posisi AC: DI DALAM RUANGAN, menempel di dinding SAMPING KIRI
  // X = -2.3 (dimajukan supaya tidak tertutup dinding)
  // Y = 2.5 (tinggi standar AC)
  // Z = -3.5 (posisi horizontal)
  acBody.position = new BABYLON.Vector3(-2.3, 2.5, -3.5)
  acBody.rotation.y = Math.PI / 2 // Face ke kanan (ke dalam ruangan)
  
  // Material AC
  const acMaterial = new BABYLON.StandardMaterial("acMaterial", scene)
  acMaterial.diffuseColor = new BABYLON.Color3(0.9, 0.9, 0.9)
  acMaterial.specularColor = new BABYLON.Color3(0.6, 0.6, 0.6)
  acMaterial.roughness = 0.3
  acBody.material = acMaterial
  
  // Front panel with vents
  const ventPanel = BABYLON.MeshBuilder.CreateBox("ventPanel", {
    width: 1.0,
    height: 0.2,
    depth: 0.02
  }, scene)
  ventPanel.position = new BABYLON.Vector3(0, 0, 0.18)
  
  const ventMaterial = new BABYLON.StandardMaterial("ventMaterial", scene)
  ventMaterial.diffuseColor = new BABYLON.Color3(0.15, 0.15, 0.15)
  ventPanel.material = ventMaterial
  ventPanel.parent = acBody
  
  // Create horizontal vent slits
  for (let i = 0; i < 6; i++) {
    const vent = BABYLON.MeshBuilder.CreateBox(`vent${i}`, {
      width: 0.8,
      height: 0.015,
      depth: 0.01
    }, scene)
    vent.position = new BABYLON.Vector3(0, -0.06 + i * 0.025, 0.19)
    
    const slitMaterial = new BABYLON.StandardMaterial(`slitMaterial${i}`, scene)
    slitMaterial.diffuseColor = new BABYLON.Color3(0.05, 0.05, 0.05)
    vent.material = slitMaterial
    
    vent.parent = acBody
    shadowGenerator.addShadowCaster(vent)
  }
  
  // LED indicator (hijau = AC hidup)
  const led = BABYLON.MeshBuilder.CreateSphere("acLED", {
    diameter: 0.04
  }, scene)
  led.position = new BABYLON.Vector3(0.4, 0.08, 0.19)
  
  const ledMaterial = new BABYLON.StandardMaterial("ledMaterial", scene)
  ledMaterial.emissiveColor = new BABYLON.Color3(0, 1, 0)
  ledMaterial.diffuseColor = new BABYLON.Color3(0, 0.6, 0)
  led.material = ledMaterial
  led.parent = acBody
  
  // Add glow effect
  const glowLayer = new BABYLON.GlowLayer("glow", scene)
  glowLayer.addIncludedOnlyMesh(led)
  glowLayer.intensity = 1.0
  
  // Louver/Air flow direction indicator
  const louver = BABYLON.MeshBuilder.CreateBox("louver", {
    width: 0.9,
    height: 0.08,
    depth: 0.01
  }, scene)
  louver.position = new BABYLON.Vector3(0, -0.13, 0.19)
  louver.rotation.x = Math.PI / 6 // Slight angle downward
  
  const louverMaterial = new BABYLON.StandardMaterial("louverMaterial", scene)
  louverMaterial.diffuseColor = new BABYLON.Color3(0.3, 0.3, 0.3)
  louver.material = louverMaterial
  louver.parent = acBody
  
  // Enable shadows
  acBody.receiveShadows = true
  ventPanel.receiveShadows = true
  louver.receiveShadows = true
  
  shadowGenerator.addShadowCaster(acBody)
  shadowGenerator.addShadowCaster(ventPanel)
  shadowGenerator.addShadowCaster(louver)
  
  // Create particle system for cold air effect
  const particleSystem = new BABYLON.ParticleSystem("acParticles", 2000, scene)
  
  // Texture for particles (using a white dot)
  particleSystem.particleTexture = new BABYLON.Texture("https://www.babylonjs-playground.com/textures/flare.png", scene)
  
  // Position where particles emit from (from AC vents)
  // AC body is at (0, 2.5, -4.5), emit from front vents
  particleSystem.emitter = acBody.position.clone()
  particleSystem.minEmitBox = new BABYLON.Vector3(-0.5, -0.1, 0.18)
  particleSystem.maxEmitBox = new BABYLON.Vector3(0.5, -0.05, 0.35)
  
  // Colors
  particleSystem.color1 = new BABYLON.Color4(0.7, 0.9, 1.0, 0.3)
  particleSystem.color2 = new BABYLON.Color4(0.8, 0.95, 1.0, 0.2)
  particleSystem.colorDead = new BABYLON.Color4(0.9, 0.98, 1.0, 0)
  
  // Size of particles
  particleSystem.minSize = 0.05
  particleSystem.maxSize = 0.15
  
  // Life time of particles
  particleSystem.minLifeTime = 0.5
  particleSystem.maxLifeTime = 1.5
  
  // Emission rate
  particleSystem.emitRate = 200
  
  // Blend mode
  particleSystem.blendMode = BABYLON.ParticleSystem.BLENDMODE_ADD
  
  // Direction of particles (downward and forward into the room)
  particleSystem.direction1 = new BABYLON.Vector3(-0.3, -0.5, 0.5)
  particleSystem.direction2 = new BABYLON.Vector3(0.3, -0.8, 1.0)
  
  // Speed
  particleSystem.minEmitPower = 0.5
  particleSystem.maxEmitPower = 1.2
  particleSystem.updateSpeed = 0.01
  
  // Gravity effect (slight downward)
  particleSystem.gravity = new BABYLON.Vector3(0, -0.5, 0)
  
  // Start the particle system
  particleSystem.start()
  
  // Animation - subtle vibration effect
  let angle = 0
  scene.registerBeforeRender(() => {
    angle += 0.02
    acBody.position.y = 2.5 + Math.sin(angle) * 0.003
    
    // Update particle emitter position to follow AC body exactly
    particleSystem.emitter = acBody.position.clone()
  })
  
  console.log('✅ AC unit created above door INSIDE room at position:', acBody.position)
  console.log('✅ Cold air particle system started')
  console.log('   Mounted on interior wall above door')
}

const resetCamera = () => {
  if (camera) {
    camera.alpha = Math.PI / 4
    camera.beta = Math.PI / 3
    camera.radius = 15
    camera.target = new BABYLON.Vector3(0, 2, 0)
  }
}

const zoomIn = () => {
  if (camera) {
    camera.radius = Math.max(camera.radius - 2, camera.lowerRadiusLimit)
  }
}

const zoomOut = () => {
  if (camera) {
    camera.radius = Math.min(camera.radius + 2, camera.upperRadiusLimit)
  }
}

const toggleAnimation = () => {
  isAnimating.value = !isAnimating.value
}

const showSensorData = (icon) => {
  selectedItem.value = {
    name: `Sensor ${icon.label}`,
    data: icon.data,
    status: 'active',
    statusText: 'Sensor Aktif'
  }
}

const closePopup = () => {
  selectedItem.value = null
}

const updateSensorVisualization = (data) => {
  // Implement sensor visualization if needed
  console.log('Sensor data updated:', data)
}

const updatePeopleVisualization = (count) => {
  // Implement people count visualization if needed
  console.log('People count updated:', count)
}

const updateSelectedItem = () => {
  // Update selected item data
  if (selectedItem.value) {
    selectedItem.value.data = {
      temperature: props.sensorData.temperature,
      humidity: props.sensorData.humidity,
      voltage: props.sensorData.voltage,
      current: props.sensorData.current,
      power: props.sensorData.power
    }
  }
}

const formatLabel = (key) => {
  const labels = {
    temperature: 'Suhu',
    humidity: 'Kelembaban',
    voltage: 'Tegangan',
    current: 'Arus',
    power: 'Daya',
    peopleCount: 'Jumlah Orang'
  }
  return labels[key] || key
}

const formatValue = (key, value) => {
  const units = {
    temperature: '°C',
    humidity: '%',
    voltage: 'V',
    current: 'A',
    power: 'W',
    peopleCount: ' orang'
  }
  return `${value}${units[key] || ''}`
}

const cleanup = () => {
  if (engine) {
    engine.dispose()
  }
  window.removeEventListener('resize', () => {
    engine?.resize()
  })
}
</script>

<style scoped>
.digital-twin-3d {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
  border-radius: 12px;
}

.canvas-wrapper {
  position: relative;
  width: 100%;
  height: 100%;
}

.canvas-container {
  width: 100%;
  height: 100%;
  display: block;
  outline: none;
  cursor: grab;
}

.canvas-container:active {
  cursor: grabbing;
}

.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(15, 23, 42, 0.9);
  backdrop-filter: blur(8px);
  z-index: 10;
}

.loading-spinner {
  text-align: center;
  color: white;
  max-width: 350px;
  padding: 30px;
}

.spinner {
  border: 4px solid rgba(255, 255, 255, 0.2);
  border-radius: 50%;
  border-top: 4px solid #3b82f6;
  border-right: 4px solid #8b5cf6;
  width: 60px;
  height: 60px;
  animation: spin 1s linear infinite;
  margin: 0 auto 20px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.loading-text {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 15px;
  color: #f8fafc;
}

.progress-bar-container {
  width: 100%;
  height: 8px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  overflow: hidden;
  margin-bottom: 12px;
}

.progress-bar {
  height: 100%;
  background: linear-gradient(90deg, #3b82f6, #8b5cf6, #ec4899);
  background-size: 200% 100%;
  animation: progressGradient 2s linear infinite;
  border-radius: 10px;
  transition: width 0.3s ease;
}

@keyframes progressGradient {
  0% { background-position: 0% 50%; }
  100% { background-position: 200% 50%; }
}

.loading-details {
  font-size: 13px;
  color: #94a3b8;
  margin-bottom: 10px;
}

.loading-tip {
  font-size: 12px;
  color: #fbbf24;
  background: rgba(251, 191, 36, 0.1);
  padding: 8px 12px;
  border-radius: 8px;
  margin-top: 15px;
}

.controls {
  position: absolute;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  gap: 10px;
  z-index: 5;
}

/* Sensor Icons Overlay */
.sensor-icons-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
  padding: 20px;
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 15px;
  align-content: start;
  z-index: 5;
}

.sensor-icons-overlay > * {
  pointer-events: auto;
}

.sensor-icon {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border-radius: 16px;
  padding: 12px;
  cursor: pointer;
  transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  border: 2px solid rgba(255, 255, 255, 0.5);
  position: relative;
  overflow: hidden;
  animation: cardFadeIn 0.6s ease-out backwards;
}

[data-theme="dark"] .sensor-icon {
  background: rgba(30, 41, 59, 0.95);
  border-color: rgba(255, 255, 255, 0.1);
}

@keyframes cardFadeIn {
  from {
    opacity: 0;
    transform: scale(0.8) translateY(-20px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

.sensor-icon:nth-child(1) { animation-delay: 0.1s; }
.sensor-icon:nth-child(2) { animation-delay: 0.2s; }
.sensor-icon:nth-child(3) { animation-delay: 0.3s; }
.sensor-icon:nth-child(4) { animation-delay: 0.4s; }
.sensor-icon:nth-child(5) { animation-delay: 0.5s; }

.sensor-icon:hover {
  transform: translateY(-8px) scale(1.08);
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.25);
  border-color: rgba(102, 126, 234, 0.5);
}

.icon-emoji {
  font-size: 32px;
  margin-bottom: 6px;
  text-align: center;
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.1));
  transition: all 0.3s ease;
}

.sensor-icon:hover .icon-emoji {
  transform: scale(1.15);
  filter: drop-shadow(0 4px 8px rgba(0, 0, 0, 0.2));
}

.icon-label {
  font-size: 10px;
  font-weight: 700;
  color: var(--text-secondary);
  text-align: center;
  margin-bottom: 4px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  transition: color 0.3s ease;
}

.icon-value {
  font-size: 18px;
  font-weight: 800;
  color: var(--text-primary);
  text-align: center;
  line-height: 1.2;
  transition: all 0.3s;
}

.sensor-icon:hover .icon-value {
  transform: scale(1.05);
  color: #667eea;
}

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.3s ease;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
}

.btn-secondary {
  background: linear-gradient(135deg, #4ade80 0%, #22c55e 100%);
  color: white;
}

.btn-secondary:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
}

.item-popup {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(5px);
  z-index: 100;
}

.popup-content {
  background: white;
  padding: 25px;
  border-radius: 15px;
  max-width: 400px;
  width: 90%;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
  position: relative;
}

.close-btn {
  position: absolute;
  top: 10px;
  right: 10px;
  background: none;
  border: none;
  font-size: 30px;
  cursor: pointer;
  color: #999;
  line-height: 1;
  padding: 5px 10px;
}

.close-btn:hover {
  color: #333;
}

.popup-content h3 {
  margin: 0 0 20px 0;
  font-size: 22px;
  color: #333;
}

.popup-details {
  margin-bottom: 20px;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  padding: 10px 0;
  border-bottom: 1px solid #eee;
}

.detail-label {
  font-weight: 600;
  color: #666;
}

.detail-value {
  color: #333;
  font-weight: 500;
}

.popup-status {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px;
  background: #f8f9fa;
  border-radius: 8px;
  font-weight: 500;
}

.status-indicator {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  display: inline-block;
}

.status-indicator.normal {
  background: #10b981;
}

.status-indicator.warning {
  background: #f59e0b;
}

.status-indicator.critical {
  background: #ef4444;
}

/* Hover Tooltip Styles */
.hover-tooltip {
  position: absolute;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(15, 23, 42, 0.9);
  backdrop-filter: blur(10px);
  padding: 12px 20px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  gap: 10px;
  z-index: 50;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.1);
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateX(-50%) translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
  }
}

.tooltip-icon {
  font-size: 24px;
}

.tooltip-text {
  font-size: 16px;
  font-weight: 600;
  color: #f8fafc;
}

.tooltip-hint {
  font-size: 12px;
  color: #94a3b8;
  padding-left: 10px;
  border-left: 1px solid rgba(255, 255, 255, 0.2);
}

@media (max-width: 768px) {
  .sensor-icons-overlay {
    grid-template-columns: repeat(3, 1fr);
    gap: 10px;
    padding: 15px;
  }
  
  .sensor-icon {
    padding: 10px;
  }
  
  .icon-emoji {
    font-size: 24px;
  }
  
  .icon-label {
    font-size: 9px;
  }
  
  .icon-value {
    font-size: 14px;
  }
}

@media (max-width: 480px) {
  .sensor-icons-overlay {
    grid-template-columns: repeat(2, 1fr);
    gap: 8px;
    padding: 10px;
  }
  
  .icon-emoji {
    font-size: 20px;
  }
  
  .icon-value {
    font-size: 12px;
  }
}
</style>
