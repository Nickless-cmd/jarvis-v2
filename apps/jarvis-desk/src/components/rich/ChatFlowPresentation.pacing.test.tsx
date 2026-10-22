/**
 * Fold-sekvensen målt med den RIGTIGE pacer — ikke en mock.
 *
 * `ChatFlowPresentation.test.tsx` mocker `useChatPacedBlocks` til at returnere
 * blokke uændret, så alle 24 tests der kører med pacing slået fra. Det er
 * derfor «det hurtige svar» (Bjørn 20/10-2026) kunne opstå uden at nogen test
 * fældede den: fejlen bor netop i forskellen mellem pacet og upacet tekst.
 *
 * Denne fil styrer `requestAnimationFrame` manuelt, så pacens ur er
 * deterministisk og hvert step kan måles.
 */
import { act, render } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
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

/** Kør præcis én frame frem `ms` millisekunder. */
function frame(ms = 16) {
  ur += ms
  const ko = rafKo
  rafKo = []
  act(() => {
    for (const cb of ko) cb(ur)
  })
}

function answerText(container: HTMLElement): string {
  return container.querySelector('.chat-flow-answer')?.textContent ?? ''
}

const LANG = 'Dette er et langt svar som serveren leverede i et enkelt hug, og det maa ikke vises paa én gang.'

const arbejde: ContentBlock = { type: 'tool_use', id: 't1', name: 'read_file', input: {}, status: 'done' }

describe('ChatFlowPresentation — fold uden at dumpe svaret', () => {
  it('viser ikke hele svaret i fold-framen mens pacen stadig kører', () => {
    const blokke: ContentBlock[] = [arbejde, { type: 'text', text: LANG }]

    // Før fold: turen kører, teksten er begyndt at streame.
    const view = render(
      <ChatFlowPresentation blocks={blokke} mode="living" density="compact"
        streaming status="working" finalAnswerStarted={false} runId="run-fold" />,
    )
    frame()
    frame()
    const foerFold = answerText(view.container)
    expect(foerFold.length).toBeLessThan(LANG.length)

    // Fold: serveren har leveret alt. Pacen må IKKE springe til ende.
    view.rerender(
      <ChatFlowPresentation blocks={blokke} mode="living" density="compact"
        streaming={false} status="done" finalAnswerStarted={false} runId="run-fold"
        paceFinalAnswer />,
    )
    const iFold = answerText(view.container)
    expect(iFold.length).toBeLessThan(LANG.length)

    // Et par frames senere er den stadig ikke færdig — pacen ejer teksten.
    frame()
    frame()
    const efterFold = answerText(view.container)
    expect(efterFold.length).toBeLessThan(LANG.length)
    expect(efterFold.length).toBeGreaterThanOrEqual(iFold.length)
  })

  it('når frem til hele svaret når pacen er færdig', () => {
    const blokke: ContentBlock[] = [arbejde, { type: 'text', text: 'Kort svar.' }]
    const view = render(
      <ChatFlowPresentation blocks={blokke} mode="living" density="compact"
        streaming={false} status="done" finalAnswerStarted={false} runId="run-kort"
        paceFinalAnswer />,
    )
    for (let i = 0; i < 40; i += 1) frame()
    expect(answerText(view.container)).toBe('Kort svar.')
  })

  it('bevarer bekræftet tekst når turen vender tilbage til værktøjsarbejde', () => {
    const foerste: ContentBlock[] = [arbejde, { type: 'text', text: 'Første svar.' }]
    const view = render(
      <ChatFlowPresentation blocks={foerste} mode="living" density="compact"
        streaming status="working" finalAnswerStarted runId="run-retur" />,
    )
    for (let i = 0; i < 120; i += 1) frame()
    expect(answerText(view.container)).toContain('Første svar.')

    const anden: ContentBlock[] = [
      ...foerste,
      { type: 'tool_use', id: 't2', name: 'search', input: {}, status: 'done' },
      { type: 'text', text: 'Supplerende svar.' },
    ]
    view.rerender(
      <ChatFlowPresentation blocks={anden} mode="living" density="compact"
        streaming status="working" finalAnswerStarted runId="run-retur" />,
    )
    for (let i = 0; i < 160; i += 1) frame()
    expect(answerText(view.container)).toContain('Første svar.')
    expect(answerText(view.container)).toContain('Supplerende svar.')
  })
})

