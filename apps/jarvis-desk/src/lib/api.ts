/**
 * REST API klient for jarvis-desk.
 *
 * Robust HTTP-call wrapper med:
 *   - Typed StreamError-bevidst error-håndtering
 *   - Bearer-token i header (aldrig URL)
 *   - Timeout (10s default, configurable per call)
 *   - Auto-retry på transient fejl (network/5xx) op til 2x
 */
import { StreamError } from './streamClient'
import type { ContentBlock } from './sseProtocol'
import { messageToBlocks } from './normalizeMessage'

export interface ChatSession {
  id: string
  title: string
  updated_at: string
  message_count?: number
  workspace_kind?: string | null
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'tool' | 'system' | 'approval_request'
  content: ContentBlock[]       // ændret fra string — understøtter tool_use/image
  created_at: string
  parent_id?: string | null     // branch-søm
}

export interface WhoAmI {
  user_id: string
  display_name: string
  role: 'owner' | 'member' | 'guest'
}

export interface ApiConfig {
  apiBaseUrl: string
  authToken: string | null
}

interface FetchOptions {
  method?: 'GET' | 'POST' | 'DELETE' | 'PATCH' | 'PUT'
  body?: unknown
  timeoutMs?: number
  retries?: number
  signal?: AbortSignal
}

export async function apiFetch<T>(
  config: ApiConfig,
  path: string,
  options: FetchOptions = {},
): Promise<T> {
  const {
    method = 'GET',
    body,
    timeoutMs = 10_000,
    retries = 2,
    signal,
  } = options

  const url = new URL(path, config.apiBaseUrl).toString()
  const headers: Record<string, string> = {
    Accept: 'application/json',
  }
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  if (config.authToken) headers.Authorization = `Bearer ${config.authToken}`

  let lastError: StreamError | null = null
  for (let attempt = 0; attempt <= retries; attempt++) {
    const timeoutController = new AbortController()
    const timeoutId = setTimeout(() => timeoutController.abort(), timeoutMs)

    // Hvis bruger har egen abort, link den.
    const onUserAbort = () => timeoutController.abort()
    signal?.addEventListener('abort', onUserAbort)

    try {
      const res = await fetch(url, {
        method,
        headers,
        body: body !== undefined ? JSON.stringify(body) : undefined,
        signal: timeoutController.signal,
      })
      clearTimeout(timeoutId)
      signal?.removeEventListener('abort', onUserAbort)

      if (res.status === 401 || res.status === 403) {
        throw new StreamError('auth', `HTTP ${res.status}`, {
          retryable: false,
          statusCode: res.status,
        })
      }
      if (res.status === 429) {
        throw new StreamError('rate_limit', 'Rate-limited', {
          retryable: true,
          statusCode: 429,
        })
      }
      if (res.status >= 500) {
        throw new StreamError('server', `HTTP ${res.status}`, {
          retryable: true,
          statusCode: res.status,
        })
      }
      if (!res.ok) {
        const text = await res.text().catch(() => '')
        throw new StreamError('unknown', `HTTP ${res.status}: ${text.slice(0, 200)}`, {
          retryable: false,
          statusCode: res.status,
        })
      }
      return (await res.json()) as T
    } catch (e) {
      clearTimeout(timeoutId)
      signal?.removeEventListener('abort', onUserAbort)

      if ((e as Error).name === 'AbortError') {
        if (signal?.aborted) {
          throw new StreamError('cancelled', 'Cancelled by user', { retryable: false })
        }
        // Timeout
        lastError = new StreamError('network', `Timeout efter ${timeoutMs}ms`, {
          retryable: true,
          context: { url, attempt },
        })
      } else if (e instanceof StreamError) {
        lastError = e
      } else {
        lastError = new StreamError(
          'network',
          `Netværksfejl: ${(e as Error).message}`,
          { retryable: true, context: { url, attempt } },
        )
      }

      if (!lastError.retryable || attempt === retries) {
        throw lastError
      }

      // Exponential backoff for retries.
      await new Promise((r) => setTimeout(r, 250 * (attempt + 1) ** 2))
    }
  }

  throw lastError ?? new StreamError('unknown', 'Ukendt fejl', {})
}

export async function listSessions(config: ApiConfig): Promise<ChatSession[]> {
  const data = await apiFetch<
    { items: ChatSession[] } | { sessions: ChatSession[] } | ChatSession[]
  >(config, '/chat/sessions')
  // Backend kan returnere enten array eller wrapped object — håndter alle:
  //   - direkte array
  //   - {sessions: [...]}
  //   - {items: [...]}  (faktisk format Jarvis bruger)
  if (Array.isArray(data)) return data
  if ('items' in data) return data.items
  if ('sessions' in data) return data.sessions
  return []
}

