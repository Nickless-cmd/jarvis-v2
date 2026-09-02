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
    // Nominatim lægger gade-navnet i forskellige felter afhængigt af vejtype.
    const road = a.road || a.pedestrian || a.footway || a.path || a.cycleway
      || a.neighbourhood || a.suburb || ''
    return [road, city].filter(Boolean).join(', ')
  }
  return city
}

/** IP-baseret by-niveau fallback. Bruger HTTPS (ipwho.is) — Android blokerer
 *  cleartext-HTTP (targetSdk 36), så ip-api.com's http-endpoint fejler tavst. */
export async function ipLocation(): Promise<LocationPayload | null> {
  try {
    const res = await fetch('https://ipwho.is/?fields=success,city,region,latitude,longitude')
    const d = (await res.json()) as {
      success?: boolean; city?: string; region?: string; latitude?: number; longitude?: number
    }
    if (!d.success || d.latitude == null || d.longitude == null) return null
    const label = [d.city, d.region].filter(Boolean).join(', ')
    return { lat: d.latitude, lon: d.longitude, label, source: 'ip', precision: 'city' }
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
  // KRITISK (Bjørn 2026-06-21): requestForegroundPermissionsAsync() HÆNGER i det
  // uendelige når den kaldes fra presence-timeren uden en forgrunds-Activity —
  // selv når tilladelsen allerede ER givet. Det blokerede getDeviceLocation helt,
  // så lokationen aldrig nåede serveren (raw_loc=N for evigt). Fix: læs tilladelsen
  // IKKE-blokerende med getForegroundPermissionsAsync() (rør ikke nogen Activity),
  // og bind HELE forløbet i en overordnet timeout så funktionen aldrig kan hænge.
  return Promise.race([
    _precisePayload(),
    new Promise<LocationPayload | null>((resolve) => setTimeout(() => resolve(null), 12000)),
  ]).then((r) => r ?? ipLocation()).catch(() => ipLocation())
}

/** Indre precise-flow uden timeout-værn (kalderen race'er det mod en deadline). */
async function _precisePayload(): Promise<LocationPayload | null> {
  try {
    // Læs tilladelse uden dialog (getForegroundPermissionsAsync rører ikke en
    // Activity → hænger ikke). Bed kun aktivt hvis status er ubestemt.
    let status = 'undetermined'
    try {
      status = (await Location.getForegroundPermissionsAsync()).status
    } catch { status = 'undetermined' }
    if (status === 'undetermined') {
      try { status = (await Location.requestForegroundPermissionsAsync()).status } catch { status = 'denied' }
    }
    if (status !== 'granted') return ipLocation()
    // precise = brugeren VIL have gaden. En cachet last-known-fix er ofte et groft
    // celle/netværks-fix → reverse-geocode giver kun by, INTET vejnavn. Derfor:
    // hent en FRISK høj-præcisions-GPS-fix FØRST (race mod 10s), og brug kun
    // last-known som hurtig fallback hvis det friske fix timer ud/fejler.
    let pos: { coords: { latitude: number; longitude: number } } | null =
      await Promise.race([
        Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.High }),
        new Promise<null>((resolve) => setTimeout(() => resolve(null), 10000)),
      ]).catch(() => null)
    if (!pos) {
      pos = await Location.getLastKnownPositionAsync({ maxAge: 300000 }).catch(() => null)
    }
    if (!pos) return ipLocation()
    const { latitude, longitude } = pos.coords
    const label = await reverseLabel(latitude, longitude, true)
    return { lat: latitude, lon: longitude, label, source: 'gps', precision: 'precise' }
  } catch {
    return ipLocation()
  }
}
