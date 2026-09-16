import { describe, it, expect } from 'vitest'
import { erBaggrund, grupperAf, grupperSessioner, GRUPPE_ORDEN, grupperEfterProjekt, projektNavn } from './sessionGroups'

// Præfikserne er runtime'ens egne, målt 8/9-2026:
//   chat-*  278 · auto-dream-* 65 · auto-recurring-* 57 · auto-heartbeat-* 46
//   auto-wakeup-* 11 · auto-work-* 1 · auto-autonomous-* 1 · proactivity-bridge 1
describe('hvilken gruppe hører sessionen til', () => {
  it('kender alle de autonome præfikser der findes i runtime', () => {
    for (const id of ['auto-dream-20260908', 'auto-recurring-20260908',
      'auto-heartbeat-20260908', 'auto-wakeup-20260904', 'auto-work-1',
      'auto-autonomous-0']) {
      expect(erBaggrund(id)).toBe(true)
    }
  })

  it('den proaktive kanal er også baggrund', () => {
    expect(erBaggrund('proactivity-bridge')).toBe(true)
  })

  it('en almindelig samtale er ikke baggrund', () => {
    expect(erBaggrund('chat-bb197cb78f454c3c99181a6f6ef83d26')).toBe(false)
  })

  it('workspace_kind afgør kode — samme kriterium som sidebaren allerede åbner på', () => {
    expect(grupperAf({ id: 'chat-1', workspace_kind: 'code' })).toBe('kode')
    expect(grupperAf({ id: 'chat-2', workspace_kind: 'workstation' })).toBe('kode')
    expect(grupperAf({ id: 'chat-3', workspace_kind: null })).toBe('chat')
    expect(grupperAf({ id: 'chat-4' })).toBe('chat')
  })

  it('en autonom kørsel er baggrund selv med workspace_kind', () => {
    expect(grupperAf({ id: 'auto-work-1', workspace_kind: 'code' })).toBe('baggrund')
  })
})

describe('inddelingen', () => {
  const liste = [
    { id: 'chat-a', workspace_kind: null },
    { id: 'auto-dream-1' },
    { id: 'chat-b', workspace_kind: 'code' },
    { id: 'chat-c', workspace_kind: null },
    { id: 'proactivity-bridge' },
  ]

  it('deler i tre og beholder rækkefølgen inden for hver gruppe', () => {
    const g = grupperSessioner(liste)
    expect(g.map((x) => x.gruppe)).toEqual(['chat', 'kode', 'baggrund'])
    // serveren sorterer på updated_at — en omsortering her ville betyde at
    // "øverst" holdt op med at betyde "senest"
    expect(g[0]?.sessioner.map((s) => s.id)).toEqual(['chat-a', 'chat-c'])
    expect(g[2]?.sessioner.map((s) => s.id)).toEqual(['auto-dream-1', 'proactivity-bridge'])
  })

  it('tomme grupper vises ikke', () => {
    const g = grupperSessioner([{ id: 'chat-a', workspace_kind: null }])
    expect(g).toHaveLength(1)
    expect(g[0]?.gruppe).toBe('chat')
  })

  it('en tom liste giver ingen grupper', () => {
    expect(grupperSessioner([])).toEqual([])
  })

  it('rækkefølgen er fast: det han selv har skrevet står øverst', () => {
    expect(GRUPPE_ORDEN).toEqual(['chat', 'kode', 'baggrund'])
  })
})

describe('projekt-gruppering', () => {
  const s = (id: string, rod?: string) => ({ id, workspace_kind: 'workstation', workspace_root: rod })

  it('deler sessionerne op efter projekt', () => {
    const g = grupperEfterProjekt([
      s('a', '/media/projects/jarvis-v2'),
      s('b', '/home/bs/andet'),
      s('c', '/media/projects/jarvis-v2'),
    ])
    expect(g.map((x) => x.navn)).toEqual(['jarvis-v2', 'andet'])
    expect(g[0]!.sessioner.map((x) => x.id)).toEqual(['a', 'c'])
  })

  it('navn og sti skilles ad — som i CC', () => {
    expect(projektNavn('/media/projects/jarvis-v2')).toEqual({ navn: 'jarvis-v2', sti: '/media/projects' })
  })

  it('Windows-stier deles på deres eget skilletegn', () => {
    // «C:\Jarvis» findes i hans egne data. En deling der kun kender «/»
    // ville give hele strengen som navn.
    expect(projektNavn('C:\\Jarvis')).toEqual({ navn: 'Jarvis', sti: 'C:' })
  })

  it('en afsluttende skråstreg ændrer ikke navnet', () => {
    expect(projektNavn('/media/projects/jarvis-v2/').navn).toBe('jarvis-v2')
  })

  it('sessioner UDEN projekt havner sidst, ikke øverst', () => {
    const g = grupperEfterProjekt([s('uden'), s('med', '/x/repo')])
    expect(g.map((x) => x.navn)).toEqual(['repo', 'Uden projekt'])
  })

  it('rækkefølgen inden for en gruppe røres ikke', () => {
    // Serveren sorterer på updated_at. En sortering her ville betyde at
    // «øverst» holdt op med at betyde «senest».
    const g = grupperEfterProjekt([s('nyest', '/x'), s('aeldre', '/x')])
    expect(g[0]!.sessioner.map((x) => x.id)).toEqual(['nyest', 'aeldre'])
  })
})