export interface SessionSearchResult {
  session_id: string
  title: string
  snippet: string
  updated_at?: string
}

/** Søg sessioner på titel + besked-indhold (#5). Returnerer tomt array ved
 *  tom query. */
export async function searchSessions(
  config: ApiConfig,
  query: string,
): Promise<SessionSearchResult[]> {
  const q = query.trim()
  if (!q) return []
  const data = await apiFetch<{ items: SessionSearchResult[] }>(
    config, `/chat/sessions/search?q=${encodeURIComponent(q)}`,
  )
  return data.items ?? []
}

export async function getSession(
  config: ApiConfig,
  sessionId: string,
): Promise<{ session: ChatSession; messages: ChatMessage[] }> {
  // Server returnerer { session: { ...session, messages: [...] } } hvor hver
  // beskeds content er en markdown-string. Vi normaliserer til ContentBlock[]
  // så streamede og loadede beskeder deler samme rendering-pipeline.
  const raw = await apiFetch<{
    session: ChatSession & {
      messages?: Array<{ id: string; role: ChatMessage['role']; content: string; content_json?: unknown; created_at: string; parent_id?: string | null }>
    }
  }>(config, `/chat/sessions/${encodeURIComponent(sessionId)}`)
  const session = raw.session
  const messages: ChatMessage[] = (session?.messages ?? []).map((m) => ({
    id: m.id,
    role: m.role,
    created_at: m.created_at,
    parent_id: m.parent_id ?? null,
    content: messageToBlocks(m),
  }))
  return { session, messages }
}

export async function createSession(
  config: ApiConfig,
  title: string,
): Promise<ChatSession> {
  // Serveren returnerer { session: {...} } — unwrap så .id ikke bliver undefined.
  const raw = await apiFetch<{ session: ChatSession } | ChatSession>(config, '/chat/sessions', {
    method: 'POST',
    body: { title },
  })
  return (raw as { session?: ChatSession }).session ?? (raw as ChatSession)
}

export async function renameSession(config: ApiConfig, sessionId: string, title: string): Promise<void> {
  await apiFetch(config, `/chat/sessions/${encodeURIComponent(sessionId)}/rename`, {
    method: 'PUT',
    body: { title },
  })
}

export async function deleteSession(config: ApiConfig, sessionId: string): Promise<void> {
  await apiFetch(config, `/chat/sessions/${encodeURIComponent(sessionId)}`, { method: 'DELETE' })
}

/** Manuel compaction (Claude-Code-stil /compact). Udløser den samme baggrunds-motor NU,
 *  uanset attention-budget. `focus` styrer valgfrit hvad summary'en prioriterer. */
export async function compactNow(
  config: ApiConfig,
  sessionId: string,
  focus = '',
): Promise<{ started: boolean; reason: string; focus?: string }> {
  return apiFetch(config, '/chat/compact-now', {
    method: 'POST',
    body: { session_id: sessionId, focus },
  })
}

/** Prewarm-on-return: varm sessionens DeepSeek-prefix-cache når brugeren vender
 *  tilbage (composer-fokus), så første besked efter en pause rammer cachen i stedet
 *  for cold prefill (~32k tokens = de oplevede >10s). Fire-and-forget: aldrig await'et
 *  på send-stien, fejl sluges (best-effort). Serveren throttler pr. session (45s) og
 *  no-op'er for ikke-owner/ikke-deepseek. Gælder BÅDE chat- og code-view. */
export async function warmSession(
  config: ApiConfig,
  sessionId: string,
  opts: { provider?: string; model?: string } = {},
): Promise<void> {
  if (!sessionId) return
  try {
    await apiFetch(config, '/chat/warm', {
      method: 'POST',
      body: {
        session_id: sessionId,
        provider_choice: opts.provider || 'deepseek',
        model: opts.model || 'deepseek-v4-flash',
      },
    })
  } catch {
    /* best-effort — en warm-fejl må aldrig påvirke chatten */
  }
}

/** Upload en fil (drag/drop eller fil-vælger) → returnerer attachment_id.
 *  Serveren kræver session_id (Form-felt) og validerer at sessionen findes. */
