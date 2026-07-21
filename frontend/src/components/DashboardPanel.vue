<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import axios from 'axios'
import { t, language, weekdayLabel, monthLabel } from '../i18n'
import { selectedFacility, availableFacilities, loadFacilities, facilityLabel, isLightShadeFacility } from '../facility'
import { loadRecentActivity } from '../activity'
import BarChart from './BarChart.vue'

const props = defineProps({
  isAuthenticated: { type: Boolean, default: false },
})
const emit = defineEmits(['go-login'])

const WEEKDAY_ORDER = ['Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi', 'Pazar']
const MONTH_ORDER = [
  'Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran',
  'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık',
]

const analytics = ref(null)
const isLoading = ref(false)
const period = ref('week')
const activities = ref([])

async function loadAnalytics() {
  isLoading.value = true
  try {
    const params = { period: period.value }
    // Liman seçilmemişse facility_id gönderilmez — backend bu durumda
    // tüm limanların birleşik/genel istatistiklerini döner.
    if (selectedFacility.value) params.facility_id = selectedFacility.value
    const res = await axios.get('/api/dashboard/analytics', { params })
    analytics.value = res.data
  } catch (e) {
    analytics.value = null
  } finally {
    isLoading.value = false
  }
}

async function refreshActivities() {
  activities.value = await loadRecentActivity()
}

onMounted(() => {
  loadFacilities()
  loadAnalytics()
  refreshActivities()
})

watch(selectedFacility, loadAnalytics)
watch(period, loadAnalytics)

const hourlyChartData = computed(() => {
  if (!analytics.value) return []
  return [...analytics.value.busy_hours]
    .sort((a, b) => a.hour - b.hour)
    .map(h => ({ label: String(h.hour).padStart(2, '0'), value: h.entry_count }))
})

const weekdayChartData = computed(() => {
  if (!analytics.value) return []
  const byName = Object.fromEntries(analytics.value.weekday_density.map(d => [d.weekday, d.entry_count]))
  return WEEKDAY_ORDER.map(name => ({ label: weekdayLabel(name).slice(0, 3), value: byName[name] || 0 }))
})

const monthlyChartData = computed(() => {
  if (!analytics.value) return []
  const byName = Object.fromEntries(analytics.value.monthly_density.map(d => [d.month, d.entry_count]))
  return MONTH_ORDER.filter(name => name in byName).map(name => ({ label: monthLabel(name).slice(0, 3), value: byName[name] }))
})

// "Tüm Limanlar" seçiliyken limanları birbiriyle karşılaştıran ek grafik —
// her limanın günlük ortalama giriş sayısı (toplam değil — limanların
// verideki gün sayısı farklı olabildiği için adil karşılaştırma sağlar),
// dashboard'daki sabit liman sırasıyla.
const facilityActivityChartData = computed(() => {
  if (!analytics.value?.facility_activity) return []
  return analytics.value.facility_activity.map(f => ({ label: f.facility_id, value: f.avg_entries_per_day }))
})

const changePercent = computed(() => analytics.value?.period_comparison?.change_percent ?? null)
const changeArrow = computed(() => {
  if (changePercent.value === null) return ''
  if (changePercent.value > 0) return '▲'
  if (changePercent.value < 0) return '▼'
  return '—'
})

function activityLabel(item) {
  if (item.action_type === 'facility_viewed') {
    return `${facilityLabel(item.facility_id)} ${t('dashboardActivityFacilityViewed')}`
  }

  let base = item.action_type
  if (item.action_type === 'admin_record_added') base = t('dashboardActivityAdminRecordAdded')
  else if (item.action_type === 'chatbot_query') base = t('dashboardActivityChatbotQuery')

  // "Tüm Limanlar" seçiliyken hangi limana ait olduğu belli olsun diye ek etiket.
  if (!selectedFacility.value && item.facility_id) {
    return `${base} — ${facilityLabel(item.facility_id)}`
  }
  return base
}

function formatActivityDate(value) {
  if (!value) return ''
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return value
  return parsed.toLocaleString(language.value === 'en' ? 'en-US' : 'tr-TR')
}
</script>

