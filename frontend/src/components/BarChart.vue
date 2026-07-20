<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  items: { type: Array, required: true }, // [{ label, value }]
  valueSuffix: { type: String, default: '' },
})

const CHART_HEIGHT = 200 // px — .bar-track ile birebir aynı olmalı

const maxValue = computed(() => Math.max(1, ...props.items.map(i => i.value)))
const maxIndex = computed(() => props.items.reduce((best, item, idx, arr) => (item.value > arr[best].value ? idx : best), 0))
const hovered = ref(null)

function barHeightPx(item) {
  return Math.max(2, Math.round((item.value / maxValue.value) * CHART_HEIGHT))
}
</script>

<template>
  <div class="bar-chart">
    <div class="bars-row">
      <div
        v-for="(item, idx) in items"
        :key="idx"
        class="bar-col"
        @mouseenter="hovered = idx"
        @mouseleave="hovered = null"
      >
        <div class="bar-track">
          <div v-if="hovered === idx" class="bar-tooltip">{{ item.value }}{{ valueSuffix }}</div>
          <div class="bar" :class="{ peak: idx === maxIndex }" :style="{ height: barHeightPx(item) + 'px' }"></div>
        </div>
        <div class="bar-label">{{ item.label }}</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.bar-chart {
  width: 100%;
}

.bars-row {
  display: flex;
  align-items: flex-end;
  justify-content: center;
  gap: 4px;
  overflow: visible;
  padding-bottom: 2px;
  width: 100%;
}

.bar-col {
  /* Az öğe varken (örn. 2 ay) 34px'e kadar büyür ve ortalanır; çok öğe
     varken (örn. 24 saat) hepsi orantılı küçülüp sığar — hiçbir zaman
     scrollbar gerekmez. */
  flex: 1 1 0;
  min-width: 10px;
  max-width: 34px;
  display: flex;
  flex-direction: column;
  align-items: center;
  cursor: default;
}

.bar-track {
  position: relative;
  height: 200px;
  width: 100%;
  display: flex;
  align-items: flex-end;
  justify-content: center;
}

.bar {
  width: 100%;
  max-width: 28px;
  background: linear-gradient(180deg, #7dd3fc 0%, #22d3ee 40%, #0891b2 100%);
  border-radius: 6px 6px 0 0;
  transition: opacity 0.15s, filter 0.15s;
}

.bar.peak {
  filter: brightness(1.12);
}

.bar-col:hover .bar {
  opacity: 0.8;
}

.bar-label {
  font-size: 0.65rem;
  color: rgba(255, 255, 255, 0.55);
  margin-top: 6px;
  white-space: nowrap;
}

.bar-tooltip {
  position: absolute;
  bottom: 100%;
  margin-bottom: 4px;
  background: rgba(6, 44, 67, 0.98);
  color: white;
  padding: 2px 6px;
  border-radius: 6px;
  font-size: 0.7rem;
  white-space: nowrap;
  z-index: 10;
  border: 1px solid rgba(255, 255, 255, 0.15);
}
</style>
