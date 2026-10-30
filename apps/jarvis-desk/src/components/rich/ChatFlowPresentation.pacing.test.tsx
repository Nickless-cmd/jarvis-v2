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

  it('folger code mode: gruppen lukkes i samme frame som hovedet folder', () => {
    // Bjørn 22/10-2026, fjerde runde: «ja gør som i code mode.. det virker».
    //
    // Code mode (`RaekkeTranskript.tsx:449/469`) har ÉN gate: `aaben` følger
    // svarets start, og gruppen skjules i samme frame. Ingen `rammeAaben`, der
    // holder rammen åben indtil pacen er færdig — det var netop den der fik
    // foldet til at se ud som om det ventede på pacen.
    //
    // Syntesen er en tekstblok med `phase: 'commentary'` — den bliver i
    // `workBlocks` efter `finalAnswerStarted`. En blok uden phase bliver
    // slutsvaret og kan derfor ikke bruges som syntese her (målt 22/10-2026).
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] })
    const syntese: ContentBlock = { type: 'text', text: 'Læser koden', phase: 'commentary' } as ContentBlock
    const blokke: ContentBlock[] = [arbejde, syntese, { type: 'text', text: LANG }]
    const view = render(
      <ChatFlowPresentation blocks={blokke} mode="living" density="compact"
        streaming status="working" finalAnswerStarted runId="run-vindue" />,
    )
    frame()
    // Hovedet folder ved svarets start — uafhaengigt af hvor pacen er.
    const hoved = view.container.querySelector('.rv-tur') as HTMLElement
    expect(hoved).toBeInTheDocument()
    expect(hoved).toHaveAttribute('aria-expanded', 'false')
    // Og rammen foelger hovedet, som i code mode. Ikke pacen.
    const ydre = view.container.querySelector('.chat-flow-gruppe-ydre') as HTMLElement
    expect(ydre).toHaveAttribute('data-aaben', 'false')
    // Linjerne er ikke monteret naar gruppen er lukket (code mode:
    // `{aaben && sektioner.map(...)}`).
    expect(view.container.querySelector('[data-testid="chat-flow-activity"]')).not.toBeInTheDocument()
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

  it('rundelinjens levende Jarvis-markør overlever faden', () => {
    // Faden maa kun aendre SYNLIGHED, ikke levetid. `usePacingWorkLine` saetter
    // en attribut — den unmounter ikke linjen — saa Jarvis-markoeren skal
    // vaere den SAMME DOM-node efter faden. Det bevarer animationens fase og
    // giver chat-linjen samme rolige tilstedevaerelse som code mode.
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] })
    try {
      const syntese = { type: 'text', text: 'Læser koden', phase: 'commentary' } as ContentBlock
      const blokke: ContentBlock[] = [arbejde, syntese, { type: 'text', text: LANG }]
      const view = render(
        <ChatFlowPresentation blocks={blokke} mode="living" density="compact"
          streaming status="working" finalAnswerStarted={false} runId="run-ur" />,
      )
      frame()
      const markoerFoer = view.container.querySelector(
        '[data-testid="chat-flow-round"] .jarvis-ring',
      ) as HTMLElement
      expect(markoerFoer).toBeInTheDocument()
      expect(markoerFoer).toHaveClass('is-working')
      act(() => { vi.advanceTimersByTime(420) })
      const linje = view.container.querySelector('[data-testid="chat-flow-round"]') as HTMLElement
      expect(linje).toHaveAttribute('data-pacing-skjult')
      const markoerEfter = view.container.querySelector(
        '[data-testid="chat-flow-round"] .jarvis-ring',
      ) as HTMLElement
      expect(markoerEfter).toBe(markoerFoer)
    } finally {
      vi.useRealTimers()
    }
  })
})

