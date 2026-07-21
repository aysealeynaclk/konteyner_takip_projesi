import { ref, watch } from 'vue'
import axios from 'axios'
import { logActivity } from './activity'

// Haritadan, chatbot'taki select box'tan ve dashboard'dan ortak okunup
// yazılan liman seçimi. Sayfa yenilenince sıfırlanır (localStorage'a yazılmıyor).
export const selectedFacility = ref(null)

// Herhangi bir yerden (harita tıklaması, chat/dashboard select box'ı) liman
// seçimi değiştiğinde, girişli kullanıcılar için backend'e, misafirler için
// sessionStorage'a "bu limana bakıldı" kaydı düşer.
watch(selectedFacility, (value) => {
  if (value) logActivity('facility_viewed', value)
})

// Aktif bir sohbet (en az 1 mesaj) varken true olur. ChatWidget bunu günceller,
// OceanMap da haritadan liman değiştirilmeye çalışıldığında buna bakar —
// sohbet sürerken liman ne chat içinden ne haritadan değiştirilebilmeli.
export const facilityLocked = ref(false)

export const FACILITY_LABELS = {
  GBZ: 'Gebze Terminali',
  YCT: 'Körfez Terminali',
  ANK: 'Ankara Terminali',
  MXK: 'Marsaxlokk Terminali',
  TKD: 'Takoradi Terminali',
  TAR: 'Taranto Terminali',
  OSL: 'Oslo Terminali',
  GVL: 'Gävle Terminali',
  STO: 'Stockholm Nord Terminali',
  AQJ: 'Acajutla Terminali',
  LUX: 'La Unión Terminali',
  PAI: 'Paita Terminali',
  PBO: 'Puerto Bolívar Terminali',
  PRQ: 'Puerto Quetzal Terminali',
  LIS: 'Liscont Terminali',
  FIG: 'Figueira Da Foz Terminali',
  SOT: 'Sotagus Terminali',
  LEI: 'Leixões Terminali',
  AVE: 'Aveiro Terminali',
  SET: 'Setúbal Terminali',
  TER: 'Tersado Terminali',
  HUE: 'Huelva Terminali',
  FRO: 'Ferrol Terminali',
  ELV: 'Elvas Terminali',
}

export function facilityLabel(code) {
  if (!code) return ''
  const name = FACILITY_LABELS[code]
  return name ? `${name} (${code})` : code
}

// Liman dropdown'unda görsel gruplama: bu koddaki limanlar bir tık daha açık
// renkte gösterilir (Gebze/Körfez/Ankara/Marsaxlokk/Taranto grubuyla aynı
// tonda kalmayıp hafifçe ayrışsınlar diye) — kullanıcının verdiği sıra/gruba göre.
export const LIGHT_SHADE_FACILITIES = new Set([
  'OSL', 'GVL', 'STO', 'PBO', 'PAI', 'PRQ', 'AQJ', 'LUX', 'TKD',
])

export function isLightShadeFacility(code) {
  return LIGHT_SHADE_FACILITIES.has(code)
}

// Haritadan bir liman seçildikten sonra "Chatbot'a Git" tıklandığında ilgili
// sekme adına ('chat' | 'dashboard') çekilir; App.vue bunu izleyip o sekmeye
// geçer, sonra sıfırlar.
export const tabRequested = ref(null)

export function requestTab(tabName) {
  tabRequested.value = tabName
}

export const availableFacilities = ref([])

export async function loadFacilities() {
  try {
    const res = await axios.get('/api/facilities')
    availableFacilities.value = res.data.facilities || []
  } catch (e) {
    console.error('Liman listesi alınamadı:', e)
    availableFacilities.value = []
  }
}
