import axios from 'axios'

// Girişli kullanıcılar için backend'e (user_activity tablosu), misafirler
// için sadece bu sekmenin ömrü boyunca sessionStorage'a yazılır.
const GUEST_KEY = 'corex_guest_activity'
const MAX_GUEST_ENTRIES = 5

function isLoggedIn() {
  return !!localStorage.getItem('corex_token')
}

export async function logActivity(actionType, facilityId = null) {
  if (isLoggedIn()) {
    try {
      const token = localStorage.getItem('corex_token')
      await axios.post(
        '/api/activity',
        { action_type: actionType, facility_id: facilityId },
        { headers: { Authorization: `Bearer ${token}` } }
      )
    } catch (e) {
      // Sessizce yok say; dashboard bir sonraki açılışta güncel hâlini gösterir.
    }
    return
  }

  const list = JSON.parse(sessionStorage.getItem(GUEST_KEY) || '[]')
  list.unshift({ action_type: actionType, facility_id: facilityId, created_at: new Date().toISOString() })
  sessionStorage.setItem(GUEST_KEY, JSON.stringify(list.slice(0, MAX_GUEST_ENTRIES)))
}

export async function loadRecentActivity() {
  if (isLoggedIn()) {
    try {
      const token = localStorage.getItem('corex_token')
      const res = await axios.get('/api/activity', {
        headers: { Authorization: `Bearer ${token}` },
      })
      return res.data.activities || []
    } catch (e) {
      return []
    }
  }
  return JSON.parse(sessionStorage.getItem(GUEST_KEY) || '[]')
}
