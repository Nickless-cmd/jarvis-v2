import { apiFetch, type ApiConfig } from './api'

/**
 * Hvad der kører LIGE NU — RUTINER, og kun rutiner.
 *
 * Bjørn 15/11-2026: «kører nu under artefakter viser den kørende samtale og
 * ikk rutiner når de køre.. den ska kun vise rutinerne når de køre».
 *
 * Første udgave flettede to kilder: `/chat/active-runs` (hvilke SESSIONER der
 * har et levende run) og `/api/routines/active-runs` (hvilke RUTINER der er i
 * gang). Det var forkert prioriteret: den kørende samtale er noget man allerede
 * SER — man sidder i den, eller den står i sessionslisten med sin spinner. Det
 * man ikke kan se, er de rutiner der kører i baggrunden uden en session.
 * Blokken viste altså det synlige og skjulte det usynlige.
 *
 * Session-kilden er derfor fjernet helt. Rutiner kører som baggrundsrun uden
 * session (målt 15/11-2026: 190 kørsler, nul med session), så et klik fører til
 * rutine-fladen — ikke til et chatview der ikke findes.
 */
export interface LiveRun {
  /** Stabil nøgle på tværs af pollinger — bruges til at fade ud, ikke til at slå op. */
  id: string
  navn: string
  status: string
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
  const svar = await apiFetch<AktivRutineKoersel[]>(config, '/api/routines/active-runs')
    .catch(() => [] as AktivRutineKoersel[])

  const ud: LiveRun[] = []
  for (const r of Array.isArray(svar) ? svar : []) {
    if (!r?.run_id) continue
    ud.push({
      id: `r:${r.run_id}`,
      navn: r.name || 'Rutine',
      status: r.status || 'queued',
      routineId: r.routine_id,
      runId: r.run_id,
      startedAt: r.started_at,
    })
  }
  return ud
}