<template>
  <div class="dashboard-page">
    <div class="dashboard-body">
      <div v-if="!isAuthenticated" class="guest-cta">
        <div class="guest-cta-text">
          <h3>{{ t('dashboardGuestCtaTitle') }}</h3>
          <p>{{ t('dashboardGuestCtaText') }}</p>
        </div>
        <button class="guest-cta-btn" @click="emit('go-login')">{{ t('loginNav') }} →</button>
      </div>

      <div class="facility-select-row">
        <select v-model="selectedFacility">
          <option value="">{{ t('dashboardAllFacilities') }}</option>
          <option
            v-for="fac in availableFacilities"
            :key="fac"
            :value="fac"
            :class="{ 'option-light-shade': isLightShadeFacility(fac) }"
          >{{ facilityLabel(fac) }}</option>
        </select>
      </div>

      <div v-if="isLoading" class="empty-note">{{ t('dashboardLoading') }}</div>

      <div v-else-if="analytics" class="dashboard-grid">
        <!-- Üst sıra: 3 ana istatistik kartı -->
        <div class="card stat-card span-4">
          <div class="card-label">{{ t('dashboardCurrentInYard') }}</div>
          <div class="card-value">{{ analytics.status_with_trend.current_in_yard }}</div>
        </div>
        <div class="card stat-card span-4">
          <div class="card-label">{{ t('dashboardTodayEntries') }}</div>
          <div class="card-value">{{ analytics.status_with_trend.today_entry_count }}</div>
        </div>
        <div class="card stat-card span-4">
          <div class="card-label-row">
            <span class="card-label">{{ t('dashboardChangeLabel') }}</span>
            <div class="period-toggle-mini">
              <button :class="{ active: period === 'week' }" @click="period = 'week'">{{ t('dashboardPeriodWeek') }}</button>
              <button :class="{ active: period === 'month' }" @click="period = 'month'">{{ t('dashboardPeriodMonth') }}</button>
            </div>
          </div>
          <div v-if="changePercent === null" class="card-value muted-small">{{ t('dashboardNoComparisonData') }}</div>
          <div v-else class="card-value change-value">
            <span class="change-arrow">{{ changeArrow }}</span>{{ Math.abs(changePercent) }}%
          </div>
        </div>

        <!-- Orta sıra: saatlik yoğunluk (geniş) + son işlemler -->
        <div class="card chart-card span-8">
          <div class="card-label">{{ t('dashboardHourlyTitle') }}</div>
          <BarChart :items="hourlyChartData" :value-suffix="' ' + t('dashboardEntriesUnit')" />
        </div>
        <div class="card activity-card span-4">
          <div class="card-label">{{ t('dashboardActivityTitle') }}</div>
          <div v-if="activities.length === 0" class="empty-note">{{ t('dashboardActivityEmpty') }}</div>
          <div v-else class="activity-list">
            <div v-for="(item, idx) in activities" :key="idx" class="activity-row">
              <div class="activity-text">{{ activityLabel(item) }}</div>
              <div class="activity-date">{{ formatActivityDate(item.created_at) }}</div>
            </div>
          </div>
        </div>

        <!-- Alt sıra: haftalık + aylık yoğunluk -->
        <div class="card chart-card span-6">
          <div class="card-label">{{ t('dashboardWeekdayTitle') }}</div>
          <BarChart :items="weekdayChartData" :value-suffix="' ' + t('dashboardEntriesUnit')" />
        </div>
        <div class="card chart-card span-6">
          <div class="card-label">{{ t('dashboardMonthlyTitle') }}</div>
          <BarChart :items="monthlyChartData" :value-suffix="' ' + t('dashboardEntriesUnit')" />
        </div>

        <!-- Sadece "Tüm Limanlar" seçiliyken: limanları karşılaştıran grafik -->
        <div v-if="!selectedFacility" class="card chart-card span-12">
          <div class="card-label">{{ t('dashboardFacilityActivityTitle') }}</div>
          <BarChart :items="facilityActivityChartData" :value-suffix="' ' + t('dashboardEntriesPerDayUnit')" />
        </div>

        <!-- Ek sıra: kalış süresi istatistikleri -->
        <div class="card stat-card small span-3">
          <div class="card-label">{{ t('dashboardDailyAverage') }}</div>
          <div class="card-value small-value">{{ analytics.status_with_trend.historical_avg_entries_per_day ?? '—' }}</div>
        </div>
        <div class="card stat-card small span-3">
          <div class="card-label">{{ t('dashboardAvgDwell') }}</div>
          <div class="card-value small-value">{{ analytics.dwell_time_stats.avg_minutes ?? '—' }}</div>
        </div>
        <div class="card stat-card small span-3">
          <div class="card-label">{{ t('dashboardMinDwell') }}</div>
          <div class="card-value small-value">{{ analytics.dwell_time_stats.min_minutes ?? '—' }}</div>
        </div>
        <div class="card stat-card small span-3">
          <div class="card-label">{{ t('dashboardMaxDwell') }}</div>
          <div class="card-value small-value">{{ analytics.dwell_time_stats.max_minutes ?? '—' }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
* {
  box-sizing: border-box;
}

.dashboard-page {
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, #0c2438 0%, #051627 100%);
  color: white;
  font-family: 'Segoe UI', system-ui, sans-serif;
  overflow: hidden;
}

.dashboard-body {
  height: 100%;
  overflow-y: auto;
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.guest-cta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 14px;
  padding: 1.1rem 1.4rem;
}

.guest-cta-text h3 {
  margin: 0 0 0.3rem;
  font-size: 1.15rem;
}

.guest-cta-text p {
  margin: 0;
  color: rgba(255, 255, 255, 0.65);
  font-size: 0.88rem;
}

.guest-cta-btn {
  flex-shrink: 0;
  background: linear-gradient(135deg, #0c4a6e, #0891b2);
  color: white;
  border: none;
  padding: 0.65rem 1.3rem;
  border-radius: 10px;
  font-weight: 600;
  cursor: pointer;
  font-size: 0.9rem;
  white-space: nowrap;
}

.guest-cta-btn:hover {
  opacity: 0.9;
}

.facility-select-row select {
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.25);
  border-radius: 8px;
  color: white;
  padding: 0.5rem 0.7rem;
  font-size: 0.9rem;
  outline: none;
}

.facility-select-row select option {
  color: #0b1a2b;
  background: #ffffff;
}

/* Harita dropdown'undaki gruplamayla aynı mantık (bkz. facility.js
   LIGHT_SHADE_FACILITIES) — burada beyaz zemin üstünde hafif gri. */
.facility-select-row select option.option-light-shade {
  background: #d8dde2;
}

.empty-note {
  color: rgba(255, 255, 255, 0.6);
  font-size: 0.85rem;
  padding: 0.4rem 0;
}

/* --- Blok/kart ızgarası --- */
.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  gap: 1rem;
}

