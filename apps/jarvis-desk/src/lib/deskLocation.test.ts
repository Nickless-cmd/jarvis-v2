import { describe, it, expect, beforeEach } from 'vitest'
import { parseMode, loadMode, saveMode, loadManual, saveManual, getDesktopLocation } from './deskLocation'
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

describe('browser-lokation må ikke melde et gæt som «precise»', () => {
  const stubGeo = (reverse: () => Promise<string>) => {
    ;(window as unknown as { jarvisDesk?: unknown }).jarvisDesk = { geo: { reverse } }
  }
  const stubBrowser = (coords: { latitude: number; longitude: number; accuracy: number }) => {
    Object.defineProperty(navigator, 'geolocation', {
      configurable: true,
      value: { getCurrentPosition: (ok: (p: unknown) => void) => ok({ coords }) },
    })
  }

  it('kasserer Electrons hardkodede standard-position', async () => {
    // Uden GOOGLE_API_KEY svarer Electron 38.883333, -77.0 (Arlington, VA).
    // Målt 18/10-2026: desk meldte den som «precise», 6.500 km fra Svendborg.
    stubBrowser({ latitude: 38.883333, longitude: -77.0, accuracy: 100_000 })
    stubGeo(async () => 'Arlington, Virginia')
    expect(await getDesktopLocation('browser')).toBeNull()
  })

  it('kasserer et fix der ikke kan navngives', async () => {
    stubBrowser({ latitude: 55.06, longitude: 10.61, accuracy: 25 })
    stubGeo(async () => '')
    expect(await getDesktopLocation('browser')).toBeNull()
  })

  it('beholder et navngivet, præcist fix', async () => {
    stubBrowser({ latitude: 55.06, longitude: 10.61, accuracy: 25 })
    stubGeo(async () => 'Græsvej, Svendborg')
    expect(await getDesktopLocation('browser')).toMatchObject({
      lat: 55.06,
      lon: 10.61,
      label: 'Græsvej, Svendborg',
      source: 'browser',
      precision: 'precise',
    })
  })
})
