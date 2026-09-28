import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'node:path'
import { readFileSync } from 'node:fs'

// Desks egen version, bagt ind ved build. Renderer'en har ingen adgang til
// package.json, og at foere den gennem preload-broen ville vaere tre led for
// ét tal. `package.json` er i forvejen den ENESTE versionskilde for desk.
const DESK_VERSION = JSON.parse(
  readFileSync(resolve(__dirname, 'package.json'), 'utf-8'),
).version as string

// jarvis-desk Vite config.
// Port 5174 så vi ikke kolliderer med JarvisX (5173).
export default defineConfig({
  base: './',
  define: { __DESK_VERSION__: JSON.stringify(DESK_VERSION) },
  plugins: [react()],
  server: {
    port: 5174,
    strictPort: true,
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    sourcemap: true,
  },
  resolve: {
    alias: { '@': resolve(__dirname, 'src') },
  },
})
