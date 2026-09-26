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

/**
 * En AFGJORT post. Samme felter som `Notifikation` — plus hvornaar den blev
 * lukket og hvad udfaldet blev. `kan_afgoere` er altid false her; der er
 * intet at svare paa, og det er hele forskellen til listen ovenfor.
 */
export interface TidligereNotifikation extends Notifikation {
  klaret: string
  udfald: string
  udfald_tekst: string
}

export interface TidligereFeed { poster: TidligereNotifikation[]; antal: number }

export async function hentNotifikationer(config: ApiConfig): Promise<Feed> {
  return apiFetch<Feed>(config, '/notifikationer')
}

/** Historikken — de sidste syv dage, som er saa laenge lageret beholder dem. */
export async function hentTidligere(config: ApiConfig): Promise<TidligereFeed> {
  return apiFetch<TidligereFeed>(config, '/notifikationer/tidligere')
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

export async function hentNotifikationsValg(config: ApiConfig): Promise<{ valg: Record<string, string> }> {
  return apiFetch(config, '/notifikations-valg')
}

export async function saetNotifikationsValg(
  config: ApiConfig, slags: string, kanal: string,
): Promise<{ ok: boolean; fejl: string }> {
  // `apiFetch` JSON.stringify'er selv `body` — en raa objekt her, ikke en
  // fortstrenget en (se afgoerNotifikation ovenfor for samme moenster).
  return apiFetch(config, '/notifikations-valg', {
    method: 'POST',
    body: { slags, kanal },
  })
}
