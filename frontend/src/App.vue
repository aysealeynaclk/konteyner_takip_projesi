<script setup>
import OceanMap from './components/OceanMap.vue'
import ChatWidget from './components/ChatWidget.vue'
</script>

<template>
  <div class="app-root">
    <OceanMap />
    <ChatWidget />
  </div>
</template>


<style scoped>
.app-root {
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  position: relative;
}
</style>