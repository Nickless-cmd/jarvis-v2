/** API-klient for notifikations-feeden. Serverens kontrakt:
 *
 *     GET /notifikationer → {"poster": [...], "antal": number}
 *
 * `antal` er antal AABNE poster — alle slags, ikke kun dem der kraever et
 * svar. Se Klokke.tsx for hvorfor.
 */
import { apiFetch, type ApiConfig } from './api'

export interface Notifikation {
  id: string
  slags: string
  titel: string
  tekst: string
  session_id: string | null
  oprettet: string
  kan_afgoere: boolean
  foraeldet: boolean
}

export interface Feed { poster: Notifikation[]; antal: number }

export async function hentNotifikationer(config: ApiConfig): Promise<Feed> {
  return apiFetch<Feed>(config, '/notifikationer')
}

export async function afgoerNotifikation(
  config: ApiConfig, id: string, approved: boolean,
): Promise<{ ok: boolean; fejl: string }> {
  // `apiFetch` JSON.stringify'er selv `body` — en raa objekt her, ikke en
  // fortstrenget en (ellers faar serveren en streng som payload, ikke JSON).
  return apiFetch(config, `/notifikationer/${encodeURIComponent(id)}/afgoer`, {
    method: 'POST',
    body: { approved },
  })
}

export async function setNotifikation(config: ApiConfig, id: string): Promise<void> {
  await apiFetch(config, `/notifikationer/${encodeURIComponent(id)}/set`, { method: 'POST' })
}
