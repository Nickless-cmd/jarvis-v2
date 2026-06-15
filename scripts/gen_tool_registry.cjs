#!/usr/bin/env node
/* Dev-hjælper: rapportér hvilke backend-tools der mangler en kurateret entry i
 * toolRegistry.ts. Læser tool-navne fra et JSON-dump genereret af backend
 * (scripts/dump_tool_names.py > /tmp/tool_names.json) eller argument. Ikke i test-
 * stien — ren rapport, så dækningen kan udvides over tid. */
const fs = require('fs')
const path = require('path')

const reg = fs.readFileSync(path.join(__dirname, '..', 'apps', 'jarvis-desk', 'src', 'lib', 'toolRegistry.ts'), 'utf8')
const curated = new Set([...reg.matchAll(/^\s{2}([a-z_]+):\s*\{/gm)].map((m) => m[1]))

let names = []
try {
  names = JSON.parse(fs.readFileSync(process.argv[2] || '/tmp/tool_names.json', 'utf8'))
} catch {
  console.error('Forventer en JSON-liste af tool-navne som argument (eller /tmp/tool_names.json).')
  process.exit(1)
}

const missing = names.filter((n) => !curated.has(n))
console.log(`${curated.size} kuraterede, ${missing.length} mangler kurateret entry (dækkes af Title-Case fallback):`)
missing.forEach((n) => console.log('  ' + n))
