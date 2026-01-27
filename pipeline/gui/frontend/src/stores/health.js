import { defineStore } from 'pinia'
import { checkHealth } from '../api/health'

export const useHealthStore = defineStore('health', {
  state: () => ({
    online: false,
    lastCheck: null
  }),

  actions: {
    async check() {
      try {
        const result = await checkHealth()
        this.online = result?.status === 'ok'
      } catch (err) {
        this.online = false
      }

      this.lastCheck = Date.now()
    },

    startPolling() {
      this.check()
      setInterval(() => this.check(), 5000)
    }
  }
})
