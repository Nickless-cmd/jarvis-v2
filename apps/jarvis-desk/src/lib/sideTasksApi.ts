import { apiFetch, type ApiConfig } from './api'

/**
 * Jarvis' flaggede sideopgaver (server: core.services.side_tasks, ruterne
 * /cowork/side-tasks). Serveren er eneste sandhed — desk holder ingen kopi
 * af status, den spørger bare igen.
 */
export interface SideTask {
  side_task_id: string
  title: string
  prompt: string
  tldr: string
  /** `completed`/`dismissed` optræder kun i `scope=all` — kortet viser de åbne. */
  status: 'pending' | 'queued' | 'activated' | 'completed' | 'dismissed'
  session_id: string
  created_at: string
  /** Sat når opgaven er SKJULT i chatkortet (8/10-2026). Opgaven er stadig
   *  ÅBEN — den vises bare ikke over samtalen. Modsat `dismissed`, som er
   *  terminal: skjult kan vises igen med `setSideTaskSkjult(…, false)`. */
  skjult_i_chat?: boolean
  /** Sat når opgaven er lukket. */
  resolved_at?: string
  /** Hvem der lukkede den — fx `desk`, `jarvis` eller `auto:stilstand 42min`. */
  lukket_af?: string
  /** BEVISET for en `completed`-lukning: hvad der faktisk blev gjort
   *  (16/10-2026). Serveren afviser en lukning uden det. */
  bevis?: string
  /** Grunden til en `dismissed`-lukning: hvorfor den ikke skal løses. */
  dismiss_reason?: string
  /** Samtalen der løser/løste opgaven. */
  arbejds_session?: string
  arbejds_run_id?: string
  finding_key?: string
  evidence?: string
}

export type SideTaskAfslutning = 'queued' | 'activated' | 'completed' | 'dismissed'

export async function getSideTasks(config: ApiConfig): Promise<SideTask[]> {
  const d = await apiFetch<{ side_tasks?: SideTask[] }>(config, '/cowork/side-tasks', { retries: 0 })
  return d.side_tasks ?? []
}

/**
 * ALLE opgaver, også de lukkede. Bjørn 3/10-2026: «desk har ikk noget panel der
 * viser opgaver der er flagged selv om jeg har trykket dem væk». Kortet i
 * chatten viser kun de åbne — så en lukket opgave forsvandt sporløst, og man
 * kunne ikke se forskel på «lukket» og «blev den nogensinde gemt?».
 */
export async function getAlleSideTasks(config: ApiConfig): Promise<SideTask[]> {
  const d = await apiFetch<{ side_tasks?: SideTask[] }>(
    config, '/cowork/side-tasks?scope=all', { retries: 0 },
  )
  return d.side_tasks ?? []
}

export async function setSideTaskStatus(
  config: ApiConfig,
  id: string,
  status: SideTaskAfslutning,
  opts: { session?: string; bevis?: string; reason?: string } = {},
): Promise<void> {
  // `session` er samtalen der LØSER opgaven. Uden den kan serveren ikke knytte
  // turen til opgaven, og så er der ingen der kan lukke den (Bjørn 3/10: «måtte
  // jeg minde ham om at markere den flaggede opgave færdig»).
  //
  // `bevis`/`reason` (16/10-2026): serveren AFVISER en lukning uden sin grund —
  // `completed` kræver hvad der faktisk blev gjort, `dismissed` hvorfor den ikke
  // skal løses. Bjørn: «Krav ved completed — men dismissed med begrundelse er
  // altid en vej ud». Derfor er begge felter med her: uden dem virker knapperne
  // i panelet ikke, og en lukning ville igen kunne efterlade en MEMORY-sektion
  // der kalder afsluttet arbejde «stadig åben».
  const body: Record<string, string> = { status }
  if (opts.session) body.session = opts.session
  if (opts.bevis) body.bevis = opts.bevis
  if (opts.reason) body.reason = opts.reason
  const r = await apiFetch<{ status?: string; error?: string }>(
    config, `/cowork/side-tasks/${encodeURIComponent(id)}/status`,
    { method: 'POST', body },
  )
  // Serveren svarer 200 med {status:'error'} for en ukendt eller allerede
  // afsluttet opgave. Det er en fejl for brugeren, ikke en succes.
  if (r?.status === 'error') throw new Error(r.error || 'Kunne ikke opdatere sideopgaven')
}

/**
 * Skjul (eller vis) en sideopgave i chatkortet — uden at lukke den.
 *
 * Bjørn 8/10-2026: «sørg for X'et ikk sletter dem men bare fjerner dem fra
 * chatview». Før kaldte krydset `setSideTaskStatus(…, 'dismissed')`, og det er
 * TERMINALT: opgaven kunne ikke genåbnes, og fire klik i et hjørne afskrev
 * fire opgaver permanent. Skjult er den bløde, reversible modsætning —
 * opgaven forbliver åben og står i panelet; den vises bare ikke i kortet.
 */
export async function setSideTaskSkjult(
  config: ApiConfig, id: string, skjult = true,
): Promise<void> {
  const r = await apiFetch<{ status?: string; error?: string }>(
    config, `/cowork/side-tasks/${encodeURIComponent(id)}/skjul`,
    { method: 'POST', body: { skjult } },
  )
  if (r?.status === 'error') throw new Error(r.error || 'Kunne ikke skjule sideopgaven')
}

/**
 * Opret en sideopgave fra Desk.
 *
 * Bjørn 15/10-2026: «jeg mangler et sted i desk jeg kan oprette side-opgaver
 * selv». Indtil nu kunne KUN Jarvis flagge en (`flag_side_task`), så en ting
 * han selv bemærkede midt i noget andet måtte igennem en samtale for at blive
 * skrevet ned — og det er præcis den omvej sideopgaven findes for at undgå.
 *
 * `title` og `prompt` er begge påkrævet; serveren svarer 400 hvis en mangler.
 * Returnerer opgavens id, så kalderen kan vise den nye opgave med det samme
 * i stedet for at vente på panelets 8-sekunders poll.
 */
export async function opretSideTask(
  config: ApiConfig, title: string, prompt: string, tldr = '',
): Promise<string> {
  const r = await apiFetch<{ status?: string; side_task_id?: string; error?: string }>(
    config, '/cowork/side-tasks',
    { method: 'POST', body: { title, prompt, ...(tldr ? { tldr } : {}) } },
  )
  if (r?.status !== 'ok' || !r.side_task_id) {
    throw new Error(r?.error || 'Kunne ikke oprette sideopgaven')
  }
  return r.side_task_id
}
