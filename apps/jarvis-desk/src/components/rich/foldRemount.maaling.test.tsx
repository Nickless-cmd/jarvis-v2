/**
 * MÅLING, ikke en vagt: nulstilles turens fold når komponenten remountes?
 *
 * Bjørn 30/10-2026: «Fremprovoker et remount og se om folden nulstilles».
 *
 * Baggrunden er sammenligningen med Codex-appen (målt 30/10): deres
 * `chatgpt-reasoning-group` har en STABIL identitet
 * (`streamingParentRegion.id = ${kildemessageId}:${indeks}`) brugt som React-key,
 * så samme komponentinstans overlever at items bliver spillet igen. Vores
 * fold-tilstand er derimod `useState<boolean|null>` inde i komponenten, uden
 * nogen nøgle der binder den til beskeden.
 *
 * ## Hvad testen måler
 *
 * Tre scenarier, kørt på BEGGE flader:
 *
 *   1. RERENDER uden remount — tilstanden skal overleve (den gør, det er React).
 *   2. REMOUNT efter manuel udfoldning — nulstilles den?
 *   3. Den ægte overgang: live-tur (streaming) → persisteret besked. Det er den
 *      ChatView faktisk laver: den levende række er en BETINGET søskende uden
 *      key, mens de historiske rækker ligger i et `.map` med `key={m.id}`.
 *      Når streamen slutter, afmonteres den levende række og en NY monteres.
 *
 * Testen er en måling: den fejler ikke på et forkert tal, den udskriver hvad
 * der faktisk sker, så vi kan beslutte os på data frem for på læsning.
 *
 * ⚠️ FORVENTNINGERNE DOKUMENTERER NUVÆRENDE ADFÆRD, ikke ønsket adfærd.
 * `expect(efterRemount).toBe('false')` siger «i dag nulstilles folden». Giver
 * vi fold-tilstanden en stabil identitet (som Codex' `${beskedId}:${indeks}`),
 * skal de vendes til `'true'` — det er meningen, ikke en regression.
 *
 * MÅLT 30/10-2026 (4/4 grønne, begge flader):
 *   rerender uden remount  → tilstanden overlever
 *   remount                → NULSTILLES (både chat og code)
 * Transcriptet virtualiseres IKKE, så historiske rækker bliver siddende mens
 * sessionen er åben. Remountet rammer derfor i praksis ved (a) overgangen
 * live → persisteret besked når turen slutter, og (b) genindlæsning/skift af
 * session. Inden for samme session overlever en manuel fold.
 */
import { act, render, cleanup, fireEvent } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { ChatFlowPresentation } from './ChatFlowPresentation'
import { RaekkeTranskript } from './RaekkeTranskript'
import type { ContentBlock } from '../../lib/sseProtocol'

const kald = (navn: string, input: Record<string, unknown> = {}): ContentBlock => ({
  type: 'tool_use', id: `${navn}-1`, name: navn, input,
})

/** Arbejde UDEN slutsvar — så hovedet er foldbart og turen kan «køre». */
const ARBEJDE: ContentBlock[] = [
  { type: 'thinking', thinking: 'Jeg finder filen først.', seconds: 12 },
  kald('read_file', { path: '/media/projects/jarvis-v2/x.py' }),
  kald('bash', { command: 'ls -la' }),
]

/** Slår hovedets fold-tilstand op. `null` = hovedet findes ikke. */
function foldTilstand(container: HTMLElement): string | null {
  const knap = container.querySelector('button.rv-tur')
  if (!knap) return null
  return knap.getAttribute('aria-expanded')
}

function klikFold(container: HTMLElement): void {
  const knap = container.querySelector('button.rv-tur') as HTMLButtonElement | null
  if (!knap) throw new Error('hovedet er ikke foldbart — testen kan ikke måle noget')
  act(() => { fireEvent.click(knap) })
}

afterEach(cleanup)