export async function uploadAttachment(
  config: ApiConfig,
  file: File,
  sessionId: string,
): Promise<{ id: string; filename?: string; mime_type?: string }> {
  const url = new URL('/attachments/upload', config.apiBaseUrl).toString()
  const form = new FormData()
  form.append('file', file, file.name)
  form.append('session_id', sessionId)
  const headers: Record<string, string> = {}
  if (config.authToken) headers.Authorization = `Bearer ${config.authToken}`
  const res = await fetch(url, { method: 'POST', headers, body: form })
  if (!res.ok) throw new StreamError('unknown', `Upload fejlede: HTTP ${res.status}`, { retryable: false })
  return res.json() as Promise<{ id: string; filename?: string; mime_type?: string }>
}

/** Send optaget lyd til /transcribe (lokal faster-whisper) → tekst. */
export async function transcribeAudio(
  config: ApiConfig,
  blob: Blob,
  filename = 'dictation.webm',
): Promise<{ status: string; text: string; language?: string; error?: string }> {
  const url = new URL('/transcribe', config.apiBaseUrl).toString()
  const form = new FormData()
  form.append('file', blob, filename)
  const headers: Record<string, string> = {}
  if (config.authToken) headers.Authorization = `Bearer ${config.authToken}`
  const res = await fetch(url, { method: 'POST', headers, body: form })
  if (!res.ok) throw new StreamError('unknown', `Transskription fejlede: HTTP ${res.status}`, { retryable: false })
  return res.json() as Promise<{ status: string; text: string; language?: string; error?: string }>
}

/** Send tekst til /api/tts/synthesize → MP3-Blob (ElevenLabs primær, edge-tts fallback). */
export async function synthesizeTts(
  config: ApiConfig,
  text: string,
  opts?: { provider?: 'auto' | 'elevenlabs' | 'edge' },
): Promise<{ blob: Blob; provider: string }> {
  const url = new URL('/api/tts/synthesize', config.apiBaseUrl).toString()
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (config.authToken) headers.Authorization = `Bearer ${config.authToken}`
  const res = await fetch(url, {
    method: 'POST',
    headers,
    body: JSON.stringify({ text, provider: opts?.provider ?? 'auto' }),
  })
  if (!res.ok) throw new StreamError('unknown', `TTS fejlede: HTTP ${res.status}`, { retryable: false })
  const provider = res.headers.get('X-TTS-Provider') || 'unknown'
  return { blob: await res.blob(), provider }
}

export interface ImageAttachment {
  attachment_id: string
  session_id: string
  filename: string
  mime_type: string
  created_at?: string
}

/** Galleri-liste (#6): billed-attachments på tværs af sessioner. */
export async function listImages(config: ApiConfig): Promise<ImageAttachment[]> {
  const data = await apiFetch<{ items: ImageAttachment[] }>(config, '/attachments/images')
  return data.items ?? []
}

/** Hent et billede som object-URL (med Bearer-token, som <img> ikke selv kan
 *  sende). Kalderen skal URL.revokeObjectURL() når billedet ikke skal bruges. */
export async function fetchImageObjectUrl(
  config: ApiConfig,
  attachmentId: string,
): Promise<string> {
  const url = new URL(`/attachments/image/${encodeURIComponent(attachmentId)}`, config.apiBaseUrl).toString()
  const headers: Record<string, string> = {}
  if (config.authToken) headers.Authorization = `Bearer ${config.authToken}`
  const res = await fetch(url, { headers })
  if (!res.ok) throw new StreamError('unknown', `Billede fejlede: HTTP ${res.status}`, { retryable: false })
  return URL.createObjectURL(await res.blob())
}

export interface TreeEntry { name: string; kind: 'dir' | 'file' }
/** Mappe-listing til Code-mode fil-træ. */
export async function getTree(
  config: ApiConfig, kind: 'container' | 'workstation', root: string, path: string,
): Promise<TreeEntry[]> {
  const qs = `kind=${encodeURIComponent(kind)}&root=${encodeURIComponent(root)}&path=${encodeURIComponent(path)}`
  const data = await apiFetch<{ entries: TreeEntry[] }>(config, `/chat/tree?${qs}`)
  return data.entries ?? []
}

export interface GitStatus {
  branch: string
  dirty: number
  added: number
  removed: number
  is_git: boolean
}

/** Git-state for det aktive code-workspace (header-chip). */
export async function getGitStatus(
  config: ApiConfig, kind: 'container' | 'workstation', root: string,
): Promise<GitStatus> {
  const qs = `kind=${encodeURIComponent(kind)}&root=${encodeURIComponent(root)}`
  return apiFetch(config, `/chat/git-status?${qs}`)
}

export interface GitTarget { kind: string; root: string }

