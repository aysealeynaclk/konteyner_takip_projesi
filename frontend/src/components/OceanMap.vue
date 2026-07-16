<script setup>
import { onMounted, ref, reactive } from 'vue'
import axios from 'axios'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { t, countryName } from '../i18n'

const mapContainer = ref(null)

// Corex'in takip ettiği 55 ülke (7'sinde liman var), backend'deki `ports`
// tablosundan çekilir — artık burada sabit (hardcoded) liste tutulmuyor.
const countries = ref([])

async function loadCountries() {
  try {
    const res = await axios.get('/api/countries')
    countries.value = res.data.countries || []
  } catch (e) {
    console.error('Ülke listesi alınamadı:', e)
    countries.value = []
  }
}

// Normalize utility (diacritics stripped, lowercase) reused in matching
function normalize(str) {
  if (!str) return ''
  try {
    return str.normalize('NFD').replace(/\p{Diacritic}/gu, '').toLowerCase()
  } catch (e) {
    return str.replace(/[ÇçĞğİıÖöŞşÜü]/g, c => ({ 'Ç':'C','ç':'c','Ğ':'G','ğ':'g','İ':'I','ı':'i','Ö':'O','ö':'o','Ş':'S','ş':'s','Ü':'U','ü':'u' }[c] || c)).toLowerCase()
  }
}

