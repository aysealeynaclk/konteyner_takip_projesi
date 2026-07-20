<script setup>
import { ref, watch, onMounted } from 'vue'
import OceanMap from './components/OceanMap.vue'
import ChatWidget from './components/ChatWidget.vue'
import LoginView from './components/LoginView.vue'
import DashboardPanel from './components/DashboardPanel.vue'
import TopNav from './components/TopNav.vue'
import { t } from './i18n'
import { tabRequested } from './facility'

// Aktif sekme: 'dashboard' | 'map' | 'chat'. Giriş/misafir seçimi yapılınca
// varsayılan olarak Dashboard açılır (iş verenin isteği).
const activeTab = ref('dashboard')

// Authentication state
const isAuthenticated = ref(false)
const isGuest = ref(false)
const authToken = ref(null)
const currentUsername = ref('')
const isAdmin = ref(false)

onMounted(() => {
  // LocalStorage'dan önceki oturumu yükle (varsa)
  const token = localStorage.getItem('corex_token')
  const guest = localStorage.getItem('corex_guest')
  const uname = localStorage.getItem('corex_username')
  const displayName = localStorage.getItem('corex_display_name')
  const admin = localStorage.getItem('corex_is_admin')

  if (token) {
    authToken.value = token
    isAuthenticated.value = true
    currentUsername.value = displayName || uname || ''
    isAdmin.value = admin === 'true'
  } else if (guest === 'true') {
    isGuest.value = true
  }
})

// Haritadan bir sekmeye geçiş istendiğinde (örn. "Chatbot'a Git") o sekmeye geç.
watch(tabRequested, (requested) => {
  if (requested) {
    activeTab.value = requested
    tabRequested.value = null
  }
})

function handleLoginSuccess(payload) {
  authToken.value = payload.token
  currentUsername.value = payload.displayName || payload.username || ''
  isAuthenticated.value = true
  isGuest.value = false
  isAdmin.value = !!payload.isAdmin
  activeTab.value = 'dashboard'
}

function handleGuestContinue() {
  isGuest.value = true
  activeTab.value = 'dashboard'
}

function handleLogout() {
  localStorage.removeItem('corex_token')
  localStorage.removeItem('corex_username')
  localStorage.removeItem('corex_display_name')
  localStorage.removeItem('corex_is_admin')
  localStorage.removeItem('corex_guest')
  isAuthenticated.value = false
  isGuest.value = false
  authToken.value = null
  currentUsername.value = ''
  isAdmin.value = false
  activeTab.value = 'dashboard'
}
</script>

<template>
  <div class="app-root">
    <LoginView
      v-if="!isAuthenticated && !isGuest"
      @login-success="handleLoginSuccess"
      @guest-continue="handleGuestContinue"
    />

    <template v-else>
      <TopNav
        :active-tab="activeTab"
        :is-authenticated="isAuthenticated"
        :is-guest="isGuest"
        :current-username="currentUsername"
        @change-tab="activeTab = $event"
        @logout="handleLogout"
      />

      <main class="tab-content">
        <DashboardPanel v-show="activeTab === 'dashboard'" :is-authenticated="isAuthenticated" @go-login="handleLogout" />

        <OceanMap :is-active="activeTab === 'map'" />

        <div v-show="activeTab === 'chat'" class="chat-tab-area">
          <ChatWidget v-if="isAuthenticated" :token="authToken" :is-admin="isAdmin" />
          <div v-else class="chat-locked">
            <div class="chat-locked-icon">🔒💬</div>
            <h3>{{ t('chatLockedTitle') }}</h3>
            <p>{{ t('chatLockedText') }}</p>
            <button class="login-cta" @click="handleLogout">{{ t('loginNav') }}</button>
          </div>
        </div>
      </main>
    </template>
  </div>
</template>

<style scoped>
* {
  box-sizing: border-box;
}

.app-root {
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.tab-content {
  flex: 1;
  position: relative;
  overflow: hidden;
}

.chat-tab-area {
  position: absolute;
  inset: 0;
}

.chat-locked {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  padding: 2rem;
  text-align: center;
  color: #e2e8f0;
  font-family: 'Segoe UI', system-ui, sans-serif;
  background: linear-gradient(180deg, #0c2438 0%, #051627 100%);
}

.chat-locked-icon {
  font-size: 2.2rem;
}

.chat-locked h3 {
  margin: 0;
  font-size: 1.1rem;
}

.chat-locked p {
  margin: 0;
  max-width: 420px;
  color: rgba(255, 255, 255, 0.65);
  font-size: 0.9rem;
}

.login-cta {
  margin-top: 0.5rem;
  background: linear-gradient(135deg, #0c4a6e, #0891b2);
  color: white;
  border: none;
  padding: 0.6rem 1.4rem;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  font-size: 0.9rem;
}

.login-cta:hover {
  opacity: 0.9;
}
</style>
