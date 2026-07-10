<script setup>
import { onMounted, ref, reactive } from 'vue'
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

// Map of portName -> latest weather
const portWeather = reactive({})

// Selected country / details for right-side panel
const selected = reactive({ visible: false, country: null, ports: [] })

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

  // store weather for later use in details panel
  if (weather) portWeather[port.name] = weather

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

  // Load GeoJSON for Corex countries (approximate shapes) and add hover/click interactions
  try {
    const geoResp = await fetch('/src/data/corex_countries.geojson')
    const geoJson = await geoResp.json()

    function defaultStyle() {
      return {
        color: '#1f2937',
        weight: 1,
        fillColor: '#ffffff',
        fillOpacity: 0,
      }
    }

    function highlightStyle() {
      return {
        color: '#0ea5e9',
        weight: 1.5,
        fillColor: '#0ea5e9',
        fillOpacity: 0.45,
      }
    }

    const geoLayer = L.geoJSON(geoJson, {
      style: defaultStyle,
      onEachFeature(feature, layer) {
        layer.on('mouseover', () => {
          layer.setStyle(highlightStyle())
        })
        layer.on('mouseout', () => {
          // don't remove highlight if it's the selected country
          if (!selected.country || selected.country !== feature.properties.name) {
            layer.setStyle(defaultStyle())
          }
        })
        layer.on('click', () => {
          // when clicked, open details panel with ports in this country
          const cname = feature.properties.name
          selected.visible = true
          selected.country = cname
          selected.ports = ports.filter(p => p.country === cname)
          // attach weather info to each port entry
          selected.ports = selected.ports.map(p => ({
            ...p,
            weather: portWeather[p.name] || null,
          }))
          // ensure this feature stays highlighted
          layer.setStyle(highlightStyle())
        })
      }
    }).addTo(map)
  } catch (e) {
    console.error('Corex countries geojson yüklenemedi:', e)
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
  
  <!-- Details panel -->
  <div v-if="selected.visible" class="details-panel">
    <div class="details-header">
      <strong>{{ selected.country }}</strong>
      <button class="close-btn" @click="() => { selected.visible = false; selected.country = null }">✕</button>
    </div>
    <div class="details-body">
      <div v-if="selected.ports.length === 0">Bu ülkede Corex limanı bulunmuyor.</div>
      <div v-for="p in selected.ports" :key="p.name" class="port-detail">
        <div class="port-title">{{ p.name }} — {{ p.country }}</div>
        <div class="port-weather" v-if="p.weather">
          <span class="weather-icon">{{ weatherInfo(p.weather.weathercode).icon }}</span>
          <span>{{ weatherInfo(p.weather.weathercode).label }}</span>
          <span class="temp">{{ Math.round(p.weather.temperature) }}°C</span>
        </div>
        <div v-else class="port-weather">Hava durumu alınamadı.</div>
      </div>
    </div>
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

<style scoped>
.details-panel {
  position: absolute;
  right: 24px;
  top: 80px;
  width: 300px;
  max-height: 60vh;
  overflow: auto;
  background: rgba(6, 44, 67, 0.9);
  color: white;
  border-radius: 12px;
  padding: 12px;
  z-index: 1200;
  border: 1px solid rgba(14,165,233,0.18);
}
.details-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:8px }
.details-body { font-size:0.9rem }
.port-detail { padding:8px 0; border-top:1px dashed rgba(255,255,255,0.04) }
.port-title { font-weight:600 }
.port-weather { margin-top:6px; display:flex; gap:8px; align-items:center }
.weather-icon { font-size:1.1rem }
.temp { opacity:0.85 }
.close-btn { background:none; border:none; color:white; cursor:pointer }
</style>