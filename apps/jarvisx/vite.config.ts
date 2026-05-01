import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'node:path'

// JarvisX renderer — React 19 + Tailwind shell that lives inside Electron.
// In dev, vite dev server runs at :5173; Electron loads it directly.
// In production, vite build emits dist/ which Electron loads via file://.
export default defineConfig({
  plugins: [react()],
  base: './', // critical for Electron file:// loads
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
      // Reuse existing apps/ui chat components and adapters in JarvisX.
      // This keeps a single source of truth for chat behaviour — fixes
      // and features land in both webchat and the desktop app at once.
      '@ui': path.resolve(__dirname, '..', 'ui', 'src'),
    },
  },
  server: {
    port: 5173,
    strictPort: true,
    // Proxy all Jarvis API paths to the configured backend so apps/ui's
    // adapters.js (which uses relative paths like /chat/stream) just
    // works when imported into JarvisX. The backend is on port 80 by
    // default; override with JARVISX_API_URL env var when developing
    // against the thin-client server (jarvis.srvlab.dk).
    proxy: {
      '/chat': { target: process.env.JARVISX_API_URL || 'http://localhost', changeOrigin: true },
      '/attachments': { target: process.env.JARVISX_API_URL || 'http://localhost', changeOrigin: true },
      '/files': { target: process.env.JARVISX_API_URL || 'http://localhost', changeOrigin: true },
      '/mc': { target: process.env.JARVISX_API_URL || 'http://localhost', changeOrigin: true },
      '/api': { target: process.env.JARVISX_API_URL || 'http://localhost', changeOrigin: true },
      '/health': { target: process.env.JARVISX_API_URL || 'http://localhost', changeOrigin: true },
      '/status': { target: process.env.JARVISX_API_URL || 'http://localhost', changeOrigin: true },
      '/sensory': { target: process.env.JARVISX_API_URL || 'http://localhost', changeOrigin: true },
      '/ws': {
        target: process.env.JARVISX_API_URL || 'http://localhost',
        changeOrigin: true,
        ws: true,
      },
      '/live': {
        target: process.env.JARVISX_API_URL || 'http://localhost',
        changeOrigin: true,
        ws: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
})
