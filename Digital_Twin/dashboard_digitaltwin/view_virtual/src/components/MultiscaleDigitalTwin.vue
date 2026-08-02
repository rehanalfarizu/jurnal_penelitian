<template>
  <section class="multiscale-twin" aria-label="Visualisasi Digital Twin multiskala">
    <div class="scale-tabs" role="tablist" aria-label="Skala visualisasi">
      <button
        v-for="view in views"
        :key="view.id"
        type="button"
        role="tab"
        :aria-selected="activeView === view.id"
        :class="{ active: activeView === view.id }"
        @click="activeView = view.id"
      >
        <span>{{ view.icon }}</span>
        {{ view.label }}
      </button>
    </div>

    <div v-if="activeView === 'geospatial_site'" class="scale-panel site-panel">
      <svg viewBox="0 0 900 390" role="img" aria-label="Konteks lokasi, edge, dan cloud">
        <defs>
          <linearGradient id="siteBackground" x1="0" x2="1">
            <stop offset="0" stop-color="#dbeafe" />
            <stop offset="1" stop-color="#cffafe" />
          </linearGradient>
          <marker id="routeArrow" markerWidth="10" markerHeight="10" refX="7" refY="3" orient="auto">
            <path d="M0,0 L0,6 L8,3 z" fill="#0284c7" />
          </marker>
        </defs>
        <rect width="900" height="390" rx="22" fill="url(#siteBackground)" />
        <path d="M0 300 C180 220 310 350 500 275 S760 190 900 245 V390 H0Z" fill="#bbf7d0" />
        <path d="M95 90 L340 90 L390 180 L310 290 L80 260 Z" fill="none" stroke="#94a3b8" stroke-width="3" stroke-dasharray="9 7" />
        <path d="M580 65 C520 65 505 125 540 150 C505 205 580 238 625 202 C670 235 750 195 720 140 C755 93 695 47 650 77 C630 48 600 48 580 65Z" fill="#ffffff" stroke="#0284c7" stroke-width="4" />
        <path d="M385 210 C470 205 500 175 548 152" fill="none" stroke="#0284c7" stroke-width="5" stroke-dasharray="10 8" marker-end="url(#routeArrow)" />
        <rect x="245" y="164" width="145" height="112" rx="8" fill="#f8fafc" stroke="#0f172a" stroke-width="3" />
        <path d="M230 165 L318 105 L407 165 Z" fill="#7c3aed" />
        <circle cx="318" cy="210" r="14" fill="#16a34a" />
        <text x="318" y="310" text-anchor="middle" class="svg-title">Bangunan / gateway edge</text>
        <text x="630" y="146" text-anchor="middle" class="svg-title">Cloud</text>
        <text x="630" y="171" text-anchor="middle" class="svg-note">rute selektif</text>
      </svg>
      <div class="panel-facts">
        <strong>{{ coordinateLabel }}</strong>
        <span>{{ twinContext.geospatialVerification }}</span>
        <span>{{ routeLabel }}</span>
      </div>
    </div>

    <div v-else-if="activeView === 'building'" class="scale-panel building-panel">
      <div class="building-layout" aria-label="Ringkasan skala bangunan">
        <div class="floor-plan">
          <div class="room room-main">
            <span>Zona utama</span>
            <strong>{{ occupancyLabel }}</strong>
          </div>
          <div class="room"><span>Gateway</span><strong>{{ routeLabel }}</strong></div>
          <div class="room"><span>Daya legacy</span><strong>{{ formatNumber(sensorData.power, 1, ' W') }}</strong></div>
          <div class="room"><span>Energi satu siklus</span><strong>{{ formatNumber(sensorData.energyCumulativeWh, 3, ' Wh') }}</strong></div>
        </div>
        <div class="building-flow">
          <span>Sensor historis</span><b>→</b><span>Edge</span><b>→</b><span>API</span><b>→</b><span>Visual</span>
        </div>
      </div>
    </div>

    <div v-else class="scale-panel indoor-panel">
      <DigitalTwin3D
        :sensor-data="sensorData"
        :people-count="peopleCount"
        :is-dark-mode="isDarkMode"
      />
    </div>

    <p class="scale-disclaimer">
      {{ twinContext.scaleSemantics }} · Sinkronisasi:
      {{ twinContext.synchronizationMode }}.
    </p>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue'
import DigitalTwin3D from './DigitalTwin3D_Babylon.vue'

const props = defineProps({
  sensorData: {
    type: Object,
    default: () => ({})
  },
  peopleCount: {
    type: Number,
    default: null
  },
  isDarkMode: {
    type: Boolean,
    default: false
  }
})

