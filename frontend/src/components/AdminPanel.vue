<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import axios from 'axios'
import { t, transactionTypeLabel, freightKindLabel, recordStatusLabel } from '../i18n'
import { facilityLabel, isLightShadeFacility } from '../facility'

const FACILITY_YARD_PREFIX = {
  YCT: 'YCT', GBZ: 'TRGEB', ANK: 'TRANK',
  MXK: 'TRMXK', TKD: 'TRTKD', TAR: 'TRTAR',
  OSL: 'TROSL', GVL: 'TRGVL', STO: 'TRSTO',
  AQJ: 'TRAQJ', LUX: 'TRLUX', PAI: 'TRPAI',
  PBO: 'TRPBO', PRQ: 'TRPRQ',
  LIS: 'TRLIS', FIG: 'TRFIG', SOT: 'TRSOT',
  LEI: 'TRLEI', AVE: 'TRAVE', SET: 'TRSET',
  TER: 'TRTER', HUE: 'TRHUE', FRO: 'TRFRO', ELV: 'TRELV',
}
const NEW_OPTION = '__new__'

const props = defineProps({
  token: { type: String, required: true },
})

const TRANSACTION_TYPES = [
  'ReceiveExport', 'DeliverImport', 'DeliverEmpty',
  'ReceiveEmpty', 'DrayOffExport', 'DrayOffImport', 'DeliverBreakBulk',
]
const FREIGHT_KINDS = ['FCL', 'MTY', 'BBK']
const CONTAINER_NO_PATTERN = /^[A-Z]{4}\d{7}$/

const activeTab = ref('add')
const facilities = ref([])

function authHeaders() {
  return { Authorization: `Bearer ${props.token}` }
}

onMounted(async () => {
  try {
    const response = await axios.get('/api/admin/meta', { headers: authHeaders() })
    facilities.value = response.data.facilities || []
  } catch (error) {
    facilities.value = []
  }
})

// datetime-local input'un "max" değeri: şu an, gelecekte bir zaman seçilemesin
function nowForDatetimeLocal() {
  const now = new Date()
  now.setMinutes(now.getMinutes() - now.getTimezoneOffset())
  return now.toISOString().slice(0, 16)
}
const maxEntryTime = ref(nowForDatetimeLocal())

// --- Yeni kayıt ekleme ---
const newRecord = ref({
  facility_id: '',
  container_no: '',
  time_entered_yard: '',
  time_exited_yard: '',
  loc_name: '',
  transaction_type: TRANSACTION_TYPES[0],
  freight_kind: FREIGHT_KINDS[0],
  damage: false,
})
const addMessage = ref('')
const addError = ref('')
const isSubmitting = ref(false)

function containerNoValidity(value) {
  const trimmed = (value || '').trim().toUpperCase()
  if (!trimmed) return null
  return CONTAINER_NO_PATTERN.test(trimmed) ? 'valid' : 'invalid'
}

const containerNoStatus = computed(() => containerNoValidity(newRecord.value.container_no))
const searchContainerNoStatus = computed(() => containerNoValidity(searchQuery.value))

// --- Saha konumu (loc_name) hiyerarşik seçici: LocType -> Blok/Plaka -> Bay-Row/Kat ---
// Hem "kayıt ekle" formunda hem de arama sonuçlarındaki düzenleme kartlarında
// (her kayıt için ayrı bir örnek) kullanılan genel yardımcılar.
function makeLocPicker() {
  return {
    locType: '', blocks: [], selectedBlock: '', addresses: [], selectedAddress: '',
    newBayRow: '', newTier: '', plates: [], selectedPlate: '', newPlate: '',
  }
}

async function loadLocTypeOptions(picker, facilityId) {
  picker.selectedBlock = ''
  picker.addresses = []
  picker.selectedAddress = ''
  picker.selectedPlate = ''
  picker.newPlate = ''
  picker.blocks = []
  picker.plates = []
  if (!facilityId || !picker.locType) return
  try {
    const response = await axios.get('/api/admin/loc-options', {
      params: { facility_id: facilityId, loc_type: picker.locType },
      headers: authHeaders(),
    })
    if (picker.locType === 'TRUCK') {
      picker.plates = response.data.plates || []
    } else {
      picker.blocks = response.data.blocks || []
    }
  } catch (error) {
    // sessizce boş bırak, kullanıcı "yeni" seçeneğinden elle girebilir
  }
}

