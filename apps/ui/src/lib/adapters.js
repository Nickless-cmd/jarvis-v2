// Chat-only backend adapter.
//
// Mission Control was ripped out of the web-UI (Fase E) — the heavy MC
// pollers that hammered /mc/runtime, /mc/operations, /mc/events etc. are
// gone. MC now lives entirely in the Central / Central-CLI. What remains
// here is the chat surface plus the few runtime endpoints the chat lane
// genuinely needs (session model selection, system health/git for the
// composer, and the Jarvis presence surface for the chat support rail).

const JSON_HEADERS = { 'Content-Type': 'application/json' }
const inflightJsonRequests = new Map()

async function requestJson(path, options = {}) {
  const method = String(options.method || 'GET').toUpperCase()
  const isDedupableGet = method === 'GET' && !options.body
  const requestKey = isDedupableGet ? `${method}:${path}` : ''

  if (requestKey) {
    const pending = inflightJsonRequests.get(requestKey)
    if (pending) return pending
  }

  const request = fetch(path, {
    ...options,
    headers: {
      ...(options.body ? JSON_HEADERS : {}),
      ...(options.headers || {}),
    },
  }).then(async (response) => {
    if (!response.ok) {
      let detail = `${response.status} ${response.statusText}`
      try {
        const data = await response.json()
        detail = data.detail || JSON.stringify(data)
      } catch {
        detail = await response.text()
      }
      throw new Error(`${path}: ${detail}`)
    }

    return response.json()
  })

  if (!requestKey) return request

  inflightJsonRequests.set(requestKey, request)
  return request.finally(() => {
    if (inflightJsonRequests.get(requestKey) === request) {
      inflightJsonRequests.delete(requestKey)
    }
  })
}

