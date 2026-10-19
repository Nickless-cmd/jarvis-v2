/**
 * MÅLING, ikke en vagt: overlever pacing-cursoren at blok-arrayet skiftes ud?
 *
 * ## Hvorfor dette er det afgørende tal
 *
 * `opdel`/`deriveChatFlow` bygger NYE arrays ved fase-skiftet. Hvis hookets
 * cursor blev nulstillet ved en ny array-reference, ville slutsvaret rulle
 * forfra — og så er problemet pacing, ikke containere.
 *
 * Cursoren er nøglet på `${runId}:chat-text`, og visningen bevares kun hvis
 * `target.startsWith(previous.shown)`. Her måles begge led direkte:
 *
 *   - samme runId + ny array-reference + længere tekst  → cursoren SKAL vokse
 *   - nyt runId                                        → cursoren SKAL nulstilles
 *
 * Kører vi aldrig et frame, er der intet at måle — derfor drives
 * `requestAnimationFrame` manuelt her i stedet for at vente på en browser.
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

/** Kør nok frames til at cursoren har spist hele målet (eller opgiv). */
function rulFrames(antal = 400): void {
  let t = 0
  for (let i = 0; i < antal; i += 1) {
    t += 16
    act(() => flushFrame(t))
  }
}

function tekst(blokke: ContentBlock[]): string {
  return blokke.filter((b) => b.type === 'text').map((b) => (b as { text: string }).text).join('')
}

describe('useChatPacedBlocks — cursor over array-skift', () => {
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

  it('MAALER: samme runId + ny array + laengere tekst => cursoren vokser, nulstilles ikke', () => {
    const foerste: ContentBlock[] = [{ type: 'text', text: 'Det er svaret.' } as ContentBlock]
    const options = { live: true, finalAnswerStarted: true, paceAllText: true, runId: 'run-A' }
    const view = renderHook(({ blocks }) => useChatPacedBlocks(blocks, options), {
      initialProps: { blocks: foerste },
    })

    rulFrames(60)
    const vistFoer = tekst(view.result.current).length

    // Ny array-reference, samme runId, teksten er en FORLÆNGELSE.
    const laengere: ContentBlock[] = [{ type: 'text', text: 'Det er svaret. Og mere tekst.' } as ContentBlock]
    view.rerender({ blocks: laengere })
    rulFrames(20)
    const vistLigeEfter = tekst(view.result.current).length

    rulFrames(400)
    const vistTilSlut = tekst(view.result.current).length

    // eslint-disable-next-line no-console
    console.log(
      `[MAALING] samme runId: vist foer=${vistFoer} ligeEfter=${vistLigeEfter}`
      + ` tilSlut=${vistTilSlut} (maal=${laengere[0] && (laengere[0] as { text: string }).text.length})`,
    )

    // Det ærlige krav: teksten må ikke FALDE tilbage til nul ved array-skiftet.
    expect(vistLigeEfter).toBeGreaterThanOrEqual(vistFoer)
    expect(vistTilSlut).toBeGreaterThanOrEqual(vistFoer)
  })

  it('MAALER: nyt runId => cursoren nulstilles (bevidst)', () => {
    const blokke: ContentBlock[] = [{ type: 'text', text: 'Det er svaret.' } as ContentBlock]
    const view = renderHook(
      ({ runId }) => useChatPacedBlocks(blokke, {
        live: true, finalAnswerStarted: true, paceAllText: true, runId,
      }),
      { initialProps: { runId: 'run-A' } },
    )

    rulFrames(80)
    const vistA = tekst(view.result.current).length

    view.rerender({ runId: 'run-B' })
    const vistBUmedDetSamme = tekst(view.result.current).length
    rulFrames(10)
    const vistBEfterLidt = tekst(view.result.current).length

    // eslint-disable-next-line no-console
    console.log(`[MAALING] nyt runId: vistA=${vistA} vistB0=${vistBUmedDetSamme} vistB10=${vistBEfterLidt}`)

    expect(vistA).toBeGreaterThan(0)
    // Nulstilling er kontrakten: et nyt run maa ikke arve det forriges tekst.
    expect(vistBUmedDetSamme).toBeLessThan(vistA)
  })
})
