import type { AccountProfile, ApiConfig, ChatMessage, ChatSession, Connector, ModelOption, VisibleProvider, WhoAmI } from './types'

export type ApiErrorKind = 'network' | 'auth' | 'rate_limit' | 'server' | 'unknown'

export class ApiError extends Error {
  constructor(
    public kind: ApiErrorKind,
    message: string,
    public statusCode: number | null = null
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

interface FetchOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  body?: unknown
}

/** Serverens egen forklaring, ellers statuskoden. Kaster aldrig. */
async function _forklaring(response: Response): Promise<string> {
  try {
    const krop = await response.json()
    const d = (krop as { detail?: unknown })?.detail
    if (typeof d === 'string' && d.trim()) return d.trim()
    if (Array.isArray(d) && d.length > 0) return String((d[0] as { msg?: string })?.msg ?? d[0])
  } catch {
    // ikke JSON, tom krop, eller allerede laest — statuskoden maa raekke
  }
  return `HTTP ${response.status}`
}

export async function apiFetch<T>(
  config: ApiConfig,
  path: string,
  options: FetchOptions = {}
): Promise<T> {
  const url = new URL(path, config.apiBaseUrl).toString()

  try {
    const response = await fetch(url, {
      method: options.method ?? 'GET',
      headers: {
        Accept: 'application/json',
        ...(options.body === undefined ? {} : { 'Content-Type': 'application/json' }),
        Authorization: `Bearer ${config.authToken}`
      },
      body: options.body === undefined ? undefined : JSON.stringify(options.body)
    })

    if (response.status === 401 || response.status === 403) {
      throw new ApiError('auth', `HTTP ${response.status}`, response.status)
    }

    if (response.status === 429) {
      throw new ApiError('rate_limit', 'Rate-limited', response.status)
    }

    if (response.status >= 500) {
      throw new ApiError('server', `HTTP ${response.status}`, response.status)
    }

    if (!response.ok) {
      // Serveren FORKLARER hvad der gik galt — FastAPI svarer med
      // {"detail": "..."} — men kroppen blev aldrig laest, saa brugeren fik
      // et tal. Set live: en godkendelse afvist som «stale and must be
      // recreated» viste sig som «HTTP 409» paa telefonen.
      // Best-effort: kan kroppen ikke laeses, falder vi tilbage til koden.
      throw new ApiError('unknown', await _forklaring(response), response.status)
    }

    return (await response.json()) as T
  } catch (error) {
    if (error instanceof ApiError) {
      throw error
    }

    throw new ApiError('network', error instanceof Error ? error.message : 'Network error')
  }
}

export async function whoami(config: ApiConfig): Promise<WhoAmI> {
  const raw = await apiFetch<{
    user_id?: string
    user_display_name?: string
    display_name?: string
    role?: string
  }>(config, '/api/whoami')

  return {
    user_id: raw.user_id ?? '',
    display_name: raw.display_name ?? raw.user_display_name ?? 'Bruger',
    role: raw.role === 'owner' || raw.role === 'member' || raw.role === 'guest' ? raw.role : 'guest'
  }
}

/**
 * Sessionerne — valgfrit kun den ene slags.
 *
 * `kind` UDELADT betyder ALT, ikke «chat». Serveren har samme regel, og de to
 * skal være enige: en klient der beder om alt, og en server der leverer chat,
 * ville vise en tom liste for én af fladerne uden at nogen af dem tog fejl.
 */
export async function listSessions(
  config: ApiConfig, kind?: 'chat' | 'code',
): Promise<ChatSession[]> {
  const sti = kind ? `/chat/sessions?kind=${encodeURIComponent(kind)}` : '/chat/sessions'
  const raw = await apiFetch<{ items?: ChatSession[]; sessions?: ChatSession[] } | ChatSession[]>(
    config,
    sti
  )

  if (Array.isArray(raw)) {
    return raw
  }

  return raw.items ?? raw.sessions ?? []
}

export async function createSession(
  config: ApiConfig,
  title = 'Ny samtale',
  kind: 'chat' | 'code' = 'chat'
): Promise<ChatSession> {
  const raw = await apiFetch<{ session?: ChatSession } | ChatSession>(config, '/chat/sessions', {
    method: 'POST',
    body: { title, kind }
  })

  if ('session' in raw && raw.session) {
    return raw.session
  }

  return raw as ChatSession
}

export async function getSession(
  config: ApiConfig,
  sessionId: string
): Promise<{ session: ChatSession; messages: ChatMessage[] }> {
  const raw = await apiFetch<{ session: ChatSession & { messages?: ChatMessage[] } }>(
    config,
    `/chat/sessions/${encodeURIComponent(sessionId)}`
  )

  return {
    session: raw.session,
    messages: raw.session.messages ?? []
  }
}

export async function cancelRun(config: ApiConfig, runId: string): Promise<void> {
  await apiFetch(config, `/chat/runs/${encodeURIComponent(runId)}/cancel`, {
    method: 'POST'
  })
}

export async function cancelRunById(config: ApiConfig, runId: string): Promise<void> {
  await cancelRun(config, runId)
}

export async function steerRun(config: ApiConfig, runId: string, content: string): Promise<void> {
  await apiFetch(config, `/chat/runs/${encodeURIComponent(runId)}/steer`, {
    method: 'POST',
    body: { content }
  })
}

/** Sessioner med et aktivt run lige nu (server-side). Bruges til at vise
 * "arbejder" og forhindre at man sender ind i et kørende svar (= nudge-swallow). */
/** Omdoeb en samtale. Serveren svarer med hele sessionen. */
export async function renameSession(
  config: ApiConfig, sessionId: string, title: string,
): Promise<void> {
  await apiFetch(config, `/chat/sessions/${encodeURIComponent(sessionId)}/rename`, {
    method: 'PUT',
    body: JSON.stringify({ title }),
  })
}

/** Slet en samtale. Uigenkaldeligt — kalderen spoerger foerst. */
export async function deleteSession(config: ApiConfig, sessionId: string): Promise<void> {
  await apiFetch(config, `/chat/sessions/${encodeURIComponent(sessionId)}`, {
    method: 'DELETE',
  })
}

/**
 * Fastgoer eller arkivér.
 *
 * Kun de felter man vil aendre sendes med: `undefined` betyder «roer ikke», og
 * serveren skelner. Ellers ville et kald der kun vil arkivere ogsaa frigoere
 * en fastgjort samtale.
 */
export async function setSessionFlags(
  config: ApiConfig, sessionId: string,
  flags: { pinned?: boolean; archived?: boolean },
): Promise<void> {
  await apiFetch(config, `/chat/sessions/${encodeURIComponent(sessionId)}/flags`, {
    method: 'PATCH',
    body: JSON.stringify(flags),
  })
}

export async function getActiveRuns(config: ApiConfig): Promise<string[]> {
  const data = await apiFetch<{ session_ids?: string[] }>(config, '/chat/active-runs')
  return data.session_ids ?? []
}

export interface ActiveRunSnapshot {
  sessionId: string
  runId: string
  status: string
  researchRunId?: string
  researchStatus?: string
  researchTier?: string
}

export async function getActiveRunSnapshot(config: ApiConfig): Promise<ActiveRunSnapshot[]> {
  const data = await apiFetch<{
    sessions?: {
      session_id?: string; run_id?: string; status?: string
      research_run_id?: string; research_status?: string; research_tier?: string
    }[]
  }>(config, '/chat/active-runs')
  return (data.sessions ?? []).map((item) => ({
    sessionId: String(item.session_id ?? ''),
    runId: String(item.run_id ?? ''),
    status: String(item.status ?? 'working'),
    researchRunId: item.research_run_id ? String(item.research_run_id) : undefined,
    researchStatus: item.research_status ? String(item.research_status) : undefined,
    researchTier: item.research_tier ? String(item.research_tier) : undefined,
  })).filter((item) => item.sessionId)
}

export interface PresenceDebugDevice {
  device_key: string
  platform: string
  foreground: boolean
  awake: boolean
  network: string
  device_name?: string
  active_session_id?: string
  battery_saver?: boolean
  ping_age_s?: number
  interaction_age_s?: number
  location?: unknown
}

export interface PresenceDebugSnapshot {
  devices: PresenceDebugDevice[]
  ranked: { device_key: string; platform: string; score: number; via: string }[]
  summary: string
}

export async function getPresenceDebug(config: ApiConfig): Promise<PresenceDebugSnapshot> {
  return apiFetch<PresenceDebugSnapshot>(config, '/presence/debug')
}

/** Afbryd det run der kører for en session (når appen ikke selv streamer det,
 * fx efter baggrund hvor serveren stadig arbejder). */
export async function cancelActiveRun(config: ApiConfig, sessionId: string): Promise<void> {
  await apiFetch(config, `/chat/sessions/${encodeURIComponent(sessionId)}/cancel-active`, {
    method: 'POST'
  })
}

export async function approveTool(config: ApiConfig, approvalId: string): Promise<void> {
  await apiFetch(config, `/chat/approvals/${encodeURIComponent(approvalId)}/approve`, {
    method: 'POST'
  })
}

export async function denyTool(config: ApiConfig, approvalId: string): Promise<void> {
  await apiFetch(config, `/chat/approvals/${encodeURIComponent(approvalId)}/deny`, {
    method: 'POST'
  })
}

export interface UploadedAttachment {
  id: string
}

/** Upload et billede (multipart) til en session → attachment_id.
 *  Bruger expo-file-system uploadAsync (robust multipart-fil-upload) i stedet
 *  for RN FormData+fetch, som fejler tavst klient-side på Android — requesten
 *  nåede aldrig serveren. Dynamisk import så native-modulet ikke loades i tests. */
export async function uploadAttachment(
  config: ApiConfig,
  sessionId: string,
  photo: { uri: string; name: string; mime: string },
  onProgress?: (percent: number) => void
): Promise<UploadedAttachment> {
  const FS = await import('expo-file-system/legacy')
  const url = new URL('/attachments/upload', config.apiBaseUrl).toString()
  const options: Parameters<typeof FS.uploadAsync>[2] = {
    httpMethod: 'POST' as const,
    uploadType: FS.FileSystemUploadType.MULTIPART,
    fieldName: 'file',
    mimeType: photo.mime,
    parameters: { session_id: sessionId },
    headers: { Accept: 'application/json', Authorization: `Bearer ${config.authToken}` }
  }
  const createUploadTask = (FS as typeof FS & {
    createUploadTask?: (
      url: string,
      fileUri: string,
      options: Parameters<typeof FS.uploadAsync>[2],
      callback: (data: { totalBytesSent?: number; totalBytesExpectedToSend?: number }) => void
    ) => { uploadAsync: () => Promise<{ status: number; body: string } | null | undefined> }
  }).createUploadTask
  const res = createUploadTask && onProgress
    ? await createUploadTask(url, photo.uri, options, (data) => {
        const total = Number(data.totalBytesExpectedToSend ?? 0)
        const sent = Number(data.totalBytesSent ?? 0)
        if (total > 0) onProgress(Math.max(1, Math.min(99, Math.round((sent / total) * 100))))
      }).uploadAsync()
    : await FS.uploadAsync(url, photo.uri, options)
  if (!res) {
    throw new ApiError('network', 'Upload blev afbrudt')
  }
  if (res.status >= 400) {
    throw new ApiError(res.status === 401 ? 'auth' : 'server', `HTTP ${res.status}: ${(res.body || '').slice(0, 160)}`, res.status)
  }
  try {
    return JSON.parse(res.body) as UploadedAttachment
  } catch {
    throw new ApiError('server', 'Ugyldigt upload-svar')
  }
}

export async function getAccountMe(config: ApiConfig): Promise<AccountProfile> {
  return apiFetch<AccountProfile>(config, '/account/me')
}

export async function getModelOptions(config: ApiConfig): Promise<ModelOption[]> {
  // Owner-only endpoint; member/guest får 403 → tom liste (skjuler pillen).
  let raw: { providers?: VisibleProvider[] }
  try {
    raw = await apiFetch<{ providers?: VisibleProvider[] }>(config, '/chat/visible-providers')
  } catch {
    return []
  }
  const out: ModelOption[] = []
  for (const p of raw.providers ?? []) {
    for (const model of p.models ?? []) {
      out.push({ provider: p.id, model, label: `${p.id} · ${model}` })
    }
  }
  return out
}

export async function listConnectors(config: ApiConfig): Promise<Connector[]> {
  const raw = await apiFetch<{ connectors?: Connector[] }>(config, '/api/connectors')
  return raw.connectors ?? []
}

export async function setConnectorEnabled(
  config: ApiConfig,
  connectorId: string,
  enabled: boolean
): Promise<void> {
  await apiFetch(config, `/api/connectors/${encodeURIComponent(connectorId)}/enabled`, {
    method: 'POST',
    body: { enabled }
  })
}

export async function health(apiBaseUrl: string): Promise<boolean> {
  const url = new URL('/health', apiBaseUrl).toString()
  const response = await fetch(url, {
    headers: {
      Accept: 'application/json'
    }
  })

  return response.ok
}

export interface GoogleLoginStartResult {
  authorize_url?: string
  nonce?: string
  error?: string
}

export interface GoogleLoginResult {
  status: 'pending' | 'ok' | 'error' | 'unknown' | string
  token?: string
  role?: string
  user_id?: string
  error?: string
}

export interface PairRedeemResult {
  status?: string
  token?: string
  user_id?: string
  role?: string
  error?: string
}

/** Indløs en QR-pairing-kode → friskt token. PUBLIC (mobilen har intet token endnu). */
export async function redeemPairingCode(apiBaseUrl: string, code: string): Promise<PairRedeemResult> {
  const url = new URL('/api/auth/pair/redeem', apiBaseUrl).toString()
  const response = await fetch(url, {
    method: 'POST',
    headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
    body: JSON.stringify({ code })
  })
  return (await response.json()) as PairRedeemResult
}

export async function googleLoginStart(
  apiBaseUrl: string,
  appId = 'jarvis-mobile'
): Promise<GoogleLoginStartResult> {
  const url = new URL(
    `/api/auth/google/start?app_id=${encodeURIComponent(appId)}`,
    apiBaseUrl
  ).toString()
  const response = await fetch(url)
  return (await response.json()) as GoogleLoginStartResult
}

export async function googleLoginResult(
  apiBaseUrl: string,
  nonce: string
): Promise<GoogleLoginResult> {
  const url = new URL(
    `/api/auth/google/result?nonce=${encodeURIComponent(nonce)}`,
    apiBaseUrl
  ).toString()
  const response = await fetch(url)
  return (await response.json()) as GoogleLoginResult
}

export async function googleLinkStart(config: ApiConfig): Promise<GoogleLoginStartResult> {
  return apiFetch(config, '/api/auth/google/link/start')
}

export interface ContextUsage {
  /** Transcript-fyld siden sidste compaction. Backend-autoritativt. */
  tokens: number
  /** Tallet der komprimeres ved. Nævneren i ringen. */
  compactAt: number
  compacting: boolean
}

/**
 * Hvor fuld er samtalens kontekst?
 *
 * ## Hvorfor den IKKE regnes ud i klienten
 *
 * Desk prøvede det først og fik en ring der skøjtede: den blev fodret af
 * `stream.usage.input + cacheHit`, altså HELE prompten inklusive
 * systemprompten. Den viste derfor et tal der aldrig faldt når compaction
 * fyrede, fordi systemprompten bliver ved med at være der.
 *
 * `/chat/context-usage` svarer med transcript-fyldet siden sidste compaction
 * — tallet der faktisk falder. Den lektie er allerede betalt én gang; den
 * gentages ikke her.
 */
export async function getContextUsage(
  config: ApiConfig, sessionId: string,
): Promise<ContextUsage | null> {
  if (!sessionId) return null
  const data = await apiFetch<{
    tokens?: number; compact_at?: number; effective?: number; compacting?: boolean
  }>(config, `/chat/context-usage?session_id=${encodeURIComponent(sessionId)}`)
  // `effective` FOERST: serveren regner den som min(model_window, compact_at),
  // altsaa den graense der faktisk fyrer. De to er identiske her fordi
  // klienten ikke sender provider/model - men den dag den goer, er `effective`
  // den rigtige, og `compact_at` ville tegne en ring der naaede 80 % og saa
  // blev komprimeret.
  const compactAt = Number(data.effective ?? data.compact_at ?? 0)
  return {
    tokens: Number(data.tokens ?? 0),
    compactAt,
    compacting: Boolean(data.compacting),
  }
}

/**
 * Komprimér samtalen NU frem for at vente på at grænsen nås.
 *
 * Den hører sammen med ringen: ringen fortæller at det snart sker, og det her
 * er den eneste handling ringen inviterer til. Uden den er ringen en advarsel
 * man ikke kan gøre noget ved.
 */
export async function compactNow(
  config: ApiConfig, sessionId: string, focus = '',
): Promise<{ started: boolean; reason?: string }> {
  return apiFetch(config, '/chat/compact-now', {
    method: 'POST',
    body: { session_id: sessionId, focus },
  })
}

export interface GitStatus {
  branch: string
  /** Antal filer med ændringer. «73 filer ændret». */
  dirty: number
  added: number
  removed: number
  isGit: boolean
  repo: string
  host: string
}

/**
 * Arbejdstræets tilstand — branch, antal berørte filer og linjer ind/ud.
 *
 * ## Hvad tallene FAKTISK er
 *
 * `git diff --numstat HEAD` på arbejdstræet: det der er ændret og endnu ikke
 * committet. Det er IKKE et regnskab over hvad netop denne samtale har lavet
 * — et sådant findes ikke, og et tal der lod som om det gjorde, ville lyve så
 * snart to ting arbejdede i samme repo.
 *
 * Det er stadig det rigtige tal at vise: når Jarvis er midt i en opgave, er
 * arbejdstræet præcis dét arbejde. Er der committet, står badgen på nul —
 * og det er en sand besked, ikke en tom.
 */
export async function getGitStatus(
  config: ApiConfig, kind = 'container', root = '',
): Promise<GitStatus | null> {
  const qs = new URLSearchParams({ kind, root }).toString()
  const d = await apiFetch<{
    branch?: string; dirty?: number; added?: number; removed?: number
    is_git?: boolean; repo?: string; host?: string
  }>(config, `/chat/git-status?${qs}`)
  if (!d.is_git) return null
  return {
    branch: String(d.branch || ''),
    dirty: Number(d.dirty || 0),
    added: Number(d.added || 0),
    removed: Number(d.removed || 0),
    isGit: true,
    repo: String(d.repo || ''),
    host: String(d.host || ''),
  }
}
