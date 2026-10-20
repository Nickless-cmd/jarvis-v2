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

    // FOLD (20/10-2026): `live` bliver falsk når streamen slutter. Det må
    // IKKE dumpe resten — det var præcis «det hurtige svar» Bjørn så. Teksten
    // skal rulle færdig med samme kurve som før foldet.
    rerender({ live: false })
    const vedFold = (result.current[0] as Extract<ContentBlock, { type: 'text' }>).text
    expect(vedFold.length).toBe(later.length)
    expect(vedFold.length).toBeLessThan(text.length)

    // …og den når hele vejen, blot i sin egen takt.
    act(() => vi.advanceTimersByTime(33 * 400))
    expect((result.current[0] as Extract<ContentBlock, { type: 'text' }>).text).toBe(text)
  })

  it('viser værktøjer straks og lader tekstblokken rulle færdig', () => {
    vi.useFakeTimers()
    const blocks: ContentBlock[] = [{ type: 'text', text: 'A'.repeat(200) }]
    const { result, rerender } = renderHook(({ current }) => usePacedBlocks(current, true), {
      initialProps: { current: blocks },
    })
    rerender({ current: [...blocks, { type: 'tool_use', id: 't1', name: 'search', input: {}, status: 'running' }] })
    // Værktøjet er ikke tekst og skal frem med det samme.
    expect(result.current[1]?.type).toBe('tool_use')
    // Men en NY blok må ikke afslutte den forrige tekst: den var midt i sin
    // kurve, og et blokskift er ikke et signal om at dumpe resten.
    expect((result.current[0] as Extract<ContentBlock, { type: 'text' }>).text.length).toBeLessThan(200)

    act(() => vi.advanceTimersByTime(33 * 400))
    expect(result.current[0]).toEqual(blocks[0])
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

  it('deler ikke en emoji midt i et tegn', () => {
    vi.useFakeTimers()
    const text = 'abcd🙂' + ' videre i teksten'.repeat(3)
    const { result } = renderHook(() => usePacedBlocks([{ type: 'text', text }], true))
    act(() => vi.advanceTimersByTime(33))
    const visible = (result.current[0] as Extract<ContentBlock, { type: 'text' }>).text
    expect(visible).toBe('abcd🙂')
  })

  it('genbruger ikke synlig tekst fra et tidligere svar', () => {
    vi.useFakeTimers()
    const first = 'Jarvis: ' + 'A'.repeat(72)
    const next = 'Jarvis: ' + 'B'.repeat(72)
    const { result, rerender } = renderHook(({ text, live }) => usePacedBlocks([{ type: 'text', text }], live), {
      initialProps: { text: first, live: true },
    })
    act(() => vi.advanceTimersByTime(33))
    rerender({ text: first, live: false })
    rerender({ text: next, live: true })
    expect((result.current[0] as Extract<ContentBlock, { type: 'text' }>).text).toBe('')
  })

  it('pacer ALLE tekstblokke — ikke kun den sidste', () => {
    // Målt 20/10-2026: med to tekstblokke blev den første dumpet råt (82 af
    // 167 tegn vist) fordi kun den sidste blok havde et ur. Det er samme
    // familie som «det hurtige svar»: en del af svaret stod færdigt med det
    // samme, resten rullede.
    vi.useFakeTimers()
    const blocks: ContentBlock[] = [
      { type: 'text', text: 'A'.repeat(80) },
      { type: 'tool_use', id: 't1', name: 'read_file', input: {}, status: 'done' },
      { type: 'text', text: 'B'.repeat(80) },
    ]
    const { result } = renderHook(() => usePacedBlocks(blocks, true))

    // Ingen af blokkene er vist endnu — begge er under cursoren.
    expect((result.current[0] as Extract<ContentBlock, { type: 'text' }>).text).toBe('')
    expect((result.current[2] as Extract<ContentBlock, { type: 'text' }>).text).toBe('')

    act(() => vi.advanceTimersByTime(33))
    const foersteVist = (result.current[0] as Extract<ContentBlock, { type: 'text' }>).text.length
    expect(foersteVist).toBeGreaterThan(0)
    // Den første blok må ikke være dumpet fuldt ud mens den anden venter.
    expect(foersteVist).toBeLessThan(80)
    expect((result.current[2] as Extract<ContentBlock, { type: 'text' }>).text).toBe('')

    // …og efter nok ticks står begge blokke komplette.
    act(() => vi.advanceTimersByTime(33 * 400))
    expect(result.current[0]).toEqual(blocks[0])
    expect(result.current[2]).toEqual(blocks[2])
  })
})