/** Google app-login (§12): start → få authorize-URL + nonce (ingen auth). */
export async function googleLoginStart(
  apiBaseUrl: string, appId = '',
): Promise<{ authorize_url?: string; nonce?: string; error?: string }> {
  const url = new URL(`/api/auth/google/start?app_id=${encodeURIComponent(appId)}`, apiBaseUrl).toString()
  const r = await fetch(url)
  return r.json()
}

/** Poll login-resultatet. {status: pending|ok|error|unknown}. */
export async function googleLoginResult(
  apiBaseUrl: string, nonce: string,
): Promise<{ status: string; token?: string; role?: string; user_id?: string; error?: string }> {
  const url = new URL(`/api/auth/google/result?nonce=${encodeURIComponent(nonce)}`, apiBaseUrl).toString()
  const r = await fetch(url)
  return r.json()
}

/** Start Google-linking for indlogget bruger (migration: knyt Gmail). Kræver auth. */
export async function googleLinkStart(
  config: ApiConfig,
): Promise<{ authorize_url?: string; nonce?: string; error?: string }> {
  return apiFetch(config, '/api/auth/google/link/start')
}

/** Opret kort-levende QR-pairing-kode (mobil-companion scanner den). Auth kræves. */
export async function createPairing(
  config: ApiConfig,
): Promise<{ status?: string; code?: string; expires_in?: number; error?: string }> {
  return apiFetch(config, '/api/auth/pair/create', { method: 'POST', body: {} })
}

/** Poll pairing-status: pending=QR vist, redeemed=mobil tilsluttet, expired=udløbet. */
export async function getPairStatus(
  config: ApiConfig, code: string,
): Promise<{ state?: 'pending' | 'redeemed' | 'expired' }> {
  return apiFetch(config, `/api/auth/pair/status?code=${encodeURIComponent(code)}`)
}

/** Commit ALLE ændringer (git add -A + commit, ingen push). Rolle-aware target. */
export async function commitAllChanges(
  config: ApiConfig, target: GitTarget, message = '',
): Promise<{ status: string; sha?: string; branch?: string; message?: string }> {
  return apiFetch(config, '/chat/git/commit-all', { method: 'POST', body: { target, message } })
}

/** Opret pull request (commit + push + PR via GitHub-API/gh). Udadvendt — kun ved
 *  bruger-klik. Returnerer PR-URL. */
export async function createPullRequest(
  config: ApiConfig, target: GitTarget, title = '', body = '',
): Promise<{ status: string; url?: string; branch?: string; via?: string }> {
  return apiFetch(config, '/chat/git/create-pr', { method: 'POST', body: { target, title, body } })
}

/** Er et workspace betroet (skrive/exec-gate i code-mode)? */
export async function getWorkspaceTrust(
  config: ApiConfig, kind: 'container' | 'workstation', root: string,
): Promise<boolean> {
  const qs = `kind=${encodeURIComponent(kind)}&root=${encodeURIComponent(root)}`
  const data = await apiFetch<{ trusted: boolean }>(config, `/chat/workspace-trust?${qs}`)
  return !!data.trusted
}

/** Markér/afmarkér et workspace som betroet. */
export async function setWorkspaceTrust(
  config: ApiConfig, kind: 'container' | 'workstation', root: string, trusted: boolean,
): Promise<boolean> {
  const data = await apiFetch<{ trusted: boolean }>(config, '/chat/workspace-trust', {
    method: 'POST',
    body: { kind, root, trusted },
  })
  return !!data.trusted
}

/** Godkend et afventende tool-kald (code/cowork approval). */
export async function approveTool(config: ApiConfig, approvalId: string): Promise<void> {
  await apiFetch(config, `/chat/approvals/${encodeURIComponent(approvalId)}/approve`, { method: 'POST' })
}

/** Afvis et afventende tool-kald. */
export async function denyTool(config: ApiConfig, approvalId: string): Promise<void> {
  await apiFetch(config, `/chat/approvals/${encodeURIComponent(approvalId)}/deny`, { method: 'POST' })
}

/** Sessioner med et aktivt visible-run lige nu (#8 — også autonome runs). */
export async function getActiveRuns(config: ApiConfig): Promise<string[]> {
  const data = await apiFetch<{ session_ids: string[] }>(config, '/chat/active-runs')
  return data.session_ids ?? []
}

