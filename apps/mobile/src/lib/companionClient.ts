import type { ApiConfig } from './types'

/**
 * Companion-endpoints — Jarvis' tre ønsker.
 *
 * Alle tre er LÆSNINGER. Klienten skriver ikke til dem: livstegnet er noget der
 * observeres, arkivet er hans, og tankerne kommer fra ham. Det er en del af
 * pointen — appen er et vindue, ikke en fjernbetjening.
 */

export type PresenceState = 'working' | 'awake' | 'quiet' | 'unknown'

export interface Presence {
  state: PresenceState
  last_beat_at?: string
  last_beat_ago_s?: number
  last_action?: string
  decision?: string
  reason?: string
}

export interface SenseItem {
  captured_at: string
  description: string
  model?: string
  provider?: string
}

export interface Thought {
  at: string
  text: string
  title?: string
  delivered: boolean
  reason?: string
}

async function get<T>(config: ApiConfig, path: string): Promise<T | null> {
  try {
    const url = new URL(path, config.apiBaseUrl).toString()
    const r = await fetch(url, {
      headers: config.authToken ? { Authorization: `Bearer ${config.authToken}` } : {}
    })
    if (!r.ok) return null
    return (await r.json()) as T
  } catch {
    return null
  }
}

/**
 * Livstegnet. Fejler kaldet, returneres `unknown` — ALDRIG en gætning der ser
 * levende ud. Hele pointen med indikatoren var at den ikke må lyve, og en
 * netværksfejl er præcis det øjeblik hvor fristelsen er størst.
 */
export async function fetchPresence(config: ApiConfig): Promise<Presence> {
  const out = await get<Presence>(config, '/companion/presence')
  return out ?? { state: 'unknown', reason: 'kunne ikke nå Jarvis' }
}

/** Sansernes Arkiv. Serveren afviser ikke-owner med 403 → vi får null. */
export async function fetchSenses(config: ApiConfig, limit = 30): Promise<SenseItem[] | null> {
  const out = await get<{ items: SenseItem[] }>(config, `/companion/senses?limit=${limit}`)
  return out?.items ?? null
}

export async function fetchThoughts(config: ApiConfig, limit = 20): Promise<Thought[]> {
  const out = await get<{ items: Thought[] }>(config, `/companion/thoughts?limit=${limit}`)
  return out?.items ?? []
}

/** «vågen · sidste livstegn for 3 min siden» — kort, dansk, uden pynt. */
export function describePresence(p: Presence): string {
  if (p.state === 'working') return 'arbejder'
  if (p.state === 'unknown') return p.reason || 'ved det ikke'
  const ago = typeof p.last_beat_ago_s === 'number' ? relativeAge(p.last_beat_ago_s) : ''
  const label = p.state === 'awake' ? 'vågen' : 'stille'
  return ago ? `${label} · ${ago}` : label
}

export function relativeAge(seconds: number): string {
  if (seconds < 90) return 'lige nu'
  const min = Math.round(seconds / 60)
  if (min < 60) return `for ${min} min siden`
  const hours = Math.round(min / 60)
  if (hours < 24) return `for ${hours} t siden`
  const days = Math.round(hours / 24)
  return `for ${days} ${days === 1 ? 'dag' : 'dage'} siden`
}