// GeoJSON'daki İngilizce ülke adını (ADMIN alanı) bizim 55 ülkelik Türkçe
// listemizdeki karşılığına eşler. Intl.DisplayNames'e göre daha güvenilir
// çünkü Kazakistan gibi ülkelerde tarayıcıya göre Türkçe/İngilizce
// tutarsızlığı yaşanmıyor — burada tek, sabit bir doğru kaynak var.
const enToTr = {
  'canada': 'Kanada',
  'united states of america': 'Amerika Birleşik Devletleri',
  'united states': 'Amerika Birleşik Devletleri',
  'mexico': 'Meksika',
  'guatemala': 'Guatemala',
  'el salvador': 'El Salvador',
  'honduras': 'Honduras',
  'costa rica': 'Kosta Rika',
  'panama': 'Panama',
  'colombia': 'Kolombiya',
  'ecuador': 'Ekvador',
  'peru': 'Peru',
  'brazil': 'Brezilya',
  'chile': 'Şili',
  'argentina': 'Arjantin',
  'uruguay': 'Uruguay',
  'norway': 'Norveç',
  'finland': 'Finlandiya',
  'sweden': 'İsveç',
  'lithuania': 'Litvanya',
  'netherlands': 'Hollanda',
  'belgium': 'Belçika',
  'denmark': 'Danimarka',
  'united kingdom': 'İngiltere',
  'ireland': 'İrlanda',
  'france': 'Fransa',
  'switzerland': 'İsviçre',
  'spain': 'İspanya',
  'portugal': 'Portekiz',
  'kosovo': 'Kosova',
  'north macedonia': 'Kuzey Makedonya',
  'macedonia': 'Kuzey Makedonya',
  'serbia': 'Sırbistan',
  'republic of serbia': 'Sırbistan',
  'italy': 'İtalya',
  'malta': 'Malta',
  'greece': 'Yunanistan',
  'albania': 'Arnavutluk',
  'morocco': 'Fas',
  'ghana': 'Gana',
  'ivory coast': 'Fildişi Sahili',
  "cote d'ivoire": 'Fildişi Sahili',
  'zambia': 'Zambiya',
  'angola': 'Angola',
  'namibia': 'Namibya',
  'mozambique': 'Mozambik',
  'zimbabwe': 'Zimbabve',
  'malawi': 'Malavi',
  'tanzania': 'Tanzanya',
  'united republic of tanzania': 'Tanzanya',
  'kazakhstan': 'Kazakistan',
  'uzbekistan': 'Özbekistan',
  'turkey': 'Türkiye',
  'türkiye': 'Türkiye',
  'china': 'Çin',
  "people's republic of china": 'Çin',
  'bangladesh': 'Bangladeş',
  'india': 'Hindistan',
  'vietnam': 'Vietnam',
  'viet nam': 'Vietnam',
  'thailand': 'Tayland',
  'singapore': 'Singapur',
  'indonesia': 'Endonezya',
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

  // Önce kendi 55 ülkelik listemize bak (tarayıcıdan bağımsız, tutarlı sonuç).
  const mapped = enToTr[normalize(admin)]
  if (mapped) return mapped

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

function weatherInfo(code) {
  if (code === 0) return { icon: '☀️', label: t('weatherClear') }
  if ([1, 2, 3].includes(code)) return { icon: '⛅', label: t('weatherPartlyCloudy') }
  if ([45, 48].includes(code)) return { icon: '🌫️', label: t('weatherFoggy') }
  if ([51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82].includes(code)) return { icon: '🌧️', label: t('weatherRainy') }
  if ([71, 73, 75, 77, 85, 86].includes(code)) return { icon: '❄️', label: t('weatherSnowy') }
  if ([95, 96, 99].includes(code)) return { icon: '⛈️', label: t('weatherStormy') }
  return { icon: '🌊', label: t('weatherUnknown') }
}

// Selected country / details for right-side panel.
// `trName` her zaman Türkçe (DB eşleştirmesi için); ekranda `countryName(trName)`
// ile o an seçili dile göre gösterilir.
const selected = reactive({ visible: false, trName: null, ports: [], weather: null })

// wrapper ref to allow closing details from template
const _closeDetailsImpl = ref(null)

function closeDetails() {
  if (_closeDetailsImpl.value) _closeDetailsImpl.value()
}

onMounted(async () => {
  console.log('OceanMap: harita başlatılıyor...')

  const map = L.map(mapContainer.value, {
    center: [25, 10],
    zoom: 2,
    minZoom: 2,
    maxZoom: 5,
    worldCopyJump: true,
    zoomControl: false,
    // Dikeyde dünyanın dışına (kutupların ötesine) sonsuz kaydırılmasını engeller.
    // Yatayda geniş bırakıldı ki worldCopyJump'ın döngüsel kaydırması bozulmasın.
    maxBounds: [[-85, -1000], [85, 1000]],
    maxBoundsViscosity: 1.0,
  })

  L.control.zoom({ position: 'bottomleft' }).addTo(map)

    // We use a plain white canvas and draw country vector fills via GeoJSON
    // (no raster tile layer) so the background is neutral and matches design.

  // Konteyner boyutu geç hesaplanmış olabilir, garanti için yeniden ölç
  setTimeout(() => {
    map.invalidateSize()
    console.log('OceanMap: invalidateSize çağrıldı')
  }, 200)

  await loadCountries()

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

    function defaultStyle() {
      return {
        color: '#c7d6e3', // ülkeler arası ince açık gri-mavi sınır
        weight: 0.7,
        fillColor: '#ffffff',
        fillOpacity: 1,
      }
    }

    function highlightStyle() {
      return {
        color: '#051627', // sitenin en koyu tonu (login arka planıyla aynı)
        weight: 1.2,
        fillColor: '#0c4a6e', // sitenin imza lacivert-teal rengi (giriş sayfası, butonlar)
        fillOpacity: 1,
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
          // Eşleştirme ve DB sorgusu her zaman Türkçe ad üzerinden yapılır;
          // ekranda gösterilecek ad `countryName()` ile dile göre çevrilir.
          selected.trName = getTurkishNameForFeature(layer.feature) || name
          const nCountry = normalize(selected.trName)
          selected.ports = countries.value
            .filter(c => c.has_port && normalize(c.country) === nCountry)

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
      selected.trName = null
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
      <strong>{{ countryName(selected.trName) }}</strong>
      <button class="close-btn" @click="closeDetails()">✕</button>
    </div>
    <div class="details-body">
      <div v-if="selected.weather" class="country-weather compact" style="margin-bottom:8px;">
        <strong style="display:block; margin-bottom:6px">{{ t('generalWeather') }}</strong>
        <div class="weather-compact-row">
          <span class="weather-icon-small">{{ weatherInfo(selected.weather.weathercode).icon }}</span>
          <span class="weather-text">{{ weatherInfo(selected.weather.weathercode).label }} • {{ Math.round(selected.weather.temperature) }}°C</span>
        </div>
      </div>
      <div v-if="selected.ports.length > 0" class="has-ports">
        <div>{{ t('hasPort') }}</div>
        <ul v-if="selected.ports.some(p => p.name)" class="corex-list">
          <li v-for="(p, idx) in selected.ports.filter(p => p.name)" :key="idx">📍 {{ p.name }}</li>
        </ul>
      </div>
      <div v-else class="no-ports">{{ t('noPort') }}</div>
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
  background: linear-gradient(180deg, #eaf4fc 0%, #d5ebfb 45%, #bfe0f7 100%); /* açık mavi deniz */
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
.leaflet-control-attribution {
  font-size: 9px !important;
  background: rgba(6, 44, 67, 0.7) !important;
  color: #cbd5e1 !important;
}

.leaflet-control-attribution a {
  color: #7dd3fc !important;
}

/* Mobil: zoom +/- butonları parmakla dokunmak için biraz büyüsün */
@media (max-width: 600px) {
  .leaflet-control-zoom a {
    width: 36px !important;
    height: 36px !important;
    line-height: 36px !important;
    font-size: 18px !important;
  }
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
.close-btn { background:none; border:none; color:white; cursor:pointer }
</style>