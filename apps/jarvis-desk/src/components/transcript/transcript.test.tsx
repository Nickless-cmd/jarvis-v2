import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, renderHook, act, fireEvent } from '@testing-library/react'
import { useRef } from 'react'
import { useSendeKoe } from '../../hooks/useSendeKoe'
import { useNyeBeskeder } from '../../hooks/useNyeBeskeder'
import { JumpToLatest } from './JumpToLatest'
import { KoeChip } from './KoeChip'
import { StickyPrompt } from './StickyPrompt'
import type { ChatMessage } from '../../lib/api'

const opts = {} as never

describe('køen (§14 punkt 8)', () => {
  it('under et svar lægges beskeden i kø og sendes bagefter', () => {
    const send = vi.fn()
    const { result, rerender } = renderHook((p: { arbejder: boolean }) => useSendeKoe({ arbejder: p.arbejder, online: true, send }), { initialProps: { arbejder: true } })
    act(() => result.current.sendEllerKoe('hej', opts))
    expect(send).not.toHaveBeenCalled()
    expect(result.current.items[0]?.text).toBe('hej')
    rerender({ arbejder: false })
    expect(send).toHaveBeenCalledWith('hej', opts)
  })

  it('at fjerne den fra køen afbryder IKKE turen — og sender den ikke', () => {
    const send = vi.fn()
    const { result, rerender } = renderHook((p: { arbejder: boolean }) => useSendeKoe({ arbejder: p.arbejder, online: true, send }), { initialProps: { arbejder: true } })
    act(() => result.current.sendEllerKoe('hej', opts))
    act(() => result.current.fjern(result.current.items[0]!.id))
    rerender({ arbejder: false })
    expect(send).not.toHaveBeenCalled()
  })

  // 3/10-2026 (Bjørn): «que beskeder mangler styr funktion lige som i mobilen
  // … så det findes allerede». Køen er nu en LISTE med rediger / flyt / send
  // nu / fjern — og ingen af dem må afbryde turen der kører.
  it('redigerer teksten uden at sende den', () => {
    const send = vi.fn()
    const { result } = renderHook(() => useSendeKoe({ arbejder: true, online: true, send }))
    act(() => result.current.sendEllerKoe('foerste', opts))
    act(() => result.current.rediger(result.current.items[0]!.id, 'aendret'))
    expect(result.current.items[0]?.text).toBe('aendret')
    expect(send).not.toHaveBeenCalled()
  })

  it('flytter beskeden i køen', () => {
    const send = vi.fn()
    const { result } = renderHook(() => useSendeKoe({ arbejder: true, online: true, send }))
    act(() => result.current.sendEllerKoe('a', opts))
    act(() => result.current.sendEllerKoe('b', opts))
    const [a, b] = result.current.items.map((i) => i.id)
    act(() => result.current.flyt(b!, -1))
    expect(result.current.items.map((i) => i.text)).toEqual(['b', 'a'])
    act(() => result.current.flyt(a!, 1))
    expect(result.current.items.map((i) => i.text)).toEqual(['b', 'a'])
  })

  it('«send nu» midt i et run bruger steer — ikke en ny kørsel', async () => {
    const send = vi.fn()
    const steer = vi.fn().mockResolvedValue(undefined)
    const { result } = renderHook(() => useSendeKoe({ arbejder: true, online: true, send, steer, kanSteer: true }))
    act(() => result.current.sendEllerKoe('midt i', opts))
    await act(async () => { await result.current.sendNu(result.current.items[0]!.id) })
    expect(steer).toHaveBeenCalledWith('midt i')
    expect(send).not.toHaveBeenCalled()
    expect(result.current.items).toHaveLength(0)
  })

  it('chippen viser handlingerne og kalder dem', () => {
    const send = vi.fn()
    const { result } = renderHook(() => useSendeKoe({ arbejder: true, online: true, send }))
    act(() => result.current.sendEllerKoe('hej', opts))
    const onRediger = vi.fn(); const onFjern = vi.fn(); const onFlyt = vi.fn(); const onSendNu = vi.fn()
    const chip = render(<KoeChip items={result.current.items} busy kanSteer online
      onRediger={onRediger} onFjern={onFjern} onFlyt={onFlyt} onSendNu={onSendNu} />)
    act(() => { fireEvent.click(chip.getByRole('button', { name: 'Fjern fra kø' })) })
    expect(onFjern).toHaveBeenCalled()
    act(() => { fireEvent.click(chip.getByRole('button', { name: 'Send nu til det kørende run' })) })
    expect(onSendNu).toHaveBeenCalled()
  })
})

