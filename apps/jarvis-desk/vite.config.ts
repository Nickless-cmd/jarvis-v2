import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'node:path'
import { readFileSync } from 'node:fs'
import { execSync } from 'node:child_process'

// 25/10-2026 (målt): jeg kunne bevise at koden var rigtig og at serveren sendte
// det nye build — men ikke hvilket build KLIENTEN kørte. Bjørn så en rå
// jarvis-ui-blok og vi brugte tid på at gætte: gammel cache eller ny fejl?
// Samme fælde som 9/10 med den gamle CSS (se pwa/register.ts). Et build-id bagt
// ind ved build gør spørgsmålet målbart i stedet for gættet.
function buildId(): string {
  try {
    const sha = execSync('git rev-parse --short=9 HEAD', { encoding: 'utf-8' }).trim()
    const dirty = execSync('git status --porcelain', { encoding: 'utf-8' }).trim() ? '+' : ''
    return `${sha}${dirty}`
  } catch {
    return new Date().toISOString().slice(0, 19).replace(/[-:T]/g, '')
  }
}

// Desks egen version, bagt ind ved build. Renderer'en har ingen adgang til
// package.json, og at foere den gennem preload-broen ville vaere tre led for
// ét tal. `package.json` er i forvejen den ENESTE versionskilde for desk.
const DESK_VERSION = JSON.parse(
  readFileSync(resolve(__dirname, 'package.json'), 'utf-8'),
).version as string

// jarvis-desk Vite config.
// Port 5174 så vi ikke kolliderer med JarvisX (5173).
export default defineConfig(({ mode }) => ({
  base: mode === 'web' ? '/' : './',
  define: {
    __DESK_VERSION__: JSON.stringify(DESK_VERSION),
    __WEB_BUILD__: JSON.stringify(mode === 'web'),
    __BUILD_ID__: JSON.stringify(buildId()),
  },
  plugins: [react()],
  server: {
    port: 5174,
    strictPort: true,
  },
  build: {
    outDir: mode === 'web' ? 'dist-web' : 'dist',
    emptyOutDir: true,
    sourcemap: true,
  },
  resolve: {
    alias: { '@': resolve(__dirname, 'src') },
  },
}))