// ─── Den Intelligente Central — real-time owner-vindue (code mode) ───────────
export interface CentralFeedItem {
  cluster: string; nerve: string; kind: string; decision: string
  reason: string; run_id: string; security: boolean
}
export interface CentralIncident {
  cluster: string; nerve: string; kind: string; severity: string; message: string; ts: string
}
export interface CentralClusterStatus {
  cluster: string; status: 'green' | 'yellow' | 'red' | 'idle'; security: boolean
}
export interface CentralAnomaly {
  signature: string; category: string; importance: string; source: string
  count: number; first_seen: string; last_seen: string; sample: string
}
export interface CentralSnapshot {
  status: 'green' | 'yellow' | 'red'
  coverage: { nerves?: number; clusters?: number; security_clusters?: number; trace_buffer?: number }
  diagnose: { decide_ok?: boolean; observe_ok?: boolean; degraded?: boolean }
  feed: CentralFeedItem[]
  incidents: CentralIncident[]
  open_breakers: string[]
  config_drift: { declared_port?: unknown; actual_port?: unknown } | null
  clusters?: CentralClusterStatus[]
  anomalies?: { counts?: Record<string, number>; recent?: CentralAnomaly[] }
  processes?: { process: string; degraded?: boolean; open_breakers?: string[] }[]
  learning: {
    degrading?: { target: string; rate_hr?: number }[]
    autonomy?: string
    autonomy_reason?: string
    proposals?: number
    root_causes?: { target: string; count: number }[]
  }
}

/** Snapshot af Centralens live-tilstand (owner-only; 403 for ikke-ejere). */
export async function getCentralRealtime(config: ApiConfig): Promise<CentralSnapshot> {
  return apiFetch<CentralSnapshot>(config, '/central/realtime')
}

/** Live owner-terminal ind i Centralen: kør en kommando-linje, få terminal-linjer retur. */
export async function runCentralCommand(
  config: ApiConfig, line: string,
): Promise<{ ok: boolean; command: string; lines: string[] }> {
  return apiFetch(config, '/central/command', { method: 'POST', body: { line } })
}

/** Fuldt diagnostik-data til Central-HUD'ens Diagnostik-mode (incidents/anomalier/silent-
 *  failures/rod-årsager). Owner-only. */
export interface CentralDiagnostics {
  incidents: { severity: string; kind: string; cluster: string; nerve: string; message: string; ts: string; run_id?: string }[]
  anomalies: { signature: string; importance: string; category: string; count: number; sample: string; last_seen: string; location?: string }[]
  instrument: { kind: string; severity: string; score: number; file: string; line: number; snippet: string }[]
  root_causes: { cluster: string; nerve: string; count: number }[]
  degrading: { cluster: string; nerve: string; recent_rate_hr?: number }[]
}
export async function getCentralDiagnostics(config: ApiConfig): Promise<CentralDiagnostics> {
  return apiFetch(config, '/central/diagnostics')
}

/** Provider-helbred til Central-HUD'en (læser gemt ping-snapshot — billigt). */
export interface CentralProvider { provider: string; ok: boolean; degraded: boolean; latency_ms: number; model_count: number }
export async function getCentralProviders(
  config: ApiConfig,
): Promise<{ providers: CentralProvider[]; dry_cheap: string[]; summary: string }> {
  return apiFetch(config, '/central/providers')
}

/** Jarvis Mind-hub (Centralen som ÉT samlingspunkt). Uden section → index af alle faner. */
export interface MindIndexEntry { section: string; label: string; ready: boolean }
export async function getMindIndex(config: ApiConfig): Promise<{ index: MindIndexEntry[] }> {
  return apiFetch(config, '/central/mind')
}
/** Én Jarvis Mind-sektions projektion (læst fra Centralens cachede kilde — ét ground truth). */
export async function getMindSection(
  config: ApiConfig, section: string,
): Promise<Record<string, unknown>> {
  return apiFetch(config, `/central/mind?section=${encodeURIComponent(section)}`)
}

/** SSE-live-feed af nerve-fyringer (ægte realtid). fetch-baseret (EventSource kan ikke
 *  sende Authorization). onItem pr. fyring. Returnér {abort}. */
