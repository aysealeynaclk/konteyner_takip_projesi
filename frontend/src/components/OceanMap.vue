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

// Normalize utility and small Turkish->English map (reused in matching)
function normalize(str) {
  if (!str) return ''
  try {
    return str.normalize('NFD').replace(/\p{Diacritic}/gu, '').toLowerCase()
  } catch (e) {
    return str.replace(/[ÇçĞğİıÖöŞşÜü]/g, c => ({ 'Ç':'C','ç':'c','Ğ':'G','ğ':'g','İ':'I','ı':'i','Ö':'O','ö':'o','Ş':'S','ş':'s','Ü':'U','ü':'u' }[c] || c)).toLowerCase()
  }
}

const trToEn = {
  'türkiye': 'turkey',
  'isveç': 'sweden',
  'kazakistan': 'kazakhstan',
  'arnavutluk': 'albania',
  'kolombiya': 'colombia',
  'portekiz': 'portugal',
  'peru': 'peru',
  'ingiltere': 'united kingdom',
  'abd': 'united states',
  'amerika': 'united states',
  'çin': 'china',
  'hindistan': 'india',
}

// Minimal helper to get Turkish display name for a GeoJSON feature
let trDisplay = null
try {
  trDisplay = new Intl.DisplayNames(['tr'], { type: 'region' })
} catch (e) {
  trDisplay = null
}

function getTurkishNameForFeature(feature) {
  if (!feature || !feature.properties) return ''
  const p = feature.properties
  const admin = p.ADMIN || p.NAME || p.name || ''
  const iso2 = (
    p['ISO3166-1-Alpha-2'] ||
    p.ISO_A2 ||
    p.iso_a2 ||
    p['ISO_A2'] ||
    ''
  ).toString().trim()
  if (trDisplay && iso2) {
    try {
      return trDisplay.of(iso2.toUpperCase())
    } catch (e) {}
  }

  const iso3 = (
    p['ISO3166-1-Alpha-3'] ||
    p.ISO_A3 ||
    p.ADM0_A3 ||
    p.iso_a3 ||
    p['ISO_A3'] ||
    ''
  ).toString().trim()
  if (trDisplay && iso3) {
    try {
      return trDisplay.of(iso3.toUpperCase())
    } catch (e) {}
  }

  // Fallback: simple replacements for the most common English names.
  const low = (admin || '').toLowerCase()
  if (low.includes('turkey')) return 'Türkiye'
  if (low.includes('united states')) return 'Amerika Birleşik Devletleri'
  if (low.includes('united kingdom') || low.includes('england')) return 'İngiltere'
  return admin
}

// (no normalized trToEn mapping here)

// (no static Corex country list here — use `ports` for presence checks)

// (removed isCorexAdmin — presence is determined from `ports` array)

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
const selected = reactive({ visible: false, country: null, ports: [], weather: null })

// wrapper ref to allow closing details from template
const _closeDetailsImpl = ref(null)

