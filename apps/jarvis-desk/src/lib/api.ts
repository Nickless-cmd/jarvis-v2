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

export interface ChatSession {
  id: string
  title: string
  updated_at: string
  message_count?: number
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'tool' | 'system' | 'approval_request'
  content: string
  created_at: string
}

export interface ApiConfig {
  apiBaseUrl: string
  authToken: string | null
}

interface FetchOptions {
  method?: 'GET' | 'POST' | 'DELETE' | 'PATCH'
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
  const data = await apiFetch<{ sessions: ChatSession[] } | ChatSession[]>(
    config,
    '/chat/sessions',
  )
  // Backend kan returnere enten array eller wrapped object — håndter begge.
  return Array.isArray(data) ? data : data.sessions
}

export async function getSession(
  config: ApiConfig,
  sessionId: string,
): Promise<{ session: ChatSession; messages: ChatMessage[] }> {
  return apiFetch<{ session: ChatSession; messages: ChatMessage[] }>(
    config,
    `/chat/sessions/${encodeURIComponent(sessionId)}`,
  )
}

export async function createSession(
  config: ApiConfig,
  title: string,
): Promise<ChatSession> {
  return apiFetch<ChatSession>(config, '/chat/sessions', {
    method: 'POST',
    body: { title },
  })
}
