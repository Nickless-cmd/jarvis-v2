/**
 * ACCEPTTEST — én tur, én monteret komponent, hele forløbet.
 *
 * Bjørn 26/11-2026, efter GPT's tredje gennemgang: «Vi skal stoppe med at
 * bevise komponenterne hver for sig og begynde at bevise forløbet som helhed.»
 *
 * ## Hvorfor denne fil findes
 *
 * Hver enkelt mekanisme i turhovedet er blevet bevist isoleret — og bagefter
 * er der fundet et ANDET sted i systemet der brød dens forudsætning. Mønstret
 * er målt: `blokId` blev indført og testet på et værktøjskald, som ikke vokser;
 * den fejl den skulle fjerne, sad i en tekstblok der vokser. Testen var grøn,
 * defekten var der.
 *
 * Denne fil måler derfor ikke mekanismer. Den måler ÉN turs livscyklus gennem
 * den SAMME monterede komponent, med DOM-node-identitet (`isSameNode`) som
 * bevis — ikke sammenligning af data-attributter på separate mounts. Et
 * remount kan nemlig give identiske attributter og alligevel rive noden ned,
 * og det er præcis det brugeren ser som et blink.
 *
 * ## De fire kontrakter (alle røde da filen blev skrevet)
 *
 *  1. **Dokumentstrukturen skifter ikke midt i turen.** Den betingede
 *     `fladtFlow`-gren afmonterer den gamle renderer når første runde efter
 *     besvarelsen ankommer. Stabile keys kan ikke redde DOM-noder på tværs af
 *     forskellige forældre.
 *  2. **Blokidentiteten er uforanderlig.** `blokId` bygges som
 *     `"${activeRunId ?? 'r'}:${index}"`. Kommer blokken før run-id'et, og
 *     genafspilles den bagefter, skifter identiteten — samme logiske blok,
 *     ny key.
 *  3. **Alle tekstfødsler stempler identiteten.** `provisional_text_commit`
 *     og `message_stop` skriver blokke direkte i arrayet uden `blokId`.
 *  4. **Exit venter på at pacen er drænet, og kollaps fjerner plads.**
 *     `kollapset` er i dag `opacity: 0.55`, og levetiden er den rene ternær
 *     `turenKoerer ? 'live' : 'kollapset'` — så den slår til ved server-done,
 *     ikke ved pace-done.
 */
import { act, render } from '@testing-library/react'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('../../hooks/useSettings', () => ({
  useSettings: () => ({ settings: { apiBaseUrl: 'https://api.srvlab.dk', authToken: 't' } }),
}))

import { ChatFlowPresentation } from './ChatFlowPresentation'
import { initialStreamState, streamReducer } from '../../lib/streamReducer'
import type { ContentBlock } from '../../lib/sseProtocol'

// ── pacens ur, styret manuelt ────────────────────────────────────────────
// Uden dette er pacen ikke-deterministisk og hvert step kan ikke måles. Det er
// samme greb som `ChatFlowPresentation.pacing.test.tsx` bruger.
let rafKo: FrameRequestCallback[] = []
let ur = 0

beforeEach(() => {
  rafKo = []
  ur = 0
  vi.stubGlobal('requestAnimationFrame', (cb: FrameRequestCallback) => {
    rafKo.push(cb)
    return rafKo.length
  })
  vi.stubGlobal('cancelAnimationFrame', () => undefined)
})

afterEach(() => {
  vi.unstubAllGlobals()
})

function frame(ms = 16) {
  ur += ms
  const ko = rafKo
  rafKo = []
  act(() => {
    for (const cb of ko) cb(ur)
  })
}

const common = {
  mode: 'living' as const,
  density: 'compact' as const,
  workingStep: null,
  rundeEtiketter: {},
  tankeResumeer: {},
  tokens: 0,
  config: {} as never,
}

const tekst = (text: string, phase?: 'commentary' | 'final_answer'): ContentBlock =>
  ({ type: 'text', text, ...(phase ? { phase } : {}) }) as ContentBlock

const kald = (id: string): ContentBlock =>
  ({ type: 'tool_use', id, name: 'bash', input: {}, status: 'done' }) as ContentBlock

