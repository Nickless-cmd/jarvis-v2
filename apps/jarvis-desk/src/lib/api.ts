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

async function apiFetch<T>(
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

/** Læs en repo-fil til preview-panelet (path-jailed server-side). */
export async function getFile(
  config: ApiConfig,
  path: string,
): Promise<{ path: string; content: string; language: string }> {
  return apiFetch(config, `/chat/file?path=${encodeURIComponent(path)}`)
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