function closeDetails() {
  if (_closeDetailsImpl.value) _closeDetailsImpl.value()
}

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

    // We use a plain white canvas and draw country vector fills via GeoJSON
    // (no raster tile layer) so the background is neutral and matches design.

  // Konteyner boyutu geç hesaplanmış olabilir, garanti için yeniden ölç
  setTimeout(() => {
    map.invalidateSize()
    console.log('OceanMap: invalidateSize çağrıldı')
  }, 200)

  let stormyCount = 0

  for (const port of ports) {
    // Do NOT add visible markers on the map per user request.
    // Still fetch and store per-port weather for the details panel.
    const weather = await fetchWeather(port)
    if (weather) portWeather[port.name] = weather
    if (weather && STORMY_CODES.includes(weather.weathercode)) {
      stormyCount++
    }
  }
  // Fetch world GeoJSON (public dataset) and render vector countries
  try {
    const resp = await fetch('https://raw.githubusercontent.com/datasets/geo-countries/master/data/countries.geojson')
    const worldGeo = await resp.json()

    // Remove very small island features (tiny polygons) so map is cleaner
    function isLargeFeature(feature) {
      if (!feature || !feature.geometry) return false
      try {
        const tmp = L.geoJSON(feature)
        const b = tmp.getBounds()
        const latSpan = Math.abs(b.getNorth() - b.getSouth())
        const lngSpan = Math.abs(b.getEast() - b.getWest())
        // keep feature if either span is larger than threshold (degrees)
        const THRESH = 0.6
        return latSpan > THRESH || lngSpan > THRESH
      } catch (e) {
        return false
      }
    }

    const filteredFeatures = (worldGeo.features || []).filter(isLargeFeature)
    const filteredGeo = { type: 'FeatureCollection', features: filteredFeatures }

    // simple deterministic blue palette to give countries varying blue shades
    const bluePalette = ['#e6f6ff', '#cff3ff', '#b3ecff', '#99e4ff', '#7edcff', '#62d3ff', '#45c9ff', '#2bbfff', '#12b5ff', '#0599db']

    // (Turkish display names removed — revert to original ADMIN/NAME labels)

    function hashString(s) {
      let h = 2166136261 >>> 0
      for (let i = 0; i < s.length; i++) {
        h ^= s.charCodeAt(i)
        h = Math.imul(h, 16777619) >>> 0
      }
      return h
    }

    function colorForFeature(feature) {
      const key = (feature.properties.ISO_A3 || feature.properties.ADM0_A3 || feature.properties.ADMIN || feature.properties.NAME || '') + ''
      const h = hashString(key)
      return bluePalette[h % bluePalette.length]
    }

    function defaultStyle(feature) {
      return {
        color: '#374151', // dark gray border
        weight: 0.8,
        fillColor: colorForFeature(feature),
        fillOpacity: 1,
      }
    }

    function highlightStyle(feature) {
      return {
        color: '#0b84a5',
        weight: 1.6,
        fillColor: '#0ea5e9',
        fillOpacity: 0.55,
      }
    }

    // Track hovered and selected layers so hover highlight does not stick
    let hoveredLayer = null
    let selectedLayer = null

    const geoLayer = L.geoJSON(filteredGeo, {
      style: defaultStyle,
      onEachFeature(feature, layer) {
        const name = feature.properties.ADMIN || feature.properties.NAME || feature.properties.name

        layer.on('mouseover', () => {
          // reset previous hovered if it's different and not the selected
          if (hoveredLayer && hoveredLayer !== layer && hoveredLayer !== selectedLayer) {
            hoveredLayer.setStyle(defaultStyle(hoveredLayer.feature))
          }
          if (layer !== selectedLayer) {
            layer.setStyle(highlightStyle(layer.feature))
            hoveredLayer = layer
          }
        })

        layer.on('mouseout', () => {
          // revert hover style unless this is the selected layer
          if (layer !== selectedLayer) {
            layer.setStyle(defaultStyle(layer.feature))
            if (hoveredLayer === layer) hoveredLayer = null
          }
        })

        layer.on('click', async () => {
          // clear previous selected layer style
          if (selectedLayer && selectedLayer !== layer) {
            selectedLayer.setStyle(defaultStyle(selectedLayer.feature))
          }
          selectedLayer = layer
          selected.visible = true
          // Display country name in Turkish when available
          selected.country = getTurkishNameForFeature(layer.feature) || name
          // Match ports to the clicked country robustly using top-level normalize and mappings
          const adminName = (layer.feature && (layer.feature.properties.ADMIN || layer.feature.properties.NAME || name)) || name
          const nAdmin = normalize(adminName)
          
          selected.ports = ports.filter(p => {
            const np = normalize(p.country)
            if (np === nAdmin) return true
            if (trToEn[np] && normalize(trToEn[np]) === nAdmin) return true
            if (nAdmin.includes(np) || np.includes(nAdmin)) return true
            // also allow matching via Turkish->English map
            const mapped = trToEn[np]
            if (mapped && normalize(mapped) === nAdmin) return true
            return false
          }).map(p => ({ ...p, weather: portWeather[p.name] || null }))

          // Fetch current weather for country's center (no port coords available)
          try {
            const center = layer.getBounds().getCenter()
            const wres = await fetch(
              `https://api.open-meteo.com/v1/forecast?latitude=${center.lat}&longitude=${center.lng}&current_weather=true`
            )
            const wdata = await wres.json()
            selected.weather = wdata.current_weather || null
          } catch (e) {
            selected.weather = null
          }

          // Ensure highlight stays
          layer.setStyle(highlightStyle(layer.feature))

          // Zoom to country bounds with padding
          try {
            const b = layer.getBounds()
            if (b.isValid()) map.fitBounds(b.pad(0.2), { padding: [20, 20], maxZoom: 6 })
          } catch (e) {
            console.warn('Zoom to bounds failed', e)
          }
        })
      }
    }).addTo(map)

    // Close details helper to clear selected style
    function closeDetails() {
      selected.visible = false
      selected.country = null
      selected.ports = []
      selected.weather = null
      if (selectedLayer) {
        selectedLayer.setStyle(defaultStyle(selectedLayer.feature))
        selectedLayer = null
      }
    }

    // expose closeDetails to template via wrapper ref
    _closeDetailsImpl.value = closeDetails
  } catch (e) {
    console.error('World GeoJSON yüklenemedi:', e)
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
  </div>
  
  <!-- Details panel -->
  <div v-if="selected.visible" class="details-panel">
    <div class="details-header">
      <strong>{{ selected.country }}</strong>
      <button class="close-btn" @click="closeDetails()">✕</button>
    </div>
    <div class="details-body">
      <div v-if="selected.weather" class="country-weather compact" style="margin-bottom:8px;">
        <strong style="display:block; margin-bottom:6px">Genel Hava:</strong>
        <div class="weather-compact-row">
          <span class="weather-icon-small">{{ weatherInfo(selected.weather.weathercode).icon }}</span>
          <span class="weather-text">{{ weatherInfo(selected.weather.weathercode).label }} • {{ Math.round(selected.weather.temperature) }}°C</span>
        </div>
      </div>
      <div v-if="selected.ports.length > 0" class="has-ports">Bu ülkede Corex limanı bulunmakta.</div>
      <div v-else class="no-ports">Bu ülkede Corex limanı bulunmuyor.</div>
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
  z-index: 0; /* restore map stacking so it's visible while UI elements stay above */
  background-color: #ffffff; /* white canvas as requested */
}

