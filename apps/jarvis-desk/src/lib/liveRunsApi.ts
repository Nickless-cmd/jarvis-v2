import { apiFetch, getActiveRunSessions, type ActiveRunSession, type ApiConfig } from './api'

/**
 * Hvad der kører LIGE NU — fra to kilder, samlet til én liste.
 *
 * To kilder fordi de er to forskellige ting: `/chat/active-runs` svarer på
 * hvilke SESSIONER der har et levende run (det er den session man kan åbne),
 * og `/api/routines/active-runs` svarer på hvilke RUTINER der er i gang
 * (rutiner kører som baggrundsrun uden session — målt 15/11-2026: 190 kørsler,
 * nul med session).
 *
 * Sessions-delen går gennem `getActiveRunSessions` og ikke et eget `apiFetch`:
 * den ligger bag husets `sharedRead`, så sidebarens eksisterende polling og
 * denne blok deler ét kald pr. TTL i stedet for at spørge to gange.
 *
 * Derfor har en række en `kind` der bestemmer hvor klikket fører hen: en
 * session åbnes i chatview, en rutine åbnes i rutine-fladen. At påstå noget
 * andet ville være at vise en knap der ikke gør noget.
 */
export type LiveRunKind = 'rutine' | 'autonom' | 'samtale'

export interface LiveRun {
  /** Stabil nøgle på tværs af pollinger — bruges til at fade ud, ikke til at slå op. */
  id: string
  kind: LiveRunKind
  navn: string
  status: string
  sessionId?: string
  routineId?: string
  runId?: string
  startedAt?: string
}

interface AktivRutineKoersel {
  run_id: string
  routine_id: string
  name?: string
  status?: string
  started_at?: string
}

export async function hentLiveRuns(config: ApiConfig): Promise<LiveRun[]> {
  // Parallelt: to uafhængige opslag. En fejl i det ene må ikke slukke det
  // andet — en kørende rutine er stadig sand selv om sessions-opslaget fejler.
  const [sessionListe, rutineSvar] = await Promise.all([
    getActiveRunSessions(config).catch(() => [] as ActiveRunSession[]),
    apiFetch<AktivRutineKoersel[]>(config, '/api/routines/active-runs')
      .catch(() => [] as AktivRutineKoersel[]),
  ])

  const ud: LiveRun[] = []
  for (const s of sessionListe) {
    if (!s?.session_id) continue
    ud.push({
      id: `s:${s.session_id}`,
      kind: s.kind === 'autonom' ? 'autonom' : 'samtale',
      navn: s.label || 'Samtale',
      status: s.status || 'working',
      sessionId: s.session_id,
      runId: s.run_id || undefined,
    })
  }
  const rutiner = Array.isArray(rutineSvar) ? rutineSvar : []
  for (const r of rutiner) {
    if (!r?.run_id) continue
    ud.push({
      id: `r:${r.run_id}`,
      kind: 'rutine',
      navn: r.name || 'Rutine',
      status: r.status || 'queued',
      routineId: r.routine_id,
      runId: r.run_id,
      startedAt: r.started_at,
    })
  }
  return ud
}
