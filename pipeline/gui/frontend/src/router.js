import { createRouter, createWebHistory } from 'vue-router'

import MotionPage from './pages/MotionPage.vue'
import SpritePage from './pages/SpritePage.vue'
import ModelPage from './pages/ModelPage.vue'
import ProjectPage from './pages/ProjectPage.vue'
import WorkflowGraphPage from './pages/WorkflowGraphPage.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/motion' },
    { path: '/motion', component: MotionPage },
    { path: '/sprites', component: SpritePage },
    { path: '/models', component: ModelPage },
    { path: '/projects', component: ProjectPage },
    { path: '/workflows/graph', component: WorkflowGraphPage },
    { path: '/:pathMatch(.*)*', redirect: '/motion' }
  ]
})

export default router