async function loadBlockAddresses(picker, facilityId) {
  picker.selectedAddress = ''
  picker.newBayRow = ''
  picker.newTier = ''
  picker.addresses = []
  if (!picker.selectedBlock) return
  try {
    const response = await axios.get('/api/admin/loc-options', {
      params: { facility_id: facilityId, loc_type: 'YARD', block: picker.selectedBlock },
      headers: authHeaders(),
    })
    picker.addresses = response.data.addresses || []
  } catch (error) {
    picker.addresses = []
  }
}

function blockHasTier(picker) {
  return picker.addresses.some(a => a.loc_tier !== null && a.loc_tier !== undefined)
}

function buildLocName(picker, facilityId) {
  if (picker.locType === 'TRUCK') {
    const plate = picker.selectedPlate === NEW_OPTION ? picker.newPlate.trim().toUpperCase() : picker.selectedPlate
    return plate ? `T-${plate}-TIP-Y` : ''
  }
  if (picker.locType === 'YARD') {
    const prefix = FACILITY_YARD_PREFIX[facilityId] || facilityId
    if (picker.selectedAddress && picker.selectedAddress !== NEW_OPTION) {
      const suffix = picker.selectedAddress.replace('.', '')
      return `Y-${prefix}-${suffix}`
    }
    if (picker.selectedAddress === NEW_OPTION && picker.selectedBlock && picker.newBayRow.trim()) {
      const suffix = `${picker.selectedBlock}${picker.newBayRow.trim()}${picker.newTier.trim()}`
      return `Y-${prefix}-${suffix}`
    }
    return ''
  }
  return ''
}

const locPicker = ref(makeLocPicker())

// Liman değişince blok/plaka listeleri geçersiz olur, sıfırlanır.
watch(() => newRecord.value.facility_id, () => { locPicker.value = makeLocPicker() })

function onLocTypeChange() {
  return loadLocTypeOptions(locPicker.value, newRecord.value.facility_id)
}

function onBlockChange() {
  return loadBlockAddresses(locPicker.value, newRecord.value.facility_id)
}

// Facility'nin gerçek verisinde kat (tier) bilgisi var mı? (YCT var, GBZ yok)
const blockHasTierData = computed(() => blockHasTier(locPicker.value))

const builtLocName = computed(() => buildLocName(locPicker.value, newRecord.value.facility_id))

watch(builtLocName, (value) => {
  newRecord.value.loc_name = value
})

async function submitNewRecord() {
  addMessage.value = ''
  addError.value = ''

  if (newRecord.value.time_entered_yard && new Date(newRecord.value.time_entered_yard) > new Date()) {
    addError.value = t('adminFutureEntryError')
    return
  }

  isSubmitting.value = true
  try {
    await axios.post(
      '/api/admin/containers',
      {
        facility_id: newRecord.value.facility_id,
        container_no: newRecord.value.container_no.trim().toUpperCase(),
        time_entered_yard: newRecord.value.time_entered_yard,
        time_exited_yard: newRecord.value.time_exited_yard || null,
        loc_name: newRecord.value.loc_name.trim() || null,
        transaction_type: newRecord.value.transaction_type,
        freight_kind: newRecord.value.freight_kind,
        damage: newRecord.value.damage,
      },
      { headers: authHeaders() }
    )
    addMessage.value = t('adminSuccessCreate')
    newRecord.value = {
      facility_id: newRecord.value.facility_id,
      container_no: '',
      time_entered_yard: '',
      time_exited_yard: '',
      loc_name: '',
      transaction_type: TRANSACTION_TYPES[0],
      freight_kind: FREIGHT_KINDS[0],
      damage: false,
    }
    locPicker.value = makeLocPicker()
  } catch (error) {
    addError.value = error.response?.data?.detail || t('adminErrorGeneric')
  } finally {
    isSubmitting.value = false
  }
}

// --- Arama / iptal / çıkış ekleme ---
const searchQuery = ref('')
const searchFacilityId = ref('')
const searchResults = ref([])

