<script setup>
import { ref, nextTick, onMounted, computed } from 'vue'
import axios from 'axios'

const props = defineProps({
  token: { type: String, required: false },
})

const API_URL = 'http://127.0.0.1:8000/api/chat'
const HISTORY_KEY = 'konteyner_takip_gecmis_sohbetler'

const isOpen = ref(false)
const showHistory = ref(false)
const messages = ref([])
const userInput = ref('')
const isLoading = ref(false)
const messagesContainer = ref(null)
const pastSessions = ref([])

onMounted(() => {
  // Sayfa açılınca aktif sohbet BOŞ başlar (istediğin gibi)
  // Ama geçmiş oturumları yükleyelim, çekmecede göstermek için
  const saved = localStorage.getItem(HISTORY_KEY)
  if (saved) {
    try {
      pastSessions.value = JSON.parse(saved)
    } catch (e) {
      pastSessions.value = []
    }
  }
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
    const response = await axios.post(API_URL, { message: messageText }, { headers })
    messages.value.push({ role: 'assistant', content: response.data.reply })
  } catch (error) {
    messages.value.push({
      role: 'assistant',
      content: 'Üzgünüm, sunucuya bağlanırken bir sorun oluştu.',
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
  if (messages.value.length > 0) {
    saveCurrentAsHistory()
  }
  messages.value = []
  showHistory.value = false
}

function saveCurrentAsHistory() {
  const firstUserMsg = messages.value.find(m => m.role === 'user')
  const title = firstUserMsg ? firstUserMsg.content.slice(0, 40) : 'Sohbet'

  pastSessions.value.unshift({
    id: Date.now(),
    title,
    messages: [...messages.value],
    date: new Date().toLocaleString('tr-TR'),
  })

  // En fazla son 20 sohbeti sakla
  pastSessions.value = pastSessions.value.slice(0, 20)
  localStorage.setItem(HISTORY_KEY, JSON.stringify(pastSessions.value))
}

function loadSession(session) {
  messages.value = [...session.messages]
  showHistory.value = false
  scrollToBottom()
}

function deleteSession(id, event) {
  event.stopPropagation()
  pastSessions.value = pastSessions.value.filter(s => s.id !== id)
  localStorage.setItem(HISTORY_KEY, JSON.stringify(pastSessions.value))
}

const hasActiveChat = computed(() => messages.value.length > 0)
</script>

<template>
  <!-- Kapalıyken görünen amblem -->
  <button v-if="!isOpen" class="chat-bubble" @click="toggleChat">
    <span class="bubble-icon">⚓</span>
  </button>

  <!-- Açık sohbet penceresi -->
  <div v-else class="chat-window">
    <header class="chat-header">
      <div class="header-left">
        <span class="header-icon">⚓</span>
        <span class="header-title">Konteyner Asistanı</span>
      </div>
      <div class="header-actions">
        <button class="icon-btn" title="Geçmiş sohbetler" @click="toggleHistory">
          🕑
        </button>
        <button class="icon-btn" title="Yeni sohbet" @click="startNewChat">
          ✚
        </button>
        <button class="icon-btn" title="Kapat" @click="toggleChat">
          ✕
        </button>
      </div>
    </header>

    <!-- Geçmiş sohbetler paneli -->
    <div v-if="showHistory" class="history-panel">
      <div v-if="pastSessions.length === 0" class="history-empty">
        Henüz kayıtlı sohbet yok.
      </div>
      <div
        v-for="session in pastSessions"
        :key="session.id"
        class="history-item"
        @click="loadSession(session)"
      >
        <div class="history-item-text">
          <div class="history-title">{{ session.title }}</div>
          <div class="history-date">{{ session.date }}</div>
        </div>
        <button class="delete-btn" @click="deleteSession(session.id, $event)">🗑</button>
      </div>
    </div>

    <!-- Mesaj alanı -->
    <main v-else class="chat-area" ref="messagesContainer">
      <div v-if="messages.length === 0" class="empty-state">
        <p>Bir konteyner numarası veya limana dair bir soru sorarak başlayabilirsin.</p>
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
        placeholder="Bir soru yaz..."
        rows="1"
        @keydown.enter.prevent="handleEnter"
      ></textarea>
      <button class="send-btn" :disabled="!userInput.trim() || isLoading" @click="sendMessage()">
        Gönder
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
  width: 60px;
  height: 60px;
  border-radius: 50%;
  background: linear-gradient(135deg, #0c4a6e, #0891b2);
  border: none;
  box-shadow: 0 4px 16px rgba(8, 145, 178, 0.5);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  transition: transform 0.2s;
}

.chat-bubble:hover {
  transform: scale(1.08);
}

.bubble-icon {
  font-size: 1.6rem;
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
  z-index: 1000;
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

.delete-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 0.85rem;
  opacity: 0.5;
}

.delete-btn:hover {
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