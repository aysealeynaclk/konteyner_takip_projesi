<script setup>
import { t, language, setLanguage } from '../i18n'

defineProps({
  activeTab: { type: String, required: true },
  isAuthenticated: { type: Boolean, default: false },
  isGuest: { type: Boolean, default: false },
  currentUsername: { type: String, default: '' },
})

const emit = defineEmits(['change-tab', 'logout'])
</script>

<template>
  <nav class="top-nav">
    <div class="nav-brand">
      <img src="/logo-icon.png" alt="Corex logo" class="nav-logo" />
      <span>COREX</span>
    </div>

    <div class="nav-tabs">
      <button :class="{ active: activeTab === 'dashboard' }" @click="emit('change-tab', 'dashboard')">
        📊 {{ t('navDashboard') }}
      </button>
      <button :class="{ active: activeTab === 'map' }" @click="emit('change-tab', 'map')">
        🗺️ {{ t('navMap') }}
      </button>
      <button :class="{ active: activeTab === 'chat' }" @click="emit('change-tab', 'chat')">
        💬 {{ t('navChat') }} <span v-if="!isAuthenticated" class="lock-icon">🔒</span>
      </button>
    </div>

    <div class="nav-right">
      <div class="lang-switch">
        <button :class="{ active: language === 'tr' }" @click="setLanguage('tr')">TR</button>
        <button :class="{ active: language === 'en' }" @click="setLanguage('en')">EN</button>
      </div>
      <span v-if="isAuthenticated" class="status-badge user">👤 {{ currentUsername }}</span>
      <span v-else class="status-badge guest">🤚 {{ t('guestLabel') }}</span>
      <button class="logout-btn" @click="emit('logout')">{{ isGuest ? t('loginNav') : t('logout') }}</button>
    </div>
  </nav>
</template>

<style scoped>
* {
  box-sizing: border-box;
}

.top-nav {
  flex-shrink: 0;
  height: 64px;
  display: flex;
  align-items: center;
  gap: 1.5rem;
  padding: 0 1.25rem;
  background: rgba(6, 44, 67, 0.9);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.12);
  color: white;
  font-family: 'Segoe UI', system-ui, sans-serif;
  position: relative;
  z-index: 1500;
}

.nav-brand {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 700;
  font-size: 1.05rem;
  letter-spacing: 0.5px;
  flex-shrink: 0;
}

.nav-logo {
  width: 32px;
  height: 32px;
  object-fit: contain;
}

.nav-tabs {
  display: flex;
  gap: 0.4rem;
  flex: 1;
}

.nav-tabs button {
  background: transparent;
  border: none;
  color: rgba(255, 255, 255, 0.65);
  padding: 0.5rem 0.9rem;
  border-radius: 10px;
  font-size: 0.88rem;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}

.nav-tabs button:hover {
  background: rgba(255, 255, 255, 0.08);
  color: white;
}

.nav-tabs button.active {
  background: rgba(34, 211, 238, 0.18);
  color: white;
  border: 1px solid rgba(34, 211, 238, 0.4);
}

.lock-icon {
  font-size: 0.75rem;
  opacity: 0.8;
}

.nav-right {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  flex-shrink: 0;
}

.lang-switch {
  display: flex;
  gap: 0.2rem;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 999px;
  padding: 0.15rem;
}

.lang-switch button {
  background: transparent;
  border: none;
  color: rgba(255, 255, 255, 0.65);
  padding: 0.25rem 0.5rem;
  border-radius: 999px;
  font-size: 0.7rem;
  font-weight: 600;
  cursor: pointer;
}

.lang-switch button.active {
  background: rgba(34, 211, 238, 0.3);
  color: white;
}

.status-badge {
  font-size: 0.82rem;
  white-space: nowrap;
}

.status-badge.guest {
  background: rgba(234, 179, 8, 0.18);
  border: 1px solid rgba(234, 179, 8, 0.4);
  color: #fde68a;
  padding: 0.3rem 0.7rem;
  border-radius: 999px;
}

.logout-btn {
  background: rgba(255, 255, 255, 0.12);
  border: none;
  color: white;
  padding: 0.4rem 0.85rem;
  border-radius: 999px;
  font-size: 0.8rem;
  cursor: pointer;
  white-space: nowrap;
}

.logout-btn:hover {
  background: rgba(255, 255, 255, 0.22);
}

/* Mobil: dar ekranlarda sekme metinleri ve boşluklar daralsın */
@media (max-width: 700px) {
  .top-nav {
    gap: 0.6rem;
    padding: 0 0.6rem;
  }

  .nav-tabs {
    gap: 0.2rem;
  }

  .nav-tabs button {
    padding: 0.4rem 0.5rem;
    font-size: 0.78rem;
  }

  .status-badge:not(.guest) {
    display: none;
  }
}
</style>
