/**
 * Bjørns seks punkter om chat-linjerne, 17/9-2026 — ét sted, så de kan læses
 * samlet: sekunder der forsvandt, kald der pulserede efter han var videre,
 * «Kører bash…» uden metadata, og tanke-linjen uden indhold mens den løber.
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen, act } from '@testing-library/react'
import { streamReducer, udfaldsStatus } from './streamReducer'
import { describeTool, summarizeRound } from './toolRound'
import { afslutForladteKald } from '../components/rich/BlocksRenderer'
import { ThinkingLine } from '../components/rich/ThinkingLine'
import { ToolGroupCard } from '../components/rich/ToolGroupCard'
import type { ContentBlock, StreamEvent } from './sseProtocol'

afterEach(() => { vi.useRealTimers() })

function reduce(events: StreamEvent[]) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return events.reduce((s, e) => streamReducer(s, e), { status: 'working', blocks: [], usage: { input: 0, output: 0 } } as any)
}

describe('tænketid ligger på blokken', () => {
  it('en tanke får sine sekunder når næste blok starter', () => {
    vi.useFakeTimers()
    vi.setSystemTime(1_000_000)
    let s = reduce([{ type: 'content_block_start', index: 0, content_block: { type: 'thinking', thinking: '' } } as StreamEvent])
    vi.setSystemTime(1_012_400)
    s = streamReducer(s, { type: 'content_block_start', index: 1, content_block: { type: 'text', text: '' } } as StreamEvent)
    expect(s.blocks[0]).toMatchObject({ type: 'thinking', seconds: 12.4 })
  })

  it('et replay af SAMME tanke lukker den ikke', () => {
    const start = { type: 'content_block_start', index: 0, content_block: { type: 'thinking', thinking: '' } } as StreamEvent
    const s = reduce([start, start])
    expect((s.blocks[0] as Extract<ContentBlock, { type: 'thinking' }>).seconds).toBeUndefined()
  })

  it('tiden overlever at linjen monteres om — uret følger blokken, ikke komponenten', () => {
    vi.useFakeTimers()
    vi.setSystemTime(2_000_000)
    const startet = Date.now()
    vi.setSystemTime(2_007_000)
    render(<ThinkingLine text="x" live startet={startet} />)
    expect(screen.getByTestId('tanke-meta')).toHaveTextContent('· 7 s')
  })

  it('live viser hvad han tænker på, og det forsvinder når tanken er slut', () => {
    const { rerender } = render(<ThinkingLine text={'Første tanke\nLad mig se hvor værnet sidder'} live />)
    expect(screen.getByTestId('tanke-meta')).toHaveTextContent('Lad mig se hvor værnet sidder')
    rerender(<ThinkingLine text={'Første tanke\nLad mig se hvor værnet sidder'} live={false} seconds={9} />)
    expect(screen.queryByTestId('tanke-meta')).toBeNull()
    expect(screen.getByText('Tænkte i 9 s')).toBeInTheDocument()
  })
})

describe('kald der pulserede efter han var videre', () => {
  const kald = (id: string, status?: 'running' | 'done' | 'error'): ContentBlock =>
    ({ type: 'tool_use', id, name: 'bash', input: {}, status })

  it('gemt besked: intet kører', () => {
    const ud = afslutForladteKald([kald('a', 'running')], false)
    expect(ud[0]).toMatchObject({ status: 'done' })
    // Men den er IKKE vist som lykkedes: udfaldet er ukendt (18/9-2026).
    expect(ud[0]).toMatchObject({ anomali: 'uden-resultat' })
  })

  it('live kan resultatet stadig være på vej — ingen anomali mens der streames', () => {
    const ud = afslutForladteKald([kald('a', 'running'), { type: 'text', text: 'Så…' }], true)
    expect((ud[0] as any).anomali).toBeUndefined()
  })

  it('live: tekst efter kaldet betyder at det er slut', () => {
    const ud = afslutForladteKald([kald('a', 'running'), { type: 'text', text: 'Så…' }], true)
    expect(ud[0]).toMatchObject({ status: 'done' })
  })

  it('live: et parallelt kald efter det lukker det IKKE', () => {
    const ud = afslutForladteKald([kald('a', 'running'), kald('b', 'done')], true)
    expect(ud[0]).toMatchObject({ status: 'running' })
  })

  it('ukendte udfald er færdige, fejl-lignende er fejl', () => {
    expect(udfaldsStatus('blocked')).toBe('error')
    expect(udfaldsStatus('timeout')).toBe('error')
    expect(udfaldsStatus('skipped')).toBe('done')
    expect(udfaldsStatus('running')).toBe('running')
  })

  it('message_stop afslutter kald hvis resultat aldrig kom', () => {
    const s = reduce([
      { type: 'content_block_start', index: 0, content_block: { type: 'tool_use', id: 't', name: 'bash', input: {} } } as StreamEvent,
      { type: 'message_stop' } as StreamEvent,
    ])
    expect(s.blocks[0]).toMatchObject({ status: 'done' })
  })
})

describe('live metadata i stedet for «Kører bash…»', () => {
  it('kommandoen læses mens argumenterne strømmer ind', () => {
    const partial = '{"command": "cd /tmp/ocp && cat > fwd.py <<\'PY\'\\nimport json'
    // Ikke de foerste tegn af kommandoen: mappeskiftet foran siger intet, og
    // det var det der stod paa linjen hele koerslen igennem (17/9-2026).
    expect(describeTool('bash', {}, true, partial)).toBe('Kører cat fwd.py…')
  })

  it('færdige argumenter vinder stadig', () => {
    expect(summarizeRound([{ type: 'tool_use', id: 'x', name: 'read_file', input: { path: '/a/b/agent.ts' }, status: 'done' }]))
      .toBe('Læste agent.ts')
  })

  it('runde-linjen viser hvor længe den har kørt', () => {
    vi.useFakeTimers()
    vi.setSystemTime(5_000_000)
    const startet = Date.now()
    vi.setSystemTime(5_012_000)
    render(<ToolGroupCard density="compact" block={{ type: 'tool_group', kind: 'round', count: 1,
      tools: [{ type: 'tool_use', id: 't', name: 'bash', input: { command: 'npm test' }, status: 'running', startet }] }} />)
    expect(screen.getByTestId('runde-tid')).toHaveTextContent('12 s')
    act(() => { vi.advanceTimersByTime(3000) })
    expect(screen.getByTestId('runde-tid')).toHaveTextContent('15 s')
  })
})


describe('prikker i enden af en linje der kører', () => {
  const blok = (status: 'running' | 'done') => ({
    type: 'tool_group' as const, kind: 'round' as const, count: 1,
    tools: [{ type: 'tool_use' as const, id: 't', name: 'bash', input: { command: 'npm test' }, status }],
  })

  it('runde-linjen: prikkerne er tre rullende spans — og de forsvinder når kaldet er færdigt', () => {
    // Foer var prikkerne TEKST («.» -> «..» -> «...») drevet af et interval i
    // JS. Nu er de tre spans med CSS-bevægelse: teksten staar stille, og React
    // roerer sig ikke mens de ruller.
    const { container, rerender } = render(<ToolGroupCard density="compact" block={blok('running')} />)
    expect(container.querySelector('.linje-titel')!.textContent).toBe('Kører npm test')
    expect(container.querySelectorAll('.prikker > span')).toHaveLength(3)
    rerender(<ToolGroupCard density="compact" block={blok('done')} />)
    expect(container.querySelector('.prikker')).toBeNull()
    expect(container.querySelector('.linje-titel')!.textContent).toBe('Kørte npm test')
  })

  it('tanke-linjen: prikker mens den tænker, ingen når den er færdig', () => {
    const { container, rerender } = render(<ThinkingLine text="x" live />)
    expect(container.querySelectorAll('.prikker > span')).toHaveLength(3)
    rerender(<ThinkingLine text="x" live={false} seconds={9} />)
    expect(container.querySelector('.prikker')).toBeNull()
  })

  it('klokken venter mens linjen kører — men en færdig runde viser sit målte tal', () => {
    // Claude Desktop viser først klokken efter 5 s, saa et kort kald ikke naar
    // at flimre «0 s» -> «1 s». Desk goer det samme mens runden KOERER; er den
    // faerdig, er tallet information man vil have, og det vises med det samme.
    vi.useFakeTimers()
    const startet = Date.now() - 3_000
    const med = (status: 'running' | 'done') => ({
      type: 'tool_group' as const, kind: 'round' as const, count: 1,
      tools: [{ type: 'tool_use' as const, id: 't', name: 'bash', input: { command: 'npm test' }, status, startet }],
    })
    const { rerender } = render(<ToolGroupCard density="compact" block={med('running')} />)
    expect(screen.queryByTestId('runde-tid')).toBeNull()
    rerender(<ToolGroupCard density="compact" block={med('done')} />)
    expect(screen.getByTestId('runde-tid')).toHaveTextContent('3 s')
  })

  it('en runde man aldrig har aabnet baerer intet i DOM\'en', () => {
    // Folden animerer hoejden, men indholdet bliver foerst monteret naar runden
    // aabnes - og fjernet igen naar folden har lukket. En lang traad skal ikke
    // baere hvert eneste uaabnede tool-kort.
    const { container } = render(<ToolGroupCard density="compact" block={blok('done')} />)
    expect(container.querySelector('.linje-fold-indre')!.childElementCount).toBe(0)
  })
})
