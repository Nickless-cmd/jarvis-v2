import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'node:path'
import { existsSync, readFileSync } from 'node:fs'
import { homedir } from 'node:os'

// JarvisX renderer — React 19 + Tailwind shell that lives inside Electron.
// In dev, vite dev server runs at :5173; Electron loads it directly.
// In production, vite build emits dist/ which Electron loads via file://.

// Resolve API target for dev-server proxy, in priority order:
//   1. JARVISX_API_URL env var (explicit override)
//   2. apiBaseUrl from ~/.config/jarvisx/config.json (matches Electron config)
//   3. http://localhost (legacy fallback)
function resolveApiTarget(): string {
  if (process.env.JARVISX_API_URL) return process.env.JARVISX_API_URL
  try {
    const cfgPath = path.join(homedir(), '.config', 'jarvisx', 'config.json')
    if (existsSync(cfgPath)) {
      const cfg = JSON.parse(readFileSync(cfgPath, 'utf8'))
      if (cfg.apiBaseUrl && typeof cfg.apiBaseUrl === 'string') {
        return cfg.apiBaseUrl
      }
    }
  } catch {
    // fall through to localhost
  }
  return 'http://localhost'
}

const API_TARGET = resolveApiTarget()
console.log(`[vite] proxying API requests to ${API_TARGET}`)

// Inject app version from package.json at build time so the renderer can
// surface it (Sidebar footer, StatusBar) without drift between code and
// the actual built artifact. Stringified so it lands as a literal.
const PKG_VERSION = JSON.parse(
  readFileSync(path.join(__dirname, 'package.json'), 'utf8'),
).version as string

export default defineConfig({
  define: {
    __APP_VERSION__: JSON.stringify(PKG_VERSION),
  },
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
    // works when imported into JarvisX. Target picked by resolveApiTarget()
    // — defaults to the Electron config's apiBaseUrl so we don't drift
    // when the runtime moves hosts (e.g. CheifOne → 10.0.0.39 migration).
    proxy: {
      '/chat': { target: API_TARGET, changeOrigin: true },
      '/attachments': { target: API_TARGET, changeOrigin: true },
      '/files': { target: API_TARGET, changeOrigin: true },
      '/mc': { target: API_TARGET, changeOrigin: true },
      '/api': { target: API_TARGET, changeOrigin: true },
      '/health': { target: API_TARGET, changeOrigin: true },
      '/status': { target: API_TARGET, changeOrigin: true },
      '/sensory': { target: API_TARGET, changeOrigin: true },
      '/ws': {
        target: API_TARGET,
        changeOrigin: true,
        ws: true,
      },
      '/live': {
        target: API_TARGET,
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