// Son aramalar limana göre ayrı tutulur (her limanın kendi geçmişi olsun diye).
function recentSearchesKey(facilityId) {
  return `corex_admin_recent_searches_${facilityId || 'none'}`
}
const recentSearches = ref([])

function loadRecentSearches() {
  recentSearches.value = JSON.parse(localStorage.getItem(recentSearchesKey(searchFacilityId.value)) || '[]')
}

function addRecentSearch(query) {
  recentSearches.value = [query, ...recentSearches.value.filter(q => q !== query)].slice(0, 3)
  localStorage.setItem(recentSearchesKey(searchFacilityId.value), JSON.stringify(recentSearches.value))
}

function searchFromRecent(query) {
  searchQuery.value = query
  runSearch()
}

function onSearchFacilityChange() {
  searchQuery.value = ''
  searchResults.value = []
  searchError.value = ''
  loadRecentSearches()
}
const searchError = ref('')
const isSearching = ref(false)
const exitDrafts = ref({})
const detailDrafts = ref({})
// Her kayda özel işlem sonucu mesajı (çıkış ekleme / iptal / detay güncelleme) —
// üstte tek bir genel uyarı yerine, mesaj işlem yapılan kartın üzerinde gösterilir.
const recordMessages = ref({})

function setRecordMessage(recordId, text, isError) {
  recordMessages.value[recordId] = text ? { text, isError } : null
}

// Arama sonuçlarındaki her kayıt kartının kendi saha konumu seçicisi olur
// (add tab'daki ile aynı yapı) — serbest metinle değil, seçerek belirlenir.
const detailLocPickers = ref({})

function seedDetailDraft(record) {
  detailDrafts.value[record.id] = {
    loc_name: record.loc_name || '',
    damage: !!record.damage,
    freight_kind: record.freight_kind,
  }
  detailLocPickers.value[record.id] = makeLocPicker()
}

function onDetailLocTypeChange(record) {
  return loadLocTypeOptions(detailLocPickers.value[record.id], searchFacilityId.value)
}

function onDetailBlockChange(record) {
  return loadBlockAddresses(detailLocPickers.value[record.id], searchFacilityId.value)
}

// Seçiciden henüz yeni bir konum seçilmediyse kaydın mevcut konumunu gösterir.
function detailLocPreview(record) {
  const built = buildLocName(detailLocPickers.value[record.id], searchFacilityId.value)
  return built || detailDrafts.value[record.id]?.loc_name || ''
}

// Aktif (iptal edilmemiş) kayıtlar üstte, iptal edilenler altta.
const sortedResults = computed(() => {
  const active = searchResults.value.filter(r => r.transaction_status !== 'CANCEL')
  const cancelled = searchResults.value.filter(r => r.transaction_status === 'CANCEL')
  return [...active, ...cancelled]
})

async function runSearch() {
  const query = searchQuery.value.trim().toUpperCase()
  if (!query || !searchFacilityId.value) return
  searchError.value = ''
  isSearching.value = true
  addRecentSearch(query)
  try {
    const response = await axios.get('/api/admin/containers/search', {
      params: { container_no: query, facility_id: searchFacilityId.value },
      headers: authHeaders(),
    })
    searchResults.value = response.data.records || []
    detailDrafts.value = {}
    recordMessages.value = {}
    searchResults.value.forEach(seedDetailDraft)
  } catch (error) {
    searchError.value = error.response?.data?.detail || t('adminNoResults')
    searchResults.value = []
  } finally {
    isSearching.value = false
  }
}

function isOpenRecord(record) {
  return record.transaction_status === 'IN_PROGRESS' && !record.time_exited_yard
}

// DB'deki giriş tarihini datetime-local input'un "min" değeri için normalize eder
// (bazı kayıtlarda "YYYY-MM-DD HH:MM:SS", bazılarında "YYYY-MM-DDTHH:MM" olabiliyor).
function toDatetimeLocalMin(value) {
  if (!value) return undefined
  return value.replace(' ', 'T').slice(0, 16)
}

