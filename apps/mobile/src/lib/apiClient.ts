import type { ApiConfig, ChatMessage, ChatSession, WhoAmI } from './types'

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
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
  body?: unknown
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
      throw new ApiError('unknown', `HTTP ${response.status}`, response.status)
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

export async function listSessions(config: ApiConfig): Promise<ChatSession[]> {
  const raw = await apiFetch<{ items?: ChatSession[]; sessions?: ChatSession[] } | ChatSession[]>(
    config,
    '/chat/sessions'
  )

  if (Array.isArray(raw)) {
    return raw
  }

  return raw.items ?? raw.sessions ?? []
}

export async function createSession(
  config: ApiConfig,
  title = 'Ny samtale'
): Promise<ChatSession> {
  const raw = await apiFetch<{ session?: ChatSession } | ChatSession>(config, '/chat/sessions', {
    method: 'POST',
    body: { title }
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
