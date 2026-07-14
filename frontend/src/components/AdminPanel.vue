<script setup>
import { ref, computed } from 'vue'
import axios from 'axios'
import { t, transactionTypeLabel, freightKindLabel, recordStatusLabel } from '../i18n'

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

function authHeaders() {
  return { Authorization: `Bearer ${props.token}` }
}

// datetime-local input'un "max" değeri: şu an, gelecekte bir zaman seçilemesin
function nowForDatetimeLocal() {
  const now = new Date()
  now.setMinutes(now.getMinutes() - now.getTimezoneOffset())
  return now.toISOString().slice(0, 16)
}
const maxEntryTime = ref(nowForDatetimeLocal())

// --- Yeni kayıt ekleme ---
const newRecord = ref({
  container_no: '',
  time_entered_yard: '',
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
        container_no: newRecord.value.container_no.trim().toUpperCase(),
        time_entered_yard: newRecord.value.time_entered_yard,
        loc_name: newRecord.value.loc_name.trim() || null,
        transaction_type: newRecord.value.transaction_type,
        freight_kind: newRecord.value.freight_kind,
        damage: newRecord.value.damage,
      },
      { headers: authHeaders() }
    )
    addMessage.value = t('adminSuccessCreate')
    newRecord.value = {
      container_no: '',
      time_entered_yard: '',
      loc_name: '',
      transaction_type: TRANSACTION_TYPES[0],
      freight_kind: FREIGHT_KINDS[0],
      damage: false,
    }
  } catch (error) {
    addError.value = error.response?.data?.detail || t('adminErrorGeneric')
  } finally {
    isSubmitting.value = false
  }
}

// --- Arama / iptal / çıkış ekleme ---
const searchQuery = ref('')
const searchResults = ref([])
const RECENT_SEARCHES_KEY = 'corex_admin_recent_searches'
const recentSearches = ref(JSON.parse(localStorage.getItem(RECENT_SEARCHES_KEY) || '[]'))

function addRecentSearch(query) {
  recentSearches.value = [query, ...recentSearches.value.filter(q => q !== query)].slice(0, 3)
  localStorage.setItem(RECENT_SEARCHES_KEY, JSON.stringify(recentSearches.value))
}

function searchFromRecent(query) {
  searchQuery.value = query
  runSearch()
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

function seedDetailDraft(record) {
  detailDrafts.value[record.id] = {
    loc_name: record.loc_name || '',
    damage: !!record.damage,
    freight_kind: record.freight_kind,
  }
}

// Aktif (iptal edilmemiş) kayıtlar üstte, iptal edilenler altta.
const sortedResults = computed(() => {
  const active = searchResults.value.filter(r => r.transaction_status !== 'CANCEL')
  const cancelled = searchResults.value.filter(r => r.transaction_status === 'CANCEL')
  return [...active, ...cancelled]
})

async function runSearch() {
  const query = searchQuery.value.trim().toUpperCase()
  if (!query) return
  searchError.value = ''
  isSearching.value = true
  addRecentSearch(query)
  try {
    const response = await axios.get('/api/admin/containers/search', {
      params: { container_no: query },
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
  return record.transaction_status === 'COMPLETE' && !record.time_exited_yard
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
  try {
    const response = await axios.patch(
      `/api/admin/containers/${record.id}`,
      {
        loc_name: draft.loc_name.trim() || null,
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
        <span>{{ t('adminLocName') }}</span>
        <input v-model="newRecord.loc_name" type="text" :placeholder="t('adminLocNamePlaceholder')" />
      </label>
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

      <button class="submit-btn" :disabled="isSubmitting || !newRecord.container_no || !newRecord.time_entered_yard" @click="submitNewRecord">
        {{ t('adminSubmit') }}
      </button>
    </div>

    <div v-else class="admin-tab-content">
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
          <label class="field">
            <span>{{ t('adminLocName') }}</span>
            <input v-model="detailDrafts[record.id].loc_name" type="text" :placeholder="t('adminLocNamePlaceholder')" />
          </label>
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
          <input v-model="exitDrafts[record.id]" type="datetime-local" />
          <button @click="submitExit(record)" :disabled="!exitDrafts[record.id]">{{ t('adminCloseExit') }}</button>
        </div>
        <div v-if="record.transaction_status !== 'CANCEL'" class="record-actions">
          <button class="cancel-btn" @click="cancelRecord(record)">{{ t('adminCancelRecord') }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.admin-panel {
  flex: 1;
  overflow-y: auto;
  padding: 0.85rem;
  color: white;
  font-family: 'Segoe UI', system-ui, sans-serif;
  font-size: 0.85rem;
}

.admin-tabs {
  display: flex;
  gap: 0.4rem;
  margin-bottom: 0.85rem;
}

.admin-tabs button {
  flex: 1;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: rgba(255, 255, 255, 0.7);
  padding: 0.45rem;
  border-radius: 8px;
  font-size: 0.78rem;
  font-weight: 600;
  cursor: pointer;
}

.admin-tabs button.active {
  background: rgba(34, 211, 238, 0.25);
  color: white;
  border-color: rgba(34, 211, 238, 0.4);
}

.admin-tab-content {
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  font-size: 0.78rem;
  color: rgba(255, 255, 255, 0.7);
}

.field input,
.field select {
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 8px;
  padding: 0.5rem 0.6rem;
  color: white;
  font-size: 0.85rem;
  outline: none;
}

.field select option {
  color: #0b1a2b;
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
  background: linear-gradient(135deg, #0c4a6e, #0891b2);
  color: white;
  border: none;
  padding: 0.6rem;
  border-radius: 8px;
  font-weight: 600;
  font-size: 0.85rem;
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
