import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { watch } from 'vue'

import App from './App.vue'
import router from './router'
import './theme.css'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/controls/dist/style.css'
import '@vue-flow/minimap/dist/style.css'

import { registerShortcuts } from './shortcuts'

// Stores
import { useMotionStore } from './stores/motion'
import { useSpritesStore } from './stores/sprites'
import { useModelsStore } from './stores/models'
import { useWorkflowsStore } from './stores/workflows'
import { useProjectsStore } from './stores/projects'
import { useFilesStore } from './stores/files'
import { useSettingsStore } from './stores/settings'

const app = createApp(App)
const pinia = createPinia()

// Install Pinia BEFORE using any store
app.use(pinia)
app.use(router)

// Now it's safe to use stores
const settings = useSettingsStore()
settings.load()

// Register stores globally for shortcuts
app.config.globalProperties.$motion = useMotionStore()
app.config.globalProperties.$sprites = useSpritesStore()
app.config.globalProperties.$models = useModelsStore()
app.config.globalProperties.$workflows = useWorkflowsStore()
app.config.globalProperties.$projects = useProjectsStore()
app.config.globalProperties.$files = useFilesStore()

// Register global keyboard shortcuts
registerShortcuts(app)

app.mount('#app')

// Theme watcher
watch(
  () => settings.theme,
  (theme) => {
    document.documentElement.classList.toggle('light', theme === 'light')
  }
)
