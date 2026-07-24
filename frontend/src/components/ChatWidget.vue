<script setup>
import { ref, nextTick, onMounted, watch, computed } from 'vue'
import axios from 'axios'
import { language, t } from '../i18n'
import { selectedFacility, availableFacilities, loadFacilities, facilityLabel, facilityLocked, isLightShadeFacility } from '../facility'
import AdminPanel from './AdminPanel.vue'

const props = defineProps({
  token: { type: String, required: false },
  isAdmin: { type: Boolean, default: false },
})

const API_URL = '/api/chat'
const HISTORY_API_URL = '/api/chat/sessions'

const showHistory = ref(false)
const showAdminPanel = ref(false)
const messages = ref([])
const userInput = ref('')
const isLoading = ref(false)
const messagesContainer = ref(null)
const pastSessions = ref([])
const activeSessionId = ref(null)
const editingSessionId = ref(null)
const editingTitle = ref('')
let editingInputEl = null

function formatSessionDate(value) {
  if (!value) return ''
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return value
  return parsed.toLocaleString(language.value === 'en' ? 'en-US' : 'tr-TR', {
    year: 'numeric', month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit',
  })
}

function normalizeSession(session) {
  return {
    id: session.id,
    title: session.title,
    messages: session.messages || [],
    created_at: session.created_at,
    updated_at: session.updated_at,
    date: formatSessionDate(session.updated_at || session.created_at),
    facility_id: session.facility_id || null,
  }
}

function upsertSession(session) {
  const normalized = normalizeSession(session)
  const index = pastSessions.value.findIndex(item => item.id === normalized.id)
  if (index === -1) {
    pastSessions.value.unshift(normalized)
  } else {
    pastSessions.value[index] = normalized
    pastSessions.value.unshift(pastSessions.value.splice(index, 1)[0])
  }
}

async function loadSessions() {
  if (!props.token) return

  try {
    const headers = { Authorization: `Bearer ${props.token}` }
    const response = await axios.get(HISTORY_API_URL, { headers })
    pastSessions.value = (response.data.sessions || []).map(normalizeSession)
  } catch (error) {
    pastSessions.value = []
  }
}

onMounted(() => {
  loadSessions()
  loadFacilities()
})

function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

function toggleHistory() {
  showHistory.value = !showHistory.value
  showAdminPanel.value = false
  if (showHistory.value) loadSessions()
}

function toggleAdminPanel() {
  showAdminPanel.value = !showAdminPanel.value
  showHistory.value = false
}

async function sendMessage() {
  const messageText = userInput.value.trim()
  if (!messageText || isLoading.value) return

  messages.value.push({ role: 'user', content: messageText })
  userInput.value = ''
  isLoading.value = true
  scrollToBottom()

  try {
    const headers = props.token ? { Authorization: `Bearer ${props.token}` } : {}
    const response = await axios.post(
      API_URL,
      {
        message: messageText,
        history: messages.value.slice(0, -1),
        session_id: activeSessionId.value,
        language: language.value,
        facility_id: selectedFacility.value,
      },
      { headers }
    )
    messages.value.push({ role: 'assistant', content: response.data.reply })

    if (response.data.session) {
      activeSessionId.value = response.data.session.id
      upsertSession(response.data.session)
    }
  } catch (error) {
    messages.value.push({
      role: 'assistant',
      content: t('chatConnectionError'),
      isError: true,
    })
  } finally {
    isLoading.value = false
    scrollToBottom()
  }
}

function handleEnter(e) {
  if (!e.shiftKey) sendMessage()
}

function askSuggestion(text) {
  userInput.value = text
  sendMessage()
}

// Mevcut sohbeti "geçmiş" olarak kaydedip yeni bir sohbete başlar
function startNewChat() {
  messages.value = []
  activeSessionId.value = null
  showHistory.value = false
  showAdminPanel.value = false
}

function loadSession(session) {
  messages.value = [...session.messages]
  activeSessionId.value = session.id
  if (session.facility_id) selectedFacility.value = session.facility_id
  showHistory.value = false
  scrollToBottom()
}

function startEditTitle(session, event) {
  event.stopPropagation()
  editingSessionId.value = session.id
  editingTitle.value = session.title
  nextTick(() => {
    editingInputEl?.focus()
    editingInputEl?.select()
  })
}