const activeView = ref('geospatial_site')
const views = [
  { id: 'geospatial_site', label: 'LoD-A · Tapak geospasial', icon: '🌐' },
  { id: 'building', label: 'LoD-B · Bangunan', icon: '🏢' },
  { id: 'indoor', label: 'LoD-C · Indoor 3D', icon: '🧭' }
]

const twinContext = computed(() => ({
  latitude: props.sensorData.digitalTwin?.latitude ?? -7.723,
  longitude: props.sensorData.digitalTwin?.longitude ?? 110.5187,
  crs: props.sensorData.digitalTwin?.crs || 'EPSG:4326',
  geospatialVerification:
    props.sensorData.digitalTwin?.geospatialVerification ||
    'koordinat legacy; belum diverifikasi survei',
  scaleSemantics:
    props.sensorData.digitalTwin?.scaleSemantics ||
    'LoD aplikatif proyek: LoD-A tapak, LoD-B bangunan, LoD-C indoor 3D; kepatuhan LoD geometrik standar belum dievaluasi',
  synchronizationMode:
    props.sensorData.digitalTwin?.synchronizationMode ||
    'replay historis berbasis permintaan'
}))

const coordinateLabel = computed(
  () =>
    `${twinContext.value.latitude.toFixed(4)}, ` +
    `${twinContext.value.longitude.toFixed(4)} · ${twinContext.value.crs}`
)
const routeLabel = computed(() =>
  props.sensorData.route === 'cloud' ? 'cloud selektif' : 'edge lokal'
)
const occupancyLabel = computed(() => {
  if (!Number.isFinite(Number(props.peopleCount))) return 'okupansi tidak tersedia'
  return `${Math.trunc(Number(props.peopleCount))} orang · ${
    props.sensorData.occupancyStatus || 'status tidak tersedia'
  }`
})

const formatNumber = (value, digits, unit) => {
  const parsed = Number(value)
  return value !== null && value !== undefined && Number.isFinite(parsed)
    ? `${parsed.toFixed(digits)}${unit}`
    : '—'
}
</script>

<style scoped>
.multiscale-twin {
  display: grid;
  gap: 14px;
}

.scale-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.scale-tabs button {
  border: 1px solid var(--border-dark);
  border-radius: 999px;
  padding: 9px 14px;
  color: var(--text-primary);
  background: var(--bg-secondary);
  cursor: pointer;
  font-weight: 700;
}

.scale-tabs button.active {
  color: white;
  border-color: #0284c7;
  background: #0284c7;
}

.scale-panel {
  min-height: 390px;
  border: 1px solid var(--border-dark);
  border-radius: 18px;
  overflow: hidden;
  background: var(--bg-secondary);
}

.site-panel {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 260px;
  align-items: stretch;
}

.site-panel svg {
  width: 100%;
  height: 100%;
}

.svg-title {
  fill: #0f172a;
  font-size: 17px;
  font-weight: 700;
}

.svg-note {
  fill: #475569;
  font-size: 14px;
}

.panel-facts {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 15px;
  padding: 24px;
  color: var(--text-primary);
  border-left: 1px solid var(--border-dark);
}

.panel-facts span {
  color: var(--text-secondary);
  line-height: 1.45;
}

.building-layout {
  min-height: 390px;
  display: grid;
  grid-template-columns: minmax(0, 2fr) minmax(190px, 1fr);
  gap: 24px;
  padding: 24px;
}

.floor-plan {
  display: grid;
  grid-template-columns: 1.4fr 1fr;
  grid-template-rows: 1fr 1fr;
  gap: 10px;
  padding: 10px;
  border: 4px solid #334155;
  background: #e2e8f0;
}

.room {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 8px;
  padding: 18px;
  border: 2px solid #94a3b8;
  color: #0f172a;
  background: #f8fafc;
}

.room-main {
  grid-row: 1 / span 2;
  background: #dcfce7;
}

.building-flow {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 10px;
  text-align: center;
  color: var(--text-primary);
}

.building-flow span {
  padding: 10px;
  border-radius: 10px;
  background: var(--bg-card);
  border: 1px solid var(--border-dark);
}

.scale-disclaimer {
  margin: 0;
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.5;
}

@media (max-width: 800px) {
  .site-panel,
  .building-layout {
    grid-template-columns: 1fr;
  }

  .panel-facts {
    border-left: 0;
    border-top: 1px solid var(--border-dark);
  }
}
</style>
