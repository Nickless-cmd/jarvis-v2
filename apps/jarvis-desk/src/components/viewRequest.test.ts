import { describe, it, expect, vi } from 'vitest'
import { udfoer } from './ViewRequestWatcher'
import { registrerSkaerm, skaermFor, type Skaerm } from '../lib/skaermRegister'

/** Jarvis' desk-værktøjer — Claude Desktops ccd_view (19/9-2026). */
function skaerm(over: Partial<Skaerm> = {}): Skaerm {
  let aabne: string[] = []
  return {
    sessionId: 's1', flade: 'code',
    aabne: () => aabne,
    vis: vi.fn((p) => (p === 'artifact' ? 'Ikke et panel i desk.' : (aabne = [...aabne, p], null))),
    luk: vi.fn(() => null),
    ...over,
  }
}

describe('udfoer', () => {
  it('get_layout: hvor samtalen står og hvad der er åbent', () => {
    const s = skaerm({ aabne: () => ['diff'] })
    expect(udfoer({ id: 'v1', op: 'get_layout', args: {}, session_id: 's1' }, s))
      .toEqual({ views: [{ placement: 'primary', surface: 'code' }], open_panes: ['diff'] })
  })

  it('show_pane: panelet står i svaret med det samme — før React har tegnet', () => {
    const s = skaerm({ aabne: () => [] })
    const ud = udfoer({ id: 'v2', op: 'show_pane', args: { pane: 'diff', path: 'core/login.py' }, session_id: 's1' }, s)
    expect(s.vis).toHaveBeenCalledWith('diff', { path: 'core/login.py', line: undefined })
    expect(ud.open_panes).toEqual(['diff'])
  })

  it('en fejl siger HVAD der mangler — som CC', () => {
    const ud = udfoer({ id: 'v3', op: 'show_pane', args: { pane: 'artifact' }, session_id: 's1' }, skaerm())
    expect(ud).toEqual({ error: 'Ikke et panel i desk.' })
  })

  it('close_pane: panelet er væk fra svaret', () => {
    const s = skaerm({ aabne: () => ['diff', 'tasks'] })
    expect(udfoer({ id: 'v4', op: 'close_pane', args: { pane: 'diff' }, session_id: 's1' }, s).open_panes).toEqual(['tasks'])
  })
})

describe('registret', () => {
  it('finder skærmen for samtalen — og glemmer den ved afmontering', () => {
    const af = registrerSkaerm(skaerm({ sessionId: 's7' }))
    expect(skaermFor('s7')?.sessionId).toBe('s7')
    expect(skaermFor('andre')).toBeUndefined()
    af()
    expect(skaermFor('s7')).toBeUndefined()
  })
})