function cancelEditTitle(event) {
  event?.stopPropagation()
  editingSessionId.value = null
  editingTitle.value = ''
}

async function saveEditTitle(session, event) {
  event?.stopPropagation()
  const newTitle = editingTitle.value.trim()
  if (!newTitle || newTitle === session.title) {
    cancelEditTitle()
    return
  }

  try {
    const headers = props.token ? { Authorization: `Bearer ${props.token}` } : {}
    const response = await axios.patch(
      `${HISTORY_API_URL}/${session.id}`,
      { title: newTitle },
      { headers }
    )
    if (response.data.session) {
      upsertSession(response.data.session)
    }
  } catch (error) {
    // Sessizce yok say; panel bir sonraki açılışta güncel hâlini gösterir.
  } finally {
    cancelEditTitle()
  }
}

async function deleteSession(id, event) {
  event.stopPropagation()
  try {
    const headers = props.token ? { Authorization: `Bearer ${props.token}` } : {}
    await axios.delete(`${HISTORY_API_URL}/${id}`, { headers })
    pastSessions.value = pastSessions.value.filter(s => s.id !== id)
    if (activeSessionId.value === id) {
      activeSessionId.value = null
      messages.value = []
    }
  } catch (error) {
    // Silently ignore for now; panel will refresh next time.
  }
}

const hasActiveChat = computed(() => messages.value.length > 0)

// Sohbette en az bir mesaj varken liman kilitlenir — bu bilgi haritayla da
// paylaşılıyor (facility.js), çünkü haritadan tıklayarak da değiştirilebiliyordu.
watch(hasActiveChat, (locked) => {
  facilityLocked.value = locked
}, { immediate: true })
</script>

