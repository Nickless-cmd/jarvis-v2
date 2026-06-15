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
import { stringToBlocks } from './normalizeMessage'

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
      messages?: Array<{ id: string; role: ChatMessage['role']; content: string; created_at: string; parent_id?: string | null }>
    }
  }>(config, `/chat/sessions/${encodeURIComponent(sessionId)}`)
  const session = raw.session
  const messages: ChatMessage[] = (session?.messages ?? []).map((m) => ({
    id: m.id,
    role: m.role,
    created_at: m.created_at,
    parent_id: m.parent_id ?? null,
    content: stringToBlocks(m.content),
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
    const url = new URL(`/chat/sessions/${encodeURIComponent(sessionId)}/follow`, config.apiBaseUrl).toString()
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

/** Mål forbindelses-latency mod serveren (ping). Returnerer ms eller null hvis nede. */
export async function pingServer(config: ApiConfig): Promise<number | null> {
  const url = new URL('/openapi.json', config.apiBaseUrl).toString()
  const t0 = performance.now()
  try {
    const res = await fetch(url, { method: 'GET', cache: 'no-store' })
    if (!res.ok) return null
    return Math.round(performance.now() - t0)
  } catch {
    return null
  }
}
