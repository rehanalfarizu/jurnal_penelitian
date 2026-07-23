<template>
  <div class="app-shell">
    <DashboardHome
      :is-dark-mode="isDarkMode"
      @toggle-theme="toggleTheme"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import DashboardHome from './components/DashboardHome.vue'

const isDarkMode = ref(false)

const applyTheme = () => {
  document.documentElement.setAttribute('data-theme', isDarkMode.value ? 'dark' : 'light')
}

const loadTheme = () => {
  const savedTheme = localStorage.getItem('theme')
  if (savedTheme) {
    isDarkMode.value = savedTheme === 'dark'
  } else {
    isDarkMode.value = window.matchMedia('(prefers-color-scheme: dark)').matches
  }
  applyTheme()
}

const toggleTheme = () => {
  isDarkMode.value = !isDarkMode.value
  localStorage.setItem('theme', isDarkMode.value ? 'dark' : 'light')
  applyTheme()
}

onMounted(() => {
  loadTheme()
})
</script>

<style scoped>
.app-shell {
  min-height: 100vh;
}
</style>
