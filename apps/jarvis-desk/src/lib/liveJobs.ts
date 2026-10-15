import type { BackgroundJob, JobsSvar } from './jobsApi'

const OUTPUT_CAP = 65_536

export interface LiveJobEvent {
  cursor: number
  type: string
  job_key?: string
  session_id?: string
  source?: string
  payload?: Record<string, unknown>
  jobs?: BackgroundJob[]
  bridge_ok?: boolean
  uspecificeret?: number
}

export interface LiveJobsState {
  byKey: Record<string, BackgroundJob>
  order: string[]
  cursor: number
  bridgeOk: boolean
  uspecificeret: number
}

export function jobKey(job: BackgroundJob): string {
  return job.job_key || job.id
}

/** Er jobbet slut? Kun `running` og `paused` er levende tilstande — alt andet
 *  (exited, error, failed, cancelled, timeout, lost) er en afsluttet række.
 *  Ukendte statusser tælles som sluttede: vi genopliver ikke på et gæt. */
export function erTerminal(status: unknown): boolean {
  const s = String(status ?? '')
  return s !== '' && s !== 'running' && s !== 'paused'
}

export function emptyLiveJobs(): LiveJobsState {
  return { byKey: {}, order: [], cursor: 0, bridgeOk: true, uspecificeret: 0 }
}

export function fromSnapshot(
  snapshot: Pick<JobsSvar, 'jobs' | 'bridge_ok' | 'uspecificeret'>,
  cursor: number,
  previous?: LiveJobsState,
): LiveJobsState {
  const byKey: Record<string, BackgroundJob> = {}
  const order: string[] = []
  for (const raw of snapshot.jobs ?? []) {
    const key = jobKey(raw)
    const old = previous?.byKey[key]
    byKey[key] = old ? {
      ...raw,
      job_key: raw.job_key,
      liveOutput: old.liveOutput,
      liveOutputSeq: old.liveOutputSeq,
      liveOutputTruncated: old.liveOutputTruncated,
    } : { ...raw }
    order.push(key)
  }
  return {
    byKey, order, cursor, bridgeOk: snapshot.bridge_ok !== false,
    uspecificeret: snapshot.uspecificeret ?? 0,
  }
}

function source(value: unknown): BackgroundJob['kilde'] {
  const raw = String(value || 'tool')
  return raw as BackgroundJob['kilde']
}

function startedJob(event: LiveJobEvent): BackgroundJob {
  const payload = event.payload ?? {}
  const supplied = payload.job
  if (supplied && typeof supplied === 'object') {
    return { ...(supplied as BackgroundJob), job_key: event.job_key }
  }
  const tool = String(payload.tool || 'Værktøj')
  const title = String(payload.title || payload.description || '').trim()
  const command = String(payload.command || '').trim()
  return {
    id: String(payload.tool_use_id || event.job_key || ''),
    job_key: event.job_key,
    kilde: source(event.source),
    navn: title || command || tool,
    kommando: command || tool,
    status: 'running',
    can_pause: false,
    can_stop: false,
  }
}

export function applyJobEvent(state: LiveJobsState, event: LiveJobEvent): LiveJobsState {
  if (event.type === 'heartbeat') return state
  if (event.type === 'snapshot') {
    return fromSnapshot({
      jobs: event.jobs ?? [], bridge_ok: event.bridge_ok !== false,
      uspecificeret: event.uspecificeret,
    }, event.cursor, state)
  }
  if (event.type === 'source_status') {
    const healthy = event.payload?.healthy !== false
    return { ...state, cursor: Math.max(state.cursor, event.cursor || 0), bridgeOk: healthy }
  }
  const key = String(event.job_key || '')
  if (!key) return state
  const byKey = { ...state.byKey }
  let order = state.order
  if (event.type === 'job_started') {
    const old = byKey[key]
    // Et job der allerede er SLUTTET må ikke genoplives af et replay.
    // Strømmen genoptager fra sin cursor efter et afbrudt forløb, og serveren
    // kan derfor sende `job_started` for et job hvis slutning vi allerede har
    // set. Uden denne vagt hoppede færdige server-jobs tilbage i «Kører» et
    // øjeblik — målt 12/10-2026: tre shells blinkede frem mens ingen skrev.
    if (old && erTerminal(old.status)) {
      return { ...state, cursor: Math.max(state.cursor, event.cursor || 0) }
    }
    byKey[key] = { ...startedJob(event), ...old, status: 'running', stale: false }
    if (!old) order = [...order, key]
  } else if (event.type === 'job_output') {
    const old = byKey[key] ?? startedJob(event)
    const seq = Number(event.payload?.seq)
    if (Number.isFinite(seq) && seq <= (old.liveOutputSeq ?? 0)) {
      return { ...state, cursor: Math.max(state.cursor, event.cursor || 0) }
    }
    const combined = `${old.liveOutput ?? ''}${String(event.payload?.chunk ?? '')}`
    const clipped = combined.length > OUTPUT_CAP
    byKey[key] = {
      ...old,
      job_key: key,
      liveOutput: clipped ? combined.slice(-OUTPUT_CAP) : combined,
      liveOutputSeq: Number.isFinite(seq) ? seq : old.liveOutputSeq,
      liveOutputTruncated: Boolean(old.liveOutputTruncated || event.payload?.truncated || clipped),
    }
    if (!state.byKey[key]) order = [...order, key]
  } else if (event.type === 'job_finished') {
    const old = byKey[key] ?? startedJob(event)
    const resultText = String(event.payload?.result_text || '')
    const status = String(event.payload?.status || 'exited')
    const exitCode = typeof event.payload?.exit_code === 'number' ? event.payload.exit_code : null
    const failed = ['error', 'failed', 'cancelled', 'timeout'].includes(status) ||
      (exitCode !== null && exitCode !== 0)
    byKey[key] = {
      ...old,
      job_key: key,
      status,
      exit_code: exitCode,
      error: failed ? (resultText || old.error) : undefined,
      finished_at: new Date().toISOString(),
    }
    if (!state.byKey[key]) order = [...order, key]
  }
  return { ...state, byKey, order, cursor: Math.max(state.cursor, event.cursor || 0) }
}
