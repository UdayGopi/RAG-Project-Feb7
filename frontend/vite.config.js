import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: process.env.VITE_BASE || '/',
  server: {
    port: 5173,
    proxy: {
      '/chat': { target: 'http://localhost:5001', changeOrigin: true },
      '/health': { target: 'http://localhost:5001', changeOrigin: true },
      '/router-info': { target: 'http://localhost:5001', changeOrigin: true },
      '/tenants': { target: 'http://localhost:5001', changeOrigin: true },
      '/upload': { target: 'http://localhost:5001', changeOrigin: true },
      '/history': { target: 'http://localhost:5001', changeOrigin: true },
      '/feedback': { target: 'http://localhost:5001', changeOrigin: true },
      '/analytics': { target: 'http://localhost:5001', changeOrigin: true },
      '/schedules': { target: 'http://localhost:5001', changeOrigin: true },
      '/me': { target: 'http://localhost:5001', changeOrigin: true },
      '/auth': { target: 'http://localhost:5001', changeOrigin: true },
      '/download': { target: 'http://localhost:5001', changeOrigin: true },
      '/view': { target: 'http://localhost:5001', changeOrigin: true },
      '/auth.html': { target: 'http://localhost:5001', changeOrigin: true },
    },
  },
})
