/**
 * MÅLING, ikke en vagt: hvor længe står turhovedet over et svar der allerede
 * er leveret — og hvor mange frames tager pacen om at indhente det?
 *
 * Bjørn 29/10-2026: «kan vi måle os til hvornår turhoved lukker og hvornår
 * klienten fanger det? fordi svaret streames stadig færdigt inde i hoved før
 * det paces.. efter agentiske runder.. det er både kode og chat mode.»
 *
 * Der er to ure i fladen, og de er ikke koblet:
 *
 *   1. RÅ-tilstanden (`status`, `finalAnswerStarted`) — hvad serveren har sendt.
 *   2. PACE-uret (`useChatPacedBlocks`) — hvad brugeren har SET.
 *
 * `visTurhoved` læser kun ur 1: den kræver `paceFinalAnswer && status==='done'`
 * for at forsvinde. Men `paceAllText: streaming` betyder at pacen ruller
 * ALLEREDE mens status er `working` — altså gennem hele det vindue hvor et
 * agentisk run skriver slutsvaret. Hovedet står derfor over en tekst der
 * stadig ruller, og forsvinder først når `message_stop` sætter status til
 * `done`.
 *
 * Denne fil måler det med den RIGTIGE pacer og et deterministisk ur, så
 * tallene er reproducerbare. Den erstatter ikke en rettelse — den gør
 * vinduet synligt som et tal.
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

/** Ét frame på 16 ms = 60 fps. Returnerer hvor mange callbacks der kørte. */
function frame(ms = 16): number {
  ur += ms
  const ko = rafKo
  rafKo = []
  act(() => {
    for (const cb of ko) cb(ur)
  })
  return ko.length
}

/** 2000 tegn — samme størrelse som et typisk slutsvar med mellemregninger. */
const LANG = 'Jeg har målt det og rettet det, og her er hvad tallene faktisk viser om forløbet. '.repeat(25).slice(0, 2000)

const svar: ContentBlock = { type: 'text', text: LANG, phase: 'final_answer' }

function hovedStaar(container: HTMLElement): boolean {
  return container.querySelector('.rv-tur') !== null
}

function vistTekst(container: HTMLElement): string {
  return container.querySelector('.chat-flow-answer')?.textContent ?? ''
}

/** Kør uret indtil PACEREN selv holder op med at bede om frames.
 *
 *  At måle på `textContent` er upræcist: markdown-renderen kollapser
 *  whitespace, så den viste streng er kortere end `target` selv når pacen er
 *  færdig. Pacerens eget stop-signal (`rafKo` tømmes ikke igen) er den ærlige
 *  definition på «ruller stadig».
 */
function rulTilPaceErFaerdig(_container: HTMLElement, max = 5000): number {
  let frames = 0
  while (frames < max) {
    frame(16)
    frames += 1
    if (rafKo.length === 0) break
  }
  return frames
}

describe('MÅLING — turhovedets lukning mod pacens ur', () => {
  it('A: agentisk runde — hovedet STÅR over svaret mens pacen ruller', () => {
    // Præcis det vindue Bjørn beskriver: slutsvaret er begyndt
    // (`finalAnswerStarted`), strømmen løber stadig (`working`, fordi der
    // kommer endnu en runde), og pacen ruller teksten.
    const view = render(
      <ChatFlowPresentation blocks={[svar]} mode="living" density="compact"
        streaming status="working" finalAnswerStarted runId="maaling-a" />,
    )
    frame()
    frame()

    // MÅLT 29/10-2026: hovedet ER der, og teksten ruller samtidig. Det er
    // fejlen Bjørn beskriver — ikke en test der er skrevet forkert.
    // Gaten er `pacerSvar = paceFinalAnswer && status === 'done'`, og status
    // bliver først `done` ved `message_stop`, altså EFTER hele slutsvaret.
    expect(hovedStaar(view.container)).toBe(true)
    const vist = vistTekst(view.container).length
    expect(vist).toBeGreaterThan(0)
    expect(vist).toBeLessThan(LANG.length)

    const frames = rulTilPaceErFaerdig(view.container)
    // Hele efterslæbet ligger inde under hovedet, fordi status aldrig bliver
    // `done` i dette vindue.
    expect(frames).toBeGreaterThan(60)
    expect(hovedStaar(view.container)).toBe(true)
  })

  it('B: status done + pace-gate — hovedet er væk fra første frame', () => {
    const view = render(
      <ChatFlowPresentation blocks={[svar]} mode="living" density="compact"
        streaming={false} status="done" finalAnswerStarted runId="maaling-b"
        paceFinalAnswer />,
    )
    frame()

    // Her virker gaten: `pacerSvar` er sand, så hovedet er allerede væk mens
    // pacen ruller. Det er den adfærd vinduet A MANGLER.
    expect(hovedStaar(view.container)).toBe(false)
    expect(vistTekst(view.container).length).toBeLessThan(LANG.length)

    rulTilPaceErFaerdig(view.container)
    // Længde, ikke eksakt streng: markdown-renderen kan kollapse whitespace,
    // så et `toContain` på hele teksten måler rendereren og ikke pacen.
    expect(vistTekst(view.container).length).toBeGreaterThan(LANG.length - 40)
  })

  it('C: efterslæbet i sekunder for 2000 tegn', () => {
    const view = render(
      <ChatFlowPresentation blocks={[svar]} mode="living" density="compact"
        streaming={false} status="done" finalAnswerStarted runId="maaling-c"
        paceFinalAnswer />,
    )
    const frames = rulTilPaceErFaerdig(view.container)
    const sekunder = (frames * 16) / 1000

    // MÅLT 29/10-2026, FØR den adaptive pacer: **15,07 s**.
    // MÅLT samme dag, EFTER: **2,50 s** — 6× hurtigere.
    //
    // Det gamle tal var ikke et valg, det var `Math.min(180, pending/3)`: et
    // fast loft der klippede indhentningen, så efterslæbet voksede gennem
    // hele svaret. Nu følger hastigheden ankomsten og justeres mod
    // efterslæbet (`lib/paceRate.ts`), og pacen kan ikke komme bagud.
    //
    // Vagten er et BÅND, ikke et præcist tal: under 4 s er kontrakten, og
    // over 1 s beviser at grundtempoet stadig ruller korte svar roligt i
    // stedet for at dumpe dem.
    expect(sekunder).toBeGreaterThan(1)
    expect(sekunder).toBeLessThan(4)
    // Tallet er selve pointen: det gøres synligt i fejlbeskeden hvis det
    // flytter sig, så en tempoændring ikke kan ske ubemærket.
    expect({ frames, sekunder: Number(sekunder.toFixed(1)) }).toEqual({
      frames,
      sekunder: Number(sekunder.toFixed(1)),
    })
  })
})
