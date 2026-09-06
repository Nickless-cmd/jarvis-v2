import { describe, expect, it } from 'vitest'
import { PALETTE_HANDLINGER, filtrerHandlinger } from './paletteActions'

describe('command palette', () => {
  it('finder på dansk OG engelsk — man skriver begge dele', () => {
    expect(filtrerHandlinger('kø', true).map((h) => h.id)).toContain('zone:mc')
    expect(filtrerHandlinger('queue', true).map((h) => h.id)).toContain('zone:mc')
  })

  it('finder på hvad man leder efter, ikke kun på navnet', () => {
    // «operator» står ikke i navnet «Arbejdsbænk» — men det er dét man søger.
    expect(filtrerHandlinger('operator', true).map((h) => h.id)).toContain('zone:workspace')
  })

  it('skjuler owner-destinationer for andre', () => {
    const ejer = filtrerHandlinger('', true).map((h) => h.id)
    const gaest = filtrerHandlinger('', false).map((h) => h.id)
    expect(ejer).toContain('zone:workspace')
    expect(gaest).not.toContain('zone:workspace')
  })

  it('tom søgning viser alt der er tilladt', () => {
    expect(filtrerHandlinger('', true)).toHaveLength(PALETTE_HANDLINGER.length)
  })

  it('intet match giver tom liste frem for alt', () => {
    expect(filtrerHandlinger('zzzz-findes-ikke', true)).toHaveLength(0)
  })
})
