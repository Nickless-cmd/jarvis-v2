/**
 * En WebSocket-besked må ikke udløse en fuld genhentning (12/11-2026).
 *
 * Målt på CT105: seks /cowork/*-endpoints fik hver ~490 × 429 på 5 minutter (~1,6 kald/s
 * hver ≈ 600/min i alt = hele loftet for en autentificeret klient). `useCoworkData` og
 * `useMissionControl` kaldte `refresh()` fra `ws.onmessage` — HVER besked fra
 * Mission Control-strømmen, som sender hændelser hele tiden — uden at tage højde for at et
 * kald allerede var i gang. Loftet deles af alle endpoints, så chat, notifikationer og
 * kort kunne også blive 429'et.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { lavTrailingThrottle } from './trailingThrottle'

beforeEach(() => { vi.useFakeTimers() })
afterEach(() => { vi.useRealTimers() })

describe('lavTrailingThrottle', () => {
  it('første kald kører med det samme', () => {
    const fn = vi.fn()
    const t = lavTrailingThrottle(fn, 3000)
    t.kald()
    expect(fn).toHaveBeenCalledTimes(1)
  })

  it('en byge af kald giver ÉT straks og ÉT til sidst — ikke ét pr. kald', () => {
    const fn = vi.fn()
    const t = lavTrailingThrottle(fn, 3000)
    for (let i = 0; i < 200; i += 1) { t.kald(); vi.advanceTimersByTime(10) }   // 2 s med 200 beskeder
    expect(fn).toHaveBeenCalledTimes(1)
    vi.advanceTimersByTime(3000)
    expect(fn).toHaveBeenCalledTimes(2)       // trailing: den sidste besked glemmes ikke
  })

  it('højst ét kald pr. interval over lang tid, selv med konstant strøm', () => {
    const fn = vi.fn()
    const t = lavTrailingThrottle(fn, 3000)
    for (let i = 0; i < 6000; i += 1) { t.kald(); vi.advanceTimersByTime(10) }  // 60 s, 100 beskeder/s
    expect(fn.mock.calls.length).toBeLessThanOrEqual(21)   // 60 s / 3 s = 20 (+1)
  })

  it('et kald efter ro kører straks igen', () => {
    const fn = vi.fn()
    const t = lavTrailingThrottle(fn, 3000)
    t.kald()
    vi.advanceTimersByTime(5000)
    t.kald()
    expect(fn).toHaveBeenCalledTimes(2)
  })

  it('annuller dropper en ventende trailing (unmount må ikke fyre efter teardown)', () => {
    const fn = vi.fn()
    const t = lavTrailingThrottle(fn, 3000)
    t.kald(); t.kald()
    t.annuller()
    vi.advanceTimersByTime(10_000)
    expect(fn).toHaveBeenCalledTimes(1)
  })

  it('et kald der kaster vælter hverken throttle eller de næste', () => {
    const fn = vi.fn().mockImplementationOnce(() => { throw new Error('boom') })
    const t = lavTrailingThrottle(fn, 1000)
    expect(() => t.kald()).not.toThrow()
    vi.advanceTimersByTime(1500)
    t.kald()
    expect(fn).toHaveBeenCalledTimes(2)
  })
})

// ── Koblingen: ingen hook må kalde refresh() direkte fra ws.onmessage ─────────
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import ts from 'typescript'

describe('WebSocket-genhentningen er throttlet i begge hooks', () => {
  for (const fil of ['hooks/useCoworkData.ts', 'hooks/useMissionControl.ts']) {
    it(`${fil}: ws.onmessage går gennem throttlen, ikke direkte til refresh()`, () => {
      const sti = resolve(__dirname, '..', fil)
      const sf = ts.createSourceFile(sti, readFileSync(sti, 'utf-8'), ts.ScriptTarget.Latest, true, ts.ScriptKind.TS)
      let handler = ''
      const gaa = (n: ts.Node) => {
        if (ts.isBinaryExpression(n) && n.operatorToken.kind === ts.SyntaxKind.EqualsToken
          && n.left.getText().endsWith('.onmessage')) handler = n.right.getText()
        ts.forEachChild(n, gaa)
      }
      gaa(sf)
      expect(handler, 'ws.onmessage blev ikke fundet').not.toBe('')
      expect(handler, 'en WS-besked udløser en fuld genhentning pr. besked (429-storm)').not.toMatch(/refresh\s*\(/)
      expect(handler).toContain('.kald(')
    })
  }
})
