import { describe, it, expect } from 'vitest'
import { COWORK_ZONES, emitZone, onZone } from './coworkZone'

describe('coworkZone', () => {
  it('har marketplace-zone i COWORK_ZONES', () => {
    expect(COWORK_ZONES.map((z) => z.id)).toContain('marketplace')
  })

  it('hver zone har label + icon', () => {
    for (const z of COWORK_ZONES) {
      expect(z.label.length).toBeGreaterThan(0)
      expect(z.icon.length).toBeGreaterThan(0)
    }
  })

  it('emitZone når en lytter', () => {
    let seen = ''
    const off = onZone((z) => { seen = z })
    emitZone('marketplace')
    expect(seen).toBe('marketplace')
    off()
  })
})
