/**
 * SPRING I PACEREN — en `jarvis-ui`-flade må aldrig rulles halvt (Bjørn 29/10-2026).
 *
 * ## Symptomet der blev målt
 *
 * Paceren ruller `target` tegn for tegn (48 tegn/s) og er BLIND for struktur:
 * den ved ikke hvad en fence er. Når svaret indeholder
 *
 *     ```jarvis-ui
 *     {"type":"callout",…}
 *     ```
 *
 * rullede den rå JSON ind i en åben fence. `stabilizeStreamingMarkdown` lukker
 * den åbne fence midlertidigt, så react-markdown ser en LUKKET kodeblok med
 * halv JSON — og derfor voksede en kodeboks linje for linje, hvorefter fladen
 * poppede ind i ét hug da JSON'en blev komplet.
 *
 * ## Kontrakten der måles her
 *
 *   1. Er fladen KOMPLET i target: cursoren springer over den i ét spring, og
 *      prosaen EFTER fladen fortsætter pacingen normalt.
 *   2. Er fladen UKOMPLET: cursoren står stille ved fence-start. Intet af
 *      JSON'en bliver nogensinde synligt.
 *   3. `shown` er fortsat et PRÆFIKS af target — springet flytter bare cursoren.
 *   4. Mermaid-stien er UÆNDRET (regression): den rulles som før.
 *
 * `requestAnimationFrame` styres manuelt, så hvert trin kan inspiceres; en
 * test der venter på browserens frames kan ikke se de mellemtilstande hvor
 * fejlen faktisk bor.
 */
import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { ContentBlock } from './sseProtocol'
import { useChatPacedBlocks } from './useChatPacedBlocks'

let frames: FrameRequestCallback[] = []

function flushFrame(ms: number): void {
  const ko = frames
  frames = []
  for (const cb of ko) cb(ms)
}

function tekst(blokke: ContentBlock[]): string {
  return blokke.filter((b) => b.type === 'text').map((b) => (b as { text: string }).text).join('')
}

function opsæt(text: string) {
  const blokke: ContentBlock[] = [{ type: 'text', text } as ContentBlock]
  return renderHook(() => useChatPacedBlocks(blokke, {
    live: true,
    finalAnswerStarted: true,
    paceAllText: true,
    runId: 'run-flade',
  }))
}

/** Kør frames ÉT ad gangen og gem hver vist tilstand — mellemtilstandene ER målet. */
function rulOgSaml(view: { result: { current: ContentBlock[] } }, antal = 400): string[] {
  const set: string[] = []
  let t = 0
  for (let i = 0; i < antal; i += 1) {
    t += 16
    act(() => flushFrame(t))
    set.push(tekst(view.result.current))
  }
  return set
}

const FLADE = '```jarvis-ui\n{"type":"callout","tone":"info","title":"T","body":"B"}\n```'
const FOER = 'Før.\n\n'
const EFTER = '\n\nEfter med prosa.'

describe('useChatPacedBlocks — spring over jarvis-ui-flader', () => {
  beforeEach(() => {
    frames = []
    vi.stubGlobal('requestAnimationFrame', (cb: FrameRequestCallback) => {
      frames.push(cb)
      return frames.length
    })
    vi.stubGlobal('cancelAnimationFrame', () => undefined)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('springer over en KOMPLET flade — JSON bliver aldrig synlig halvt', () => {
    const view = opsæt(FOER + FLADE + EFTER)
    const set = rulOgSaml(view)

    const halve = set.filter((vist) => vist.includes('```jarvis-ui') && !vist.includes(FLADE))
    expect(halve).toEqual([])

    // Springet skete: fladen står komplet i den viste tekst.
    expect(set.some((vist) => vist.includes(FLADE))).toBe(true)

    // Prosaen EFTER fladen rulles fortsat — springet må ikke sluge halen.
    expect(set[set.length - 1]).toBe(FOER + FLADE + EFTER)
    const mellem = set.filter((vist) => vist.includes(FLADE) && !vist.endsWith(EFTER))
    expect(mellem.length).toBeGreaterThan(0)
  })

  it('holder cursoren ved en UKOMPLET flade — intet af JSONen bliver synligt', () => {
    const view = opsæt(FOER + '```jarvis-ui\n{"type":"callout","tit')
    const set = rulOgSaml(view, 120)

    for (const vist of set) {
      expect(vist).not.toContain('"type"')
      expect(vist).not.toContain('jarvis-ui\n{')
    }
    // Cursoren står stille PRÆCIS ved fence-start.
    expect(set[set.length - 1]).toBe(FOER)
  })

  it('REGRESSION: en mermaid-fence springes IKKE — den rulles tegn for tegn som før', () => {
    const MERMAID = '```mermaid\ngraph TD\n  A-->B\n```'
    const view = opsæt(FOER + MERMAID + EFTER)
    const set = rulOgSaml(view, 300)

    const halve = set.filter((vist) => vist.includes('```mermaid') && !vist.includes(MERMAID))
    expect(halve.length).toBeGreaterThan(0)
  })
})
