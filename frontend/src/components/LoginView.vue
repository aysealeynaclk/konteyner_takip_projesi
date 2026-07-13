<script setup>
import { ref } from 'vue'
import axios from 'axios'
import { language, setLanguage, t } from '../i18n'

const emit = defineEmits(['login-success', 'guest-continue'])

const username = ref('')
const password = ref('')
const showPassword = ref(false)
const isLoading = ref(false)
const errorMessage = ref('')

async function handleLogin() {
  if (!username.value.trim() || !password.value.trim()) {
    errorMessage.value = t('fillCredentials')
    return
  }

  isLoading.value = true
  errorMessage.value = ''

  try {
    const response = await axios.post('/api/login', {
      username: username.value.trim(),
      password: password.value,
    })

    const { token, username: uname, is_admin } = response.data

    localStorage.setItem('corex_token', token)
    localStorage.setItem('corex_username', uname)
    localStorage.setItem('corex_is_admin', is_admin)

    emit('login-success', { token, username: uname, isAdmin: is_admin })
  } catch (error) {
    if (error.response?.status === 401) {
      errorMessage.value = t('wrongCredentials')
    } else {
      errorMessage.value = t('serverError')
    }
  } finally {
    isLoading.value = false
  }
}

function continueAsGuest() {
  localStorage.setItem('corex_guest', 'true')
  emit('guest-continue')
}

function handleEnter(e) {
  if (e.key === 'Enter') handleLogin()
}
</script>

<template>
  <div class="login-page">
    <div class="lang-switch">
      <button :class="{ active: language === 'tr' }" @click="setLanguage('tr')">TR</button>
      <button :class="{ active: language === 'en' }" @click="setLanguage('en')">EN</button>
    </div>

    <div class="login-card">
      <div class="brand">
        <span class="brand-icon">⚓</span>
        <h1>COREX</h1>
        <p class="brand-subtitle">Global Operations Platform</p>
      </div>

      <h2 class="login-title">{{ t('loginSubtitle') }}</h2>

      <div class="field">
        <label>{{ t('username') }}</label>
        <input
          v-model="username"
          type="text"
          :placeholder="t('usernamePlaceholder')"
          @keydown="handleEnter"
        />
      </div>

      <div class="field">
        <label>{{ t('password') }}</label>
        <div class="password-wrapper">
          <input
            v-model="password"
            :type="showPassword ? 'text' : 'password'"
            :placeholder="t('passwordPlaceholder')"
            @keydown="handleEnter"
          />
          <button class="eye-btn" type="button" @click="showPassword = !showPassword">
            {{ showPassword ? '🙈' : '👁️' }}
          </button>
        </div>
      </div>

      <p v-if="errorMessage" class="error-msg">{{ errorMessage }}</p>

      <button class="login-btn" :disabled="isLoading" @click="handleLogin">
        {{ isLoading ? t('loginButtonLoading') : t('loginButton') }}
      </button>

      <div class="divider"><span>{{ t('or') }}</span></div>

      <button class="guest-btn" @click="continueAsGuest">
        {{ t('guestButton') }}
      </button>
    </div>
  </div>
</template>

<style scoped>
* {
  box-sizing: border-box;
}

.login-page {
  position: fixed;
  inset: 0;
  z-index: 2000;
  display: flex;
  align-items: center;
  justify-content: center;
  background: radial-gradient(ellipse at top, #0c4a6e 0%, #051627 70%);
  font-family: 'Segoe UI', system-ui, sans-serif;
}

.lang-switch {
  position: fixed;
  top: 20px;
  right: 24px;
  display: flex;
  gap: 0.4rem;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 999px;
  padding: 0.25rem;
}

.lang-switch button {
  background: transparent;
  border: none;
  color: rgba(255, 255, 255, 0.65);
  padding: 0.3rem 0.7rem;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 600;
  cursor: pointer;
}

.lang-switch button.active {
  background: rgba(34, 211, 238, 0.25);
  color: white;
}

.login-card {
  width: 380px;
  max-width: 90vw;
  background: rgba(255, 255, 255, 0.06);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 20px;
  padding: 2.25rem 2rem;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
}

.brand {
  text-align: center;
  margin-bottom: 1.75rem;
}

.brand-icon {
  font-size: 2.25rem;
}

.brand h1 {
  color: white;
  font-size: 1.5rem;
  letter-spacing: 3px;
  margin: 0.25rem 0 0.15rem;
}

.brand-subtitle {
  color: rgba(255, 255, 255, 0.5);
  font-size: 0.75rem;
  margin: 0;
  letter-spacing: 1px;
}

.login-title {
  color: white;
  font-size: 1.05rem;
  font-weight: 500;
  text-align: center;
  margin-bottom: 1.5rem;
}

.field {
  margin-bottom: 1.1rem;
}

.field label {
  display: block;
  color: rgba(255, 255, 255, 0.7);
  font-size: 0.8rem;
  margin-bottom: 0.4rem;
}

.field input {
  width: 100%;
  padding: 0.65rem 0.85rem;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 10px;
  color: white;
  font-size: 0.9rem;
  outline: none;
}

.field input:focus {
  border-color: #22d3ee;
  box-shadow: 0 0 0 3px rgba(34, 211, 238, 0.15);
}

.field input::placeholder {
  color: rgba(255, 255, 255, 0.35);
}

.password-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.password-wrapper input {
  padding-right: 2.5rem;
}

.eye-btn {
  position: absolute;
  right: 0.5rem;
  background: none;
  border: none;
  cursor: pointer;
  font-size: 0.95rem;
  opacity: 0.7;
}

.error-msg {
  color: #fca5a5;
  font-size: 0.82rem;
  margin: -0.4rem 0 0.9rem;
  text-align: center;
}

.login-btn {
  width: 100%;
  padding: 0.75rem;
  background: linear-gradient(135deg, #0891b2, #0c4a6e);
  color: white;
  border: none;
  border-radius: 10px;
  font-weight: 600;
  font-size: 0.92rem;
  cursor: pointer;
  transition: opacity 0.15s;
}

.login-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.login-btn:hover:not(:disabled) {
  opacity: 0.92;
}

.divider {
  display: flex;
  align-items: center;
  text-align: center;
  color: rgba(255, 255, 255, 0.4);
  font-size: 0.75rem;
  margin: 1.25rem 0;
}

.divider::before,
.divider::after {
  content: '';
  flex: 1;
  border-bottom: 1px solid rgba(255, 255, 255, 0.15);
}

.divider span {
  padding: 0 0.75rem;
}

.guest-btn {
  width: 100%;
  padding: 0.7rem;
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.25);
  color: rgba(255, 255, 255, 0.85);
  border-radius: 10px;
  font-size: 0.88rem;
  cursor: pointer;
}

.guest-btn:hover {
  background: rgba(255, 255, 255, 0.06);
}
</style>