export function streamCentral(
  config: ApiConfig,
  onItem: (item: CentralFeedItem) => void,
  onError?: () => void,
): { abort: () => void } {
  const ctrl = new AbortController()
  const run = async () => {
    const url = new URL('/central/stream', config.apiBaseUrl).toString()
    const headers: Record<string, string> = { Accept: 'text/event-stream' }
    if (config.authToken) headers.Authorization = `Bearer ${config.authToken}`
    let resp: Response
    try { resp = await fetch(url, { headers, signal: ctrl.signal }) } catch { onError?.(); return }
    if (!resp.ok || !resp.body) { onError?.(); return }
    const reader = resp.body.getReader()
    const dec = new TextDecoder()
    let buf = ''
    try {
      for (;;) {
        const { value, done } = await reader.read()
        if (done) break
        buf += dec.decode(value, { stream: true })
        let i: number
        while ((i = buf.indexOf('\n\n')) !== -1) {
          const block = buf.slice(0, i); buf = buf.slice(i + 2)
          for (const line of block.split('\n')) {
            if (line.startsWith('data:')) {
              try { onItem(JSON.parse(line.slice(5).trim()) as CentralFeedItem) } catch { /* skip */ }
            }
          }
        }
      }
    } catch { /* aborted/network */ } finally {
      try { reader.releaseLock() } catch { /* noop */ }
      onError?.()
    }
  }
  void run()
  return { abort: () => ctrl.abort() }
}

export interface CentralNerveDetail {
  nerve: string; cluster: string; security: boolean; location: string
  enabled: boolean; recent: CentralFeedItem[]
}
export async function getCentralNerve(config: ApiConfig, nerve: string): Promise<CentralNerveDetail> {
  return apiFetch<CentralNerveDetail>(config, `/central/nerve/${encodeURIComponent(nerve)}`)
}
export async function toggleCentralNerve(config: ApiConfig, nerve: string, enabled: boolean): Promise<unknown> {
  return apiFetch(config, `/central/nerve/${encodeURIComponent(nerve)}/toggle?enabled=${enabled}`, { method: 'POST' })
}

/** Token-stream det aktive autonome run i en session (desk-pickup af wakeup).
 *  GET SSE → v2-events til onEvent. Kortlivet (ingen reconnect): når runnet er
 *  færdigt lukker serveren, og onDone kaldes. Lader ChatView vise Jarvis'
 *  wakeup-svar token-for-token i stedet for at "dumpe" det ind. */
export function followRun(
  config: ApiConfig,
  sessionId: string,
  onEvent: (ev: import('./sseProtocol').StreamEvent) => void,
  onDone: () => void,
): { abort: () => void } {
  const ctrl = new AbortController()
  const run = async () => {
    const url = new URL(`/chat/sessions/${encodeURIComponent(sessionId)}/live`, config.apiBaseUrl).toString()
    const headers: Record<string, string> = { Accept: 'text/event-stream' }
    if (config.authToken) headers.Authorization = `Bearer ${config.authToken}`
    let resp: Response
    try { resp = await fetch(url, { headers, signal: ctrl.signal }) } catch { onDone(); return }
    if (!resp.ok || !resp.body) { onDone(); return }
    const reader = resp.body.getReader()
    const dec = new TextDecoder()
    let buf = ''
    try {
      for (;;) {
        const { value, done } = await reader.read()
        if (done) break
        buf += dec.decode(value, { stream: true })
        let i: number
        while ((i = buf.indexOf('\n\n')) !== -1) {
          const block = buf.slice(0, i); buf = buf.slice(i + 2)
          if (!block.trim()) continue
          let data = ''
          for (const line of block.split('\n')) {
            if (line.startsWith('data:')) data += (data ? '\n' : '') + line.slice(5).trimStart()
          }
          if (!data) continue
          try { onEvent(JSON.parse(data) as import('./sseProtocol').StreamEvent) } catch { /* skip malformet */ }
        }
      }
    } catch { /* aborted/network */ } finally {
      try { reader.releaseLock() } catch { /* noop */ }
      onDone()
    }
  }
  void run()
  return { abort: () => ctrl.abort() }
}

/** Kontekst-tærskler til composer-ringen (#9). compact_at = autocompact-punkt. */
export async function getContextInfo(
  config: ApiConfig,
): Promise<{ compact_at: number; run_compact_at: number }> {
  return apiFetch(config, '/chat/context-info')
}

/** Ægte context-ring pr. provider/model: 'effective' = det første loft der rammer
 *  (modellens vindue vs. autocompact). Bruges som ring-nævner. */
export async function getModelContext(
  config: ApiConfig, provider: string, model: string,
): Promise<{ window: number; compact_at: number; effective: number }> {
  const qs = `provider=${encodeURIComponent(provider)}&model=${encodeURIComponent(model)}`
  return apiFetch(config, `/chat/model-context?${qs}`)
}

/** Jarvis Mind (cowork owner-menu): cognitive-arkitektur — de ~70 surfaces (server-cachet 75s).
 *  systems = [{system, active, summary}]; surfaces = den fulde dict. */
