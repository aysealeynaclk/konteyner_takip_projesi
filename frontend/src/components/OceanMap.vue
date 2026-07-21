<script setup>
import { onMounted, ref, reactive, watch } from 'vue'
import axios from 'axios'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { t, countryName } from '../i18n'
import { selectedFacility, facilityLocked, requestTab, availableFacilities, loadFacilities, facilityLabel, isLightShadeFacility } from '../facility'

const props = defineProps({
  // Harita artık her zaman tam ekran değil, "Harita" sekmesi seçiliyken
  // görünür oluyor (v-show). Sekme aktif olduğunda Leaflet'in boyutunu
  // yeniden hesaplaması gerekiyor, çünkü gizliyken (display:none) container
  // boyutu 0 olarak ölçülmüş olabilir.
  isActive: { type: Boolean, default: true },
})

// Chatbot sadece girişli kullanıcılar için aktif; misafirken "artık chatbotta
// sorabilirsiniz" mesajı yanıltıcı olur, o yüzden gösterilmez.
const isLoggedIn = !!localStorage.getItem('corex_token')

// Haritadaki liman adından gerçek facility_id'ye eşleme. Şimdilik sadece
// gerçek konteyner verisi olan Gebze (GBZ), Körfez (YCT) ve Ankara (ANK) tıklanabilir.
const PORT_NAME_TO_FACILITY = {
  Gebze: 'GBZ', Körfez: 'YCT', Ankara: 'ANK',
  Marsaxlokk: 'MXK', Takoradi: 'TKD', Taranto: 'TAR',
  Oslo: 'OSL', Gävle: 'GVL', 'Stockholm Nord': 'STO',
  Acajutla: 'AQJ', 'La Unión': 'LUX', Paita: 'PAI',
  'Puerto Bolívar': 'PBO', 'YILPORT Quetzal': 'PRQ',
  Liscont: 'LIS', 'Figueira Da Foz': 'FIG', Sotagus: 'SOT',
  'Leixões': 'LEI', Aveiro: 'AVE', 'Setúbal': 'SET',
  Tersado: 'TER', Huelva: 'HUE', Ferrol: 'FRO', Elvas: 'ELV',
}

// Ters eşleme: facility_id -> harita liman adı (dropdown'dan ülkeye odaklanmak için)
const FACILITY_TO_PORT_NAME = Object.fromEntries(
  Object.entries(PORT_NAME_TO_FACILITY).map(([name, code]) => [code, name])
)

// Ülkenin Türkçe adından o ülkenin Leaflet katmanına — dropdown'dan seçilen
// limanın ülkesini programatik olarak "tıklamak" (odaklamak) için kullanılır.
let countryLayerByTrName = {}

// Dropdown'dan liman değişince önce dünya görünümüne dönüp sonra yeni limana
// uçmak için (bkz. focusOnFacility) harita referansı burada da tutulur.
let mapInstance = null

const lockedNotice = ref(false)

function selectFacility(code) {
  // Aktif bir sohbet varken (en az 1 mesaj) liman haritadan da değiştirilemez —
  // ChatWidget bu kilidi facility.js üzerinden günceller.
  if (facilityLocked.value) {
    lockedNotice.value = true
    setTimeout(() => { lockedNotice.value = false }, 3000)
    return
  }
  selectedFacility.value = code
}

