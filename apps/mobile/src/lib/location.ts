import * as Location from 'expo-location'
import * as SecureStore from 'expo-secure-store'

/** Brugerens lokationsdeling-valg. 'off' = default (ingen deling). */
export type LocationPrecision = 'off' | 'city' | 'area' | 'now' | 'precise' | 'background'

const PRECISION_KEY = 'jarvis.mobile.locationPrecision'

export function parsePrecision(raw: string | null): LocationPrecision {
  return raw === 'city' || raw === 'area' || raw === 'now' || raw === 'precise' || raw === 'background'
    ? raw
    : 'off'
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
  precision: Exclude<LocationPrecision, 'off'>
  accuracy_m?: number
  captured_at?: string
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

/**
 * GPS er den PRIMÆRE kilde på ALLE delende niveauer (18/10-2026).
 *
 * Før spurgte 'city' og 'area' aldrig GPS — de gik direkte til ipwho.is. Bag
 * carrier-grade NAT kan et IP-opslag strukturelt ikke finde byen: udgangen
 * ligger hos operatøren, ikke hos brugeren. Målt tre gange som forkert by
 * (Taastrup 24/9, København 7/10, Ålborg 18/10) mens Bjørn var i Svendborg.
 * IP er nu kun reserve når GPS ikke kan levere et fix.
 */
export function shouldUseGps(precision: LocationPrecision): boolean {
  return precision === 'city' || precision === 'area'
    || precision === 'now' || precision === 'precise' || precision === 'background'
}

export function precisionLabel(precision: LocationPrecision): string {
  switch (precision) {
    case 'city': return 'By'
    case 'area': return 'Område'
    case 'now': return 'Præcis nu'
    case 'precise': return 'Mens appen er åben'
    case 'background': return 'I baggrund'
    default: return 'Fra'
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
    return { lat: d.latitude, lon: d.longitude, label, source: 'ip', precision: 'city', captured_at: new Date().toISOString() }
  } catch {
    return null
  }
}

/**
 * Hent brugerens lokation efter valgt præcision.
 * - 'off'   → null (kalderen sender {} for at rydde server-side)
 * - 'city'/'area' → GPS (lav præcision) → by-label. IP kun som reserve.
 * - 'now'/'precise'/'background' → GPS (høj præcision) → reverse-geocode gade.
 *                                   IP kun som reserve.
 * Best-effort: returnerer null ved manglende tilladelse/fejl.
 *
 * GPS FØRST (18/10-2026): IP-opslaget var standardstien for 'city'/'area' og
 * reserve for resten — men bag CGNAT peger det på operatørens udgang, ikke på
 * brugeren. Det gav tre forkerte byer på tre måneder. IP er nu sidste udvej.
 */
export async function getDeviceLocation(precision: LocationPrecision): Promise<LocationPayload | null> {
  if (precision === 'off') return null
  // KRITISK: getCurrentPositionAsync kan hænge i det uendelige
  // indendørs/uden fix → vi MÅ tids-begrænse den (race mod 8s) så den aldrig
  // blokerer kalderen. Ved timeout/fejl → IP-fallback.
  // KRITISK (Bjørn 2026-06-21): requestForegroundPermissionsAsync() HÆNGER i det
  // uendelige når den kaldes fra presence-timeren uden en forgrunds-Activity —
  // selv når tilladelsen allerede ER givet. Det blokerede getDeviceLocation helt,
  // så lokationen aldrig nåede serveren (raw_loc=N for evigt). Fix: læs tilladelsen
  // IKKE-blokerende med getForegroundPermissionsAsync() (rør ikke nogen Activity),
  // og bind HELE forløbet i en overordnet timeout så funktionen aldrig kan hænge.
  return Promise.race([
    _precisePayload(precision),
    new Promise<LocationPayload | null>((resolve) => setTimeout(() => resolve(null), 12000)),
  ]).then((r) => r ?? ipLocation()).catch(() => ipLocation())
}

/** Indre GPS-flow uden timeout-værn (kalderen race'er det mod en deadline).
 *  'city'/'area' → lav accuracy, by-label. Resten → høj accuracy, gade-label. */
async function _precisePayload(precision: Exclude<LocationPrecision, 'off'>): Promise<LocationPayload | null> {
  const wantStreet = precision === 'now' || precision === 'precise' || precision === 'background'
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
    // 'city'/'area' har ikke brug for gaden — Balanced er nok og tager kortere tid.
    let pos: { coords: { latitude: number; longitude: number; accuracy?: number | null } } | null =
      await Promise.race([
        Location.getCurrentPositionAsync({
          accuracy: wantStreet ? Location.Accuracy.High : Location.Accuracy.Balanced,
        }),
        new Promise<null>((resolve) => setTimeout(() => resolve(null), 10000)),
      ]).catch(() => null)
    if (!pos) {
      pos = await Location.getLastKnownPositionAsync({ maxAge: 300000 }).catch(() => null)
    }
    if (!pos) return ipLocation()
    const { latitude, longitude } = pos.coords
    const label = await reverseLabel(latitude, longitude, wantStreet)
    return {
      lat: latitude,
      lon: longitude,
      label,
      source: 'gps',
      precision,
      accuracy_m: typeof pos.coords.accuracy === 'number' ? pos.coords.accuracy : undefined,
      captured_at: new Date().toISOString()
    }
  } catch {
    return ipLocation()
  }
}