async function submitExit(record) {
  const exitTime = exitDrafts.value[record.id]
  if (!exitTime) return
  setRecordMessage(record.id, '', false)
  try {
    const response = await axios.post(
      `/api/admin/containers/${record.id}/exit`,
      { time_exited_yard: exitTime },
      { headers: authHeaders() }
    )
    const index = searchResults.value.findIndex(r => r.id === record.id)
    if (index !== -1) searchResults.value[index] = response.data.record
    delete exitDrafts.value[record.id]
    setRecordMessage(record.id, t('adminSuccessExit'), false)
  } catch (error) {
    setRecordMessage(record.id, error.response?.data?.detail || t('adminErrorGeneric'), true)
  }
}

async function submitDetailsUpdate(record) {
  const draft = detailDrafts.value[record.id]
  if (!draft) return
  setRecordMessage(record.id, '', false)
  const locName = detailLocPreview(record)
  try {
    const response = await axios.patch(
      `/api/admin/containers/${record.id}`,
      {
        loc_name: locName.trim() || null,
        damage: draft.damage,
        freight_kind: draft.freight_kind,
      },
      { headers: authHeaders() }
    )
    const index = searchResults.value.findIndex(r => r.id === record.id)
    if (index !== -1) searchResults.value[index] = response.data.record
    seedDetailDraft(response.data.record)
    setRecordMessage(record.id, t('adminSuccessUpdate'), false)
  } catch (error) {
    setRecordMessage(record.id, error.response?.data?.detail || t('adminErrorGeneric'), true)
  }
}

async function cancelRecord(record) {
  if (!window.confirm(t('adminConfirmCancel'))) return
  setRecordMessage(record.id, '', false)
  try {
    const response = await axios.post(
      `/api/admin/containers/${record.id}/cancel`,
      {},
      { headers: authHeaders() }
    )
    const index = searchResults.value.findIndex(r => r.id === record.id)
    if (index !== -1) searchResults.value[index] = response.data.record
    setRecordMessage(record.id, t('adminSuccessCancel'), false)
  } catch (error) {
    setRecordMessage(record.id, error.response?.data?.detail || t('adminErrorGeneric'), true)
  }
}
</script>