<template>
  <div class="chat-window">
    <header class="chat-header">
      <div class="header-left">
        <span class="header-title">{{ t('chatTitle') }}</span>
        <template v-if="selectedFacility">
          <span class="header-sep">/</span>
          <select
            v-if="!facilityLocked"
            v-model="selectedFacility"
            class="header-facility-select"
          >
            <option
              v-for="fac in availableFacilities"
              :key="fac"
              :value="fac"
              :class="{ 'option-light-shade': isLightShadeFacility(fac) }"
            >{{ facilityLabel(fac) }}</option>
          </select>
          <span v-else class="header-facility-text">{{ facilityLabel(selectedFacility) }}</span>
        </template>
      </div>
      <div class="header-actions">
        <button class="header-action-btn" @click="toggleHistory">
          <span class="action-icon">↺</span>{{ t('chatHistoryTitle') }}
        </button>
        <button class="header-action-btn" @click="startNewChat">
          <span class="action-icon">+</span>{{ t('chatNewChat') }}
        </button>
        <button v-if="isAdmin" class="header-action-btn" @click="toggleAdminPanel">
          <span class="action-icon">⚙</span>{{ t('adminButtonTitle') }}
        </button>
      </div>
    </header>

    <!-- Admin paneli: yeni kayıt ekleme / arama-iptal etme -->
    <AdminPanel v-if="showAdminPanel" :token="token" />

    <!-- Geçmiş sohbetler paneli -->
    <div v-else-if="showHistory" class="history-panel">
      <div v-if="pastSessions.length === 0" class="history-empty">
        {{ t('chatEmptyHistory') }}
      </div>
      <div
        v-for="session in pastSessions"
        :key="session.id"
        class="history-item"
        @click="loadSession(session)"
      >
        <div class="history-item-text">
          <input
            v-if="editingSessionId === session.id"
            :ref="(el) => { editingInputEl = el }"
            v-model="editingTitle"
            class="title-input"
            maxlength="40"
            @click.stop
            @keydown.enter="saveEditTitle(session, $event)"
            @keydown.esc="cancelEditTitle($event)"
          />
          <div v-else class="history-title">{{ session.title }}</div>
          <div class="history-meta">
            <span class="history-date">{{ session.date }}</span>
            <span v-if="session.facility_id" class="history-facility">{{ facilityLabel(session.facility_id) }}</span>
          </div>
        </div>
        <div class="history-item-actions">
          <template v-if="editingSessionId === session.id">
            <button class="icon-action-btn" :title="t('chatSaveTitle')" @click="saveEditTitle(session, $event)">✓</button>
            <button class="icon-action-btn" :title="t('chatCancelEdit')" @click="cancelEditTitle($event)">✕</button>
          </template>
          <template v-else>
            <button class="icon-action-btn" :title="t('chatEditTitle')" @click="startEditTitle(session, $event)">✎</button>
            <button class="icon-action-btn delete-btn" :title="t('chatDelete')" @click="deleteSession(session.id, $event)">🗑</button>
          </template>
        </div>
      </div>
    </div>

    <!-- Liman seçilmemişse: sohbete başlamadan önce seçim iste -->
    <div v-else-if="!selectedFacility" class="facility-gate">
      <p>{{ t('chatSelectFacilityPrompt') }}</p>
      <select v-model="selectedFacility" class="facility-select">
        <option value="" disabled selected>{{ t('chatSelectFacilityPlaceholder') }}</option>
        <option
          v-for="fac in availableFacilities"
          :key="fac"
          :value="fac"
          :class="{ 'option-light-shade': isLightShadeFacility(fac) }"
        >{{ facilityLabel(fac) }}</option>
      </select>
    </div>

    <!-- Mesaj alanı -->
    <main v-else class="chat-area" ref="messagesContainer">
      <div v-if="messages.length === 0" class="hero-empty">
        <div class="hero-icon-badge">
          <img src="/logo-icon.png" alt="logo" class="hero-icon" />
        </div>
        <h2>{{ t('chatHeroTitle') }}</h2>
        <p>{{ t('chatHeroSubtitle') }}</p>

        <div class="hero-input-row">
          <textarea
            v-model="userInput"
            :placeholder="t('chatInputPlaceholder')"
            rows="1"
            @keydown.enter.prevent="handleEnter"
          ></textarea>
          <button class="send-btn" :disabled="!userInput.trim() || isLoading" @click="sendMessage()">➤</button>
        </div>

        <div class="hero-suggestions">
          <button class="suggestion-chip" @click="askSuggestion(t('chatSuggestion1'))">
            {{ t('chatSuggestion1') }}
          </button>
          <button class="suggestion-chip" @click="askSuggestion(t('chatSuggestion2'))">
            {{ t('chatSuggestion2') }}
          </button>
          <button class="suggestion-chip" @click="askSuggestion(t('chatSuggestion3'))">
            {{ t('chatSuggestion3') }}
          </button>
        </div>
      </div>

      <div v-else class="messages-column">
        <div
          v-for="(msg, index) in messages"
          :key="index"
          class="message-row"
          :class="msg.role"
        >
          <div class="bubble" :class="{ error: msg.isError }">
            {{ msg.content }}
          </div>
        </div>

        <div v-if="isLoading" class="message-row assistant">
          <div class="bubble typing">
            <span class="dot"></span>
            <span class="dot"></span>
            <span class="dot"></span>
          </div>
        </div>
      </div>
    </main>

    <footer v-if="!showHistory && !showAdminPanel && selectedFacility && messages.length > 0" class="input-area">
      <div class="input-area-inner">
      <textarea
        v-model="userInput"
        :placeholder="t('chatInputPlaceholder')"
        rows="1"
        @keydown.enter.prevent="handleEnter"
      ></textarea>
      <button class="send-btn" :disabled="!userInput.trim() || isLoading" @click="sendMessage()">
        {{ t('chatSend') }}
      </button>
      </div>
    </footer>
  </div>
</template>

<style scoped>
* {
  box-sizing: border-box;
}

.chat-window {
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, #0c2438 0%, #051627 100%);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  font-family: 'Segoe UI', system-ui, sans-serif;
}

.chat-header {
  background: transparent;
  color: white;
  padding: 1.1rem 1.5rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}

.header-icon {
  font-size: 1.2rem;
}

.header-title {
  font-weight: 700;
  font-size: 1.05rem;
}

.header-sep {
  color: rgba(255, 255, 255, 0.35);
  font-weight: 400;
}

.header-facility-select {
  color-scheme: dark;
  background: none;
  border: none;
  color: rgba(255, 255, 255, 0.75);
  font-size: 1.05rem;
  font-weight: 700;
  cursor: pointer;
  outline: none;
  padding: 0;
  scrollbar-width: thin;
  scrollbar-color: #2c5f85 #0c2438;
}

