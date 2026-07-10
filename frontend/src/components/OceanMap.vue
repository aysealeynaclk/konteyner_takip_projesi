<script setup>
import { onMounted, ref } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

const mapContainer = ref(null)
const waveSpeed = ref(8)

const ports = [
  { name: 'Aktau', country: 'Kazakistan', lat: 43.65, lng: 51.20 },
  { name: 'Durrës', country: 'Arnavutluk', lat: 41.31, lng: 19.45 },
  { name: 'Cartagena', country: 'Kolombiya', lat: 10.39, lng: -75.51 },
  { name: 'Göteborg', country: 'İsveç', lat: 57.71, lng: 11.97 },
  { name: 'Lizbon', country: 'Portekiz', lat: 38.72, lng: -9.14 },
  { name: 'Kocaeli', country: 'Türkiye', lat: 40.85, lng: 29.88 },
  { name: 'Callao', country: 'Peru', lat: -12.05, lng: -77.13 },
]

function weatherInfo(code) {
  if (code === 0) return { icon: '☀️', label: 'Açık' }
  if ([1, 2, 3].includes(code)) return { icon: '⛅', label: 'Parçalı Bulutlu' }
  if ([45, 48].includes(code)) return { icon: '🌫️', label: 'Sisli' }
  if ([51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82].includes(code)) return { icon: '🌧️', label: 'Yağmurlu' }
  if ([71, 73, 75, 77, 85, 86].includes(code)) return { icon: '❄️', label: 'Karlı' }
  if ([95, 96, 99].includes(code)) return { icon: '⛈️', label: 'Fırtınalı' }
  return { icon: '🌊', label: 'Bilinmiyor' }
}

const STORMY_CODES = [61, 63, 65, 66, 67, 80, 81, 82, 95, 96, 99]

async function fetchWeather(port) {
  try {
    const res = await fetch(
      `https://api.open-meteo.com/v1/forecast?latitude=${port.lat}&longitude=${port.lng}&current_weather=true`
    )
    const data = await res.json()
    return data.current_weather
  } catch (e) {
    console.error('Hava durumu alınamadı:', e)
    return null
  }
}

function createPortIcon() {
  return L.divIcon({
    className: 'port-marker',
    html: `<div class="port-dot"></div>`,
    iconSize: [16, 16],
  })
}

function particleStyle(n) {
  const left = (n * 37) % 100
  const top = (n * 53) % 100
  const delay = (n % 10) * 0.7
  const duration = 4 + (n % 5)
  return {
    left: left + '%',
    top: top + '%',
    animationDelay: delay + 's',
    animationDuration: duration + 's',
  }
}

onMounted(async () => {
  console.log('OceanMap: harita başlatılıyor...')

  const map = L.map(mapContainer.value, {
    center: [25, 10],
    zoom: 2,
    minZoom: 2,
    maxZoom: 10,
    worldCopyJump: true,
    zoomControl: false,
  })

  L.control.zoom({ position: 'bottomleft' }).addTo(map)

  const tileLayer = L.tileLayer(
    'https://server.arcgisonline.com/ArcGIS/rest/services/Ocean/World_Ocean_Base/MapServer/tile/{z}/{y}/{x}',
    {
      attribution: 'Tiles &copy; Esri',
      maxZoom: 10,
    }
  )

  tileLayer.on('load', () => console.log('OceanMap: karolar yüklendi ✅'))
  tileLayer.on('tileerror', (e) => console.error('OceanMap: karo hatası ❌', e))

  tileLayer.addTo(map)

  // Konteyner boyutu geç hesaplanmış olabilir, garanti için yeniden ölç
  setTimeout(() => {
    map.invalidateSize()
    console.log('OceanMap: invalidateSize çağrıldı')
  }, 200)

  let stormyCount = 0

  for (const port of ports) {
    const marker = L.marker([port.lat, port.lng], { icon: createPortIcon() }).addTo(map)
    const weather = await fetchWeather(port)

    if (weather) {
      const { icon, label } = weatherInfo(weather.weathercode)
      const temp = Math.round(weather.temperature)

      marker.bindTooltip(
        `<div class="port-tooltip">
          <strong>${port.name}</strong>, ${port.country}<br/>
          ${icon} ${label} • ${temp}°C
        </div>`,
        { direction: 'top', offset: [0, -8], className: 'custom-tooltip' }
      )

      if (STORMY_CODES.includes(weather.weathercode)) {
        stormyCount++
      }
    }
  }

  if (stormyCount > 0) {
    waveSpeed.value = Math.max(3, 8 - stormyCount * 1.5)
  }
})
</script>

