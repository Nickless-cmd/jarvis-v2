/**
 * VAGT — turhovedet (og dets skillestreg) forsvinder ALDRIG midt i en tur.
 *
 * Bjørn 30/10-2026: «nu forsvinder turhoved og skill linjen indtil svaret er
 * færdig».
 *
 * Årsagen var `pacerSvar = paceFinalAnswer && status === 'done'`, som blev sat
 * FORAN hele `visTurhoved`:
 *
 *   const visTurhoved = !pacerSvar && (harArbejde || streaming || sekunder !== null)
 *
 * Det betød at `.rv-tur` blev fjernet fra DOM'en i præcis det vindue hvor
 * slutsvaret rulles ud efter `message_stop` — altså i 2-3 sekunder hvor turen
 * stadig løber for øjet. Hovedet er turens ENESTE vandrette streg; forsvinder
 * den, ser turen ud som to.
 *
 * Gaten blev indført 29/10 som fix for det modsatte symptom («pacen kører
 * inde i hoved»). Det var en forkert læsning: teksten lå dengang i
 * arbejdsvisningen, og den vej er lukket siden (`restoredText` henter de
 * bekræftede tekster fra de PACEDE arbejdsblokke og lægger dem i svar-lanen).
 *
 * Kontrakten er derfor TO ting på én gang:
 *
 *   1. Hovedet STÅR gennem hele pace-vinduet — i hver frame.
 *   2. Foldet er LUKKET (`aria-expanded="false"`), så pacen ruller uden for det.
 *
 * Vagten måler i HVER frame, ikke kun til sidst: en gate der først slår til
 * efter frame 1 ville bestå en sluttjek og stadig blinke for brugeren.
 */
import { act, render } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('../../hooks/useSettings', () => ({
  useSettings: () => ({ settings: { apiBaseUrl: 'https://api.srvlab.dk', authToken: 't' } }),
}))

import { ChatFlowPresentation } from './ChatFlowPresentation'
import type { ContentBlock } from '../../lib/sseProtocol'

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

function frame(ms = 16): number {
  ur += ms
  const ko = rafKo
  rafKo = []
  act(() => {
    for (const cb of ko) cb(ur)
  })
  return ko.length
}

/** 2000 tegn — et typisk slutsvar med mellemregninger. Nok til at pacen ruller
 *  gennem mange frames, så et glip på ét frame er målbart. */
const LANG = 'Jeg har målt det og rettet det, og her er hvad tallene faktisk viser om forløbet. '.repeat(25).slice(0, 2000)
const svar: ContentBlock = { type: 'text', text: LANG, phase: 'final_answer' }
/** Et værktøjskald, så hovedet er FOLDBART. Uden det renderes `.rv-tur` som en
 *  statisk `<div>` uden `aria-expanded`, og en assertion på fold-tilstanden
 *  ville være tom og altid sand. */
const arbejde: ContentBlock = { type: 'tool_use', id: 't1', name: 'read_file', input: {}, status: 'done' }

function hoved(container: HTMLElement): HTMLElement | null {
  return container.querySelector('.rv-tur')
}

function vistTekst(container: HTMLElement): string {
  return container.querySelector('.chat-flow-answer')?.textContent ?? ''
}

/** Props som `ChatView` faktisk sender (linje 1104): uret følger turen, og
 *  `paceFinalAnswer` holder pacen i live efter `message_stop`. */
function renderPaceVindue(runId: string) {
  return render(
    <ChatFlowPresentation blocks={[arbejde, svar]} mode="living" density="compact"
      streaming={false} status="done" finalAnswerStarted runId={runId}
      turStart={Date.now() - 12_000} turSlut={Date.now()} paceFinalAnswer />,
  )
}

describe('VAGT — hovedet forsvinder ikke midt i turen', () => {
  it('står i HVER frame mens pacen ruller', () => {
    const view = renderPaceVindue('vagt-hver-frame')
    const manglende: number[] = []

    // Kør til pacen selv holder op med at bede om frames. Hvert frame hvor
    // `.rv-tur` er væk registreres med sit nummer, så fejlmeddelelsen viser
    // HVORNÅR det skete — ikke bare at det skete.
    let frames = 0
    while (frames < 5000) {
      frame(16)
      frames += 1
      if (!hoved(view.container)) manglende.push(frames)
      if (rafKo.length === 0) break
    }

    // Pacen SKAL have rullet flere frames, ellers måler vagten ingenting.
    expect(frames).toBeGreaterThan(30)
    expect(manglende).toEqual([])
    expect(hoved(view.container)).not.toBeNull()
  })

  it('foldet er lukket mens pacen ruller — teksten hører i svar-lanen', () => {
    const view = renderPaceVindue('vagt-lukket-fold')
    frame()
    frame()

    // `TurHoved` sætter `aria-expanded` (der findes ingen `data-aaben` på
    // elementet — en assertion på den ville være tom og altid sand).
    expect(hoved(view.container)?.getAttribute('aria-expanded')).toBe('false')
    // Og svaret ruller faktisk: teksten er begyndt men ikke færdig.
    const vist = vistTekst(view.container).length
    expect(vist).toBeGreaterThan(0)
    expect(vist).toBeLessThan(LANG.length)
  })

  it('bærer skillestregen gennem hele vinduet', () => {
    const view = renderPaceVindue('vagt-skillelinje')
    frame()

    const stregen = hoved(view.container)
    expect(stregen).not.toBeNull()
    // `data-skillelinje` er den attribut der tegner den 1px streg — den er
    // turens visuelle samling og forsvandt sammen med hovedet.
    expect(stregen?.hasAttribute('data-skillelinje')).toBe(true)

    while (rafKo.length > 0) frame(16)
    expect(hoved(view.container)?.hasAttribute('data-skillelinje')).toBe(true)
  })
})