// Dropdown'dan bir liman seçildiğinde: haritayı o ülkeye odaklar (tıklamayla
// aynı davranış — detay paneli, zoom, hava durumu) ve limanı seçili yapar.
// Bir ülkeden diğerine ani sıçramak yerine önce tüm dünya görünümüne dönüp
// oradan yeni limana doğru akıcı bir geçişle gidiyor.
// Not: burada bilerek flyTo değil setView(animate) kullanılıyor — flyTo'nun
// "uçuş" eğrisi uzak mesafelerde zoom'u hedeften daha da aşağı düşürüp
// (minZoom'un altına inip) harita bir an gerçek boyutunun çok altında,
// sanki yavaş/bozuk yükleniyormuş gibi görünmesine yol açıyordu.
function focusOnFacility(code) {
  if (!code) return
  const portName = FACILITY_TO_PORT_NAME[code]
  const countryEntry = countries.value.find(c => c.name === portName)
  const layer = countryEntry ? countryLayerByTrName[countryEntry.country] : null

  selectFacility(code)

  if (!layer || !mapInstance) return

  function triggerZoomIn() {
    layer.fire('click')
    // Animasyon zincirinin ortasında sekme odağının kaybolması gibi
    // durumlarda Leaflet'in iç boyut/pozisyon hesabı gerçek DOM ile
    // senkronize kalmayabiliyor (harita bir yerde "takılı" kalmış gibi
    // görünüyor, elle sürükleyince düzeliyordu). invalidateSize bunu her
    // seferinde zorla yeniden hesaplatıp düzeltir.
    setTimeout(() => mapInstance.invalidateSize(), 1100)
  }

  // Harita zaten tam bu dünya görünümündeyse (örn. ilk seçim — henüz hiçbir
  // ülkeye yakınlaşılmamışken) setView'in hedefi mevcut görünümle birebir
  // aynı olur ve Leaflet bu durumda 'moveend' HİÇ tetiklemiyor (no-op kabul
  // ediyor). Bu durumda "dünyaya dönüş" animasyonuna hiç gerek yok — direkt,
  // kısa bir bekleme sonrası yeni limana geçilir (7 saniye boşuna beklenmez).
  if (isAtWorldView(mapInstance)) {
    setTimeout(triggerZoomIn, 700)
    return
  }

  let triggered = false
  function triggerOnce() {
    if (triggered) return
    triggered = true
    setTimeout(triggerZoomIn, 700)
  }

  resetWorldView(mapInstance, { animate: true, duration: 6 })
  mapInstance.once('moveend', triggerOnce)
  // Gerçek bir hareket olduğu hâlde beklenmedik şekilde 'moveend' gelmezse
  // diye yedek zamanlayıcı (bu artık sadece güvenlik ağı, normalde tetiklenmez).
  setTimeout(triggerOnce, 6200)
}

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

const MAP_CENTER = [25, 10]
const MAP_ZOOM = 2

// Dünya görünümü artık sabit bir zoom seviyesiyle değil, bu sınırların
// container'ın gerçek genişliğine/yüksekliğine göre otomatik sığdırılmasıyla
// (fitBounds) hesaplanıyor — sabit zoom, geniş ekranlarda dünyayı olduğundan
// küçük (ortada, etrafı boş mavi) gösteriyordu.
const WORLD_BOUNDS = [[-58, -180], [78, 180]]

// map.fitBounds(WORLD_BOUNDS) kullanmak yerine bilerek getBoundsZoom+setView
// birleşimi kullanılıyor: WORLD_BOUNDS tam -180/180 boylamını kapsadığı için
// fitBounds'un kendi merkez hesabı, worldCopyJump ile birleşince haritayı
// bazen çok uzak bir "tekrar kopyasına" kaydırıp orada bırakabiliyordu
// (harita sola/sağa kayıp geri gelmiyordu). Burada zoom seviyesi bounds'tan
// hesaplanır ama merkez her zaman sabit, bilinen MAP_CENTER'a ayarlanır.
function resetWorldView(map, options) {
  const zoom = map.getBoundsZoom(WORLD_BOUNDS)
  map.setView(MAP_CENTER, zoom, options)
}

// Harita şu an zaten (aşağı yukarı) dünya görünümünde mi? Öyleyse
// resetWorldView'in setView çağrısı no-op olur ve 'moveend' hiç
// tetiklenmez — bu kontrol, o durumda boşuna beklememek için kullanılır.
function isAtWorldView(map) {
  const targetZoom = map.getBoundsZoom(WORLD_BOUNDS)
  const center = map.getCenter()
  return (
    Math.abs(center.lat - MAP_CENTER[0]) < 0.5 &&
    Math.abs(center.lng - MAP_CENTER[1]) < 0.5 &&
    Math.abs(map.getZoom() - targetZoom) < 0.1
  )
}

