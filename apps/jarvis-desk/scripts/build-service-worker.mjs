import { build } from 'esbuild'
import { createHash } from 'node:crypto'
import { readFileSync } from 'node:fs'

const html = readFileSync('dist-web/index.html', 'utf8')
const version = createHash('sha256').update(html).digest('hex').slice(0, 12)
const entryAssets = [...html.matchAll(/(?:src|href)="(\/assets\/[^"]+)"/g)].map((match) => match[1])

await build({
  entryPoints: ['src/pwa/service-worker.ts'],
  outfile: 'dist-web/sw.js',
  bundle: true,
  format: 'iife',
  platform: 'browser',
  target: 'es2020',
  minify: true,
  define: { __PWA_CACHE__: JSON.stringify(version), __PWA_ENTRY_ASSETS__: JSON.stringify(entryAssets) },
})
