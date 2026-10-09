import { act, renderHook } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { usePacedBlocks } from './usePacedBlocks'
import type { ContentBlock } from './sseProtocol'

describe('usePacedBlocks', () => {
  afterEach(() => vi.useRealTimers())

  it('afslører en hurtig tekststrøm gradvist og viser hele svaret ved afslutning', () => {
    vi.useFakeTimers()
    const text = 'Et langt svar med mange ord. '.repeat(12)
    const blocks: ContentBlock[] = [{ type: 'text', text }]
    const { result, rerender } = renderHook(({ live }) => usePacedBlocks(blocks, live), {
      initialProps: { live: true },
    })

    expect((result.current[0] as Extract<ContentBlock, { type: 'text' }>).text).toBe('')
    act(() => vi.advanceTimersByTime(33))
    const first = (result.current[0] as Extract<ContentBlock, { type: 'text' }>).text
    expect(first.length).toBeGreaterThan(0)
    expect(first.length).toBeLessThan(30)
    act(() => vi.advanceTimersByTime(99))
    const later = (result.current[0] as Extract<ContentBlock, { type: 'text' }>).text
    expect(later.length).toBeGreaterThan(first.length)
    expect(later.length).toBeLessThan(text.length)

    rerender({ live: false })
    expect((result.current[0] as Extract<ContentBlock, { type: 'text' }>).text).toBe(text)
  })

  it('viser værktøjer straks og afslutter forrige tekstblok når næste blok starter', () => {
    vi.useFakeTimers()
    const blocks: ContentBlock[] = [{ type: 'text', text: 'A'.repeat(200) }]
    const { result, rerender } = renderHook(({ current }) => usePacedBlocks(current, true), {
      initialProps: { current: blocks },
    })
    rerender({ current: [...blocks, { type: 'tool_use', id: 't1', name: 'search', input: {}, status: 'running' }] })
    expect(result.current[0]).toEqual(blocks[0])
    expect(result.current[1]?.type).toBe('tool_use')
  })

  it('holder synlig tekst tæt på en vedvarende hurtig stream', () => {
    vi.useFakeTimers()
    const { result, rerender } = renderHook(({ text }) => usePacedBlocks([{ type: 'text', text }], true), {
      initialProps: { text: '' },
    })
    let source = ''
    for (let frame = 0; frame < 90; frame++) {
      source += '1234567890123456789012345'
      rerender({ text: source })
      act(() => vi.advanceTimersByTime(33))
    }
    const visible = (result.current[0] as Extract<ContentBlock, { type: 'text' }>).text
    expect(visible.length).toBeLessThan(source.length)
    expect(source.length - visible.length).toBeLessThan(350)
  })
})