<template>
   <div class="map-wrapper">
    <div ref="mapContainer" class="map-container"></div>
    <div class="vignette"></div>
    <div class="particles">
      <span v-for="n in 25" :key="n" class="particle" :style="particleStyle(n)"></span>
    </div>
    <svg class="wave-layer" :style="{ '--wave-duration': waveSpeed + 's' }" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <pattern id="ripple-pattern" x="0" y="0" width="140" height="50" patternUnits="userSpaceOnUse">
          <path d="M0,25 Q35,5 70,25 T140,25" fill="none" stroke="#bae6fd" stroke-width="1.5" opacity="0.5" />
          <path d="M0,38 Q35,18 70,38 T140,38" fill="none" stroke="#e0f2fe" stroke-width="1" opacity="0.3" />
        </pattern>
      </defs>
      <rect class="ripple-rect" x="0" y="0" width="100%" height="100%" fill="url(#ripple-pattern)" />
    </svg>
  </div>
</template>

<style scoped>
.map-wrapper {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  width: 100vw;
  height: 100vh;
  z-index: 0;
  background-color: #0a2e4d;
}

.map-container {
  width: 100%;
  height: 100%;
  filter: saturate(0.5) brightness(0.85);
}

.vignette {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 400;
  background: radial-gradient(ellipse at center, transparent 40%, rgba(2, 10, 22, 0.6) 100%);
}

.particles {
  position: absolute;
  inset: 0;
  pointer-events: none;
  overflow: hidden;
  z-index: 401;
}

.particle {
  position: absolute;
  width: 2px;
  height: 2px;
  border-radius: 50%;
  background: #7dd3fc;
  animation-name: twinkle;
  animation-iteration-count: infinite;
  animation-timing-function: ease-in-out;
}

.wave-layer {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  mix-blend-mode: screen;
  opacity: 0.18;
  z-index: 402;
}

.ripple-rect {
  animation: ripple-flow var(--wave-duration, 8s) linear infinite;
}

@keyframes ripple-flow {
  from { transform: translateX(0); }
  to   { transform: translateX(-140px); }
}

@keyframes twinkle {
  0%, 100% { opacity: 0; transform: scale(0.5); }
  50% { opacity: 0.8; transform: scale(1.5); }
}

</style>

<style>
.port-marker {
  background: transparent;
  border: none;
}

.port-dot {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: #22d3ee;
  box-shadow: 0 0 0 4px rgba(34, 211, 238, 0.3), 0 0 12px rgba(34, 211, 238, 0.9);
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.25); }
}

.custom-tooltip {
  background: rgba(6, 44, 67, 0.92) !important;
  border: 1px solid #38bdf8 !important;
  color: white !important;
  border-radius: 8px !important;
  padding: 4px 4px !important;
}

.port-tooltip {
  font-family: 'Segoe UI', sans-serif;
  font-size: 0.8rem;
  line-height: 1.4;
}

.leaflet-control-attribution {
  font-size: 9px !important;
  background: rgba(6, 44, 67, 0.7) !important;
  color: #cbd5e1 !important;
}

.leaflet-control-attribution a {
  color: #7dd3fc !important;
}
</style>