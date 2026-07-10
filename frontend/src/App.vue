<script setup>
import { ref, onMounted } from 'vue'
import OceanMap from './components/OceanMap.vue'
import ChatWidget from './components/ChatWidget.vue'
import LoginView from './components/LoginView.vue'

// Authentication state
const isAuthenticated = ref(false)
const isGuest = ref(false)
const authToken = ref(null)
const currentUsername = ref('')

onMounted(() => {
  // LocalStorage'dan önceki oturumu yükle (varsa)
  const token = localStorage.getItem('corex_token')
  const guest = localStorage.getItem('corex_guest')
  const uname = localStorage.getItem('corex_username')

  if (token) {
    authToken.value = token
    isAuthenticated.value = true
    currentUsername.value = uname || ''
  } else if (guest === 'true') {
    isGuest.value = true
  }
})

function handleLoginSuccess(payload) {
  authToken.value = payload.token
  currentUsername.value = payload.username || ''
  isAuthenticated.value = true
  isGuest.value = false
}

function handleGuestContinue() {
  isGuest.value = true
}

function handleLogout() {
  localStorage.removeItem('corex_token')
  localStorage.removeItem('corex_username')
  localStorage.removeItem('corex_is_admin')
  localStorage.removeItem('corex_guest')
  isAuthenticated.value = false
  isGuest.value = false
  authToken.value = null
  currentUsername.value = ''
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
      <OceanMap />

      <!-- Sadece giriş yapmış kullanıcılar chatbot'u görebilir -->
      <ChatWidget v-if="isAuthenticated" :token="authToken" />

      <!-- Sağ üstte kullanıcı bilgisi / çıkış butonu -->
      <div class="user-bar">
        <span v-if="isAuthenticated">👤 {{ currentUsername }}</span>
        <span v-else>👋 Misafir</span>
        <button class="logout-btn" @click="handleLogout">Çıkış</button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.app-root {
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  position: relative;
}

.user-bar {
  position: fixed;
  top: 16px;
  right: 16px;
  z-index: 1500;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  background: rgba(8, 47, 73, 0.5);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 999px;
  padding: 0.4rem 0.4rem 0.4rem 0.9rem;
  color: white;
  font-size: 0.85rem;
  font-family: 'Segoe UI', sans-serif;
}

.logout-btn {
  background: rgba(255, 255, 255, 0.12);
  border: none;
  color: white;
  padding: 0.35rem 0.75rem;
  border-radius: 999px;
  font-size: 0.78rem;
  cursor: pointer;
}

.logout-btn:hover {
  background: rgba(255, 255, 255, 0.22);
}
</style>