import { apiFetch, type ApiConfig } from './api'

/**
 * Enheder — desk-siden af enhedsregistret (core/runtime/db_devices.py,
 * 19/9-2026, efter Codex' fjernstyring).
 *
 * Kaldene tager selv imod 400/403/404/412/429: `apiFetch` gør ellers en 403
 * til «HTTP 403» og en 429 til «Rate-limited», og her ER serverens forklaring
 * pointen («Forkert totrinskode.», «Slå totrinsbekræftelse til først …»).
 */
export interface Enhed { id: string; type: 'telefon' | 'computer'; navn: string; platform: string; oprettet: number; sidst_set: number }
export interface EnhedsOverblik {
  enheder: Enhed[]
  kraev_aktivt: boolean
  denne: { type: 'telefon' | 'computer' | 'ukendt'; tilfoejet: boolean; kode_tilladt: boolean }
}

type Svar<T> = { ok: true; data: T } | { ok: false; fejl: string }

async function kald<T>(config: ApiConfig, sti: string, init: { method?: 'GET' | 'POST' | 'PUT' | 'DELETE'; body?: unknown } = {}): Promise<Svar<T>> {
  try {
    const r = await apiFetch<{ status: number; body: Record<string, unknown> }>(config, sti, {
      ...init,
      acceptedStatuses: [400, 401, 403, 404, 409, 412, 429],
      responseHandler: async (res) => ({ status: res.status, body: await res.json().catch(() => ({})) }),
    })
    if (r.status >= 400) {
      const d = r.body.detail ?? r.body.error
      return { ok: false, fejl: typeof d === 'string' ? d : `Serveren sagde nej (${r.status})` }
    }
    return { ok: true, data: r.body as T }
  } catch (e) {
    return { ok: false, fejl: e instanceof Error ? e.message : 'Kunne ikke nå serveren' }
  }
}

export const hentEnheder = (c: ApiConfig) => kald<EnhedsOverblik>(c, '/api/auth/enheder')
export const fjernEnhed = (c: ApiConfig, id: string) => kald<{ ok: boolean }>(c, `/api/auth/enheder/${encodeURIComponent(id)}`, { method: 'DELETE' })
export const tilfoejDenneComputer = (c: ApiConfig, totp: string, navn: string) =>
  kald<Enhed>(c, '/api/auth/enheder/denne-computer', { method: 'POST', body: { totp, navn } })
export const saetEnhedsKrav = (c: ApiConfig, aktiv: boolean, totp: string, navn: string) =>
  kald<{ ok: boolean }>(c, '/api/auth/enheds-krav', { method: 'PUT', body: { aktiv, totp, navn } })
export const opretParring = (c: ApiConfig, totp: string) =>
  kald<{ code: string; expires_in: number }>(c, '/api/auth/pair/create', { method: 'POST', body: { totp } })