describe('ChatFlowPresentation — hovedet under pacen (30/10-2026)', () => {
  // Bjørn 29/10-2026: «pacen kører først inde i hoved efter foldet, og så går
  // der indtil pacen er færdig inde i hoved, til den pacer for nyt uden for
  // hoved». Jeg læste det som «hovedet skal væk» og satte en gate foran hele
  // `visTurhoved`. Det var den forkerte læsning.
  //
  // Bjørn 30/10-2026: «nu forsvinder turhoved og skill linjen indtil svaret er
  // færdig». Gaten fjernede ikke et problem — den fjernede turens eneste
  // vandrette streg midt i turen, så turen så ud som to.
  //
  // Den ægte kerne i 29/10-klagen var PLACERINGEN: teksten rullede inde i
  // arbejdsvisningen under hovedet. Den vej er lukket (`restoredText` henter
  // de bekræftede tekster fra de PACEDE arbejdsblokke og lægger dem i
  // svar-lanen; `retainedWork` filtrerer dem ud af arbejdet). Så nu er begge
  // krav opfyldt på én gang: hovedet står, og teksten ruller uden for det.
  //
  // Kontrakten er derfor:
  //   1. `.rv-tur` STÅR gennem pace-vinduet.
  //   2. Foldet er LUKKET (`aria-expanded="false"`).
  //   3. Teksten ruller i `.chat-flow-answer`.
  //   4. Teksten står IKKE i arbejdsvisningen.
  it('beholder hovedet, men lukker foldet — teksten ruller uden for det', () => {
    const blokke: ContentBlock[] = [arbejde, { type: 'text', text: LANG }]
    const view = render(
      <ChatFlowPresentation blocks={blokke} mode="living" density="compact"
        streaming={false} status="done" finalAnswerStarted runId="run-hoved"
        paceFinalAnswer turStart={Date.now() - 5000} />,
    )
    frame()
    frame()

    // 1. Pacen ruller stadig — teksten er ikke færdig.
    expect(answerText(view.container).length).toBeLessThan(LANG.length)

    // 2. Hovedet STÅR. Det er turens skillestreg, ikke en statuslinje.
    const hoved = view.container.querySelector('.rv-tur')
    expect(hoved).not.toBeNull()

    // 3. Foldet er lukket, så pacen ikke ruller inde i hovedet.
    expect(hoved).toHaveAttribute('aria-expanded', 'false')

    // 4. Arbejdsvisningen er ikke monteret — svaret har ingen vej ind i den.
    expect(view.container.querySelector('.chat-flow-work-details')).toBeNull()
    // Og teksten står i svar-lanen, som er en SØSKEN til hovedet.
    expect(answerText(view.container).length).toBeGreaterThan(0)
  })

  it('står ogsaa naar KUN paceFinalAnswer baerer pacen (intet fold-signal)', () => {
    // Vejen hvor serveren ikke har sendt `final_answer_start`: `pacingFinal`
    // bliver sand via `paceFinalAnswer && status === 'done'`, men
    // `finalAnswerStarted` er FALSK. Hovedet skal stadig stå — det er samme
    // tur for øjet, uanset hvilket signal der satte pacen i gang.
    const blokke: ContentBlock[] = [arbejde, { type: 'text', text: LANG }]
    const view = render(
      <ChatFlowPresentation blocks={blokke} mode="living" density="compact"
        streaming={false} status="done" finalAnswerStarted={false} runId="run-uden-signal"
        paceFinalAnswer turStart={Date.now() - 5000} />,
    )
    frame()
    frame()
    expect(answerText(view.container).length).toBeLessThan(LANG.length)
    expect(view.container.querySelector('.rv-tur')).not.toBeNull()
    // Uden fold-signal er `arbejdeKoerer` falsk, så hovedet er ikke åbent.
    expect(view.container.querySelector('.rv-tur')).toHaveAttribute('aria-expanded', 'false')
  })

  it('hovedet bliver ogsaa staaende efter pacen er færdig', () => {
    // Det modsatte yderpunkt: hvis hovedet forsvandt da pacen sluttede, ville
    // turen skifte form midt for øjet på brugeren. Det må ikke ske.
    const blokke: ContentBlock[] = [arbejde, { type: 'text', text: 'Kort svar.' }]
    const view = render(
      <ChatFlowPresentation blocks={blokke} mode="living" density="compact"
        streaming={false} status="done" finalAnswerStarted runId="run-efter"
        paceFinalAnswer turStart={Date.now() - 5000} />,
    )
    for (let i = 0; i < 60; i += 1) frame()
    expect(answerText(view.container)).toBe('Kort svar.')
    expect(view.container.querySelector('.rv-tur')).not.toBeNull()
  })
})

