import { describe, it, expect } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'

/**
 * Runde-etiketten skal hele vejen ud — «Rettede fejl i login».
 *
 * Serveren regner den, streamen bærer den, reduceren gemmer den. Uden de
 * sidste led bliver den regnet, sendt og gemt uden nogensinde at nå skærmen,
 * og det er husets hyppigste fejl. Kæden har seks led i desk, og hvert enkelt
 * er stille når det knækker.
 *
 * Testen er en kilde-vagt og ikke en render-test med vilje: den måler at
 * LEDDENE er der, hvilket er præcis det en render-test af ét lag ikke kan se.
 */
const kilde = (p: string) =>
  fs.readFileSync(path.join(__dirname, '..', p), 'utf8')

describe('runde-etiketten når fra stream til skærm', () => {
  it('protokollen kender eventet', () => {
    expect(kilde('lib/sseProtocol.ts')).toMatch(/type: 'tool_round_label'/)
  })

  it('reduceren gemmer den paa TOOL-ID', () => {
    // Nøglen er kaldets id og ikke rundenummeret: en etiket der kom sent ville
    // ellers sætte sig over de forkerte kald.
    const r = kilde('lib/streamReducer.ts')
    expect(r).toMatch(/case 'tool_round_label'/)
    expect(r).toMatch(/rundeEtiketter/)
  })

  it('konteksten baerer den videre', () => {
    expect(kilde('contexts/StreamContext.tsx'))
      .toMatch(/rundeEtiketter: state\.rundeEtiketter/)
  })

  it('ChatView giver den til beskeden', () => {
    expect(kilde('views/ChatView.tsx')).toMatch(/rundeEtiketter=\{stream\.rundeEtiketter\}/)
  })

  it('renderen slaar op paa kaldets id', () => {
    expect(kilde('components/rich/BlocksRenderer.tsx'))
      .toMatch(/rundeEtiketter\?\.\[t\.id\]/)
  })

  it('kortet tegner etiketten OVER den mekaniske linje', () => {
    // Bjørns rækkefølge: overskriften først, tallene efter. At begge findes er
    // ikke nok — rækkefølgen ER beslutningen.
    const c = kilde('components/rich/ToolGroupCard.tsx')
    expect(c).toMatch(/toolgroup-etiket/)
    expect(c.indexOf('toolgroup-etiket')).toBeLessThan(c.indexOf('toolgroup-label'))
  })

  it('etiketten har en stil — ellers er den usynlig', () => {
    expect(kilde('styles/app.css')).toMatch(/\.toolgroup-etiket/)
  })
})

describe('etiketten kommer ad TO veje', () => {
  it('reduceren tager BEGGE former — direkte og indpakket i system_event', () => {
    // SSE-v2 pakker ukendte event-navne som `system_event` med
    // `kind = event_name`. Uden den gren fyrede `case 'tool_round_label'`
    // aldrig — maalt i produktion 14/9 paa en klient der HAVDE koden.
    const r = kilde('lib/streamReducer.ts')
    expect(r).toMatch(/case 'tool_round_label':/)
    expect(r).toMatch(/event\.kind === 'tool_round_label'/)
    // ÉT sted der laegger den ind — to kopier ville drive fra hinanden.
    expect((r.match(/function medEtiket/g) ?? []).length).toBe(1)
  })
})