describe('fold overlever ikke et remount — målt på begge flader', () => {
  it('chat mode: manuel udfoldning overlever rerender, men IKKE remount', () => {
    // ── 1. En afsluttet tur: hovedet er foldet sammen som standard.
    const a = render(
      <ChatFlowPresentation
        blocks={ARBEJDE} mode="calm" density="compact"
        streaming={false} status="done" finalAnswerStarted={false}
      />,
    )
    expect(foldTilstand(a.container)).toBe('false')

    // ── 2. Brugeren folder ud.
    klikFold(a.container)
    expect(foldTilstand(a.container)).toBe('true')

    // ── 3. RERENDER uden remount — tilstanden skal holde.
    a.rerender(
      <ChatFlowPresentation
        blocks={ARBEJDE} mode="calm" density="compact"
        streaming={false} status="done" finalAnswerStarted={false}
        tokens={4711}
      />,
    )
    const efterRerender = foldTilstand(a.container)
    expect(efterRerender).toBe('true')

    // ── 4. REMOUNT — samme props, ny instans. Det er her spørgsmålet står.
    cleanup()
    const b = render(
      <ChatFlowPresentation
        blocks={ARBEJDE} mode="calm" density="compact"
        streaming={false} status="done" finalAnswerStarted={false}
      />,
    )
    const efterRemount = foldTilstand(b.container)

    // Målingen, ikke en dom: vi skriver tallet, så det kan læses i output.
    console.log(
      `[MÅLING chat] rerender=${efterRerender} remount=${efterRemount} ` +
      `→ ${efterRemount === 'true' ? 'OVERLEVER' : 'NULSTILLES'}`,
    )

    // Det er HVAD DEN GØR der dokumenteres — nulstilles den, er det målingen.
    expect(efterRemount).toBe('false')
  })

  it('code mode: manuel udfoldning overlever rerender, men IKKE remount', () => {
    const a = render(
      <RaekkeTranskript
        blocks={ARBEJDE} streaming={false} finalAnswerStarted={false}
      />,
    )
    expect(foldTilstand(a.container)).toBe('false')

    klikFold(a.container)
    expect(foldTilstand(a.container)).toBe('true')

    a.rerender(
      <RaekkeTranskript
        blocks={ARBEJDE} streaming={false} finalAnswerStarted={false}
        tokens={4711}
      />,
    )
    const efterRerender = foldTilstand(a.container)
    expect(efterRerender).toBe('true')

    cleanup()
    const b = render(
      <RaekkeTranskript
        blocks={ARBEJDE} streaming={false} finalAnswerStarted={false}
      />,
    )
    const efterRemount = foldTilstand(b.container)

    console.log(
      `[MÅLING code] rerender=${efterRerender} remount=${efterRemount} ` +
      `→ ${efterRemount === 'true' ? 'OVERLEVER' : 'NULSTILLES'}`,
    )
    expect(efterRemount).toBe('false')
  })

  it('den ægte overgang: foldet-under-arbejde tabes når turen persisteres', () => {
    // Den levende tur: `arbejdeKoerer` er sand, så hovedet er ÅBENT af sig selv.
    const live = render(
      <ChatFlowPresentation
        blocks={ARBEJDE} mode="calm" density="compact"
        streaming status="working" finalAnswerStarted={false}
      />,
    )
    expect(foldTilstand(live.container)).toBe('true')

    // Brugeren FOLDER SAMMEN undervejs — vil se svaret, ikke arbejdet.
    klikFold(live.container)
    expect(foldTilstand(live.container)).toBe('false')

    // Streamen slutter. ChatView afmonterer den levende række og monterer den
    // persisterede besked fra historikken (nyt element, `key={m.id}`).
    cleanup()
    const historisk = render(
      <ChatFlowPresentation
        blocks={ARBEJDE} mode="calm" density="compact"
        streaming={false} status="done" finalAnswerStarted={false}
      />,
    )
    const efter = foldTilstand(historisk.container)

    console.log(
      `[MÅLING live→historisk] sammenfoldet under arbejde → efter persistering=${efter}`,
    )

    // Begge veje ender lukket her, så overgangen er usynlig i DETTE tilfælde.
    expect(efter).toBe('false')
  })

  it('den anden vej: udfoldet-under-arbejde foldes SAMMEN når turen persisteres', () => {
    // Live: åbent (fordi arbejdet kører). Brugeren rører den ikke.
    const live = render(
      <ChatFlowPresentation
        blocks={ARBEJDE} mode="calm" density="compact"
        streaming status="working" finalAnswerStarted={false}
      />,
    )
    expect(foldTilstand(live.container)).toBe('true')

    // Turen slutter → persisteret besked monteres → standarden er nu LUKKET.
    cleanup()
    const historisk = render(
      <ChatFlowPresentation
        blocks={ARBEJDE} mode="calm" density="compact"
        streaming={false} status="done" finalAnswerStarted={false}
      />,
    )
    const efter = foldTilstand(historisk.container)

    console.log(
      `[MÅLING live→historisk] åben under arbejde → efter persistering=${efter}`,
    )
    expect(efter).toBe('false')
  })
})
