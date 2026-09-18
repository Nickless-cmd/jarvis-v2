import { apiFetch, type ApiConfig } from './api'

/**
 * Artefakter: de filer Jarvis har skrevet og rettet i den valgte arbejdsmappe,
 * på tværs af samtaler (Bjørn 18/9-2026: «på tværs»).
 *
 * Kilden er `GET /chat/artifacts`, der læser hans fil-kald ud af
 * samtalehistorikken. Den eksisterende dispatch-tabel, mobilens artefakt-skærm
 * står på, har NUL rækker — se `core/runtime/db_artifact_index.py`.
 */
export interface Artefakt {
  path: string
  /** Stien under den valgte mappe — det man genkender en fil på. */
  rel: string
  last_at: string
  session_id: string
  session_title: string
  last_tool: string
  /** Antal fil-kald på tværs af samtaler. */
  edits: number
  session_count: number
  add: number
  del: number
}

export interface ArtefaktListe {
  ok: boolean
  root: string
  /** Hvor mange svar serveren læste — så et lavt tal kan kontrolleres. */
  scanned: number
  total: number
  artifacts: Artefakt[]
  error?: string
}

export async function hentArtefakter(config: ApiConfig, root: string): Promise<ArtefaktListe> {
  const r = await apiFetch<Partial<ArtefaktListe>>(
    config, `/chat/artifacts?root=${encodeURIComponent(root)}`,
  )
  return {
    ok: !!r?.ok,
    root: String(r?.root ?? ''),
    scanned: Number(r?.scanned ?? 0),
    total: Number(r?.total ?? 0),
    artifacts: Array.isArray(r?.artifacts) ? r.artifacts : [],
    error: r?.error ? String(r.error) : undefined,
  }
}

export type MappeValg = { root: string; kind: 'container' | 'workstation' }

/**
 * Den mappe code mode står i lige nu.
 *
 * CodeView gemmer sit valg i `jarvis-desk:code-ws` som `{kind, root, wsPath}`.
 * For en workstation er mappen `wsPath`; for serveren er det den navngivne rod
 * (`repo`), som serveren selv oversætter til en sti. Artefakt-fladen læser det
 * samme valg frem for at have sit eget — to valg af «den aktuelle mappe» ville
 * før eller siden pege to steder hen.
 */
export function laesKodeMappe(): MappeValg {
  try {
    const v = JSON.parse(localStorage.getItem('jarvis-desk:code-ws') || '{}') as {
      kind?: string; root?: string; wsPath?: string
    }
    if (v.kind === 'workstation' && v.wsPath) return { root: v.wsPath, kind: 'workstation' }
    return { root: v.root || 'repo', kind: 'container' }
  } catch {
    return { root: 'repo', kind: 'container' }
  }
}
