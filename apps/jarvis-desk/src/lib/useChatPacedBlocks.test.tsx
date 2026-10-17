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

  function nextFrame(): void {
    const callback = frames.shift()
    expect(callback).toBeDefined()
    act(() => callback?.(performance.now()))
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
    let frames = 0
    while (shown().length < text.length && frames < 200) {
      nextFrame()
      const now = shown().length
      expect(now - previous).toBeLessThanOrEqual(60)
      previous = now
      frames += 1
    }
    expect(shown()).toBe(text)
    expect(frames).toBeLessThan(200)
  })

  it('følger en vedvarende hurtig stream uden at sakke ubegrænset bagud', () => {
    const { result, rerender } = renderHook(({ text }) => useChatPacedBlocks(
      [{ type: 'text', text }],
      { live: true, finalAnswerStarted: true, runId: 'run-fast' },
    ), { initialProps: { text: '' } })

    let source = ''
    for (let index = 0; index < 60; index += 1) {
      source += '1234567890'.repeat(5)
      rerender({ text: source })
      nextFrame()
    }
    const visible = (result.current[0] as Extract<ContentBlock, { type: 'text' }>).text
    expect(visible.length).toBeLessThan(source.length)
    // Efterslæbet stabiliserer sig (loftet kan følge kilden) i stedet for at vokse.
    expect(source.length - visible.length).toBeLessThan(800)
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

  it('flushes immediately when streaming completes', () => {
    const text = 'Svar '.repeat(100)
    const blocks: ContentBlock[] = [{ type: 'text', text }]
    const { result, rerender } = renderHook(({ live }) => useChatPacedBlocks(blocks, {
      live, finalAnswerStarted: true, runId: 'run-finish',
    }), { initialProps: { live: true } })
    nextFrame()
    expect((result.current[0] as Extract<ContentBlock, { type: 'text' }>).text).not.toBe(text)
    rerender({ live: false })
    expect((result.current[0] as Extract<ContentBlock, { type: 'text' }>).text).toBe(text)
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
