import { useEffect, useSyncExternalStore } from 'react'
import { AppState } from 'react-native'
import { apiFetch } from './apiClient'
import type { ApiConfig } from './types'

/**
 * Tilstands-hjernen på telefonen (server: core.runtime.opmaerksomhed).
 * ÉN samlet tilstand — Codex' prioritet: venter › fejlede › færdig ›
 * arbejder › intet. Samme endpoint og samme kvittering som desk, så et svar
 * man har set på den ene flade også forsvinder på den anden.
 *
 * Én poller (i ChatScreen, der kender config og den åbne samtale) udgiver
 * her; topbjælken i App og sidepanelet lytter. Samme mønster som
 * lib/stickyPrompt.
 */
export type OpmTilstand = 'waiting' | 'failed' | 'review' | 'running' | 'idle'

export interface OpmPunkt {
  session_id: string
  run_id: string
  tilstand: OpmTilstand
  titel: string
  tekst: string
  tid: number
}

export interface Opmaerksomhed {
  tilstand: OpmTilstand
  etiket: string
  antal: { waiting: number; failed: number; review: number; running: number }
  baggrund: number
  indbakke: number
  fokus: OpmPunkt | null
  punkter: OpmPunkt[]
}

export const POLL_MS = 8000

let nu: Opmaerksomhed | null = null
const lyttere = new Set<() => void>()

export function udgiv(o: Opmaerksomhed | null): void {
  nu = o
  lyttere.forEach((l) => l())
}

export function useOpmaerksomhed(): Opmaerksomhed | null {
  return useSyncExternalStore(
    (l) => { lyttere.add(l); return () => { lyttere.delete(l) } },
    () => nu,
    () => nu,
  )
}

export function hentOpmaerksomhed(config: ApiConfig): Promise<Opmaerksomhed> {
  return apiFetch<Opmaerksomhed>(config, '/cowork/opmaerksomhed')
}

export async function markerSet(config: ApiConfig, sessionId: string): Promise<void> {
  await apiFetch(config, `/cowork/opmaerksomhed/set/${encodeURIComponent(sessionId)}`, { method: 'POST' })
}

/** Er der et «færdig»/«fejlede» for den åbne samtale, der skal kvitteres? */
export function skalKvittere(o: Opmaerksomhed | null, aktivId: string | null): boolean {
  if (!o || !aktivId) return false
  return o.punkter.some((p) => p.session_id === aktivId && (p.tilstand === 'review' || p.tilstand === 'failed'))
}

/** Uden punktet for samtalen — og med tilstanden regnet om, så prikken ikke
 *  hænger på «færdig» til næste poll efter man har åbnet svaret. */
export function udenSamtale(o: Opmaerksomhed, sessionId: string): Opmaerksomhed {
  const punkter = o.punkter.filter((p) => p.session_id !== sessionId)
  const fokus = punkter[0] ?? null
  const tilstand: OpmTilstand = fokus ? fokus.tilstand : 'idle'
  const antal = { waiting: 0, failed: 0, review: 0, running: 0 }
  for (const p of punkter) if (p.tilstand !== 'idle') antal[p.tilstand] += 1
  return { ...o, punkter, fokus, tilstand, etiket: tilstand === o.tilstand ? o.etiket : ETIKET[tilstand], antal }
}

export const ETIKET: Record<OpmTilstand, string> = {
  waiting: 'Venter på dig',
  failed: 'Noget gik galt',
  review: 'Færdig — se svaret',
  running: 'Arbejder',
  idle: 'Intet kræver dig',
}

/** Polleren. Kun mens appen er fremme — i baggrunden er der ingen at vise det for. */
export function useOpmaerksomhedsPoll(config: ApiConfig | null, aktivId: string | null): void {
  useEffect(() => {
    if (!config) return
    let aktiv = true
    const tick = () => {
      if (AppState.currentState && AppState.currentState !== 'active') return
      Promise.resolve().then(() => hentOpmaerksomhed(config))
        .then((d) => { if (aktiv) udgiv(d) })
        .catch(() => { /* behold sidste — ingen flimren ved netværks-blip */ })
    }
    tick()
    const id = setInterval(tick, POLL_MS)
    const sub = AppState.addEventListener?.('change', (s) => { if (s === 'active') tick() })
    return () => { aktiv = false; clearInterval(id); sub?.remove?.(); udgiv(null) }
  }, [config?.apiBaseUrl, config?.authToken]) // eslint-disable-line react-hooks/exhaustive-deps

  const o = useOpmaerksomhed()
  useEffect(() => {
    if (!config || !aktivId || !skalKvittere(o, aktivId)) return
    udgiv(udenSamtale(o!, aktivId))
    void markerSet(config, aktivId).catch(() => {})
  }, [aktivId, o, config])
}
