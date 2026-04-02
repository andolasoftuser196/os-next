import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/api': 'http://localhost:8900',
      '/ws': { target: 'ws://localhost:8900', ws: true },
    },
  },
})
