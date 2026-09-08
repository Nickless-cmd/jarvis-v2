import { apiFetch, type ApiConfig } from './api'

/**
 * Baggrunds-processer Jarvis selv har startet — og som kan stoppes igen.
 *
 * Bjørn 8/9-2026: «vi mangler et sted at vise kørende background job … et fold
 * panel som de 2 andre, bare hvor man kan se og lukke jobs.»
 *
 * Kilden er `process_supervisor` bag `/api/processes`. Den har eksisteret hele
 * tiden med både liste, stop og fjern — den havde bare ingen flade i desk.
 * Serveren tæller selv uptime; klienten regner ikke sin egen tid ud, for så
 * ville to ure kunne drive fra hinanden.
 */
export interface ManagedProcess {
  name: string
  pid: number | null
  status: string
  command: string
  cwd?: string
  started_at?: string
  uptime_seconds?: number
  exit_code?: number | null
  stopped_at?: string | null
  log_path?: string
}

export async function listProcesses(config: ApiConfig): Promise<ManagedProcess[]> {
  const d = await apiFetch<{ processes?: ManagedProcess[] }>(config, '/api/processes')
  return d.processes ?? []
}

/** Stop et kørende job. Ejer-kun på serveren; medlemmer ser kun. */
export async function stopProcess(config: ApiConfig, name: string): Promise<void> {
  await apiFetch(config, `/api/processes/${encodeURIComponent(name)}/stop`, { method: 'POST' })
}

/** Fjern et STOPPET job fra listen. Rydder op, dræber ikke. */
export async function removeProcess(config: ApiConfig, name: string): Promise<void> {
  await apiFetch(config, `/api/processes/${encodeURIComponent(name)}`, { method: 'DELETE' })
}

/** «29t 02m 34s» — samme form som Claude Codes egen rude. */
export function varighed(sekunder: number): string {
  const s = Math.max(0, Math.floor(sekunder))
  const t = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const r = s % 60
  const to = (n: number) => String(n).padStart(2, '0')
  return t > 0 ? `${t}t ${to(m)}m ${to(r)}s` : m > 0 ? `${m}m ${to(r)}s` : `${r}s`
}