export async function getCognitiveArchitecture(
  config: ApiConfig,
): Promise<{ systems?: { system: string; active: boolean; summary?: string }[]; active_count?: number; total_count?: number; summary?: string; surfaces?: Record<string, unknown> }> {
  return apiFetch(config, '/mc/cognitive-architecture')
}

/** Jarvis Mind: runtime-oversigt (aktive runs, seneste events, approvals, valgt model). */
export async function getMcOverview(
  config: ApiConfig,
): Promise<Record<string, unknown>> {
  return apiFetch(config, '/mc/overview')
}

/** Session-milepæle (kapitler) til navigations-rail'en — som Claude Code's mark_chapter.
 *  Hvert anker = en user-besked der starter et kapitel + en kort titel. Cached server-side. */
export async function getSessionMilestones(
  config: ApiConfig, sessionId: string,
): Promise<{ milestones: { anchor_id: string; title: string }[] }> {
  const qs = new URLSearchParams({ session_id: sessionId }).toString()
  return apiFetch(config, `/chat/session-milestones?${qs}`)
}

/** ÆGTE kontekst-fyld for en session (backend-autoritativt): `tokens` = estimat af det
 *  faktiske transcript siden sidste compact — præcis det autocompact måler mod. Persistent
 *  + harmonerer med compaction (vokser mod loftet, falder når den fyrer). `compacting` =
 *  baggrunds-compaction kører nu (til liveness-indikatoren). */
export async function getContextUsage(
  config: ApiConfig, sessionId: string, provider = '', model = '',
): Promise<{ tokens: number; compact_at: number; effective: number; model_window: number; overhead_tokens: number; compacting: boolean; compacted: boolean }> {
  const qs = new URLSearchParams({ session_id: sessionId, provider, model }).toString()
  return apiFetch(config, `/chat/context-usage?${qs}`)
}

/** Læs en fil til preview-panelet. `root` er navngivet server-root (owner:
 *  repo/jarvis-v2/workspace, member: workspace) / workstation trusted folder;
 *  `path` er rel inde i det root. */
export async function getFile(
  config: ApiConfig,
  root: string,
  path: string,
  kind: 'container' | 'workstation' = 'container',
): Promise<{ path: string; content: string; language: string }> {
  const qs = `root=${encodeURIComponent(root)}&path=${encodeURIComponent(path)}&kind=${encodeURIComponent(kind)}`
  return apiFetch(config, `/chat/file?${qs}`)
}

/** Gem en redigeret fil (in-app editor). Rolle-scopet + jailet server-side. */
export async function writeFile(
  config: ApiConfig,
  root: string,
  path: string,
  content: string,
  kind: 'container' | 'workstation' = 'container',
): Promise<{ status: string; path: string }> {
  return apiFetch(config, '/chat/file', { method: 'POST', body: { root, path, content, kind } })
}

/** "Åbn i editor" for workstation-filer: xdg-open i brugerens lokale OS-editor. */
export async function openExternal(
  config: ApiConfig,
  root: string,
  path: string,
  kind: 'container' | 'workstation' = 'workstation',
): Promise<{ status: string; path: string }> {
  return apiFetch(config, '/chat/open-external', { method: 'POST', body: { root, path, kind } })
}

/** Live: den sti Jarvis senest læste/skrev (fil-træ live-highlight). */
export async function getActiveFile(
  config: ApiConfig,
): Promise<{ path: string; op: string; ts: number | null }> {
  return apiFetch(config, '/chat/active-file')
}

/** Auto-genereret (redigerbar) commit-besked ud fra diff'en. */
export async function commitMessage(
  config: ApiConfig, root: string, path: string, content: string,
): Promise<{ message: string; auto: boolean }> {
  return apiFetch(config, '/chat/file/commit-message', { method: 'POST', body: { root, path, content } })
}

/** Gem & commit (kun repo-root, owner): skriv + git commit på aktuel branch. */
export async function commitFile(
  config: ApiConfig, root: string, path: string, content: string, message: string,
): Promise<{ status: string; sha?: string; message: string }> {
  return apiFetch(config, '/chat/file/commit', { method: 'POST', body: { root, path, content, message } })
}

/** Code-mode terminal (§17), container-side: kør én kommando server-side i
 *  repo-workspace (owner-only, cwd contained til repo). Returnerer fuld output. */
export async function runContainerCommand(
  config: ApiConfig,
  command: string,
  cwd = '',
): Promise<{ stdout: string; stderr: string; exit_code: number }> {
  return apiFetch(config, '/chat/terminal/run', {
    method: 'POST',
    body: { command, cwd },
    timeoutMs: 65_000,
    retries: 0,
  })
}

