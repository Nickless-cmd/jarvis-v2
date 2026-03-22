const JSON_HEADERS = { 'Content-Type': 'application/json' }

let shellCache = null

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
    selectionAuthority: selection.selection_authority || selection.selectionAuthority || 'runtime.settings',
    currentProvider: selection.current_provider || selection.currentProvider || '',
    currentModel: selection.current_model || selection.currentModel || '',
    currentAuthProfile: selection.current_auth_profile || selection.currentAuthProfile || '',
    availableConfiguredTargets: (selection.available_configured_targets || selection.availableConfiguredTargets || []).map((target) => ({
      provider: target.provider || '',
      model: target.model || '',
      authProfile: target.auth_profile || target.authProfile || '',
      authMode: target.auth_mode || target.authMode || 'none',
      readinessHint: target.readiness_hint || target.readinessHint || 'unknown',
    })),
  }
}

function buildMissionControl(runtime, visibleExecution, selection) {
  const readiness = visibleExecution?.readiness || runtime?.visible_execution || {}
  const codingLane = runtime?.coding_lane_execution || {}
  const localLane = runtime?.local_lane_execution || {}
  const cheapLane = runtime?.cheap_lane_execution || {}
  const alignment = runtime?.operational_preference_alignment?.current || {}

  return {
    overview: [
      { label: 'Health', value: toTitle(readiness.provider_status || readiness.auth_status || 'unknown'), tone: readiness.auth_ready ? 'green' : 'amber' },
      { label: 'Main Agent', value: `${selection.currentProvider || 'unknown'} / ${selection.currentModel || 'unknown'}`, tone: 'accent' },
      { label: 'Coding Lane', value: String(codingLane.status || 'unknown'), tone: 'amber' },
      { label: 'Local Lane', value: String(localLane.status || 'unknown'), tone: 'blue' },
    ],
    events: [
      `main agent selection: ${selection.currentProvider || 'unknown'} / ${selection.currentModel || 'unknown'}`,
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
        title: 'Runtime Truth',
        body: `Visible provider status is ${readiness.provider_status || 'unknown'} with auth status ${readiness.auth_status || 'unknown'}.`,
      },
      {
        title: 'Operational Alignment',
        body: `Preference alignment is ${alignment.alignment_status || 'unknown'}${alignment.recommended_action ? ` and recommends ${alignment.recommended_action}` : ''}.`,
      },
    ],
  }
}

function buildSessions(runtime, selection) {
  const activeRun = runtime?.visible_run?.active_run
  const lastOutcome = runtime?.visible_run?.last_outcome

  return [
    {
      id: 'main-agent',
      title: `Main agent · ${selection.currentProvider || 'unknown'}`,
      lastMessage: selection.currentModel || 'no model',
    },
    {
      id: 'visible-run',
      title: activeRun ? `Run active · ${activeRun.provider || 'unknown'}` : 'Visible run',
      lastMessage: activeRun?.status || lastOutcome?.status || 'idle',
    },
    {
      id: 'coding-lane',
      title: 'Coding lane',
      lastMessage: runtime?.coding_lane_execution?.status || 'unknown',
    },
  ]
}

function buildChat(selection, existingMessages) {
  return {
    title: 'Jarvis',
    subtitle: `Main agent: ${selection.currentProvider || 'unknown'} / ${selection.currentModel || 'unknown'}`,
    messages: existingMessages && existingMessages.length > 0
      ? existingMessages
      : [
          {
            id: 'bootstrap-assistant',
            role: 'assistant',
            content: `Jarvis online. Main agent selection is ${selection.currentProvider || 'unknown'} / ${selection.currentModel || 'unknown'}.`,
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
  let eventName = ''
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
      let dataLine = ''
      eventName = ''
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

  if (failure && !assistantText) {
    assistantText = failure
  }

  return assistantText || 'No response content returned.'
}

async function loadShell() {
  const [selectionPayload, visibleExecution, runtime] = await Promise.all([
    requestJson('/mc/main-agent-selection'),
    requestJson('/mc/visible-execution'),
    requestJson('/mc/runtime'),
  ])

  const selection = normalizeSelection(selectionPayload)
  const messages = shellCache?.chat?.messages || null

  shellCache = {
    sessions: buildSessions(runtime, selection),
    selection,
    chat: buildChat(selection, messages),
    missionControl: buildMissionControl(runtime, visibleExecution, selection),
  }

  return shellCache
}

export const backend = {
  async getShell() {
    return loadShell()
  },

  async getMainAgentSelection() {
    const payload = await requestJson('/mc/main-agent-selection')
    return normalizeSelection(payload)
  },

  async updateMainAgentSelection(payload) {
    await requestJson('/mc/main-agent-selection', {
      method: 'PUT',
      body: JSON.stringify({
        provider: payload.provider,
        model: payload.model,
        auth_profile: payload.authProfile || '',
      }),
    })
    const shell = await loadShell()
    return shell.selection
  },

  async sendMessage({ content }) {
    if (!shellCache) {
      await loadShell()
    }

    const userMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content,
      ts: nowLabel(),
    }

    shellCache.chat.messages = [...(shellCache.chat.messages || []), userMessage]

    const response = await fetch('/chat/stream', {
      method: 'POST',
      headers: JSON_HEADERS,
      body: JSON.stringify({ message: content }),
    })
    if (!response.ok) {
      throw new Error(`/chat/stream: ${response.status} ${response.statusText}`)
    }

    const assistantText = await readSseStream(response)
    const assistantMessage = {
      id: `assistant-${Date.now()}`,
      role: 'assistant',
      content: assistantText,
      ts: nowLabel(),
    }

    shellCache.chat.messages = [...shellCache.chat.messages, assistantMessage]
    return shellCache.chat.messages
  },
}
