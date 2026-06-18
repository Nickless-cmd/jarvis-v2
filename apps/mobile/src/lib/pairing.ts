import { DEFAULT_API_BASE_URL } from './types'

export interface PairingPayload {
  url: string
  code: string
}

/**
 * Parser QR-indholdet fra desktop-appen. Accepterer:
 *  - JSON {"url": "...", "code": "..."} eller kort form {"u","c"}
 *  - en bar kode-streng (→ default API-URL)
 * Returnerer null hvis der ingen kode er.
 */
export function parsePairingPayload(raw: string): PairingPayload | null {
  const text = (raw ?? '').trim()
  if (!text) return null
  try {
    const obj = JSON.parse(text) as Record<string, unknown>
    const code = String(obj.code ?? obj.c ?? '').trim()
    const url = String(obj.url ?? obj.u ?? '').trim() || DEFAULT_API_BASE_URL
    if (!code) return null
    return { url, code }
  } catch {
    // ikke JSON → behandl som bar kode
    return { url: DEFAULT_API_BASE_URL, code: text }
  }
}