function nowLabel() {
  return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

// ── Live event stream (WebSocket) ────────────────────────────────────
// The chat lane subscribes to the eventbus WebSocket so backend-originated
// proactive messages (self-wakeup, inner-voice initiative, scheduled tasks)
// surface without a manual refresh. This is not a poller — it is a passive
// socket. The helper names keep their historical "MissionControl" prefix so
// the chat shell's call sites stay stable.
const liveEventListeners = new Set()
let liveSocket = null
let liveReconnectTimer = null
let liveRetryDelay = 1000

function scheduleLiveReconnect() {
  if (liveReconnectTimer || liveEventListeners.size === 0) return
  liveReconnectTimer = window.setTimeout(() => {
    liveReconnectTimer = null
    ensureLiveSocket()
  }, liveRetryDelay)
  liveRetryDelay = Math.min(liveRetryDelay * 2, 8000)
}

function normalizeEventItem(item = {}) {
  return {
    id: item.id || 0,
    kind: item.kind || '',
    family: item.family || 'unknown',
    payload: item.payload || {},
    createdAt: item.created_at || '',
  }
}

function ensureLiveSocket() {
  if (liveSocket || liveEventListeners.size === 0) return
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const socket = new WebSocket(`${protocol}//${window.location.host}/ws`)
  liveSocket = socket

  socket.onopen = () => {
    liveRetryDelay = 1000
  }

  socket.onmessage = (message) => {
    try {
      const item = JSON.parse(message.data)
      if (item && item.type === 'ping') return
      const normalized = normalizeEventItem(item)
      liveEventListeners.forEach((listener) => listener?.(normalized))
    } catch {
      // no-op
    }
  }

  socket.onclose = () => {
    if (liveSocket === socket) liveSocket = null
    if (liveEventListeners.size === 0) return
    scheduleLiveReconnect()
  }

  socket.onerror = () => {
    // onclose fires after onerror — reconnect handled there
  }
}

// ── Main-agent selection (model picker in the composer) ──────────────
function normalizeSelection(payload) {
  const selection = payload?.selection || payload || {}
  const ollama = payload?.ollama_models || {}
  return {
    source: selection.source || 'provider_router.main_agent_selection',
    selectionAuthority: selection.selection_authority || 'runtime.settings',
    currentProvider: selection.current_provider || '',
    currentModel: selection.current_model || '',
    currentAuthProfile: selection.current_auth_profile || '',
    availableConfiguredTargets: (selection.available_configured_targets || []).map((target) => ({
      provider: target.provider || '',
      model: target.model || '',
      authProfile: target.auth_profile || '',
      authMode: target.auth_mode || 'none',
      readinessHint: target.readiness_hint || 'unknown',
      baseUrl: target.base_url || '',
    })),
    ollamaModels: (ollama.models || []).map((item) => ({
      name: item.name || '',
      family: item.family || '',
      parameterSize: item.parameter_size || '',
      quantizationLevel: item.quantization_level || '',
    })),
    ollamaStatus: ollama.status || 'unknown',
    ollamaBaseUrl: ollama.base_url || 'http://127.0.0.1:11434',
  }
}

function buildChat(selection) {
  return {
    title: 'Jarvis',
    subtitle: `Main agent: ${selection.currentProvider || 'unknown'} / ${selection.currentModel || 'unknown'}`,
    bootstrapMessages: [],
  }
}

// ── Chat SSE stream ──────────────────────────────────────────────────
async function readSseStream(response, handlers = {}) {
  if (!response.body) {
    throw new Error('/chat/stream: response body missing')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let assistantText = ''
  let failure = null

  while (true) {
    const { value, done } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const frames = buffer.split('\n\n')
    buffer = frames.pop() || ''

    for (const frame of frames) {
      const lines = frame.split('\n')
      let eventName = ''
      let dataLine = ''
      for (const line of lines) {
        if (line.startsWith('event:')) eventName = line.slice(6).trim()
        if (line.startsWith('data:')) dataLine += line.slice(5).trim()
      }
      if (!dataLine) continue

      const payload = JSON.parse(dataLine)
      if (eventName === 'run') handlers.onRun?.(payload)
      if (eventName === 'delta' && payload.delta) {
        assistantText += payload.delta
        handlers.onDelta?.(payload.delta, assistantText)
      }
      if (eventName === 'working_step') handlers.onWorkingStep?.(payload)
      if (eventName === 'failed') {
        failure = payload.error || 'Chat failed'
        handlers.onFailed?.(failure)
      }
      if (eventName === 'capability') handlers.onCapability?.(payload)
      if (eventName === 'approval_request') handlers.onApprovalRequest?.(payload)
      if (eventName === 'cancelled') {
        failure = 'Chat cancelled'
        handlers.onFailed?.(failure)
        try { reader.cancel() } catch (_) { /* ignore */ }
        return {
          id: `assistant-${Date.now()}`,
          role: 'assistant',
          content: assistantText || failure,
          ts: nowLabel(),
          persisted: false,
        }
      }
      if (eventName === 'done') {
        handlers.onDone?.(payload, assistantText)
        // Close the reader immediately — don't wait for HTTP connection to close
        try { reader.cancel() } catch (_) { /* ignore */ }
        // persisted=true only for successful completion — backend persists before done.
        // For failed/cancelled runs the backend may persist an error message, but
        // the partial streamed text may not be in DB, so skip reload to keep local state.
        const completedOk = !payload.status || payload.status === 'completed'
        return {
          id: `assistant-${Date.now()}`,
          role: 'assistant',
          content: assistantText || 'No response content returned.',
          ts: nowLabel(),
          persisted: completedOk,
        }
      }
    }
  }

  // Stream ended without a done event (connection dropped, timeout, etc.)
  // Return with persisted=false so the caller knows NOT to reload from DB.
  return {
    id: `assistant-${Date.now()}`,
    role: 'assistant',
    content: assistantText || failure || 'No response content returned.',
    ts: nowLabel(),
    persisted: false,
  }
}

export const backend = {
  async getShell() {
    const selectionPayload = await requestJson('/mc/main-agent-selection')
    const selection = normalizeSelection(selectionPayload)
    return {
      selection,
      chat: buildChat(selection),
    }
  },

  async updateMainAgentSelection(payload) {
    const updated = await requestJson('/mc/main-agent-selection', {
      method: 'PUT',
      body: JSON.stringify({
        provider: payload.provider,
        model: payload.model,
        auth_profile: payload.authProfile || '',
      }),
    })
    return normalizeSelection(updated)
  },

  // Passive eventbus WebSocket subscription for live proactive messages.
  subscribeMissionControlEvents(onEvent) {
    liveEventListeners.add(onEvent)
    ensureLiveSocket()

    return () => {
      liveEventListeners.delete(onEvent)
      if (liveEventListeners.size > 0) return
      if (liveReconnectTimer) {
        window.clearTimeout(liveReconnectTimer)
        liveReconnectTimer = null
      }
      liveRetryDelay = 1000
      if (liveSocket) {
        liveSocket.close()
        liveSocket = null
      }
    }
  },

  async listSessions() {
    const data = await requestJson('/chat/sessions')
    return data.items || []
  },

  async createSession(title = 'New chat') {
    const data = await requestJson('/chat/sessions', {
      method: 'POST',
      body: JSON.stringify({ title }),
    })
    return data.session
  },

  async getSession(sessionId) {
    const data = await requestJson(`/chat/sessions/${sessionId}`)
    return data.session
  },

  async streamMessage({ sessionId, content, attachmentIds = [], approvalMode = 'ask', thinkingMode = 'think', signal, onRun, onDelta, onDone, onFailed, onWorkingStep, onCapability, onApprovalRequest }) {
    const response = await fetch('/chat/stream', {
      method: 'POST',
      headers: JSON_HEADERS,
      body: JSON.stringify({
        message: content,
        session_id: sessionId,
        attachment_ids: attachmentIds,
        approval_mode: approvalMode,
        thinking_mode: thinkingMode,
      }),
      signal,
    })
    if (!response.ok) {
      throw new Error(`/chat/stream: ${response.status} ${response.statusText}`)
    }
    return readSseStream(response, { onRun, onDelta, onDone, onFailed, onWorkingStep, onCapability, onApprovalRequest })
  },

  async uploadAttachment(sessionId, file) {
    const form = new FormData()
    form.append('file', file)
    form.append('session_id', sessionId)
    const response = await fetch('/attachments/upload', { method: 'POST', body: form })
    if (!response.ok) {
      const err = await response.json().catch(() => ({}))
      throw new Error(err.detail || `Upload failed: ${response.status}`)
    }
    return response.json()
  },

  async cancelRun(runId) {
    const res = await fetch(`/chat/runs/${runId}/cancel`, { method: 'POST', headers: JSON_HEADERS })
    if (!res.ok) throw new Error(`Cancel failed: ${res.status}`)
    return res.json()
  },

  async steerRun(runId, content) {
    const res = await fetch(`/chat/runs/${runId}/steer`, {
      method: 'POST',
      headers: JSON_HEADERS,
      body: JSON.stringify({ content }),
    })
    if (!res.ok) throw new Error(`Steer failed: ${res.status}`)
    return res.json()
  },

  async renameSession(sessionId, title) {
    return requestJson(`/chat/sessions/${sessionId}/rename`, {
      method: 'PUT',
      body: JSON.stringify({ title }),
    })
  },

  async deleteSession(sessionId) {
    return requestJson(`/chat/sessions/${sessionId}`, { method: 'DELETE' })
  },

  async getSystemHealth() {
    try {
      return await requestJson('/mc/system/health')
    } catch {
      return { cpu_pct: 0, ram_pct: 0, disk_free_mb: 0 }
    }
  },

  async getSystemGit() {
    try {
      return await requestJson('/mc/system/git')
    } catch {
      return { branch: '', insertions: 0, deletions: 0, files_changed: 0, workspace: '' }
    }
  },

  async gitCommit(message) {
    return await requestJson('/mc/system/git/commit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message }),
    })
  },

  // Jarvis presence surface for the chat support rail (emotional state,
  // inner voice, personality). Polled lightly (60s) by the chat shell —
  // this is the only remaining runtime read, not the old MC firehose.
  async getJarvisSurface() {
    const [jarvis, affective] = await Promise.all([
      requestJson('/mc/jarvis'),
      requestJson('/mc/affective-meta-state').catch(() => ({})),
    ])
    return {
      ...jarvis,
      affectiveMetaState: affective,
      protectedVoice: jarvis?.state?.protected_inner_voice || {},
      skills: [],
    }
  },
}
