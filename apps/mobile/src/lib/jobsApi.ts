import { apiFetch } from './apiClient'
import type { ApiConfig } from './types'

export type JobKilde = 'supervisor' | 'operator'
export type JobStatus = 'running' | 'paused' | 'exited' | 'lost'

export interface BaggrundsJob {
  id: string
  kilde: JobKilde
  navn: string
  kommando: string
  status: JobStatus
  pid: number | null
  /** Kørselstid i sekunder. Serverens tal — klienten tæller ikke selv. */
  sekunder: number | null
  exitCode: number | null
  kanPause: boolean
}

export interface JobsSvar {
  jobs: BaggrundsJob[]
  /**
   * Kunne vi overhovedet spørge operatørens maskine?
   *
   * `false` betyder at vi ikke VED hvad der kører derovre — ikke at der ingenting
   * kører. De to er stik modsat, og en tom liste må ikke kunne betyde begge dele.
   */
  broOk: boolean
}

/**
 * Alle kørende baggrundsopgaver.
 *
 * To kilder bag ét svar: supervisorens langtidsservicer på serveren, og de ad
 * hoc-shells Jarvis starter på Bjørns egen maskine. Et panel der kun viste den
 * ene ville lade én tro at der ikke kørte noget, mens der gjorde.
 */
export async function hentJobs(config: ApiConfig, medFaerdige = false): Promise<JobsSvar> {
  const d = await apiFetch<{ jobs?: Record<string, unknown>[]; bridge_ok?: boolean }>(
    config, `/api/jobs?include_done=${medFaerdige ? 'true' : 'false'}`,
  )
  return {
    jobs: (d.jobs ?? []).map(normalisér).filter((j): j is BaggrundsJob => j !== null),
    broOk: d.bridge_ok !== false,
  }
}

function normalisér(raw: Record<string, unknown>): BaggrundsJob | null {
  const id = typeof raw.id === 'string' ? raw.id : ''
  const kilde = raw.kilde === 'operator' ? 'operator' : 'supervisor'
  if (!id) return null
  const st = String(raw.status ?? '')
  return {
    id,
    kilde,
    navn: String(raw.navn ?? id),
    kommando: String(raw.kommando ?? ''),
    status: st === 'paused' || st === 'running' || st === 'exited' ? st : 'lost',
    pid: typeof raw.pid === 'number' ? raw.pid : null,
    sekunder: typeof raw.sekunder === 'number' ? raw.sekunder : null,
    exitCode: typeof raw.exit_code === 'number' ? raw.exit_code : null,
    kanPause: raw.can_pause === true,
  }
}

export async function jobHandling(
  config: ApiConfig, job: BaggrundsJob, handling: 'pause' | 'resume' | 'stop',
): Promise<void> {
  await apiFetch(
    config,
    `/api/jobs/${job.kilde}/${encodeURIComponent(job.id)}/${handling}`,
    { method: 'POST' },
  )
}
