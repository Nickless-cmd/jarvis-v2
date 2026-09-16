import { apiFetch, type ApiConfig } from './api'

/**
 * Baggrundsjob fra BEGGE kilder — serverens supervisor og Bjørns egne shells.
 *
 * Panelet hentede før `/api/processes`, som kun kender serverens supervisor.
 * Alt Jarvis satte i gang på Bjørns EGEN maskine (`operator_run_in_background`,
 * gemt som filer i /tmp/jarvis-bg/) fandtes aldrig i den liste — og det er
 * netop dem der opstår midt i en opgave.
 *
 * `/api/jobs` samler begge og har eksisteret siden 12/9-2026 med både pause,
 * resume og stop. Ingen klient kaldte den. (Bjørn 16/9: «undersøg hvornår han
 * kører baggrundsjobs både på min maskine og sin egen — hvorfor de ikk bliver
 * vist overhovedet».)
 */
export interface BackgroundJob {
  id: string
  /** 'supervisor' = serverens egne services. 'operator' = Bjørns maskine. */
  kilde: 'supervisor' | 'operator'
  navn: string
  kommando: string
  status: 'running' | 'paused' | 'exited' | string
  pid?: number | null
  sekunder?: number | null
  exit_code?: number | null
  can_pause?: boolean
}

export interface JobsSvar {
  jobs: BackgroundJob[]
  /** false = vi VED ikke hvad der kører på hans maskine. Det er noget ANDET
   *  end at der ikke kører noget, og panelet skal sige forskel. */
  bridge_ok: boolean
}

export async function listJobs(config: ApiConfig, medFaerdige = false): Promise<JobsSvar> {
  const d = await apiFetch<Partial<JobsSvar>>(
    config, `/api/jobs?include_done=${medFaerdige ? 'true' : 'false'}`,
  )
  return { jobs: d.jobs ?? [], bridge_ok: d.bridge_ok !== false }
}

export async function stopJob(config: ApiConfig, job: BackgroundJob): Promise<void> {
  await apiFetch(config, `/api/jobs/${job.kilde}/${encodeURIComponent(job.id)}/stop`,
                 { method: 'POST' })
}

export async function pauseJob(config: ApiConfig, job: BackgroundJob): Promise<void> {
  await apiFetch(config, `/api/jobs/${job.kilde}/${encodeURIComponent(job.id)}/pause`,
                 { method: 'POST' })
}

export async function resumeJob(config: ApiConfig, job: BackgroundJob): Promise<void> {
  await apiFetch(config, `/api/jobs/${job.kilde}/${encodeURIComponent(job.id)}/resume`,
                 { method: 'POST' })
}

/** «1t 51m 52s» — samme form som Claude Codes egen rude. Serveren tæller, vi
 *  formaterer; to ure der hver især tæller ville drive fra hinanden. */
export function varighed(sekunder?: number | null): string {
  if (sekunder === null || sekunder === undefined) return ''
  const s = Math.max(0, Math.floor(sekunder))
  const t = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const r = s % 60
  if (t) return `${t}t ${m}m ${r}s`
  if (m) return `${m}m ${r}s`
  return `${r}s`
}

/** Hvor kører den? CC skriver værktøjet («Bash», «Preview»); vi skriver
 *  MASKINEN, fordi det er dét der er forskellen her — og det var netop den
 *  ene af de to man ikke kunne se. */
export function kildeNavn(kilde: string): string {
  return kilde === 'operator' ? 'Din maskine' : 'Server'
}