.span-3 { grid-column: span 3; }
.span-4 { grid-column: span 4; }
.span-6 { grid-column: span 6; }
.span-8 { grid-column: span 8; }
.span-12 { grid-column: span 12; }

.card {
  background: rgba(255, 255, 255, 0.055);
  backdrop-filter: blur(18px) saturate(150%);
  -webkit-backdrop-filter: blur(18px) saturate(150%);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 16px;
  padding: 1.25rem;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.08), 0 8px 24px rgba(0, 0, 0, 0.2);
}

.card-label {
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.6px;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.5);
}

.card-label-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.card-value {
  margin-top: 0.5rem;
  font-size: 2rem;
  font-weight: 700;
  color: #ffffff;
  line-height: 1;
}

.card-value.small-value {
  font-size: 1.3rem;
}

.card-value.muted-small {
  font-size: 0.85rem;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.55);
}

.change-value {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.change-arrow {
  font-size: 1.4rem;
}

.stat-card.small {
  padding: 1rem 1.1rem;
}

.period-toggle-mini {
  display: flex;
  gap: 0.25rem;
}

.period-toggle-mini button {
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: rgba(255, 255, 255, 0.65);
  padding: 0.15rem 0.5rem;
  border-radius: 999px;
  font-size: 0.68rem;
  cursor: pointer;
}

.period-toggle-mini button.active {
  background: rgba(34, 211, 238, 0.25);
  color: white;
  border-color: rgba(34, 211, 238, 0.4);
}

.chart-card .card-label {
  margin-bottom: 0.75rem;
  display: block;
}

.activity-card .card-label {
  margin-bottom: 0.75rem;
  display: block;
}

.activity-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-height: 260px;
  overflow-y: auto;
}

.activity-row {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  padding: 0.6rem 0.75rem;
}

.activity-text {
  color: #f0f9ff;
  font-size: 0.85rem;
}

.activity-date {
  color: rgba(255, 255, 255, 0.5);
  font-size: 0.72rem;
  margin-top: 3px;
}

@media (max-width: 900px) {
  .span-3, .span-4, .span-6, .span-8 {
    grid-column: span 12;
  }
}

@media (max-width: 600px) {
  .dashboard-body {
    padding: 1rem;
  }

  .guest-cta {
    flex-direction: column;
    align-items: stretch;
    text-align: center;
  }
}
</style>
