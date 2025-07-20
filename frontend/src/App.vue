<script setup lang="ts">
import { onMounted } from 'vue'
import { useAppStore } from '@/stores/app'
import AppLayout from '@/components/layout/AppLayout.vue'

const store = useAppStore()

onMounted(() => {
  // Initialize dark theme
  document.documentElement.classList.add('dark')
  store.updateUserSettings({ theme: 'dark' })
})
</script>

<template>
  <div id="app" class="min-h-screen bg-background text-foreground">
    <AppLayout />
  </div>
</template>

<style>
/* Global styles are handled in main.css */
</style>