// ═════════════════════════════════════════════════════════════════════════
// KONTRAKT 1 — dokumentstrukturen skifter ikke midt i turen
// ═════════════════════════════════════════════════════════════════════════
describe('accepttest — én tur gennem hele forløbet', () => {
  it('KONTRAKT 1: besvarelsens DOM-node overlever at første runde ankommer', () => {
    // Fase 1: besvarelse A er i gang. Ingen runde endnu → den gamle struktur.
    const foerste = [tekst('Besvarelse A.', 'final_answer')]
    const view = render(
      <ChatFlowPresentation {...common} blocks={foerste} streaming status="working" finalAnswerStarted />,
    )
    const svarFoer = view.container.querySelector('.chat-flow-answer')
    expect(svarFoer).not.toBeNull()
    const foraelderFoer = svarFoer!.parentElement

    // Fase 2: runden EFTER besvarelsen ankommer. Nu tager `fladtFlow` over —
    // og hvis den gør det ved at skifte forælder, er noden væk for brugeren.
    view.rerender(
      <ChatFlowPresentation
        {...common}
        blocks={[...foerste, kald('k-efter')]}
        streaming
        status="working"
        finalAnswerStarted
      />,
    )
    const svarEfter = view.container.querySelector('.chat-flow-answer')
    expect(svarEfter).not.toBeNull()

    // KERNEN: samme node, samme forælder. En ny forælder er et remount, og et
    // remount er det blink testen skal fælde — uanset at attributterne er ens.
    expect(svarEfter!.isSameNode(svarFoer)).toBe(true)
    expect(svarEfter!.parentElement!.isSameNode(foraelderFoer)).toBe(true)
  })

  it('KONTRAKT 1b: der findes ikke to konkurrerende renderere i DOM samtidig', () => {
    // Den gamle gren og den flade gren må ikke kunne stå side om side: så er
    // der to dokumenter for én tur, og rækkefølgen er ikke længere sand.
    const view = render(
      <ChatFlowPresentation
        {...common}
        blocks={[tekst('A.', 'final_answer'), kald('k-1'), tekst('B.', 'final_answer')]}
        streaming
        status="working"
        finalAnswerStarted
      />,
    )
    const flad = view.container.querySelectorAll('[data-segmenter="flat"]').length
    const gammel = view.container.querySelectorAll('.chat-flow-gruppe-ydre').length
    // Præcis én dokumentstruktur ejer besvarelsen.
    expect(flad + (gammel > 0 ? 1 : 0)).toBe(1)
  })

  // ═══════════════════════════════════════════════════════════════════════
  // KONTRAKT 2 — rundecontaineren bevarer sin instans gennem runderne
  // ═══════════════════════════════════════════════════════════════════════
  it('KONTRAKT 2: rundecontainer 1 er den SAMME node da runde 2 ankommer', () => {
    const view = render(
      <ChatFlowPresentation
        {...common}
        blocks={[tekst('A.', 'final_answer'), kald('k-1')]}
        streaming
        status="working"
        finalAnswerStarted
      />,
    )
    const runde1 = view.container.querySelector('[data-segment-id]')
    expect(runde1).not.toBeNull()
    const id1 = runde1!.getAttribute('data-segment-id')

    view.rerender(
      <ChatFlowPresentation
        {...common}
        blocks={[tekst('A.', 'final_answer'), kald('k-1'), tekst('B.', 'final_answer'), kald('k-2')]}
        streaming
        status="working"
        finalAnswerStarted
      />,
    )
    const runde1Efter = view.container.querySelector(`[data-segment-id="${id1}"]`)
    expect(runde1Efter).not.toBeNull()
    expect(runde1Efter!.isSameNode(runde1)).toBe(true)
  })

  // ═══════════════════════════════════════════════════════════════════════
  // KONTRAKT 3 — blokidentiteten er uforanderlig (reducer-niveau)
  // ═══════════════════════════════════════════════════════════════════════
  it('KONTRAKT 3: blokidentiteten overlever at run-id ankommer efter blokken', () => {
    // Blokken fødes FØR run-id'et er kendt — `message_start` kan bære et tomt
    // id, og `system_event(kind='run')` sætter det rigtige bagefter.
    let s = initialStreamState()
    s = streamReducer(s, {
      type: 'content_block_start', index: 0, content_block: { type: 'text', text: '' },
    })
    const foedselsId = (s.blocks[0] as { blokId?: string }).blokId
    expect(foedselsId).toBeTruthy()

    // Run-id'et ankommer.
    s = streamReducer(s, {
      type: 'system_event', kind: 'run', payload: { run_id: 'run-abc' },
    } as never)
    expect(s.activeRunId).toBe('run-abc')

    // Replay af SAMME blok (reconnect / relay-replay fra offset 0).
    s = streamReducer(s, {
      type: 'content_block_start', index: 0, content_block: { type: 'text', text: '' },
    })
    const efterReplay = (s.blocks[0] as { blokId?: string }).blokId

    // KERNEN: samme logiske blok, samme identitet — uanset run-id og position.
    expect(efterReplay).toBe(foedselsId)
  })

  // ═══════════════════════════════════════════════════════════════════════
  // KONTRAKT 4 — alle tekstfødsler stempler identiteten
  // ═══════════════════════════════════════════════════════════════════════
  it('KONTRAKT 4a: en blok født af provisional_text_commit har en blokId', () => {
    let s = initialStreamState()
    // Et run skal være kendt — commit-gaten kræver run_id-match.
    s = streamReducer(s, {
      type: 'system_event', kind: 'run', payload: { run_id: 'run-abc' },
    } as never)
    // Provisonisk tekst opstår, og en delta rammer et indeks uden blok.
    s = streamReducer(s, {
      type: 'system_event', kind: 'provisional_text_delta', payload: { run_id: 'run-abc', delta: 'Hej' },
    } as never)
    s = streamReducer(s, {
      type: 'content_block_delta', index: 2, delta: { type: 'text_delta', text: 'x' },
    } as never)
    expect(s.provisionalMissingBlockIndex).toBe(2)

    s = streamReducer(s, {
      type: 'system_event', kind: 'provisional_text_commit', payload: { run_id: 'run-abc' },
    } as never)

    const blok = s.blocks[2] as { type: string; text?: string; blokId?: string } | undefined
    expect(blok?.type).toBe('text')
    expect(blok?.blokId).toBeTruthy()
  })

  it('KONTRAKT 4b: en blok født ved message_stop har en blokId', () => {
    let s = initialStreamState()
    s = streamReducer(s, {
      type: 'system_event', kind: 'run', payload: { run_id: 'run-abc' },
    } as never)
    s = streamReducer(s, {
      type: 'system_event', kind: 'provisional_text_delta', payload: { run_id: 'run-abc', delta: 'Hej' },
    } as never)
    s = streamReducer(s, {
      type: 'content_block_delta', index: 2, delta: { type: 'text_delta', text: 'x' },
    } as never)
    expect(s.provisionalMissingBlockIndex).toBe(2)

    s = streamReducer(s, { type: 'message_stop' } as never)

    const blok = s.blocks[2] as { type: string; text?: string; blokId?: string } | undefined
    expect(blok?.type).toBe('text')
    expect(blok?.blokId).toBeTruthy()
  })

  // ═══════════════════════════════════════════════════════════════════════
  // KONTRAKT 5 — exit venter på pace-drain
  // ═══════════════════════════════════════════════════════════════════════
  it('KONTRAKT 5: rundecontaineren kollapser IKKE mens pacen stadig har tekst tilbage', () => {
    const lang = 'Dette er et langt slutsvar som paceren ruller ud over mange frames, og det maa ikke kollapse undervejs.'
    const view = render(
      <ChatFlowPresentation
        {...common}
        blocks={[tekst(lang, 'final_answer'), kald('k-efter')]}
        streaming={false}
        status="done"
        finalAnswerStarted
        paceFinalAnswer
      />,
    )
    // Én frame: pacen er langtfra færdig.
    frame(16)
    const svarTekst = view.container.querySelector('.chat-flow-answer')?.textContent ?? ''
    expect(svarTekst.length).toBeLessThan(lang.length)

    const runde = view.container.querySelector('[data-segment="runde"]')
    expect(runde).not.toBeNull()
    // KERNEN: turen er server-done, men pacen kører. Containeren skal stadig
    // være `live` — ellers fader arbejdet væk mens svaret endnu ruller.
    expect(runde!.getAttribute('data-levetid')).not.toBe('kollapset')
  })

  // ═══════════════════════════════════════════════════════════════════════
  // KONTRAKT 6 — kollapset fjerner plads, det er ikke en opacity
  // ═══════════════════════════════════════════════════════════════════════
  it('KONTRAKT 6: kollaps-reglen reducerer højden, ikke kun synligheden', () => {
    // jsdom har ingen layout-motor, så højden kan ikke måles ved at rendere.
    // Vagten læser derfor reglen selv og kræver en egenskab der fjerner PLADS.
    // En `opacity` alene er ikke et kollaps — indholdet bliver stående og
    // optager den samme højde, så besvarelserne glider ikke sammen.
    const css = readFileSync(resolve(__dirname, '../../styles/chat-flow.css'), 'utf8')
    const regel = /\.chat-flow-runde\[data-levetid='kollapset'\]\s*\{([^}]*)\}/.exec(css)
    expect(regel).not.toBeNull()

    const krop = regel![1] ?? ''
    const fjernerPlads = /max-height|grid-template-rows|(^|\s)height|scaleY|margin-top\s*:\s*0/.test(krop)
    expect(fjernerPlads).toBe(true)
  })
})