.header-facility-select::-webkit-scrollbar {
  width: 10px;
}
.header-facility-select::-webkit-scrollbar-track {
  background: #0c2438;
}
.header-facility-select::-webkit-scrollbar-thumb {
  background: #2c5f85;
  border-radius: 6px;
  border: 2px solid #0c2438;
}
.header-facility-select::-webkit-scrollbar-thumb:hover {
  background: #4a86ad;
}

.header-facility-select option {
  color: #ffffff;
  background: #0c2438;
}

.header-facility-select option.option-light-shade {
  background: #1d3346;
}

.header-facility-text {
  color: rgba(255, 255, 255, 0.75);
  font-size: 1.05rem;
  font-weight: 700;
}

.header-actions {
  display: flex;
  gap: 0.6rem;
}

.header-action-btn {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(111, 168, 208, 0.3);
  border-radius: 999px;
  color: #cfe2f2;
  cursor: pointer;
  font-size: 0.85rem;
  font-weight: 600;
  line-height: 1;
  padding: 0.5rem 0.9rem;
  transition: background 0.15s, border-color 0.15s;
}

.header-action-btn:hover {
  background: rgba(111, 168, 208, 0.15);
  border-color: rgba(111, 168, 208, 0.55);
}

.action-icon {
  font-size: 1rem;
  line-height: 1;
}

.history-panel {
  flex: 1;
  overflow-y: auto;
  padding: 0.75rem;
}

.facility-gate {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  padding: 1.5rem;
  text-align: center;
  color: #e2e8f0;
  font-size: 0.9rem;
}

.facility-select {
  color-scheme: dark;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 14px;
  color: white;
  font-size: 0.85rem;
  padding: 0.45rem 0.6rem;
  outline: none;
  scrollbar-width: thin;
  scrollbar-color: #2c5f85 #0c2438;
}

.facility-select::-webkit-scrollbar {
  width: 10px;
}
.facility-select::-webkit-scrollbar-track {
  background: #0c2438;
}
.facility-select::-webkit-scrollbar-thumb {
  background: #2c5f85;
  border-radius: 6px;
  border: 2px solid #0c2438;
}
.facility-select::-webkit-scrollbar-thumb:hover {
  background: #4a86ad;
}

.facility-select option {
  color: #ffffff;
  background: #0c2438;
}

.facility-select option.option-light-shade {
  background: #1d3346;
}

.history-empty {
  text-align: center;
  color: #64748b;
  margin-top: 2rem;
  font-size: 0.9rem;
}

.history-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.65rem 0.75rem;
  background: rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(8px);
  border-radius: 10px;
  margin-bottom: 0.5rem;
  cursor: pointer;
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: white;
}

.history-item:hover {
 background: rgba(255, 255, 255, 0.16);
}

.history-title {
      color: white;
}

.history-meta {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  flex-wrap: wrap;
}

.history-date {
    color: rgba(255, 255, 255, 0.6);
}

.history-facility {
  color: rgba(255, 255, 255, 0.55);
  font-size: 0.72rem;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 999px;
  padding: 0.05rem 0.45rem;
}

.title-input {
  width: 100%;
  background: rgba(255, 255, 255, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.35);
  border-radius: 6px;
  color: white;
  font-size: 0.9rem;
  padding: 0.2rem 0.4rem;
  outline: none;
}

.history-item-actions {
  display: flex;
  gap: 0.35rem;
  flex-shrink: 0;
}

.icon-action-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 0.85rem;
  opacity: 0.5;
  color: white;
}

.icon-action-btn:hover {
  opacity: 1;
}

.chat-area {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
}

.messages-column {
  width: 100%;
  max-width: 760px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
}

.hero-empty {
  margin: auto;
  width: 100%;
  max-width: 620px;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 0.4rem;
  padding: 2rem 1rem;
}

