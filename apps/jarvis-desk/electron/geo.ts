// Geolocation-opslag fra main-processen — node https med korrekt User-Agent
// (Nominatim kræver UA; renderer-fetch kan ikke sætte den). Alle kilder gratis,
// ingen nøgler. Best-effort: returnerer null ved fejl.
import * as https from 'node:https'
import * as http from 'node:http'

const UA = 'Jarvis-Desktop-Companion/1.0 (jarvis-v2)'

function getJson(url: string, timeoutMs = 10000): Promise<unknown> {
  return new Promise((resolve, reject) => {
    const mod = url.startsWith('https:') ? https : http
    const req = mod.get(url, { headers: { 'User-Agent': UA } }, (res) => {
      let data = ''
      res.on('data', (c) => { data += c })
      res.on('end', () => {
        try { resolve(JSON.parse(data)) } catch (e) { reject(e) }
      })
    })
    req.on('error', reject)
    req.setTimeout(timeoutMs, () => req.destroy(new Error('timeout')))
  })
}

export interface GeoResult { lat: number; lon: number; label: string }

function labelFromAddress(a: Record<string, string>, precise: boolean): string {
  const city = a.city || a.town || a.village || a.municipality || a.county || ''
  if (precise) return [a.road || a.suburb || '', city].filter(Boolean).join(', ')
  return city
}

/** Adresse → koordinater + label (Nominatim). */
export async function geocode(address: string): Promise<GeoResult | null> {
  const q = encodeURIComponent((address || '').trim())
  if (!q) return null
  try {
    const rows = (await getJson(
      `https://nominatim.openstreetmap.org/search?q=${q}&format=json&limit=1&addressdetails=1`,
    )) as { lat: string; lon: string; display_name: string; address?: Record<string, string> }[]
    if (!rows?.length) return null
    const r = rows[0]
    return { lat: parseFloat(r.lat), lon: parseFloat(r.lon),
             label: labelFromAddress(r.address ?? {}, true) || r.display_name }
  } catch { return null }
}

/** Koordinater → label (Nominatim reverse). */
export async function reverse(lat: number, lon: number, precise: boolean): Promise<string> {
  try {
    const r = (await getJson(
      `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}&addressdetails=1&zoom=${precise ? 18 : 12}`,
    )) as { address?: Record<string, string> }
    return labelFromAddress(r.address ?? {}, precise)
  } catch { return '' }
}

/** Server-IP → by-niveau lokation (ip-api, ingen nøgle). */
export async function ipLookup(): Promise<GeoResult | null> {
  try {
    const d = (await getJson('http://ip-api.com/json/?fields=status,city,regionName,lat,lon')) as {
      status?: string; city?: string; regionName?: string; lat?: number; lon?: number
    }
    if (d.status !== 'success' || d.lat == null || d.lon == null) return null
    return { lat: d.lat, lon: d.lon, label: [d.city, d.regionName].filter(Boolean).join(', ') }
  } catch { return null }
}
