#!/usr/bin/env node
/**
 * Build preload.ts as CommonJS and emit it as preload.cjs.
 *
 * Why this dance: package.json has "type": "module", so any .js file
 * Node sees in this tree is interpreted as ESM regardless of its
 * source format. Electron's preload script needs to be reliably
 * loadable — ESM preloads have edge cases (timing, contextBridge
 * availability) that broke window.jarvisx for us. Forcing CJS by
 * outputting a .cjs extension sidesteps the whole class of issues.
 *
 * Steps:
 *   1. Run tsc with the preload-specific tsconfig (CJS output).
 *   2. Rename dist-electron/preload.js → dist-electron/preload.cjs.
 *   3. main.ts references preload.cjs so Electron loads it as CJS.
 */
const { execSync } = require('node:child_process')
const fs = require('node:fs')
const path = require('node:path')

const root = path.resolve(__dirname, '..')
const tsconfig = path.join(root, 'electron/tsconfig.preload.json')
const outDir = path.join(root, 'dist-electron')

execSync(`npx tsc -p "${tsconfig}"`, { cwd: root, stdio: 'inherit' })

const jsPath = path.join(outDir, 'preload.js')
const cjsPath = path.join(outDir, 'preload.cjs')
if (fs.existsSync(jsPath)) {
  if (fs.existsSync(cjsPath)) fs.unlinkSync(cjsPath)
  fs.renameSync(jsPath, cjsPath)
  console.log(`[build-preload] emitted ${path.relative(root, cjsPath)}`)
} else {
  console.error('[build-preload] preload.js not produced — check tsconfig')
  process.exit(1)
}