.hero-icon-badge {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: #12324c;
  border: 1px solid rgba(111, 168, 208, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 0.9rem;
}

.hero-icon {
  width: 75px;
  height: 75px;
  object-fit: contain;
}

.hero-empty h2 {
  margin: 0;
  font-size: 1.65rem;
  font-weight: 700;
  color: white;
}

.hero-empty p {
  margin: 0.35rem 0 1.75rem;
  color: #7d9cbd;
  font-size: 0.92rem;
}

.hero-input-row {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 0.6rem;
  background: #0e2c46;
  border: 1px solid rgba(111, 168, 208, 0.25);
  border-radius: 14px;
  padding: 0.5rem 0.6rem 0.5rem 1.1rem;
}

.hero-input-row textarea {
  flex: 1;
  background: transparent;
  border: none;
  color: white;
  font-size: 0.95rem;
  font-family: inherit;
  resize: none;
  outline: none;
  padding: 0.5rem 0;
}

.hero-input-row textarea::placeholder {
  color: #5c7d9c;
}

.hero-input-row .send-btn {
  flex-shrink: 0;
  width: 38px;
  height: 38px;
  border-radius: 50%;
  background: transparent;
  border: none;
  color: #7fb3e0;
  padding: 0;
  font-size: 1.1rem;
  display: flex;
  align-items: center;
  justify-content: center;
  align-self: center;
  transition: background 0.15s;
}

.hero-input-row .send-btn:hover:not(:disabled) {
  background: rgba(111, 168, 208, 0.15);
}

.hero-suggestions {
  margin-top: 1.5rem;
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
  justify-content: center;
}

.suggestion-chip {
  background: #0e2c46;
  border: 1px solid rgba(111, 168, 208, 0.3);
  color: #cfe2f2;
  padding: 0.7rem 1.2rem;
  border-radius: 999px;
  font-size: 0.85rem;
  cursor: pointer;
  text-align: center;
  transition: background 0.15s, border-color 0.15s;
}

.suggestion-chip:hover {
  background: #12324c;
  border-color: rgba(111, 168, 208, 0.55);
}

.message-row {
  display: flex;
}

.message-row.user {
  justify-content: flex-end;
}

.message-row.assistant {
  justify-content: flex-start;
}

.bubble {
  max-width: 80%;
  padding: 0.55rem 0.8rem;
  border-radius: 12px;
  line-height: 1.4;
  font-size: 0.88rem;
  white-space: pre-wrap;
}

.message-row.user .bubble {
  background: rgba(34, 211, 238, 0.35);
  backdrop-filter: blur(8px);
  color: white;
  border: 1px solid rgba(34, 211, 238, 0.4);
  border-bottom-right-radius: 4px;
}

.message-row.assistant .bubble {
  background: rgba(255, 255, 255, 0.12);
  backdrop-filter: blur(8px);
  color: #f0f9ff;
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-bottom-left-radius: 4px;
}

.bubble.error {
  background: #fef2f2;
  color: #991b1b;
  border-color: #fca5a5;
}

.typing {
  display: flex;
  gap: 4px;
  padding: 0.75rem 0.9rem;
}

.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #0891b2;
  opacity: 0.4;
  animation: blink 1.4s infinite both;
}

.dot:nth-child(2) { animation-delay: 0.2s; }
.dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes blink {
  0%, 80%, 100% { opacity: 0.3; transform: scale(0.85); }
  40% { opacity: 1; transform: scale(1); }
}

.input-area {
  padding: 0.75rem;
  background: rgba(255, 255, 255, 0.06);
  backdrop-filter: blur(10px);
  border-top: 1px solid rgba(255, 255, 255, 0.15);
}

.input-area-inner {
  display: flex;
  gap: 0.5rem;
  max-width: 760px;
  margin: 0 auto;
}

.input-area textarea {
  flex: 1;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.25);
  border-radius: 10px;
  padding: 0.5rem 0.7rem;
  font-size: 0.88rem;
  font-family: inherit;
  color: white;
  resize: none;
  outline: none;
}


.input-area textarea::placeholder {
  color: rgba(255, 255, 255, 0.5);
}


.input-area textarea:focus {
  border-color: #0891b2;
  box-shadow: 0 0 0 3px rgba(8, 145, 178, 0.12);
}

.send-btn {
  background: linear-gradient(135deg, #0c4a6e, #0891b2);
  color: white;
  border: none;
  padding: 0 1rem;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  font-size: 0.85rem;
}

.send-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

</style>