import { apiFetch } from './apiClient'
import type { ApiConfig } from './types'

/**
 * Artefakter: de filer Jarvis har skrevet og rettet i den valgte mappe, på
 * tværs af samtaler. Samme kilde og samme form som desk' artefakt-menu.
 *
 * ## Hvorfor kilden blev skiftet (18/9-2026)
 *
 * Skærmen læste `/api/dispatches`. To ting var galt, og de skjulte hinanden:
 *
 * 1. Ruten var bundet til en kolonne-hjælper i stedet for listen (13/9 → 18/9)
 *    og svarede med en streng.
 * 2. Tabellen bag den, `claude_dispatch_audit`, har NUL rækker på CT105 — den
 *    fyldes kun når Jarvis bruger `dispatch_to_claude_code`, og det gør han ikke.
 *
 * Selv med ruten rettet var skærmen altså tom for altid. `/chat/artifacts`
 * læser hans faktiske fil-kald ud af samtalehistorikken.
 *
 * ## Fejl er ikke det samme som tomt
 *
 * Den gamle udgave havde `catch { return [] }`. En 500 og en tom database gav
 * præcis samme skærm, og det var derfor fem dages brækket rute aldrig blev set.
 * Nu kommer fejlen med op.
 */
export interface ArtifactItem {
  path: string
  /** Stien under mappen — det man genkender en fil på. */
  rel: string
  lastAt: string
  sessionId: string
  sessionTitle: string
  edits: number
  sessionCount: number
  add: number
  del: number
}

export interface ArtifactList {
  ok: boolean
  root: string
  /** Hvor mange svar serveren læste — så et lavt tal kan kontrolleres. */
  scanned: number
  total: number
  items: ArtifactItem[]
  error?: string
}

export async function fetchArtifacts(config: ApiConfig, root: string): Promise<ArtifactList> {
  try {
    const raw = await apiFetch<Record<string, unknown>>(
      config, `/chat/artifacts?root=${encodeURIComponent(root || 'repo')}`,
    )
    const rows = Array.isArray(raw?.artifacts) ? raw.artifacts : []
    return {
      ok: !!raw?.ok,
      root: String(raw?.root ?? ''),
      scanned: Number(raw?.scanned ?? 0),
      total: Number(raw?.total ?? 0),
      error: raw?.error ? String(raw.error) : undefined,
      items: rows
        .filter((x): x is Record<string, unknown> => typeof x === 'object' && x !== null)
        .filter((x) => typeof x.path === 'string' && x.path)
        .map((x) => ({
          path: String(x.path),
          rel: String(x.rel || x.path),
          lastAt: String(x.last_at || ''),
          sessionId: String(x.session_id || ''),
          sessionTitle: String(x.session_title || ''),
          edits: Number(x.edits || 0),
          sessionCount: Number(x.session_count || 0),
          add: Number(x.add || 0),
          del: Number(x.del || 0),
        })),
    }
  } catch (e) {
    return {
      ok: false, root: root || '', scanned: 0, total: 0, items: [],
      error: e instanceof Error && e.message ? e.message : 'Kunne ikke hente artefakter',
    }
  }
}
