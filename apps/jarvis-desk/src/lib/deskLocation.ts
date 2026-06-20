// Desktop geolocation: opt-in lokation til presence. IP (by-niveau), manuel
// adresse (geocodet via main → gemt lokalt), eller browser Geolocation API.
// Nominatim/ip-api kaldes via jarvisDesk.geo-broen (main sætter User-Agent).

export type LocationMode = 'off' | 'ip' | 'manual' | 'browser'

export interface DeskLocationPayload {
  lat: number
  lon: number
  label: string
  source: 'ip' | 'manual' | 'browser'
  precision: 'city' | 'precise'
}

const MODE_KEY = 'jarvis-desk:loc-mode'
const MANUAL_KEY = 'jarvis-desk:loc-manual'

export function parseMode(raw: string | null): LocationMode {
  return raw === 'ip' || raw === 'manual' || raw === 'browser' ? raw : 'off'
}

export function loadMode(): LocationMode {
  try { return parseMode(localStorage.getItem(MODE_KEY)) } catch { return 'off' }
}
export function saveMode(m: LocationMode): void {
  try { localStorage.setItem(MODE_KEY, m) } catch { /* noop */ }
}

export function loadManual(): { lat: number; lon: number; label: string } | null {
  try {
    const raw = localStorage.getItem(MANUAL_KEY)
    if (!raw) return null
    const v = JSON.parse(raw) as { lat?: number; lon?: number; label?: string }
    if (typeof v.lat === 'number' && typeof v.lon === 'number') {
      return { lat: v.lat, lon: v.lon, label: v.label ?? '' }
    }
    return null
  } catch { return null }
}
export function saveManual(v: { lat: number; lon: number; label: string }): void {
  try { localStorage.setItem(MANUAL_KEY, JSON.stringify(v)) } catch { /* noop */ }
}

interface GeoBridge {
  geocode: (a: string) => Promise<{ lat: number; lon: number; label: string } | null>
  reverse: (lat: number, lon: number, precise: boolean) => Promise<string>
  ip: () => Promise<{ lat: number; lon: number; label: string } | null>
}
function geoBridge(): GeoBridge | undefined {
  return (window as unknown as { jarvisDesk?: { geo?: GeoBridge } }).jarvisDesk?.geo
}

/** Geocode en adresse via main-broen og gem den som manuel lokation. */
export async function geocodeAndSaveManual(address: string): Promise<{ lat: number; lon: number; label: string } | null> {
  const r = await geoBridge()?.geocode(address)
  if (r) saveManual(r)
  return r ?? null
}

function browserPosition(): Promise<GeolocationPosition | null> {
  return new Promise((resolve) => {
    if (typeof navigator === 'undefined' || !navigator.geolocation) { resolve(null); return }
    navigator.geolocation.getCurrentPosition(
      (pos) => resolve(pos),
      () => resolve(null),
      { enableHighAccuracy: false, maximumAge: 300000, timeout: 10000 },
    )
  })
}

/** Hent lokation efter valgt metode. null = ingen (off / fejl). */
export async function getDesktopLocation(mode: LocationMode): Promise<DeskLocationPayload | null> {
  if (mode === 'off') return null
  if (mode === 'ip') {
    const r = await geoBridge()?.ip()
    return r ? { ...r, source: 'ip', precision: 'city' } : null
  }
  if (mode === 'manual') {
    const m = loadManual()
    return m ? { ...m, source: 'manual', precision: 'precise' } : null
  }
  // browser
  const pos = await browserPosition()
  if (!pos) return null
  const { latitude, longitude } = pos.coords
  const label = (await geoBridge()?.reverse(latitude, longitude, true)) || ''
  return { lat: latitude, lon: longitude, label, source: 'browser', precision: 'precise' }
}
