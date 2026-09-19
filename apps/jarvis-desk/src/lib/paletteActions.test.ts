import { describe, expect, it } from 'vitest'
import { PALETTE_HANDLINGER, filtrerHandlinger } from './paletteActions'

describe('command palette', () => {
  it('finder på dansk OG engelsk — man skriver begge dele', () => {
    expect(filtrerHandlinger('kø', true).map((h) => h.id)).toContain('zone:mc')
    expect(filtrerHandlinger('queue', true).map((h) => h.id)).toContain('zone:mc')
  })

  it('finder på hvad man leder efter, ikke kun på navnet', () => {
    // «operator» står ikke i navnet «Arbejdsområde» — men det er dét man søger.
    expect(filtrerHandlinger('operator', true).map((h) => h.id)).toContain('zone:workspace')
  })

  it('finder små indstillinger under deres nye samlede side', () => {
    expect(filtrerHandlinger('lokation', true).map((h) => h.id)).toContain('zone:general')
    expect(filtrerHandlinger('notifikationer', true).map((h) => h.id)).toContain('zone:general')
    expect(filtrerHandlinger('marketplace', true).map((h) => h.id)).toContain('zone:integrations')
    expect(filtrerHandlinger('privatliv', true).map((h) => h.id)).toContain('zone:account')
  })

  it('skjuler owner-destinationer for andre', () => {
    const ejer = filtrerHandlinger('', true).map((h) => h.id)
    const gaest = filtrerHandlinger('', false).map((h) => h.id)
    expect(ejer).toContain('zone:workspace')
    expect(gaest).toContain('zone:workspace')
    expect(gaest).not.toContain('zone:capacity')
    expect(gaest).not.toContain('zone:agentPool')
  })

  it('tom søgning viser alt der er tilladt', () => {
    expect(filtrerHandlinger('', true)).toHaveLength(PALETTE_HANDLINGER.length)
  })

  it('intet match giver tom liste frem for alt', () => {
    expect(filtrerHandlinger('zzzz-findes-ikke', true)).toHaveLength(0)
  })
})