<template>
  <div class="admin-panel">
    <div class="admin-tabs">
      <button :class="{ active: activeTab === 'add' }" @click="activeTab = 'add'">{{ t('adminAddTab') }}</button>
      <button :class="{ active: activeTab === 'search' }" @click="activeTab = 'search'">{{ t('adminSearchTab') }}</button>
    </div>

    <div v-if="activeTab === 'add'" class="admin-tab-content">
      <label class="field">
        <span>{{ t('adminFacility') }}</span>
        <select v-model="newRecord.facility_id">
          <option value="" disabled>{{ t('adminSelectFacility') }}</option>
          <option
            v-for="fac in facilities"
            :key="fac"
            :value="fac"
            :class="{ 'option-light-shade': isLightShadeFacility(fac) }"
          >{{ facilityLabel(fac) }}</option>
        </select>
      </label>
      <label class="field">
        <span>{{ t('adminContainerNo') }}</span>
        <div class="input-with-icon">
          <input v-model="newRecord.container_no" type="text" :placeholder="t('adminContainerNoPlaceholder')" maxlength="11" />
          <span
            v-if="containerNoStatus"
            class="validity-icon"
            :class="containerNoStatus"
            :title="containerNoStatus === 'valid' ? t('adminContainerNoValid') : t('adminContainerNoInvalid')"
          >{{ containerNoStatus === 'valid' ? '✓' : '✕' }}</span>
        </div>
      </label>
      <label class="field">
        <span>{{ t('adminEntryTime') }}</span>
        <input v-model="newRecord.time_entered_yard" type="datetime-local" :max="maxEntryTime" />
      </label>
      <label class="field">
        <span>{{ t('adminExitTimeOptional') }}</span>
        <input v-model="newRecord.time_exited_yard" type="datetime-local" :min="newRecord.time_entered_yard || undefined" />
      </label>
      <div class="field loc-picker">
        <span>{{ t('adminLocName') }}</span>

        <select v-model="locPicker.locType" :disabled="!newRecord.facility_id" @change="onLocTypeChange">
          <option value="" disabled>{{ t('adminLocTypeSelect') }}</option>
          <option value="YARD">{{ t('adminLocTypeYard') }}</option>
          <option value="TRUCK">{{ t('adminLocTypeTruck') }}</option>
        </select>

        <!-- TRUCK: plaka seçimi -->
        <select v-if="locPicker.locType === 'TRUCK'" v-model="locPicker.selectedPlate">
          <option value="" disabled>{{ t('adminSelectPlate') }}</option>
          <option v-for="p in locPicker.plates" :key="p" :value="p">{{ p }}</option>
          <option :value="NEW_OPTION">{{ t('adminNewPlate') }}</option>
        </select>
        <input
          v-if="locPicker.locType === 'TRUCK' && locPicker.selectedPlate === NEW_OPTION"
          v-model="locPicker.newPlate"
          type="text"
          :placeholder="t('adminNewPlatePlaceholder')"
        />

        <!-- YARD: blok seçimi -->
        <select v-if="locPicker.locType === 'YARD'" v-model="locPicker.selectedBlock" @change="onBlockChange">
          <option value="" disabled>{{ t('adminSelectBlock') }}</option>
          <option v-for="b in locPicker.blocks" :key="b" :value="b">{{ b }}</option>
        </select>

        <!-- YARD: bay/row + kat seçimi -->
        <select v-if="locPicker.locType === 'YARD' && locPicker.selectedBlock" v-model="locPicker.selectedAddress">
          <option value="" disabled>{{ t('adminSelectAddress') }}</option>
          <option v-for="a in locPicker.addresses" :key="a.loc_slot" :value="a.loc_slot">
            {{ a.loc_slot }}<template v-if="a.loc_tier !== null && a.loc_tier !== undefined"> ({{ t('adminTier') }} {{ a.loc_tier }})</template>
          </option>
          <option :value="NEW_OPTION">{{ t('adminNewAddress') }}</option>
        </select>
        <div v-if="locPicker.locType === 'YARD' && locPicker.selectedAddress === NEW_OPTION" class="new-address-row">
          <input v-model="locPicker.newBayRow" type="text" :placeholder="t('adminNewBayRowPlaceholder')" maxlength="4" />
          <input
            v-if="blockHasTierData"
            v-model="locPicker.newTier"
            type="text"
            :placeholder="t('adminNewTierPlaceholder')"
            maxlength="1"
          />
        </div>

        <div v-if="newRecord.loc_name" class="loc-preview">{{ newRecord.loc_name }}</div>
      </div>
      <label class="field">
        <span>{{ t('adminTransactionType') }}</span>
        <select v-model="newRecord.transaction_type">
          <option v-for="ttype in TRANSACTION_TYPES" :key="ttype" :value="ttype">{{ transactionTypeLabel(ttype) }}</option>
        </select>
      </label>
      <label class="field">
        <span>{{ t('adminFreightKind') }}</span>
        <select v-model="newRecord.freight_kind">
          <option v-for="fk in FREIGHT_KINDS" :key="fk" :value="fk">{{ freightKindLabel(fk) }}</option>
        </select>
      </label>
      <label class="field checkbox-field">
        <input v-model="newRecord.damage" type="checkbox" />
        <span>{{ t('adminDamage') }}</span>
      </label>

      <p v-if="addMessage" class="msg success">{{ addMessage }}</p>
      <p v-if="addError" class="msg error">{{ addError }}</p>

      <button class="submit-btn" :disabled="isSubmitting || !newRecord.facility_id || !newRecord.container_no || !newRecord.time_entered_yard" @click="submitNewRecord">
        {{ t('adminSubmit') }}
      </button>
    </div>

    <div v-else class="admin-tab-content">
      <label class="field">
        <span>{{ t('adminFacility') }}</span>
        <select v-model="searchFacilityId" @change="onSearchFacilityChange">
          <option value="" disabled>{{ t('adminSelectFacility') }}</option>
          <option
            v-for="fac in facilities"
            :key="fac"
            :value="fac"
            :class="{ 'option-light-shade': isLightShadeFacility(fac) }"
          >{{ facilityLabel(fac) }}</option>
        </select>
      </label>

      <template v-if="searchFacilityId">
        <div class="search-row">
          <div class="input-with-icon">
            <input v-model="searchQuery" type="text" :placeholder="t('adminSearchPlaceholder')" @keydown.enter="runSearch" />
            <span
              v-if="searchContainerNoStatus"
              class="validity-icon"
              :class="searchContainerNoStatus"
              :title="searchContainerNoStatus === 'valid' ? t('adminContainerNoValid') : t('adminContainerNoInvalid')"
            >{{ searchContainerNoStatus === 'valid' ? '✓' : '✕' }}</span>
          </div>
          <button @click="runSearch" :disabled="isSearching">{{ t('adminSearchButton') }}</button>
        </div>

        <div v-if="recentSearches.length > 0" class="recent-searches">
          <span class="recent-label">{{ t('adminRecentSearches') }}</span>
          <button
            v-for="query in recentSearches"
            :key="query"
            class="recent-chip"
            @click="searchFromRecent(query)"
          >{{ query }}</button>
        </div>

        <p v-if="searchError" class="msg error">{{ searchError }}</p>
        <p v-if="!isSearching && searchResults.length === 0 && !searchError" class="msg muted">{{ t('adminNoResults') }}</p>

        <div v-for="record in sortedResults" :key="record.id" class="record-card">
        <div class="record-header">
          <strong>{{ record.container_no }}</strong>
          <span class="status-badge" :class="{ open: isOpenRecord(record), cancel: record.transaction_status === 'CANCEL' }">
            {{ recordStatusLabel(record) }}
          </span>
        </div>

        <p v-if="recordMessages[record.id]" class="msg" :class="recordMessages[record.id].isError ? 'error' : 'success'">{{ recordMessages[record.id].text }}</p>

        <div class="record-line">{{ t('adminEntryTime') }}: {{ record.time_entered_yard }}</div>
        <div class="record-line" v-if="record.time_exited_yard">{{ t('adminExitTime') }}: {{ record.time_exited_yard }}</div>
        <div class="record-line">{{ transactionTypeLabel(record.transaction_type) }}</div>

        <div v-if="detailDrafts[record.id]" class="edit-details">
          <div class="field loc-picker">
            <span>{{ t('adminLocName') }}</span>

            <select v-model="detailLocPickers[record.id].locType" @change="onDetailLocTypeChange(record)">
              <option value="" disabled>{{ t('adminLocTypeSelect') }}</option>
              <option value="YARD">{{ t('adminLocTypeYard') }}</option>
              <option value="TRUCK">{{ t('adminLocTypeTruck') }}</option>
            </select>

            <!-- TRUCK: plaka seçimi -->
            <select v-if="detailLocPickers[record.id].locType === 'TRUCK'" v-model="detailLocPickers[record.id].selectedPlate">
              <option value="" disabled>{{ t('adminSelectPlate') }}</option>
              <option v-for="p in detailLocPickers[record.id].plates" :key="p" :value="p">{{ p }}</option>
              <option :value="NEW_OPTION">{{ t('adminNewPlate') }}</option>
            </select>
            <input
              v-if="detailLocPickers[record.id].locType === 'TRUCK' && detailLocPickers[record.id].selectedPlate === NEW_OPTION"
              v-model="detailLocPickers[record.id].newPlate"
              type="text"
              :placeholder="t('adminNewPlatePlaceholder')"
            />

            <!-- YARD: blok seçimi -->
            <select v-if="detailLocPickers[record.id].locType === 'YARD'" v-model="detailLocPickers[record.id].selectedBlock" @change="onDetailBlockChange(record)">
              <option value="" disabled>{{ t('adminSelectBlock') }}</option>
              <option v-for="b in detailLocPickers[record.id].blocks" :key="b" :value="b">{{ b }}</option>
            </select>

            <!-- YARD: bay/row + kat seçimi -->
            <select v-if="detailLocPickers[record.id].locType === 'YARD' && detailLocPickers[record.id].selectedBlock" v-model="detailLocPickers[record.id].selectedAddress">
              <option value="" disabled>{{ t('adminSelectAddress') }}</option>
              <option v-for="a in detailLocPickers[record.id].addresses" :key="a.loc_slot" :value="a.loc_slot">
                {{ a.loc_slot }}<template v-if="a.loc_tier !== null && a.loc_tier !== undefined"> ({{ t('adminTier') }} {{ a.loc_tier }})</template>
              </option>
              <option :value="NEW_OPTION">{{ t('adminNewAddress') }}</option>
            </select>
            <div v-if="detailLocPickers[record.id].locType === 'YARD' && detailLocPickers[record.id].selectedAddress === NEW_OPTION" class="new-address-row">
              <input v-model="detailLocPickers[record.id].newBayRow" type="text" :placeholder="t('adminNewBayRowPlaceholder')" maxlength="4" />
              <input
                v-if="detailLocPickers[record.id].addresses.some(a => a.loc_tier !== null && a.loc_tier !== undefined)"
                v-model="detailLocPickers[record.id].newTier"
                type="text"
                :placeholder="t('adminNewTierPlaceholder')"
                maxlength="1"
              />
            </div>

            <div v-if="detailLocPreview(record)" class="loc-preview">{{ detailLocPreview(record) }}</div>
          </div>
          <label class="field">
            <span>{{ t('adminFreightKind') }}</span>
            <select v-model="detailDrafts[record.id].freight_kind">
              <option v-for="fk in FREIGHT_KINDS" :key="fk" :value="fk">{{ freightKindLabel(fk) }}</option>
            </select>
          </label>
          <label class="field checkbox-field">
            <input v-model="detailDrafts[record.id].damage" type="checkbox" />
            <span>{{ t('adminDamage') }}</span>
          </label>
          <button class="save-details-btn" @click="submitDetailsUpdate(record)">{{ t('adminEditDetails') }}</button>
        </div>

        <div v-if="isOpenRecord(record)" class="record-actions">
          <input v-model="exitDrafts[record.id]" type="datetime-local" :min="toDatetimeLocalMin(record.time_entered_yard)" />
          <button @click="submitExit(record)" :disabled="!exitDrafts[record.id]">{{ t('adminCloseExit') }}</button>
        </div>
        <div v-if="record.transaction_status !== 'CANCEL'" class="record-actions">
          <button class="cancel-btn" @click="cancelRecord(record)">{{ t('adminCancelRecord') }}</button>
        </div>
      </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.admin-panel {
  flex: 1;
  overflow-y: auto;
  padding: 1.5rem;
  color: white;
  font-family: 'Segoe UI', system-ui, sans-serif;
  font-size: 0.85rem;
}

