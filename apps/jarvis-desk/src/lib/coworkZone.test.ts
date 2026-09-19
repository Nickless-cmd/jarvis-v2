import { describe, it, expect } from 'vitest'
import { COWORK_ZONES, emitZone, normalizeZone, onZone } from './coworkZone'

describe('coworkZone', () => {
  it('viser samlede destinationer uden enkeltsider for indstillinger', () => {
    expect(COWORK_ZONES.map((z) => z.id)).toEqual([
      'mc', 'agentPool', 'capacity', 'integrations',
      'general', 'account', 'workspace', 'jarvis', 'system', 'about',
    ])
    expect(COWORK_ZONES.filter((z) => z.group === 'Indstillinger')).toHaveLength(4)
  })

  it('bevarer gamle zonekald ved at sende dem til den relevante kategori', () => {
    expect(normalizeZone('marketplace')).toBe('integrations')
    expect(normalizeZone('providers')).toBe('capacity')
    expect(normalizeZone('location')).toBe('general')
    expect(normalizeZone('notifications')).toBe('general')
    expect(normalizeZone('privacy')).toBe('account')
    expect(normalizeZone('memory')).toBe('jarvis')
    expect(normalizeZone('central')).toBe('system')
    expect(normalizeZone('settings')).toBe('account')
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
