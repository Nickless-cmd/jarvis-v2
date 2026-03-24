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

function formatRelativeTime(value) {
  const ts = Date.parse(String(value || ''))
  if (!Number.isFinite(ts)) return 'unknown'
  const delta = Math.max(0, Date.now() - ts)
  const sec = Math.floor(delta / 1000)
  if (sec < 10) return 'just now'
  if (sec < 60) return `${sec}s ago`
  const min = Math.floor(sec / 60)
  if (min < 60) return `${min}m ago`
  const hr = Math.floor(min / 60)
  if (hr < 24) return `${hr}h ago`
  const day = Math.floor(hr / 24)
  return `${day}d ago`
}

function formatMoney(value) {
  const amount = Number(value || 0)
  if (!Number.isFinite(amount)) return '$0.00'
  return `$${amount.toFixed(2)}`
}

function formatInteger(value) {
  const amount = Number(value || 0)
  if (!Number.isFinite(amount)) return '0'
  return new Intl.NumberFormat().format(amount)
}

function normalizeRunItem(item = {}) {
  return {
    runId: item.run_id || '',
    lane: item.lane || '',
    provider: item.provider || '',
    model: item.model || '',
    status: item.status || 'unknown',
    startedAt: item.started_at || '',
    finishedAt: item.finished_at || '',
    textPreview: item.text_preview || '',
    error: item.error || '',
    capabilityId: item.capability_id || '',
  }
}

function normalizeApprovalItem(item = {}) {
  return {
    requestId: item.request_id || '',
    capabilityId: item.capability_id || '',
    capabilityName: item.capability_name || item.capability_id || 'unknown',
    capabilityKind: item.capability_kind || '',
    executionMode: item.execution_mode || '',
    approvalPolicy: item.approval_policy || '',
    runId: item.run_id || '',
    requestedAt: item.requested_at || '',
    approvedAt: item.approved_at || '',
    executedAt: item.executed_at || '',
    status: item.status || 'unknown',
    executed: Boolean(item.executed),
    invocationStatus: item.invocation_status || '',
    invocationExecutionMode: item.invocation_execution_mode || '',
  }
}

function normalizeEventItem(item = {}) {
  return {
    id: item.id || 0,
    kind: item.kind || '',
    family: item.family || 'unknown',
    payload: item.payload || {},
    createdAt: item.created_at || '',
    relativeTime: formatRelativeTime(item.created_at),
  }
}

