import { describe, it, expect } from 'vitest'
import { erBaggrund, erKodeSamtale, grupperAf, grupperSessioner, GRUPPE_ORDEN, GRUPPER_I_MODE, grupperEfterProjekt, projektNavn } from './sessionGroups'

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
    expect(GRUPPE_ORDEN).toEqual(['chat', 'kode', 'baggrund', 'arkiv'])
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

// ── Arten kommer fra `kind`, ikke fra arbejdstræet (29/9-2026) ──────────────
//
// Kriteriet var `workspace_kind` sat. Men det felt er ARBEJDSTRÆETS art
// ('workstation', 'code'), ikke samtalens tilstand. Målt på CT105, 550
// samtaler:
//
//     kode-samtaler UDEN workspace_kind  ->  10 af 26   vist som chat
//     chat-samtaler MED workspace_kind   ->  19         vist som kode
//
// 29 samtaler i den forkerte liste, og fejlen gik BEGGE veje. Bjørn: «den
// session ham og jeg lige har skrevet i er oprettet som kode mode session men
// vises i session listen i chat mode… og når det sker ryger broen».

describe('arten afgøres af kind', () => {
  it('en kode-samtale UDEN workspace_kind hører i kode — det var hans sag', () => {
    expect(erKodeSamtale({ id: 'chat-1', kind: 'code', workspace_kind: null })).toBe(true)
    expect(grupperAf({ id: 'chat-1', kind: 'code', workspace_kind: null })).toBe('kode')
  })

  it('en chat-samtale MED workspace_kind hører i chat — den modsatte fejl', () => {
    expect(erKodeSamtale({ id: 'chat-2', kind: 'chat', workspace_kind: 'workstation' })).toBe(false)
    expect(grupperAf({ id: 'chat-2', kind: 'chat', workspace_kind: 'workstation' })).toBe('chat')
  })

  it('kind vinder ALTID over workspace_kind, begge veje', () => {
    expect(erKodeSamtale({ id: 'a', kind: 'code', workspace_kind: 'workstation' })).toBe(true)
    expect(erKodeSamtale({ id: 'b', kind: 'chat', workspace_kind: 'code' })).toBe(false)
  })

  it('uden kind falder den tilbage på workspace_kind — rækker fra før kolonnen', () => {
    expect(erKodeSamtale({ id: 'gammel-1', workspace_kind: 'code' })).toBe(true)
    expect(erKodeSamtale({ id: 'gammel-2', workspace_kind: null })).toBe(false)
    expect(erKodeSamtale({ id: 'gammel-3', kind: '', workspace_kind: 'workstation' })).toBe(true)
  })

  it('store og små bogstaver og mellemrum tæller ikke', () => {
    expect(erKodeSamtale({ id: 'a', kind: ' CODE ' })).toBe(true)
    expect(erKodeSamtale({ id: 'b', kind: 'Chat' })).toBe(false)
  })

  it('baggrunds-kørsler er stadig baggrund, uanset kind', () => {
    expect(grupperAf({ id: 'auto-dream-20260929', kind: 'code' })).toBe('baggrund')
    expect(grupperAf({ id: 'proactivity-bridge', kind: 'code' })).toBe('baggrund')
  })

  it('de to lister deler ingen samtale', () => {
    const sessioner = [
      { id: 'chat-a', kind: 'code', workspace_kind: null },
      { id: 'chat-b', kind: 'chat', workspace_kind: 'workstation' },
      { id: 'auto-recurring-1', kind: 'chat' },
    ]
    const grupper = grupperSessioner(sessioner)
    const iMode = (m: 'chat' | 'code') =>
      grupper.filter((g) => GRUPPER_I_MODE[m].includes(g.gruppe))
        .flatMap((g) => g.sessioner.map((s) => s.id))
    const iChat = iMode('chat')
    const iKode = iMode('code')
    expect(iKode).toEqual(['chat-a'])
    expect(iChat.sort()).toEqual(['auto-recurring-1', 'chat-b'])
    expect(iChat.filter((id) => iKode.includes(id))).toEqual([])
  })
})

// ── Arkiverede samtaler (29/9-2026) ────────────────────────────────────────
//
// Desk tilbød «Arkivér», men listen hentede kun ikke-arkiverede (serveren
// skjuler dem som standard), og panelet havde ingen anden kilde. Samtalen blev
// derfor usynlig — ikke arkiveret. Nu henter panelet dem med
// (`inkluder_arkiverede=1`) og giver dem deres egen gruppe nederst, med
// «Gendan» i menuen.

describe('arkiverede samtaler', () => {
  it('får deres egen gruppe — også når de er kode-samtaler', () => {
    expect(grupperAf({ id: 'chat-1', kind: 'code', archived: 1 })).toBe('arkiv')
    expect(grupperAf({ id: 'chat-2', kind: 'chat', archived: 1 })).toBe('arkiv')
  })

  it('arkiverede autonome står i arkiv, ikke blandt de kørsler der stadig lever', () => {
    expect(grupperAf({ id: 'auto-dream-1', archived: 1 })).toBe('arkiv')
    expect(grupperAf({ id: 'auto-dream-2' })).toBe('baggrund')
  })

  it('gruppen står NEDERST — efter det han selv har skrevet', () => {
    expect(GRUPPE_ORDEN[GRUPPE_ORDEN.length - 1]).toBe('arkiv')
  })

  it('vises i BEGGE modes — en arkiveret kode-samtale skal kunne findes igen', () => {
    expect(GRUPPER_I_MODE.chat).toContain('arkiv')
    expect(GRUPPER_I_MODE.code).toContain('arkiv')
  })

  it('archived: 0 og null er ikke arkiveret', () => {
    expect(grupperAf({ id: 'chat-3', archived: 0 })).toBe('chat')
    expect(grupperAf({ id: 'chat-4', archived: null })).toBe('chat')
    expect(grupperAf({ id: 'chat-5' })).toBe('chat')
  })
})
