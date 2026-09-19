import { apiFetch, type ApiConfig } from './api'
import { sharedRead } from './sharedRead'

/**
 * Tilstands-hjernen (server: core.runtime.opmaerksomhed). ÉN samlet tilstand —
 * Codex' prioritet: venter › fejlede › færdig › arbejder › intet.
 */
export type OpmTilstand = 'waiting' | 'failed' | 'review' | 'running' | 'idle'

export interface OpmPunkt {
  session_id: string
  run_id: string
  tilstand: OpmTilstand
  titel: string
  tekst: string
  tid: number
  id?: string
}

export interface Opmaerksomhed {
  tilstand: OpmTilstand
  etiket: string
  antal: { waiting: number; failed: number; review: number; running: number }
  baggrund: number
  /** Forslag og initiativer — venter, men blokerer intet. */
  indbakke: number
  fokus: OpmPunkt | null
  punkter: OpmPunkt[]
}

export async function hentOpmaerksomhed(config: ApiConfig): Promise<Opmaerksomhed> {
  return sharedRead(
    `opmaerksomhed:${config.apiBaseUrl}`,
    () => apiFetch<Opmaerksomhed>(config, '/cowork/opmaerksomhed'),
    { ttlMs: 3_000, streamingTtlMs: 10_000 },
  )
}

/** Samtalen er åbnet — dens «færdig»/«fejlede» forsvinder på serveren. */
export async function markerSet(config: ApiConfig, sessionId: string): Promise<void> {
  await apiFetch(config, `/cowork/opmaerksomhed/set/${encodeURIComponent(sessionId)}`, { method: 'POST' })
}

/** Er der et punkt for den åbne samtale der skal kvitteres? */
export function skalKvittere(o: Opmaerksomhed | null, aktivId: string | null): boolean {
  if (!o || !aktivId) return false
  return o.punkter.some((p) => p.session_id === aktivId && (p.tilstand === 'review' || p.tilstand === 'failed'))
}