/** Server-cancel af et aktivt run (R3). Idempotent: 200 og 404 (run ukendt/
 *  allerede stoppet) behandles begge som "stoppet". Netværksfejl svælges —
 *  klienten aborter lokalt alligevel. */
export async function cancelRun(config: ApiConfig, runId: string): Promise<void> {
  const url = new URL(`/chat/runs/${encodeURIComponent(runId)}/cancel`, config.apiBaseUrl).toString()
  const headers: Record<string, string> = {}
  if (config.authToken) headers.Authorization = `Bearer ${config.authToken}`
  try {
    await fetch(url, { method: 'POST', headers })
  } catch {
    // best-effort: netværksfejl ignoreres
  }
}

/** Hent authentificeret bruger + rolle. Serveren returnerer felterne
 *  user_id / user_display_name / role — normaliseres her til WhoAmI. */
export async function whoami(config: ApiConfig): Promise<WhoAmI> {
  const raw = await apiFetch<{ user_id?: string; user_display_name?: string; role?: string }>(config, '/api/whoami')
  return {
    user_id: raw.user_id ?? '',
    display_name: raw.user_display_name ?? '',
    role: (raw.role as WhoAmI['role']) ?? 'guest',
  }
}

/** Hent tilgængelige ollama-modeller på containeren (owner-only endpoint).
 *  Bruges af composer's dynamiske model-vælger. Tom liste hvis ikke owner / fejl. */
export async function getOllamaModels(config: ApiConfig): Promise<string[]> {
  try {
    const raw = await apiFetch<{ models?: string[] }>(config, '/chat/ollama-models')
    return Array.isArray(raw.models) ? raw.models : []
  } catch {
    return []
  }
}

export interface VisibleProvider { id: string; models: string[] }

/** Alle visible-klare providers + deres modeller (owner). Composeren bruger den
 *  til den universelle provider/model-vælger. Tom liste hvis ikke owner/fejl. */
export async function getVisibleProviders(config: ApiConfig): Promise<VisibleProvider[]> {
  try {
    const raw = await apiFetch<{ providers?: VisibleProvider[] }>(config, '/chat/visible-providers')
    return Array.isArray(raw.providers) ? raw.providers : []
  } catch {
    return []
  }
}

/** Device-presence: rapportér denne enheds tilstand (fokus/vågen/interaktion). */
export async function presencePing(config: ApiConfig, body: object): Promise<void> {
  try { await apiFetch(config, '/presence/ping', { method: 'POST', body, retries: 0 }) } catch { /* presence er best-effort */ }
}

export interface PendingNotification {
  notif_id: string
  kind: string
  title: string
  body: string
  session_id: string
}

/** Hent ventende proaktive desktop-notifikationer (drainer server-køen). */
export async function fetchPendingNotifications(config: ApiConfig): Promise<PendingNotification[]> {
  try {
    const r = await apiFetch<{ items?: PendingNotification[] }>(config, '/notifications/pending', { retries: 0 })
    return Array.isArray(r.items) ? r.items : []
  } catch {
    return []
  }
}

/** Kvittér en notifikation (vist/åbnet) → annullerer eskalering server-side. */
export async function ackNotification(config: ApiConfig, notifId: string): Promise<void> {
  try { await apiFetch(config, '/notifications/ack', { method: 'POST', body: { notif_id: notifId }, retries: 0 }) } catch { /* best-effort */ }
}

/** Mål forbindelses-latency mod serveren (ping). Returnerer ms eller null hvis nede. */
export async function pingServer(config: ApiConfig): Promise<number | null> {
  // /health er let (200 uden stor payload). AbortController-timeout: uden den HÆNGER fetch'en på
  // OS'ets TCP-timeout (~74s) når API'en er unåbar → app'en gik "grøn med 74000ms" når den hængende
  // request endelig lykkedes. Nu fejler et ping hurtigt (6s) → 10s-intervallet prøver igen → grøn
  // inden for ~10s af at API'en kommer tilbage, med ægte (lav) latency.
  const url = new URL('/health', config.apiBaseUrl).toString()
  const t0 = performance.now()
  const ac = new AbortController()
  const timer = setTimeout(() => ac.abort(), 6000)
  try {
    const res = await fetch(url, { method: 'GET', cache: 'no-store', signal: ac.signal })
    if (!res.ok) return null
    return Math.round(performance.now() - t0)
  } catch {
    return null
  } finally {
    clearTimeout(timer)
  }
}
