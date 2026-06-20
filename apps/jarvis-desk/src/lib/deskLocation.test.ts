import { describe, it, expect, beforeEach } from 'vitest'
import { parseMode, loadMode, saveMode, loadManual, saveManual } from './deskLocation'
import { buildPingBody } from './presence'

describe('deskLocation store', () => {
  beforeEach(() => localStorage.clear())

  it('parseMode defaults to off', () => {
    expect(parseMode(null)).toBe('off')
    expect(parseMode('nonsense')).toBe('off')
    expect(parseMode('ip')).toBe('ip')
    expect(parseMode('manual')).toBe('manual')
    expect(parseMode('browser')).toBe('browser')
  })

  it('persists mode', () => {
    saveMode('ip')
    expect(loadMode()).toBe('ip')
  })

  it('persists + reads manual coords', () => {
    saveManual({ lat: 55.86, lon: 10.39, label: 'Svendborg' })
    expect(loadManual()).toEqual({ lat: 55.86, lon: 10.39, label: 'Svendborg' })
  })

  it('returns null for missing/garbage manual', () => {
    expect(loadManual()).toBeNull()
    localStorage.setItem('jarvis-desk:loc-manual', 'not-json')
    expect(loadManual()).toBeNull()
  })
})

describe('buildPingBody location semantics', () => {
  it('omits location when undefined', () => {
    const b = buildPingBody({ deviceKey: 'd', foreground: true, awake: true, interaction: false })
    expect('location' in b).toBe(false)
  })
  it('includes {} to clear', () => {
    const b = buildPingBody({ deviceKey: 'd', foreground: true, awake: true, interaction: false, location: {} })
    expect(b.location).toEqual({})
  })
  it('includes payload', () => {
    const loc = { lat: 55.86, lon: 10.39, label: 'Svendborg', source: 'ip' as const, precision: 'city' as const }
    const b = buildPingBody({ deviceKey: 'd', foreground: true, awake: true, interaction: false, location: loc })
    expect(b.location).toEqual(loc)
  })
})
