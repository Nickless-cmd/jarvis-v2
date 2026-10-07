import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'

const css = readFileSync(join(__dirname, 'liveness.css'), 'utf8')

describe('liveness i mørkt tema', () => {
  it('bruger altid en dækkende tekstfarve, også for en afsluttet tanke', () => {
    // 29/9-2026: gennemstregningen skabte et separat malelag; den klippede
    // gradient arvede transparent text-fill og kunne fremstå sort på mørk bund.
    expect(css).not.toMatch(/(?:-webkit-)?background-clip:\s*text/)
    expect(css).not.toMatch(/-webkit-text-fill-color:\s*transparent/)
    expect(css).toMatch(/\.liveness-label\s*\{[^}]*color:\s*var\(--fg-3\)/s)
    expect(css).toMatch(/\.liveness \.shimmer\s*\{[^}]*-webkit-text-fill-color:\s*var\(--fg-3\)/s)
    expect(css).toMatch(/\.liveness-thought\.afsluttet\s*\{[^}]*-webkit-text-fill-color:\s*var\(--fg-2\)/s)
  })
})