.map-container {
  width: 100%;
  height: 100%;
  background: transparent;
}

.vignette {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 400;
  background: radial-gradient(ellipse at center, transparent 60%, rgba(2, 10, 22, 0.04) 100%);
}



/* removed decorative particle and wave animations for a cleaner, professional map */

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
  box-shadow: 0 0 0 2px rgba(34, 211, 238, 0.18);
}

/* pulse animation removed for static markers */

.custom-tooltip {
  background: rgba(6, 44, 67, 0.92) !important;
  border: 1px solid #38bdf8 !important;
  color: white !important;
  border-radius: 8px !important;
  padding: 4px 4px !important;
}

.country-label.leaflet-tooltip {
  background: rgba(6,44,67,0.9);
  color: #e6f6ff;
  border: 1px solid rgba(14,165,233,0.16);
  padding: 4px 8px;
  border-radius: 6px;
  font-size: 0.85rem;
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
  position: fixed;
  left: 16px; /* pin to top-left corner */
  top: 16px;
  right: auto;
  width: 360px;
  max-width: calc(100vw - 32px);
  max-height: calc(100vh - 32px);
  overflow: auto;
  background: rgba(6, 44, 67, 0.98);
  color: white;
  border-radius: 12px;
  padding: 12px;
  z-index: 1600; /* ensure it's above all UI */
  border: 1px solid rgba(14,165,233,0.18);
  box-shadow: 0 12px 36px rgba(2,6,23,0.35);
}

.country-weather-row { display:flex; gap:10px; align-items:center }
.weather-icon-large { font-size:1.6rem }
.country-weather-text { line-height:1 }
.weather-main { font-weight:600 }
.weather-sub { opacity:0.85; font-size:0.9rem }
.no-ports { color: rgba(255,255,255,0.75) }

.has-ports { color: #bbf7d0; font-weight:600; margin-bottom:8px }

/* Compact weather */
.weather-compact-row { display:flex; gap:8px; align-items:center }
.weather-icon-small { font-size:1.05rem; line-height:1 }

.corex-list { list-style:none; padding:6px; margin:0; max-height:150px; overflow:auto; display:flex; flex-wrap:wrap; gap:6px }
.corex-list li { background: rgba(255,255,255,0.04); padding:6px 8px; border-radius:8px; font-size:0.86rem }
.corex-list li.highlight { background: rgba(187,247,208,0.12); color: #bbf7d0; font-weight:700 }

.weather-text { font-size:0.95rem; opacity:0.95 }

/* Ensure details panel stays within viewport */
@media (max-width: 900px) {
  .details-panel { left: 12px; right: 12px; width: auto; top: 64px; }
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