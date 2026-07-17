import { ref } from 'vue'
import axios from 'axios'

// Haritadan ve chatbot'taki select box'tan ortak okunup yazılan liman
// seçimi. Sayfa yenilenince sıfırlanır (localStorage'a yazılmıyor).
export const selectedFacility = ref(null)

// Aktif bir sohbet (en az 1 mesaj) varken true olur. ChatWidget bunu günceller,
// OceanMap da haritadan liman değiştirilmeye çalışıldığında buna bakar —
// sohbet sürerken liman ne chat içinden ne haritadan değiştirilebilmeli.
export const facilityLocked = ref(false)

export const FACILITY_LABELS = {
  GBZ: 'Gebze Terminali',
  YCT: 'Körfez Terminali',
  ANK: 'Ankara Terminali',
}

export function facilityLabel(code) {
  if (!code) return ''
  const name = FACILITY_LABELS[code]
  return name ? `${name} (${code})` : code
}

export const availableFacilities = ref([])

export async function loadFacilities() {
  try {
    const token = localStorage.getItem('corex_token')
    const res = await axios.get('/api/facilities', {
      headers: { Authorization: `Bearer ${token}` },
    })
    availableFacilities.value = res.data.facilities || []
  } catch (e) {
    console.error('Liman listesi alınamadı:', e)
    availableFacilities.value = []
  }
}