.admin-tab-content,
.admin-tabs {
  max-width: 520px;
  margin-left: auto;
  margin-right: auto;
}

.admin-tabs {
  display: flex;
  gap: 0.6rem;
  margin-bottom: 1.25rem;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 14px;
  padding: 0.4rem;
}

.admin-tabs button {
  flex: 1;
  background: transparent;
  border: none;
  color: rgba(255, 255, 255, 0.55);
  padding: 0.7rem;
  border-radius: 10px;
  font-size: 0.85rem;
  font-weight: 700;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}

.admin-tabs button.active {
  background: linear-gradient(135deg, #0891b2, #22d3ee);
  color: #052030;
  box-shadow: 0 4px 14px rgba(34, 211, 238, 0.25);
}

.admin-tab-content {
  display: flex;
  flex-direction: column;
  gap: 1.1rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  font-size: 0.82rem;
  color: rgba(255, 255, 255, 0.6);
}

.field input,
.field select {
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 12px;
  padding: 0.8rem 1rem;
  color: white;
  font-size: 0.92rem;
  outline: none;
  transition: border-color 0.15s, background 0.15s;
}

.field input:focus,
.field select:focus {
  border-color: rgba(34, 211, 238, 0.5);
  background: rgba(255, 255, 255, 0.09);
}

.field input::placeholder {
  color: rgba(255, 255, 255, 0.3);
}

.field select option {
  color: #0b1a2b;
  background: #ffffff;
}

/* Harita dropdown'undaki gruplamayla aynı mantık (bkz. facility.js
   LIGHT_SHADE_FACILITIES) — burada beyaz zemin üstünde hafif gri. */
.field select option.option-light-shade {
  background: #d8dde2;
}

.input-with-icon {
  position: relative;
  display: flex;
}

.input-with-icon input {
  width: 100%;
  padding-right: 2rem;
}

.validity-icon {
  position: absolute;
  right: 0.6rem;
  top: 50%;
  transform: translateY(-50%);
  font-size: 0.9rem;
  font-weight: 700;
  pointer-events: none;
}

.validity-icon.valid {
  color: #4ade80;
}

.validity-icon.invalid {
  color: #f87171;
}

.loc-picker select,
.loc-picker input {
  margin-top: 0.3rem;
}

.new-address-row {
  display: flex;
  gap: 0.4rem;
}

.new-address-row input {
  flex: 1;
}

.loc-preview {
  margin-top: 0.2rem;
  font-size: 0.78rem;
  color: #7dd3fc;
  font-family: monospace;
}

.checkbox-field {
  flex-direction: row;
  align-items: center;
  gap: 0.5rem;
}

.checkbox-field input {
  width: auto;
}

.msg {
  font-size: 0.8rem;
  margin: 0;
  padding: 0.5rem 0.65rem;
  border-radius: 8px;
}

.msg.success {
  background: rgba(34, 197, 94, 0.15);
  color: #86efac;
}

.msg.error {
  background: rgba(239, 68, 68, 0.15);
  color: #fca5a5;
}

.msg.muted {
  color: rgba(255, 255, 255, 0.5);
  text-align: center;
}

.submit-btn {
  background: linear-gradient(135deg, #0891b2, #22d3ee);
  color: #052030;
  border: none;
  padding: 0.85rem;
  border-radius: 12px;
  font-weight: 700;
  font-size: 0.92rem;
  cursor: pointer;
}

.submit-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.search-row {
  display: flex;
  gap: 0.4rem;
}

.search-row .input-with-icon {
  flex: 1;
}

.search-row input {
  width: 100%;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 8px;
  padding: 0.5rem 0.6rem;
  color: white;
  outline: none;
}

.search-row button {
  background: rgba(34, 211, 238, 0.25);
  border: 1px solid rgba(34, 211, 238, 0.4);
  color: white;
  padding: 0.5rem 0.85rem;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
}

.recent-searches {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.4rem;
  margin-top: -0.2rem;
}

.recent-label {
  font-size: 0.72rem;
  color: rgba(255, 255, 255, 0.5);
}

.recent-chip {
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.18);
  color: rgba(255, 255, 255, 0.85);
  padding: 0.25rem 0.6rem;
  border-radius: 999px;
  font-size: 0.75rem;
  cursor: pointer;
}

.recent-chip:hover {
  background: rgba(34, 211, 238, 0.2);
  border-color: rgba(34, 211, 238, 0.4);
}

.record-card {
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 10px;
  padding: 0.65rem 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.record-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.status-badge {
  font-size: 0.7rem;
  font-weight: 700;
  padding: 0.15rem 0.5rem;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.12);
}

.status-badge.open {
  background: rgba(250, 204, 21, 0.2);
  color: #fde68a;
}

.status-badge.cancel {
  background: rgba(239, 68, 68, 0.2);
  color: #fca5a5;
}

.record-line {
  font-size: 0.78rem;
  color: rgba(255, 255, 255, 0.75);
}

.edit-details {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-top: 0.4rem;
  padding-top: 0.5rem;
  border-top: 1px dashed rgba(255, 255, 255, 0.12);
}

.save-details-btn {
  align-self: flex-start;
  background: rgba(34, 211, 238, 0.25);
  border: 1px solid rgba(34, 211, 238, 0.4);
  color: white;
  padding: 0.4rem 0.75rem;
  border-radius: 8px;
  font-size: 0.78rem;
  font-weight: 600;
  cursor: pointer;
}

.record-actions {
  display: flex;
  gap: 0.4rem;
  margin-top: 0.3rem;
}

.record-actions input {
  flex: 1;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 8px;
  padding: 0.4rem 0.5rem;
  color: white;
  font-size: 0.78rem;
}

.record-actions button {
  background: rgba(34, 211, 238, 0.25);
  border: none;
  color: white;
  padding: 0.4rem 0.7rem;
  border-radius: 8px;
  font-size: 0.78rem;
  cursor: pointer;
  white-space: nowrap;
}

.cancel-btn {
  background: rgba(239, 68, 68, 0.2) !important;
}
</style>
