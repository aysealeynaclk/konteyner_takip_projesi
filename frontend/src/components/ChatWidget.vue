<script setup>
import { ref, nextTick, onMounted, computed } from 'vue'
import axios from 'axios'
import { language, t } from '../i18n'

const props = defineProps({
  token: { type: String, required: false },
})

const API_URL = '/api/chat'
const HISTORY_API_URL = '/api/chat/sessions'

const isOpen = ref(false)
const showHistory = ref(false)
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
  return parsed.toLocaleString(language.value === 'en' ? 'en-US' : 'tr-TR')
}

function normalizeSession(session) {
  return {
    id: session.id,
    title: session.title,
    messages: session.messages || [],
    created_at: session.created_at,
    updated_at: session.updated_at,
    date: formatSessionDate(session.updated_at || session.created_at),
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
})

function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

function toggleChat() {
  isOpen.value = !isOpen.value
  if (isOpen.value) scrollToBottom()
}

function toggleHistory() {
  showHistory.value = !showHistory.value
  if (showHistory.value) loadSessions()
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

// Mevcut sohbeti "geçmiş" olarak kaydedip yeni bir sohbete başlar
function startNewChat() {
  messages.value = []
  activeSessionId.value = null
  showHistory.value = false
}

function loadSession(session) {
  messages.value = [...session.messages]
  activeSessionId.value = session.id
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
</script>

<template>
  <!-- Kapalıyken görünen amblem -->
  <button v-if="!isOpen" class="chat-bubble" @click="toggleChat">
    <img src="/chat-logo.svg" alt="logo" class="bubble-img" />
  </button>

  <!-- Açık sohbet penceresi -->
  <div v-else class="chat-window">
    <header class="chat-header">
      <div class="header-left">
        <img src="/chat-logo.svg" alt="logo" class="header-img" />
        <span class="header-title">{{ t('chatTitle') }}</span>
      </div>
      <div class="header-actions">
        <button class="icon-btn" :title="t('chatHistoryTitle')" @click="toggleHistory">
          🕑
        </button>
        <button class="icon-btn" :title="t('chatNewChat')" @click="startNewChat">
          ✚
        </button>
        <button class="icon-btn" :title="t('chatClose')" @click="toggleChat">
          ✕
        </button>
      </div>
    </header>

    <!-- Geçmiş sohbetler paneli -->
    <div v-if="showHistory" class="history-panel">
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
          <div class="history-date">{{ session.date }}</div>
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

    <!-- Mesaj alanı -->
    <main v-else class="chat-area" ref="messagesContainer">
      <div v-if="messages.length === 0" class="empty-state">
        <p>{{ t('chatEmptyState') }}</p>
      </div>

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
    </main>

    <footer v-if="!showHistory" class="input-area">
      <textarea
        v-model="userInput"
        :placeholder="t('chatInputPlaceholder')"
        rows="1"
        @keydown.enter.prevent="handleEnter"
      ></textarea>
      <button class="send-btn" :disabled="!userInput.trim() || isLoading" @click="sendMessage()">
        {{ t('chatSend') }}
      </button>
    </footer>
  </div>
</template>

<style scoped>
* {
  box-sizing: border-box;
}

.chat-bubble {
  position: fixed;
  bottom: 24px;
  right: 24px;
  width: 72px;
  height: 72px;
  border-radius: 50%;
  background: linear-gradient(135deg, #0c4a6e, #0891b2);
  border: none;
  box-shadow: 0 4px 16px rgba(8, 145, 178, 0.5);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2200;
  transition: transform 0.2s;
}

.chat-bubble:hover {
  transform: scale(1.08);
}

.bubble-icon {
  font-size: 1.6rem;
}

.bubble-img {
  width: 72px;
  height: 72px;
  object-fit: cover;
  border-radius: 50%;
  background: transparent;
  padding: 0;
  box-shadow: 0 10px 30px rgba(2,6,23,0.14);
}

.header-img {
  width: 34px;
  height: 34px;
  object-fit: contain;
  border-radius: 6px;
  background: transparent;
  padding: 2px;
}

.chat-window {
  position: fixed;
  bottom: 24px;
  right: 24px;
  width: 380px;
  height: 560px;
  max-height: 80vh;
  background: rgba(8, 47, 73, 0.35);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 18px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.45);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  z-index: 2200;
  font-family: 'Segoe UI', system-ui, sans-serif;
}

.chat-header {
  background: rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(10px);
  color: white;
  padding: 0.85rem 1rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid rgba(255, 255, 255, 0.15);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.header-icon {
  font-size: 1.2rem;
}

.header-title {
  font-weight: 600;
  font-size: 0.95rem;
}

.header-actions {
  display: flex;
  gap: 0.25rem;
}

.icon-btn {
  background: rgba(255, 255, 255, 0.15);
  border: none;
  color: white;
  width: 28px;
  height: 28px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.85rem;
  display: flex;
  align-items: center;
  justify-content: center;
}

.icon-btn:hover {
  background: rgba(255, 255, 255, 0.28);
}

.history-panel {
  flex: 1;
  overflow-y: auto;
  padding: 0.75rem;
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

.history-date {
    color: rgba(255, 255, 255, 0.6);
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

.empty-state {
  text-align: center;
  color: #64748b;
  margin: auto;
  padding: 1rem;
  font-size: 0.88rem;
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
  display: flex;
  gap: 0.5rem;
  padding: 0.75rem;
  background: rgba(255, 255, 255, 0.06);
  backdrop-filter: blur(10px);
  border-top: 1px solid rgba(255, 255, 255, 0.15);
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