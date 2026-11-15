import { apiFetch, getActiveRunSessions, type ApiConfig } from './api'

/**
 * Hvad der kører LIGE NU — rutiner OG system-rutinernes autonome sessioner.
 *
 * Bjørn 15/11-2026: «kører nu under artefakter viser den kørende samtale og
 * ikk rutiner når de køre.. den ska kun vise rutinerne når de køre».
 * Samme dag, efter at have set resultatet: «køre nu i venstre panel skal osse
 * vises de 3 system/owner sessioner/runtiner».
 *
 * De to ønsker er ikke i konflikt — de peger på hver sin halvdel af samme regel:
 *
 *   * DIN EGEN samtale hører IKKE her. Du sidder i den, eller den står i
 *     sessionslisten med sin spinner. Blokken viste altså det synlige og
 *     skjulte det usynlige.
 *   * SYSTEM-RUTINERNES autonome sessioner hører HER. De har nul kørsler i
 *     `routine_runs` — deres arbejde ligger i `auto-heartbeat-20261115` osv.
 *     (målt 15/11-2026: 672 beskeder i den ene, nul rækker i den anden). Uden
 *     dem er de tre system-rutiner usynlige mens de kører.
 *
 * Skellet er `kind`: serveren mærker hver levende session som «autonom» eller
 * «samtale» (`chat_run_streams.py`). Vi viser kun de autonome. Klienten gætter
 * ALDRIG ud fra et id-præfiks — det ville gøre et navn til en sandhed.
 */
export interface LiveRun {
  /** Stabil nøgle på tværs af pollinger — bruges til at fade ud, ikke til at slå op. */
  id: string
  navn: string
  status: string
  /** «rutine» åbner rutine-fladen; «autonom» åbner den autonome session. */
  kind: 'rutine' | 'autonom'
  routineId?: string
  sessionId?: string
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
  const ud: LiveRun[] = []

  const rutiner = await apiFetch<AktivRutineKoersel[]>(config, '/api/routines/active-runs')
    .catch(() => [] as AktivRutineKoersel[])
  for (const r of Array.isArray(rutiner) ? rutiner : []) {
    if (!r?.run_id) continue
    ud.push({
      id: `r:${r.run_id}`,
      navn: r.name || 'Rutine',
      status: r.status || 'queued',
      kind: 'rutine',
      routineId: r.routine_id,
      runId: r.run_id,
      startedAt: r.started_at,
    })
  }

  // System-rutinernes levende sessioner. `getActiveRunSessions` går gennem
  // husets delte læsning (sharedRead), så blokken ikke bliver endnu et kald pr.
  // 4. sekund oven i dem ChatView og CodeView allerede laver.
  const sessioner = await getActiveRunSessions(config).catch(() => [])
  for (const s of sessioner) {
    if (s.kind !== 'autonom' || !s.session_id) continue
    ud.push({
      id: `s:${s.session_id}`,
      navn: s.label || 'Autonom',
      status: s.status || 'working',
      kind: 'autonom',
      sessionId: s.session_id,
      runId: s.run_id,
    })
  }

  return ud
}
