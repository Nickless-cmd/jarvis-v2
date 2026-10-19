import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useChatPacedBlocks } from './useChatPacedBlocks'
import type { ContentBlock } from './sseProtocol'

type FrameRequestCallback = (time: number) => void

describe('useChatPacedBlocks', () => {
  let frames: FrameRequestCallback[]

  beforeEach(() => {
    frames = []
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
    while (shown().length < text.length && antalFrames < 400) {
      nextFrame()
      const now = shown().length
      expect(now - previous).toBeLessThanOrEqual(60)
      previous = now
      antalFrames += 1
    }
    expect(shown()).toBe(text)
    expect(antalFrames).toBeLessThan(400)
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
      // 720 tegn/s ved en 16 ms frame er højst 12 kodepunkter. Replay-kilden
      // må gerne løbe foran; skærmen må ikke forsøge at matche dens tempo.
      expect(vistNu - forrige).toBeLessThanOrEqual(12)
      forrige = vistNu
    }
    const visible = (result.current[0] as Extract<ContentBlock, { type: 'text' }>).text
    expect(visible.length).toBeLessThan(source.length)

    // Da kilden stopper, ruller pacingen resten færdig i de samme jævne trin.
    let antal = 0
    while ((result.current[0] as Extract<ContentBlock, { type: 'text' }>).text.length < source.length
      && antal < 400) {
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
    nextFrame()
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
    while (shown().length < text.length && antal < 400) {
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

  it('does not reuse a visible prefix when a new run starts', () => {
    const first = `Samme start ${'A'.repeat(100)}`
    const second = `Samme start ${'B'.repeat(100)}`
    const { result, rerender } = renderHook(({ text, runId }) => useChatPacedBlocks(
      [{ type: 'text', text }],
      { live: true, finalAnswerStarted: true, runId },
    ), { initialProps: { text: first, runId: 'run-a' } })
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
})