describe('hop til nyeste (§14 punkt 3)', () => {
  it('i bund: i DOM\'en men inert og skjult', () => {
    const { getByTestId } = render(<JumpToLatest synlig={false} live={false} ulaeste={0} onClick={() => {}} />)
    const b = getByTestId('jump-to-latest')
    expect(b.hasAttribute('inert')).toBe(true)
    expect(b.className).not.toMatch(/er-synlig/)
  })
  it('scrollet op mens svaret strømmer: synlig med accent', () => {
    const { getByTestId } = render(<JumpToLatest synlig live ulaeste={2} onClick={() => {}} />)
    const b = getByTestId('jump-to-latest')
    expect(b.hasAttribute('inert')).toBe(false)
    expect(b.className).toMatch(/er-synlig/)
    expect(b.className).toMatch(/er-live/)
    expect(b).toHaveTextContent('2 nye')
  })
})

describe('«Nye beskeder» (§14 punkt 4)', () => {
  beforeEach(() => localStorage.clear())
  it('åbner man en samtale med nyt siden sidst, står linjen over det første nye', () => {
    localStorage.setItem('jarvis-desk:sidst-set', JSON.stringify({ s1: 'b' }))
    const { result } = renderHook(() => useNyeBeskeder('s1', ['a', 'b', 'c', 'd'], false))
    expect(result.current).toBe('c')
  })
  it('intet nyt → ingen linje; og man huskes som «set» når man er i bund', () => {
    const { result } = renderHook(() => useNyeBeskeder('s1', ['a', 'b'], true))
    expect(result.current).toBeNull()
    expect(JSON.parse(localStorage.getItem('jarvis-desk:sidst-set')!).s1).toBe('b')
  })
  it('lander der nyt mens man er scrollet op, markeres det første', () => {
    const { result, rerender } = renderHook((p: { ids: string[] }) => useNyeBeskeder('s1', p.ids, false), { initialProps: { ids: ['a', 'b'] } })
    rerender({ ids: ['a', 'b', 'c', 'd'] })
    expect(result.current).toBe('c')
  })
  it('en optimistisk besked (u-…) huskes ikke som set', () => {
    renderHook(() => useNyeBeskeder('s1', ['a', 'u-123'], true))
    expect(JSON.parse(localStorage.getItem('jarvis-desk:sidst-set')!).s1).toBe('a')
  })
})

describe('sticky prompt (§14 punkt 2)', () => {
  const msg = (id: string, role: 'user' | 'assistant', text: string) =>
    ({ id, role, content: [{ type: 'text', text }], created_at: '' }) as ChatMessage

  function Harness({ beskeder, bunde }: { beskeder: ChatMessage[]; bunde: Record<string, number> }) {
    const ref = useRef<HTMLDivElement>(null)
    return (
      <div>
        <StickyPrompt containerRef={ref} beskeder={beskeder} />
        <div ref={ref} data-testid="c">
          {beskeder.map((m) => <div key={m.id} data-rail-id={m.id} ref={(n) => {
            if (n) n.getBoundingClientRect = () => ({ top: bunde[m.id]! - 20, bottom: bunde[m.id]! } as DOMRect)
          }}>{m.id}</div>)}
        </div>
      </div>
    )
  }

  it('din seneste besked over toppen står fast — klik ruller til den', () => {
    const beskeder = [msg('u1', 'user', 'Første spørgsmål'), msg('a1', 'assistant', 'svar'), msg('u2', 'user', 'Hvor sidder værnet?'), msg('a2', 'assistant', 'langt svar')]
    // Containeren står ved top=0; u1 og u2 er rullet over toppen, a2 fylder skærmen.
    const r = render(<Harness beskeder={beskeder} bunde={{ u1: -500, a1: -300, u2: -100, a2: 600 }} />)
    const knap = r.getByTestId('sticky-prompt')
    expect(knap).toHaveAccessibleName('Rul til din besked: Hvor sidder værnet?')
    // Et ikon i headeren — ikke en tekst-strimmel over samtalen.
    expect(knap).not.toHaveTextContent('Hvor sidder værnet?')
    const node = r.container.querySelector('[data-rail-id="u2"]') as HTMLElement
    node.scrollIntoView = vi.fn()
    fireEvent.click(knap)
    expect(node.scrollIntoView).toHaveBeenCalledWith({ behavior: 'smooth', block: 'start' })
  })

  it('er din besked synlig, står intet fast', () => {
    const beskeder = [msg('u1', 'user', 'Hej'), msg('a1', 'assistant', 'svar')]
    const r = render(<Harness beskeder={beskeder} bunde={{ u1: 60, a1: 400 }} />)
    expect(r.queryByTestId('sticky-prompt')).toBeNull()
  })
})
