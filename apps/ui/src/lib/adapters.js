const JSON_HEADERS = { 'Content-Type': 'application/json' }

async function requestJson(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      ...(options.body ? JSON_HEADERS : {}),
      ...(options.headers || {}),
    },
  })

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
}

function nowLabel() {
  return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function toTitle(value) {
  return String(value || '')
    .replace(/-/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase())
}

function normalizeSelection(payload) {
  const selection = payload?.selection || payload || {}
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
  }
}

function buildMissionControl(runtime, visibleExecution, selection) {
  const readiness = visibleExecution?.readiness || runtime?.visible_execution || {}
  const cheapLane = runtime?.cheap_lane_execution || {}
  const codingLane = runtime?.coding_lane_execution || {}
  const localLane = runtime?.local_lane_execution || {}
  const providerRouter = runtime?.provider_router || {}
  const localTarget = localLane?.target || providerRouter?.lane_targets?.local || {}

  return {
    overview: [
      {
        label: 'Health',
        value: toTitle(readiness.provider_status || readiness.auth_status || 'unknown'),
        tone: readiness.auth_ready ? 'green' : 'amber',
      },
      {
        label: 'Main Agent',
        value: `${selection.currentProvider || 'unknown'} / ${selection.currentModel || 'unknown'}`,
        tone: 'accent',
      },
      {
        label: 'Coding Lane',
        value: String(codingLane.status || 'unknown'),
        tone: 'amber',
      },
      {
        label: 'Local Lane',
        value: `${localTarget.model || 'unconfigured'} · ${localLane.status || 'unknown'}`,
        tone: 'blue',
      },
    ],
    events: [
      `main agent: ${selection.currentProvider || 'unknown'} / ${selection.currentModel || 'unknown'}`,
      `cheap lane: ${cheapLane.status || 'unknown'}`,
      `coding lane: ${codingLane.status || 'unknown'}`,
      `local lane: ${localLane.status || 'unknown'}`,
    ],
    panels: [
      {
        title: 'Execution Authority',
        body: `Authority stays in ${selection.selectionAuthority}. Current auth profile: ${selection.currentAuthProfile || 'none'}.`,
      },
      {
        title: 'Visible Runtime',
        body: `Visible provider status is ${readiness.provider_status || 'unknown'} with auth status ${readiness.auth_status || 'unknown'}.`,
      },
      {
        title: 'Local Ollama',
        body: `${localTarget.provider || 'ollama'} / ${localTarget.model || 'unconfigured'} at ${localTarget.base_url || 'http://127.0.0.1:11434'} is ${localLane.status || 'unknown'}.`,
      },
    ],
    lanes: {
      cheap: {
        status: cheapLane.status || 'unknown',
      },
      coding: {
        status: codingLane.status || 'unknown',
        authPath: codingLane.coding_auth_path || '',
      },
      local: {
        status: localLane.status || 'unknown',
        providerStatus: localLane.provider_status || 'unknown',
        model: localTarget.model || '',
        baseUrl: localTarget.base_url || '',
      },
    },
    readiness: {
      providerStatus: readiness.provider_status || 'unknown',
      authStatus: readiness.auth_status || 'unknown',
    },
  }
}

function buildChat(selection, runtime) {
  const localLane = runtime?.local_lane_execution || {}
  const localTarget = localLane?.target || {}
  return {
    title: 'Jarvis',
    subtitle: `Main agent: ${selection.currentProvider || 'unknown'} / ${selection.currentModel || 'unknown'}`,
    bootstrapMessages: [
      {
        id: `bootstrap-${Date.now()}`,
        role: 'assistant',
        content: `Jarvis online. Main agent is ${selection.currentProvider || 'unknown'} / ${selection.currentModel || 'unknown'}. Local lane is ${localTarget.model || 'unconfigured'} with status ${localLane.status || 'unknown'}.`,
        ts: nowLabel(),
      },
    ],
  }
}

async function readSseStream(response) {
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
      if (eventName === 'delta' && payload.delta) {
        assistantText += payload.delta
      }
      if (eventName === 'failed') {
        failure = payload.error || 'Chat failed'
      }
      if (eventName === 'cancelled') {
        failure = 'Chat cancelled'
      }
    }
  }

  return {
    id: `assistant-${Date.now()}`,
    role: 'assistant',
    content: assistantText || failure || 'No response content returned.',
    ts: nowLabel(),
  }
}

export const backend = {
  async getShell() {
    const [selectionPayload, visibleExecution, runtime] = await Promise.all([
      requestJson('/mc/main-agent-selection'),
      requestJson('/mc/visible-execution'),
      requestJson('/mc/runtime'),
    ])

    const selection = normalizeSelection(selectionPayload)
    return {
      selection,
      missionControl: buildMissionControl(runtime, visibleExecution, selection),
      chat: buildChat(selection, runtime),
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

  async sendMessage({ content }) {
    const response = await fetch('/chat/stream', {
      method: 'POST',
      headers: JSON_HEADERS,
      body: JSON.stringify({ message: content }),
    })
    if (!response.ok) {
      throw new Error(`/chat/stream: ${response.status} ${response.statusText}`)
    }
    return readSseStream(response)
  },
}