function normalizeLane(label, lane = {}, target = {}) {
  return {
    label,
    status: lane.status || 'unknown',
    providerStatus: lane.provider_status || lane.auth_status || 'unknown',
    authStatus: lane.auth_status || '',
    authReady: Boolean(lane.auth_ready),
    model: target.model || lane.model || '',
    provider: target.provider || lane.provider || '',
    baseUrl: target.base_url || lane.base_url || '',
    authProfile: target.auth_profile || lane.auth_profile || '',
    readinessHint: lane.readiness_hint || '',
    detail: lane,
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

function buildChat(selection) {
  return {
    title: 'Jarvis',
    subtitle: `Main agent: ${selection.currentProvider || 'unknown'} / ${selection.currentModel || 'unknown'}`,
    bootstrapMessages: [],
  }
}

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
      if (eventName === 'failed') {
        failure = payload.error || 'Chat failed'
        handlers.onFailed?.(failure)
      }
      if (eventName === 'cancelled') {
        failure = 'Chat cancelled'
        handlers.onFailed?.(failure)
      }
      if (eventName === 'done') handlers.onDone?.(payload, assistantText)
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
    const selectionPayload = await requestJson('/mc/main-agent-selection')
    const selection = normalizeSelection(selectionPayload)
    return {
      selection,
      missionControl: null,
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

  async getMissionControlOverview({ selection } = {}) {
    const [overview, approvals, sessions, events] = await Promise.all([
      requestJson('/mc/overview'),
      requestJson('/mc/approvals?limit=10'),
      requestJson('/chat/sessions'),
      requestJson('/mc/events?limit=12'),
    ])

    const visibleExecution = overview?.visible_execution || {}
    const recentRuns = overview?.visible_run?.persisted_recent_runs || []
    const recentEvents = (events?.items || []).map(normalizeEventItem)
    const pendingApprovals = Number(approvals?.summary?.pending_count || 0)
    const failedRuns = recentRuns.filter((item) => ['failed', 'cancelled'].includes(String(item?.status || ''))).length

    return {
      fetchedAt: new Date().toISOString(),
      cards: [
        {
          id: 'system-health',
          label: 'System Health',
          value: toTitle(visibleExecution.provider_status || visibleExecution.auth_status || 'unknown'),
          tone: visibleExecution.auth_ready ? 'green' : 'amber',
          targetTab: 'operations',
          targetSection: 'runtime-lanes',
          source: '/mc/overview',
        },
        {
          id: 'active-run',
          label: 'Active Run',
          value: overview?.visible_run?.active_run?.provider
            ? `${overview.visible_run.active_run.provider} / ${overview.visible_run.active_run.model}`
            : 'Idle',
          tone: overview?.visible_run?.active ? 'accent' : 'blue',
          targetTab: 'operations',
          targetSection: 'runs',
          source: '/mc/overview + /mc/runs',
        },
        {
          id: 'pending-approvals',
          label: 'Pending Approvals',
          value: String(pendingApprovals),
          tone: pendingApprovals > 0 ? 'amber' : 'green',
          targetTab: 'operations',
          targetSection: 'approvals',
          source: '/mc/approvals',
        },
        {
          id: 'sessions',
          label: 'Sessions',
          value: String((sessions?.items || []).length),
          tone: 'blue',
          targetTab: 'operations',
          targetSection: 'sessions',
          source: '/chat/sessions',
        },
        {
          id: 'lane-health',
          label: 'Lane Health',
          value: `${selection?.currentProvider || 'unknown'} / ${selection?.currentModel || 'unknown'}`,
          tone: 'accent',
          targetTab: 'observability',
          targetSection: 'provider-health',
          source: '/mc/main-agent-selection + /mc/overview',
        },
        {
          id: 'cost',
          label: 'Cost Snapshot',
          value: formatMoney(overview?.total_cost_usd || 0),
          tone: 'blue',
          targetTab: 'observability',
          targetSection: 'cost-usage',
          source: '/mc/overview',
        },
        {
          id: 'errors',
          label: 'Failures',
          value: String(failedRuns),
          tone: failedRuns > 0 ? 'amber' : 'green',
          targetTab: 'observability',
          targetSection: 'failure-summary',
          source: '/mc/runtime.visible_run',
        },
      ],
      activeRun: overview?.visible_run?.active_run ? normalizeRunItem(overview.visible_run.active_run) : null,
      importantEvents: recentEvents.slice(0, 6),
      summaries: {
        pendingApprovals,
        sessionCount: (sessions?.items || []).length,
        totalCostUsd: Number(overview?.total_cost_usd || 0),
        failureCount: failedRuns,
      },
    }
  },

  async getMissionControlOperations() {
    const [runtime, runs, approvals, sessions] = await Promise.all([
      requestJson('/mc/runtime'),
      requestJson('/mc/runs?limit=20'),
      requestJson('/mc/approvals?limit=20'),
      requestJson('/chat/sessions'),
    ])

    const providerRouter = runtime?.provider_router || {}
    return {
      fetchedAt: new Date().toISOString(),
      runs: {
        activeRun: runs?.active_run ? normalizeRunItem(runs.active_run) : null,
        lastOutcome: runs?.last_outcome || null,
        lastCapabilityUse: runs?.last_capability_use || null,
        recentRuns: (runs?.recent_runs || []).map(normalizeRunItem),
        recentWorkUnits: runs?.recent_work_units || [],
        recentWorkNotes: runs?.recent_work_notes || [],
        summary: runs?.summary || {},
      },
      sessions: {
        items: sessions?.items || [],
      },
      approvals: {
        summary: approvals?.summary || {},
        requests: (approvals?.requests || []).map(normalizeApprovalItem),
        recentInvocations: approvals?.recent_invocations || [],
      },
      lanes: {
        visible: normalizeLane('Visible', runtime?.visible_execution || {}, providerRouter?.main_agent_target || {}),
        cheap: normalizeLane('Cheap', runtime?.cheap_lane_execution || {}, providerRouter?.lane_targets?.cheap || {}),
        coding: normalizeLane('Coding', runtime?.coding_lane_execution || {}, providerRouter?.lane_targets?.coding || {}),
        local: normalizeLane('Local', runtime?.local_lane_execution || {}, providerRouter?.lane_targets?.local || {}),
      },
    }
  },

  async getMissionControlObservability() {
    const [events, costs, runtime, runs] = await Promise.all([
      requestJson('/mc/events?limit=80'),
      requestJson('/mc/costs?limit=40'),
      requestJson('/mc/runtime'),
      requestJson('/mc/runs?limit=20'),
    ])

    const normalizedRuns = (runs?.recent_runs || []).map(normalizeRunItem)
    const failedRuns = normalizedRuns.filter((item) => ['failed', 'cancelled'].includes(item.status))
    return {
      fetchedAt: new Date().toISOString(),
      events: (events?.items || []).map(normalizeEventItem),
      costs: {
        summary: costs?.summary || {},
        items: costs?.items || [],
      },
      failures: {
        lastOutcome: runs?.last_outcome || null,
        failedRuns,
        recentRuns: normalizedRuns,
      },
      providerHealth: {
        visible: runtime?.visible_execution || {},
        cheap: runtime?.cheap_lane_execution || {},
        coding: runtime?.coding_lane_execution || {},
        local: runtime?.local_lane_execution || {},
      },
      runEvidence: {
        recentEvents: (runs?.recent_events || []).map(normalizeEventItem),
        recentWorkUnits: runs?.recent_work_units || [],
        recentWorkNotes: runs?.recent_work_notes || [],
      },
    }
  },

  async getMissionControlPhaseA({ selection } = {}) {
    const [overview, operations, observability] = await Promise.all([
      this.getMissionControlOverview({ selection }),
      this.getMissionControlOperations(),
      this.getMissionControlObservability(),
    ])
    return { overview, operations, observability }
  },

  async approveCapabilityRequest(requestId) {
    return requestJson(`/mc/capability-approval-requests/${requestId}/approve`, {
      method: 'POST',
    })
  },

  async executeCapabilityRequest(requestId) {
    return requestJson(`/mc/capability-approval-requests/${requestId}/execute`, {
      method: 'POST',
    })
  },

  subscribeMissionControlEvents(onEvent) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const socket = new WebSocket(`${protocol}//${window.location.host}/ws`)
    socket.onmessage = (message) => {
      try {
        const item = JSON.parse(message.data)
        onEvent?.(normalizeEventItem(item))
      } catch {
        // no-op
      }
    }
    return () => {
      socket.close()
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

  async streamMessage({ sessionId, content, onRun, onDelta, onDone, onFailed }) {
    const response = await fetch('/chat/stream', {
      method: 'POST',
      headers: JSON_HEADERS,
      body: JSON.stringify({ message: content, session_id: sessionId }),
    })
    if (!response.ok) {
      throw new Error(`/chat/stream: ${response.status} ${response.statusText}`)
    }
    return readSseStream(response, { onRun, onDelta, onDone, onFailed })
  },
}