describe('ChatFlowPresentation — final_answer_start midt i streamen', () => {
  it('lader aldrig svaret overhale pacen, heller ikke efter fold', () => {
    const del1 = 'Første del af svaret som er lang nok til at pacingen ikke er færdig.'
    const del2 = ' Anden del kommer efter værktøjskaldet og er også ganske lang.'
    const foerste: ContentBlock[] = [arbejde, { type: 'text', text: del1 }]
    const view = render(
      <ChatFlowPresentation blocks={foerste} mode="living" density="compact"
        streaming status="working" finalAnswerStarted={false} runId="run-mid" />,
    )
    frame()
    frame()

    // final_answer_start: serveren har markeret slutsvaret.
    view.rerender(
      <ChatFlowPresentation blocks={foerste} mode="living" density="compact"
        streaming status="working" finalAnswerStarted runId="run-mid" />,
    )
    frame()

    // Teksten vokser i endnu en blok, derefter leverer serveren alt.
    const alle: ContentBlock[] = [arbejde, { type: 'text', text: del1 + del2 }]
    view.rerender(
      <ChatFlowPresentation blocks={alle} mode="living" density="compact"
        streaming={false} status="done" finalAnswerStarted runId="run-mid" paceFinalAnswer />,
    )

    const samlet = del1 + del2
    for (let i = 0; i < 60; i += 1) {
      frame()
      const vist = answerText(view.container)
      expect(vist.length).toBeLessThanOrEqual(samlet.length)
    }
  })
})

describe('ChatFlowPresentation — rå tekst må ikke dumpe i svar-lanen', () => {
  it('viser ikke den fulde bekræftede tekst når turen vender tilbage til værktøjsarbejde', () => {
    const LANG = 'Første bekræftede svar som er temmelig langt og slet ikke paced endnu fordi der kun er gået få frames.'
    const foerste: ContentBlock[] = [arbejde, { type: 'text', text: LANG }]
    const view = render(
      <ChatFlowPresentation blocks={foerste} mode="living" density="compact"
        streaming status="working" finalAnswerStarted runId="run-dump" />,
    )
    for (let i = 0; i < 3; i += 1) frame()
    const pacet = answerText(view.container)
    // Pacen står stadig på de første tegn — det er forudsætningen for testen.
    expect(pacet.length).toBeLessThan(LANG.length / 4)

    const anden: ContentBlock[] = [
      ...foerste,
      { type: 'tool_use', id: 't2', name: 'search', input: {}, status: 'done' },
      { type: 'text', text: 'Supplerende svar.' },
    ]
    view.rerender(
      <ChatFlowPresentation blocks={anden} mode="living" density="compact"
        streaming status="working" finalAnswerStarted runId="run-dump" />,
    )
    // Den bekræftede tekst må ikke springe til sin fulde længde: svar-lanen
    // skal stadig kun vise det pacen har nået.
    expect(answerText(view.container).length).toBeLessThan(LANG.length / 2)
  })
})

describe('ChatFlowPresentation — aktiv rundelinje under pacing', () => {
  afterEach(() => vi.useRealTimers())

  it('fader den aktive rundelinje ud mens pacen ruller', () => {
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] })
    const blokke: ContentBlock[] = [arbejde, { type: 'text', text: LANG }]
    const view = render(
      <ChatFlowPresentation blocks={blokke} mode="living" density="compact"
        streaming status="working" finalAnswerStarted={false} runId="run-fade" />,
    )
    frame()
    const linje = view.container.querySelector('[data-testid="chat-flow-round"]') as HTMLElement
    expect(linje).toBeInTheDocument()
    // Foer taersklen: linjen staar urørt, saa en kort syntese aldrig blinker.
    expect(linje).not.toHaveAttribute('data-pacing-skjult')

    act(() => { vi.advanceTimersByTime(420) })
    expect(linje).toHaveAttribute('data-pacing-skjult')
    // Synteselinjen maa IKKE fade med: da begge fadede samtidig blev skaermen
    // tom (Bjørn 22/10-2026).
    const syntese = view.container.querySelector('[data-testid="chat-flow-activity"]') as HTMLElement
    expect(syntese).not.toHaveAttribute('data-pacing-skjult')
  })

  it('lader korte synteser passere uden at blinke linjen', () => {
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] })
    const blokke: ContentBlock[] = [arbejde, { type: 'text', text: 'Kort.' }]
    const view = render(
      <ChatFlowPresentation blocks={blokke} mode="living" density="compact"
        streaming status="working" finalAnswerStarted={false} runId="run-kort" />,
    )
    // Pacen indhenter fem tegn paa under 420 ms, saa timeren naar aldrig at fyre.
    for (let i = 0; i < 20; i += 1) frame()
    act(() => { vi.advanceTimersByTime(420) })
    const linje = view.container.querySelector('[data-testid="chat-flow-round"]') as HTMLElement
    expect(linje).not.toHaveAttribute('data-pacing-skjult')
  })
})