onMounted(async () => {
  console.log('OceanMap: harita başlatılıyor...')
  loadFacilities()

  const map = L.map(mapContainer.value, {
    center: MAP_CENTER,
    zoom: MAP_ZOOM,
    minZoom: 2,
    maxZoom: 5,
    worldCopyJump: true,
    zoomControl: false,
    // maxBounds, worldCopyJump ile birlikte kullanılınca Leaflet'te bilinen bir
    // çakışmaya yol açıyor (bir yöne kayınca ters yöne dönememe gibi). Bu yüzden
    // maxBounds hiç kullanılmıyor; dikey sınır aşağıda 'moveend' olayıyla elle
    // uygulanıyor (worldCopyJump'ın yatay mantığına hiç dokunmadan).
  })
  mapInstance = map

  L.control.zoom({ position: 'bottomleft' }).addTo(map)

  // Dikeyde kutupların ötesine sonsuz kaydırılmasını engeller — maxBounds
  // yerine elle: enlem sınırı aşılırsa sadece enlemi geri çeker, boylama
  // (worldCopyJump'ın yönettiği eksene) dokunmaz.
  const MAX_LAT = 60
  map.on('moveend', () => {
    const center = map.getCenter()
    if (center.lat > MAX_LAT || center.lat < -MAX_LAT) {
      const clampedLat = Math.max(-MAX_LAT, Math.min(MAX_LAT, center.lat))
      map.panTo([clampedLat, center.lng], { animate: false })
    }
  })

    // We use a plain white canvas and draw country vector fills via GeoJSON
    // (no raster tile layer) so the background is neutral and matches design.

  // Harita "Harita" sekmesi henüz seçili değilken (gizli/display:none)
  // mount olabiliyor; o an container boyutu 0 ölçüldüğü için Leaflet'in
  // merkez hesabı bozuluyor. Sadece invalidateSize yetmiyor, container GERÇEKTEN
  // görünür olduğu ilk anda merkezi de elle geri vermek gerekiyor — ama SADECE
  // ilk seferde, yoksa kullanıcının sonradan yaptığı zoom/pan her sekme
  // değişiminde sıfırlanır.
  let hasFixedInitialView = false
  watch(() => props.isActive, (active) => {
    if (!active) return
    setTimeout(() => {
      map.invalidateSize()
      if (!hasFixedInitialView) {
        resetWorldView(map, { animate: false })
        hasFixedInitialView = true
      }
    }, 50)
  }, { immediate: true })

  await loadCountries()

  // Fetch world GeoJSON (public dataset) and render vector countries
  try {
    const resp = await fetch('https://raw.githubusercontent.com/datasets/geo-countries/master/data/countries.geojson')
    const worldGeo = await resp.json()

    // Remove very small island features (tiny polygons) so map is cleaner
    function isLargeFeature(feature) {
      if (!feature || !feature.geometry) return false
      try {
        // Limanı olan ülkeler (örn. Malta/Marsaxlokk) çok küçük olsa da
        // haritada kalmalı — yoksa dropdown'dan seçilince odaklanacak bir
        // katman bulunamıyor.
        const trName = getTurkishNameForFeature(feature)
        const hasPort = countries.value.some(c => c.has_port && normalize(c.country) === normalize(trName))
        if (hasPort) return true

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

        // Dropdown'dan liman seçilince o ülkenin katmanına programatik
        // erişebilmek için Türkçe ad -> katman eşlemesini kaydet.
        const trNameForLookup = getTurkishNameForFeature(feature) || name
        countryLayerByTrName[trNameForLookup] = layer

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
            if (b.isValid()) map.fitBounds(b.pad(0.2), { padding: [20, 20], maxZoom: 6, animate: true, duration: 1 })
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
  <!-- Tek kök eleman: v-show ile görünürlük burada kontrol edilir (App.vue
  'Harita' sekmesi seçili olmadığında bunu gizler). Component'in birden fazla
  kök elemanı olsaydı v-show sadece ilkine uygulanırdı. -->
  <div class="map-tab-root" v-show="isActive">
    <div class="map-wrapper">
      <div ref="mapContainer" class="map-container"></div>
      <div class="vignette"></div>
    </div>

    <!-- Liman dropdown: seçilince o ülkeye odaklanır (tıklamayla aynı davranış) -->
    <div class="port-dropdown">
      <select :value="selectedFacility || ''" @change="focusOnFacility($event.target.value)">
        <option value="">{{ t('mapSelectPort') }}</option>
        <option
          v-for="fac in availableFacilities"
          :key="fac"
          :value="fac"
          :class="{ 'option-light-shade': isLightShadeFacility(fac) }"
        >{{ facilityLabel(fac) }}</option>
      </select>
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
          <li v-for="(p, idx) in selected.ports.filter(p => p.name)" :key="idx">
            <button
              v-if="PORT_NAME_TO_FACILITY[p.name]"
              class="port-facility-link"
              :class="{ active: selectedFacility === PORT_NAME_TO_FACILITY[p.name] }"
              :title="t('facilitySelectHint')"
              @click="selectFacility(PORT_NAME_TO_FACILITY[p.name])"
            >📍 {{ p.name }} <span v-if="selectedFacility === PORT_NAME_TO_FACILITY[p.name]">✅</span></button>
            <span v-else>📍 {{ p.name }}</span>
          </li>
        </ul>
        <p v-if="lockedNotice" class="facility-locked-notice">{{ t('facilityLockedNotice') }}</p>
        <template v-if="selected.ports.some(p => selectedFacility === PORT_NAME_TO_FACILITY[p.name])">
          <p v-if="isLoggedIn" class="facility-confirm">{{ t('facilitySelectedInfo') }}</p>
          <button v-if="isLoggedIn" class="open-dashboard-btn" @click="requestTab('chat')">{{ t('openChatFromMap') }}</button>
        </template>
      </div>
      <div v-else class="no-ports">{{ t('noPort') }}</div>
    </div>
    </div>
  </div>
</template>

<style scoped>
.map-tab-root {
  position: absolute;
  inset: 0;
}

.map-wrapper {
  position: absolute;
  inset: 0;
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
/* Leaflet'in animasyonlu zoom/pan hareketi varsayılan olarak ease-out
   (cubic-bezier(0,0,0.25,1)) kullanıyor — anında tam hızda başlayıp sona
   doğru yavaşlıyor, bu da sert/mekanik bir sıçrama gibi hissettiriyor.
   Dropdown'dan liman değişiminde (bkz. focusOnFacility) daha yumuşak
   başlayıp yumuşak biten bir his için ease-in-out'a çeviriyoruz. */
.leaflet-zoom-anim .leaflet-zoom-animated {
  transition-timing-function: cubic-bezier(0.45, 0, 0.2, 1) !important;
}

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
.port-dropdown {
  position: absolute;
  top: 16px;
  right: 16px;
  z-index: 1500;
}

.port-dropdown select {
  color-scheme: dark;
  background: rgba(6, 44, 67, 0.9);
  color: #ffffff;
  border: 1px solid rgba(14, 165, 233, 0.3);
  border-radius: 10px;
  padding: 0.55rem 0.8rem;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  outline: none;
  box-shadow: 0 8px 24px rgba(2, 6, 23, 0.35);
}

.port-dropdown select option {
  color: #ffffff;
  background: #0c2438;
}

/* Bazı limanlar (bkz. facility.js LIGHT_SHADE_FACILITIES) listede bir tık
   daha açık renkle gösterilir, gruplar görsel olarak ayrışsın diye. */
.port-dropdown select option.option-light-shade {
  background: #1d3346;
}

.details-panel {
  position: absolute;
  left: 16px; /* pin to top-left corner of the map tab area */
  top: 16px;
  right: auto;
  width: 360px;
  max-width: calc(100% - 32px);
  max-height: calc(100% - 32px);
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

.port-facility-link {
  background: none;
  border: none;
  color: inherit;
  font: inherit;
  cursor: pointer;
  padding: 0;
  text-decoration: underline dotted;
}
.port-facility-link.active { text-decoration: none; color: #bbf7d0; }
.facility-confirm { color: #bbf7d0; font-size: 0.85rem; margin: 6px 0 0; font-weight: 600; }
.facility-locked-notice { color: #fca5a5; font-size: 0.85rem; margin: 6px 0 0; font-weight: 600; }

.open-dashboard-btn {
  margin-top: 8px;
  background: rgba(34, 211, 238, 0.18);
  border: 1px solid rgba(34, 211, 238, 0.4);
  color: #e0f7fb;
  padding: 6px 12px;
  border-radius: 8px;
  font-size: 0.82rem;
  cursor: pointer;
}
.open-dashboard-btn:hover { background: rgba(34, 211, 238, 0.3); }

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
  .port-dropdown { top: 10px; right: 10px; }
  .port-dropdown select { padding: 0.4rem 0.6rem; font-size: 0.78rem; }
}
.details-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:8px }
.details-body { font-size:0.9rem }
.close-btn { background:none; border:none; color:white; cursor:pointer }
</style>