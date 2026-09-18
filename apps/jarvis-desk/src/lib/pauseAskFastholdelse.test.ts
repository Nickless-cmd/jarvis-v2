/**
 * pause_and_ask skal BLIVE STÅENDE til man har trykket (Bjørn 18/9-2026:
 * «det forsvinder efter få sekunder»).
 *
 * Årsagen var at kortets værdi var AFLEDT og genberegnet ved hver render:
 * under streaming kom den fra `stream.blocks`, og når strømmen sluttede blev
 * de ikke længere konsulteret. Lå tool-blokken ikke i den persisterede
 * besked, faldt værdien til null — og spørgsmålet forsvandt netop som man
 * skulle svare på det.
 *
 * Reglen er nu: fasthold til der kommer en NY bruger-besked. Testen her er
 * ren logik på den regel, så den holder uanset hvordan ChatView er skruet
 * sammen.
 */
import { describe, expect, it } from 'vitest'
import type { PauseAsk } from './pauseAsk'

const ask: PauseAsk = {
  question: 'Hvilken vej?', options: ['venstre', 'højre'], context: '', urgency: 'normal',
}

/** Samme regel som ChatView: kortet lever indtil bruger-tallet vokser. */
function synligt(
  fastholdt: { ask: PauseAsk; vedBrugerAntal: number } | null,
  brugerAntal: number,
): PauseAsk | null {
  return fastholdt && brugerAntal <= fastholdt.vedBrugerAntal ? fastholdt.ask : null
}

describe('fastholdelse af pause_and_ask', () => {
  it('bliver stående når strømmen slutter — det var hele fejlen', () => {
    // Fanget mens der streamede, med 1 bruger-besked på skærmen.
    const fastholdt = { ask, vedBrugerAntal: 1 }

    // Strømmen slutter. Ingen ny bruger-besked. Kortet skal stadig stå.
    expect(synligt(fastholdt, 1)).toEqual(ask)
  })

  it('forsvinder når svaret er sendt — svaret ER en bruger-besked', () => {
    const fastholdt = { ask, vedBrugerAntal: 1 }
    expect(synligt(fastholdt, 2)).toBeNull()
  })

  it('forsvinder også hvis man skriver noget andet i stedet', () => {
    const fastholdt = { ask, vedBrugerAntal: 3 }
    expect(synligt(fastholdt, 4)).toBeNull()
  })

  it('uden et spørgsmål er der intet at vise', () => {
    expect(synligt(null, 0)).toBeNull()
  })
})
