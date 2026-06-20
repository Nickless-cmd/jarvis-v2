import * as Location from 'expo-location'
import * as SecureStore from 'expo-secure-store'

/** Brugerens lokationsdeling-valg. 'off' = default (ingen deling). */
export type LocationPrecision = 'off' | 'city' | 'precise'

const PRECISION_KEY = 'jarvis.mobile.locationPrecision'

export function parsePrecision(raw: string | null): LocationPrecision {
  return raw === 'city' || raw === 'precise' ? raw : 'off'
}

export async function loadPrecision(): Promise<LocationPrecision> {
  try {
    return parsePrecision(await SecureStore.getItemAsync(PRECISION_KEY))
  } catch {
    return 'off'
  }
}

export async function savePrecision(p: LocationPrecision): Promise<void> {
  try {
    await SecureStore.setItemAsync(PRECISION_KEY, p)
  } catch {
    /* best-effort */
  }
}

export interface LocationPayload {
  lat: number
  lon: number
  label: string
  source: 'gps' | 'wifi' | 'ip'
  precision: 'precise' | 'city'
}

const NOMINATIM = 'https://nominatim.openstreetmap.org'
const UA = 'Jarvis-Mobile-Companion/1.0'

/** Reverse-geocode coords → kort label "Vej, By" via Nominatim (gratis). */
export async function reverseLabel(lat: number, lon: number, precise: boolean): Promise<string> {
  try {
    const url = `${NOMINATIM}/reverse?format=json&lat=${lat}&lon=${lon}&addressdetails=1&zoom=${precise ? 18 : 12}`
    const res = await fetch(url, { headers: { 'User-Agent': UA } })
    const data = (await res.json()) as { address?: Record<string, string> }
    return labelFromAddress(data.address ?? {}, precise)
  } catch {
    return ''
  }
}

/** Pure: byg et kort label fra en Nominatim-adresse. Precise → vej+by; ellers by. */
export function labelFromAddress(a: Record<string, string>, precise: boolean): string {
  const city = a.city || a.town || a.village || a.municipality || a.county || ''
  if (precise) {
    const road = a.road || a.suburb || ''
    return [road, city].filter(Boolean).join(', ')
  }
  return city
}

/** IP-baseret by-niveau fallback (gratis, ingen nøgle). */
export async function ipLocation(): Promise<LocationPayload | null> {
  try {
    const res = await fetch('http://ip-api.com/json/?fields=status,city,regionName,lat,lon')
    const d = (await res.json()) as {
      status?: string; city?: string; regionName?: string; lat?: number; lon?: number
    }
    if (d.status !== 'success' || d.lat == null || d.lon == null) return null
    const label = [d.city, d.regionName].filter(Boolean).join(', ')
    return { lat: d.lat, lon: d.lon, label, source: 'ip', precision: 'city' }
  } catch {
    return null
  }
}

/**
 * Hent brugerens lokation efter valgt præcision.
 * - 'off'   → null (kalderen sender {} for at rydde server-side)
 * - 'precise' → GPS (Balanced) → reverse-geocode gade. Falder tilbage til IP.
 * - 'city'  → IP-baseret by-niveau (ingen GPS-opkald → batterivenligt).
 * Best-effort: returnerer null ved manglende tilladelse/fejl.
 */
export async function getDeviceLocation(precision: LocationPrecision): Promise<LocationPayload | null> {
  if (precision === 'off') return null
  if (precision === 'city') return ipLocation()
  // precise → GPS. KRITISK: getCurrentPositionAsync kan hænge i det uendelige
  // indendørs/uden fix → vi MÅ tids-begrænse den (race mod 8s) så den aldrig
  // blokerer kalderen. Ved timeout/fejl → IP-fallback.
  try {
    const perm = await Location.requestForegroundPermissionsAsync()
    if (perm.status !== 'granted') return ipLocation()
    const pos = await Promise.race([
      Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced }),
      new Promise<null>((resolve) => setTimeout(() => resolve(null), 8000)),
    ])
    if (!pos) return ipLocation()
    const { latitude, longitude } = pos.coords
    const label = await reverseLabel(latitude, longitude, true)
    return { lat: latitude, lon: longitude, label, source: 'gps', precision: 'precise' }
  } catch {
    return ipLocation()
  }
}
