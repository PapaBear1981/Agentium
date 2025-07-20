<template>
  <div class="flex h-screen bg-background">
    <!-- Sidebar -->
    <Sidebar 
      :is-open="store.sidebarOpen"
      @toggle="store.toggleSidebar"
    />

    <!-- Main Content Area -->
    <div class="flex-1 flex flex-col min-w-0">
      <!-- Header -->
      <AppHeader />

      <!-- Main Content -->
      <main class="flex-1 overflow-hidden">
        <ChatView v-if="store.currentView === 'chat'" />
        <AgentView v-else-if="store.currentView === 'agents'" />
        <SettingsView v-else-if="store.currentView === 'settings'" />
      </main>
    </div>

    <!-- Settings Drawer -->
    <SettingsDrawer 
      :is-open="store.settingsOpen"
      @close="store.toggleSettings"
    />
  </div>
</template>

<script setup lang="ts">
import { useAppStore } from '@/stores/app'
import Sidebar from './Sidebar.vue'
import AppHeader from './AppHeader.vue'
import ChatView from '@/components/chat/ChatView.vue'
import AgentView from './AgentView.vue'
import SettingsView from './SettingsView.vue'
import SettingsDrawer from './SettingsDrawer.vue'

const store = useAppStore()
</script>
