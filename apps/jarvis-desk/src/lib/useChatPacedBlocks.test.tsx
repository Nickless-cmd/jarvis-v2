import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useChatPacedBlocks } from './useChatPacedBlocks'
import type { ContentBlock } from './sseProtocol'

type FrameRequestCallback = (time: number) => void

describe('useChatPacedBlocks', () => {
  let frames: FrameRequestCallback[]

  beforeEach(() => {
    frames = []
    ur = 0
    vi.stubGlobal('requestAnimationFrame', vi.fn((callback: FrameRequestCallback) => {
      frames.push(callback)
      return frames.length
    }))
    vi.stubGlobal('cancelAnimationFrame', vi.fn())
  })

  afterEach(() => vi.unstubAllGlobals())

  // Simuleret ur. Pacingen er tidsbaseret, så frames skal avancere tiden —
  // ellers måler testen en verden hvor der aldrig går et millisekund.
  let ur = 0
  function nextFrame(deltaMs = 16): void {
    ur += deltaMs
    const callback = frames.shift()
    expect(callback).toBeDefined()
    act(() => callback?.(ur))
  }

  it('reveals the current final text incrementally with one scheduled frame', () => {
    const text = 'Et levende svar med en rolig strøm. '.repeat(12)
    const blocks: ContentBlock[] = [{ type: 'text', text }]
    const { result } = renderHook(() => useChatPacedBlocks(blocks, {
      live: true, finalAnswerStarted: true, runId: 'run-1',
    }))

    expect((result.current[0] as Extract<ContentBlock, { type: 'text' }>).text).toBe('')
    expect(requestAnimationFrame).toHaveBeenCalledTimes(1)
    nextFrame()
    nextFrame()
    const first = (result.current[0] as Extract<ContentBlock, { type: 'text' }>).text
    expect(first.length).toBeGreaterThan(0)
    expect(first.length).toBeLessThan(text.length)
    expect(frames).toHaveLength(1)
  })

  it('dumper ikke et svar der lander i ét hug — det kommer i jævne trin', () => {
    // Bjørn 17/10-2026: «slutbeskeden bliver dumpet i stedet for streamet».
    // Serveren replay'er slutsvaret; lander hele teksten på én gang, sprang den
    // gamle backlog-regel til `target - 300` — 2700 af 3000 tegn i FØRSTE frame.
    const text = 'Et svar der lander i ét hug. '.repeat(100)
    const blocks: ContentBlock[] = [{ type: 'text', text }]
    const { result } = renderHook(() => useChatPacedBlocks(blocks, {
      live: true, finalAnswerStarted: true, runId: 'run-dump',
    }))
    const shown = () => (result.current[0] as Extract<ContentBlock, { type: 'text' }>).text

    nextFrame()
    const first = shown()
    expect(first.length).toBeGreaterThan(0)
    // Det afgørende: første frame må ikke være nær hele svaret.
    expect(first.length).toBeLessThan(Array.from(text).length / 10)

    // …og resten skal indhentes i trin, aldrig i ét spring.
    let previous = first.length
    let antalFrames = 0
    while (shown().length < text.length && antalFrames < 4_000) {
      nextFrame()
      const now = shown().length
      // 29/10-2026: frame-loftet er ikke længere et fast 6. Det følger
      // hastigheden (`maksPrFrame = rate × MAX_FRAME_DELTA_S`), fordi et fast
      // loft gjorde indhentningen umulig — samme fælde som 20/10, hvor et
      // loft på 2 gjorde hastighedsloftet virkningsløst. Hensigten er UÆNDRET:
      // resten skal komme i TRIN, aldrig i ét spring. Derfor måles det
      // relativt: ingen frame må vise mere end en tyvendedel af svaret.
      expect(now - previous).toBeLessThanOrEqual(Math.ceil(Array.from(text).length / 20))
      previous = now
      antalFrames += 1
    }
    expect(shown()).toBe(text)
    // MÅLT 29/10-2026: ~187 frames (3,1 s) — var >800 (≈17 s) med det faste
    // loft på 180. Kravet er at det tager målbar tid, ikke den gamle tid.
    expect(antalFrames).toBeGreaterThan(150)
  })

  it('begrænser en vedvarende hurtig replay til en læsbar strøm', () => {
    const { result, rerender } = renderHook(({ text }) => useChatPacedBlocks(
      [{ type: 'text', text }],
      { live: true, finalAnswerStarted: true, runId: 'run-fast' },
    ), { initialProps: { text: '' } })

    let source = ''
    let forrige = 0
    for (let index = 0; index < 60; index += 1) {
      source += '1234567890'.repeat(5)
      rerender({ text: source })
      nextFrame()
      const vistNu = (result.current[0] as Extract<ContentBlock, { type: 'text' }>).text.length
      // Kilden løber ~3000 tegn/s foran. Skærmen må ikke matche dens tempo
      // råt — den må kun indhente via efterslæbs-reglen, og et trin må aldrig
      // blive et spring. Grænsen er `maksPrFrame` (rate × 0,1 s), ikke et
      // fast 6: ved 667 tegn/s er den 67.
      expect(vistNu - forrige).toBeLessThanOrEqual(70)
      forrige = vistNu
    }
    const visible = (result.current[0] as Extract<ContentBlock, { type: 'text' }>).text
    expect(visible.length).toBeLessThan(source.length)

    // Da kilden stopper, ruller pacingen resten færdig i de samme jævne trin.
    let antal = 0
    while ((result.current[0] as Extract<ContentBlock, { type: 'text' }>).text.length < source.length
      && antal < 4_000) {
      nextFrame()
      antal += 1
    }
    expect((result.current[0] as Extract<ContentBlock, { type: 'text' }>).text).toBe(source)
  })

  it('never splits a Unicode code point', () => {
    const text = `abcd🙂${' videre'.repeat(20)}`
    const { result } = renderHook(() => useChatPacedBlocks([{ type: 'text', text }], {
      live: true, finalAnswerStarted: true, runId: 'run-emoji',
    }))
    while (!(result.current[0] as Extract<ContentBlock, { type: 'text' }>).text.includes('🙂')) {
      nextFrame()
    }
    const visible = (result.current[0] as Extract<ContentBlock, { type: 'text' }>).text
    expect(visible).toBe(Array.from(text).slice(0, Array.from(visible).length).join(''))
    expect(visible).toContain('🙂')
  })

  it('ruller færdig selv om strømmen slutter — slutbeskeden dumpes ikke', () => {
    // Bjørn 17/10-2026: «den dumper stadig ind slut beskeden». `live` bliver
    // falsk ved `message_stop`, og før kastede det resten op i ÉN tegning.
    // Et svar der er ved at rulle færdig skal rulle færdig.
    const text = 'Svar '.repeat(100)
    const blocks: ContentBlock[] = [{ type: 'text', text }]
    const { result, rerender } = renderHook(({ live }) => useChatPacedBlocks(blocks, {
      live, finalAnswerStarted: true, runId: 'run-finish',
    }), { initialProps: { live: true } })
    nextFrame()
    const shown = () => (result.current[0] as Extract<ContentBlock, { type: 'text' }>).text
    const efterFoerste = shown()
    expect(efterFoerste).not.toBe(text)

    rerender({ live: false })
    // Stadig ikke hele svaret — det fortsætter i trin.
    expect(shown().length).toBe(efterFoerste.length)

    let antal = 0
    while (shown().length < text.length && antal < 1_000) {
      nextFrame()
      antal += 1
    }
    expect(shown()).toBe(text)
  })

  it('viser hele svaret straks på en persisteret besked — den blev aldrig streamet', () => {
    // Undtagelsen til ovenstående: en besked der monteres EFTER turen blev
    // ikke rullet for øjnene af nogen og skal stå færdig med det samme.
    const text = 'Et svar der allerede er færdigt.'
    const { result } = renderHook(() => useChatPacedBlocks([{ type: 'text', text }], {
      live: false, finalAnswerStarted: true, runId: 'run-persisted',
    }))
    expect((result.current[0] as Extract<ContentBlock, { type: 'text' }>).text).toBe(text)
    expect(requestAnimationFrame).not.toHaveBeenCalled()
  })

  it('shows tools and deliveries immediately while pacing only text', () => {
    const tool: ContentBlock = { type: 'tool_use', id: 't1', name: 'search', input: {}, status: 'running' }
    const file: ContentBlock = { type: 'file', filename: 'svar.txt', url: '/files/svar.txt' }
    const blocks: ContentBlock[] = [tool, { type: 'text', text: 'A'.repeat(200) }, file]
    const { result } = renderHook(() => useChatPacedBlocks(blocks, {
      live: true, finalAnswerStarted: true, runId: 'run-rich',
    }))
    expect(result.current[0]).toBe(tool)
    expect(result.current[2]).toBe(file)
    expect((result.current[1] as Extract<ContentBlock, { type: 'text' }>).text).toBe('')
  })

  it('indhenter et stort efterslæb hurtigere end den gamle 72-loft-kurve', () => {
    // Bjørn 20/10-2026: «synket mellem den ægte stream og pacen [skal] ikk
    // være så stort». Med MAX=72 tog 1000 tegn 18,8 s. Kontrakten er nu under
    // 12 s, og grundtempoet (korte svar) må ikke være rørt.
    const text = 'x'.repeat(1000)
    const { result } = renderHook(() => useChatPacedBlocks([{ type: 'text', text }], {
      live: true, finalAnswerStarted: true, runId: 'run-synk',
    }))
    const shown = () => (result.current[0] as Extract<ContentBlock, { type: 'text' }>).text.length
    let frames = 0
    while (shown() < text.length && frames < 5_000) {
      nextFrame()
      frames += 1
    }
    expect(shown()).toBe(text.length)
    const sekunder = frames / 60
    // MÅLT 29/10-2026: 3,13 s for 1000 tegn — 320 tegn/s, 6,7x grundtempoet.
    // MÅLT 30/10-2026: **6,07 s** efter at ankomstmålingen blev flyttet til et
    // vindue og raten fik tilbagefald. De 3,13 s VAR «pacen løber for stærkt»
    // (Bjørn 30/10), så kontrakten er hævet med vilje: 165 tegn/s er 3,4x
    // grundtempoet og stadig hurtigere end de 12 s ved det gamle 72-loft.
    expect(sekunder).toBeLessThan(7)
    expect(sekunder).toBeGreaterThan(1)
  })

  it('beholder grundtempoet på et kort svar — tuningen må ikke gøre det hurtigere', () => {
    const text = 'x'.repeat(100)
    const { result } = renderHook(() => useChatPacedBlocks([{ type: 'text', text }], {
      live: true, finalAnswerStarted: true, runId: 'run-kort-synk',
    }))
    const shown = () => (result.current[0] as Extract<ContentBlock, { type: 'text' }>).text.length
    let frames = 0
    while (shown() < text.length && frames < 5_000) {
      nextFrame()
      frames += 1
    }
    // 100 tegn ved 48 tegn/s ≈ 2,1 s. Uændret fra før tuningingen.
    expect(frames / 60).toBeGreaterThan(1.9)
    expect(frames / 60).toBeLessThan(2.4)
  })

  it('pacer alle tekstblokke i slutsvaret som én strøm', () => {
    // Serveren kan dele ét markdown-svar ved en intern blokgrænse. Før blev
    // første blok vist straks, mens kun de sidste linjer i sidste blok blev
    // pacet — præcis det synlige hop når turhovedet foldede sammen.
    const first = 'Første del. '.repeat(30)
    const second = 'Anden del. '.repeat(30)
    const blocks: ContentBlock[] = [
      { type: 'text', text: first },
      { type: 'text', text: second },
    ]
    const { result } = renderHook(() => useChatPacedBlocks(blocks, {
      live: true, finalAnswerStarted: true, runId: 'run-flere-blokke',
    }))
    const shown = () => result.current
      .flatMap((block) => block.type === 'text' ? [block.text] : []).join('')

    expect(shown()).toBe('')
    nextFrame()
    nextFrame()
    expect(shown().length).toBeGreaterThan(0)
    expect(shown().length).toBeLessThan(first.length + second.length)
    expect((result.current[1] as Extract<ContentBlock, { type: 'text' }>).text).toBe('')

    let previous = shown().length
    let antal = 0
    while (shown().length < first.length + second.length && antal < 2_000) {
      nextFrame()
      expect(shown().length - previous).toBeLessThanOrEqual(6)
      previous = shown().length
      antal += 1
    }
    expect(result.current).toEqual(blocks)
  })

  it('does not reuse a visible prefix when a new run starts', () => {
    const first = `Samme start ${'A'.repeat(100)}`
    const second = `Samme start ${'B'.repeat(100)}`
    const { result, rerender } = renderHook(({ text, runId }) => useChatPacedBlocks(
      [{ type: 'text', text }],
      { live: true, finalAnswerStarted: true, runId },
    ), { initialProps: { text: first, runId: 'run-a' } })
    nextFrame()
    nextFrame()
    expect((result.current[0] as Extract<ContentBlock, { type: 'text' }>).text.length).toBeGreaterThan(0)
    rerender({ text: second, runId: 'run-b' })
    expect((result.current[0] as Extract<ContentBlock, { type: 'text' }>).text).toBe('')
  })

  it('does not pace text before the authoritative final transition', () => {
    const block: ContentBlock = { type: 'text', text: 'arbejdstekst' }
    const { result } = renderHook(() => useChatPacedBlocks([block], {
      live: true, finalAnswerStarted: false, runId: 'run-work',
    }))
    expect(result.current[0]).toBe(block)
    expect(requestAnimationFrame).not.toHaveBeenCalled()
  })

  it('ruller færdig selv om finalAnswerStarted aldrig blev sat — rå svar må ikke dumpe', () => {
    // Målt 20/10-2026 (Bjørn: «det rå svar vises over det pacede svar»).
    //
    // `active` krævede `textIndices.length > 0`, og `textIndices` var afledt af
    // `finalAnswerStarted`. Et run hvor fold-signalet aldrig blev sat — netop
    // det jeg rettede i SSE-relæet samme dag — faldt derfor tilbage til
    // `return blocks` i det øjeblik `streaming` blev falsk: hele svaret i ÉN
    // frame, oven på den pacede linje der stadig rullede.
    //
    // Kontrakten er at en tekst der ÉN gang er begyndt at rulle, ruller
    // færdig. Det må ikke afhænge af et signal der kan udeblive.
    const text = 'Svar '.repeat(100)
    const blocks: ContentBlock[] = [{ type: 'text', text }]
    const { result, rerender } = renderHook(
      ({ live, paceAllText, finalAnswerStarted }: { live: boolean; paceAllText: boolean; finalAnswerStarted: boolean }) =>
        useChatPacedBlocks(blocks, { live, paceAllText, finalAnswerStarted, runId: 'run-uden-fold' }),
      { initialProps: { live: true, paceAllText: true, finalAnswerStarted: false } },
    )
    const shown = () => (result.current[0] as Extract<ContentBlock, { type: 'text' }>).text
    nextFrame()
    nextFrame()
    const efterFoerste = shown()
    expect(efterFoerste.length).toBeGreaterThan(0)
    expect(efterFoerste.length).toBeLessThan(text.length)

    // Strømmen slutter, og fold-signalet er stadig ikke sat. Det er fejlen.
    rerender({ live: false, paceAllText: false, finalAnswerStarted: false })
    expect(shown()).toBe(efterFoerste)

    let antal = 0
    while (shown().length < text.length && antal < 1_000) {
      nextFrame()
      antal += 1
    }
    expect(shown()).toBe(text)
  })

  it('pacer levende Chat-tekst før final_answer_start når hele chatstrømmen er slået til', () => {
    const text = 'Et normalt svar uden værktøj. '.repeat(20)
    const { result } = renderHook(() => useChatPacedBlocks([{ type: 'text', text }], {
      live: true, finalAnswerStarted: false, paceAllText: true, runId: 'run-no-tool',
    }))
    expect((result.current[0] as Extract<ContentBlock, { type: 'text' }>).text).toBe('')
    nextFrame()
    nextFrame()
    const visible = (result.current[0] as Extract<ContentBlock, { type: 'text' }>).text
    expect(visible.length).toBeGreaterThan(0)
    expect(visible.length).toBeLessThan(text.length)
  })
})
