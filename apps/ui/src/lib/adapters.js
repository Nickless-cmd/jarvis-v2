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

function normalizeMissionControlOperationsPayload(payload = {}) {
  const runtime = payload?.runtime || {}
  const runs = payload?.runs || {}
  const approvals = payload?.approvals || {}
  const sessions = payload?.sessions || {}
  const providerRouter = runtime?.provider_router || {}
  const toolIntentSource = payload?.toolIntent || runtime?.runtime_tool_intent || {}

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
    toolIntent: Object.keys(toolIntentSource || {}).length ? normalizeToolIntent(toolIntentSource) : null,
    runtime,
  }
}

const missionControlEventListeners = new Set()
let missionControlSocket = null
let missionControlReconnectTimer = null
let missionControlRetryDelay = 1000

function scheduleMissionControlReconnect() {
  if (missionControlReconnectTimer || missionControlEventListeners.size === 0) return
  missionControlReconnectTimer = window.setTimeout(() => {
    missionControlReconnectTimer = null
    ensureMissionControlSocket()
  }, missionControlRetryDelay)
  missionControlRetryDelay = Math.min(missionControlRetryDelay * 2, 8000)
}

function ensureMissionControlSocket() {
  if (missionControlSocket || missionControlEventListeners.size === 0) return
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const socket = new WebSocket(`${protocol}//${window.location.host}/ws`)
  missionControlSocket = socket

  socket.onopen = () => {
    missionControlRetryDelay = 1000
  }

  socket.onmessage = (message) => {
    try {
      const item = JSON.parse(message.data)
      if (item && item.type === 'ping') return
      const normalized = normalizeEventItem(item)
      missionControlEventListeners.forEach((listener) => {
        listener?.(normalized)
      })
    } catch {
      // no-op
    }
  }

  socket.onclose = () => {
    if (missionControlSocket === socket) missionControlSocket = null
    if (missionControlEventListeners.size === 0) return
    scheduleMissionControlReconnect()
  }

  socket.onerror = () => {
    // onclose will fire after onerror — reconnect handled there
  }
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

function normalizeVisibleExecutionTrace(item = {}) {
  const selectedCapabilityId = item.selected_capability_id || ''
  const parsedCommandText = item.parsed_command_text || ''
  const parsedTargetPath = item.parsed_target_path || ''
  const providerFirstPassStatus = item.provider_first_pass_status || 'unknown'
  const providerSecondPassStatus = item.provider_second_pass_status || 'not-started'
  const invokeStatus = item.invoke_status || 'not-invoked'
  const finalStatus = item.final_status || 'unknown'
  return {
    runId: item.run_id || '',
    lane: item.lane || '',
    provider: item.provider || '',
    model: item.model || '',
    selectedCapabilityId,
    parsedCommandText,
    parsedTargetPath,
    parsedArgumentSummary: parsedCommandText || parsedTargetPath || '',
    argumentSource: item.argument_source || 'none',
    argumentBindingMode: item.argument_binding_mode || 'id-only',
    invokeStatus,
    blockedReason: item.blocked_reason || '',
    providerFirstPassStatus,
    providerSecondPassStatus,
    providerErrorSummary: item.provider_error_summary || '',
    providerCallCount: Number(item.provider_call_count || 0),
    capabilityMarkupCount: Number(item.capability_markup_count || 0),
    multipleCapabilityTags: Boolean(item.multiple_capability_tags),
    firstPassInputTokens: Number(item.first_pass_input_tokens || 0),
    firstPassOutputTokens: Number(item.first_pass_output_tokens || 0),
    secondPassInputTokens: Number(item.second_pass_input_tokens || 0),
    secondPassOutputTokens: Number(item.second_pass_output_tokens || 0),
    totalInputTokens: Number(item.total_input_tokens || 0),
    totalOutputTokens: Number(item.total_output_tokens || 0),
    finalStatus,
    updatedAt: item.updated_at || '',
    source: '/mc/operations',
    summary:
      item.summary ||
      [
        selectedCapabilityId || 'no capability',
        invokeStatus,
        providerFirstPassStatus,
        providerSecondPassStatus,
        finalStatus,
      ].join(' · '),
    raw: item,
  }
}

function normalizeJarvisItem(item = {}, defaults = {}) {
  const source = item?.source || defaults.source || ''
  const createdAt = item?.created_at || item?.updated_at || defaults.createdAt || ''
  return {
    ...item,
    summary: defaults.summary || '',
    source,
    createdAt,
  }
}

function normalizeContractFile(item = {}) {
  return {
    name: item.name || '',
    path: item.path || '',
    role: item.role || 'unknown',
    present: Boolean(item.present),
    loadedByDefault: Boolean(item.loaded_by_default),
    activation: item.activation || '',
    writer: item.writer || '',
    source: item.source || '/mc/runtime-contract',
    summary:
      item.summary ||
      `${item.role || 'unknown'} · ${item.present ? 'present' : 'missing'}${item.loaded_by_default ? ' · default-load' : ''}`,
  }
}

function normalizePromptMode(item = {}) {
  return {
    id: item.id || '',
    label: item.label || item.id || 'unknown',
    status: item.status || 'unknown',
    implementationState: item.implementation_state || '',
    loadOrder: item.load_order || [],
    alwaysLoaded: item.always_loaded || [],
    conditionalFiles: item.conditional_files || [],
    derivedInputs: item.derived_inputs || [],
    excludedByDefault: item.excluded_by_default || [],
    source: item.source || '/mc/runtime-contract',
    summary: item.summary || 'Prompt contract metadata',
  }
}

function normalizeCapabilityContract(item = {}) {
  return {
    authoritySource: item.authority_source || 'runtime.workspace_capabilities',
    runtimeAuthoritative: item.runtime_authoritative !== false,
    guidanceOnlyDocs: item.guidance_only_docs !== false,
    guidanceSources: item.guidance_sources || [],
    describedCount: Number(item.described_count || 0),
    runtimeCount: Number(item.runtime_count || 0),
    availableNowCount: Number(item.available_now_count || 0),
    approvalRequiredCount: Number(item.approval_required_count || 0),
    guidanceOnlyCount: Number(item.guidance_only_count || 0),
    unavailableCount: Number(item.unavailable_count || 0),
    currentlyAvailable: item.currently_available || [],
    approvalGated: item.approval_gated || [],
    guidanceDescriptions: item.guidance_descriptions || [],
    source: item.source || '/mc/runtime-contract',
    summary: item.summary || 'Runtime capability truth is authoritative.',
  }
}

function normalizePendingWrite(item = {}) {
  return {
    id: item.id || '',
    label: item.label || item.id || 'unknown',
    targetFile: item.target_file || '',
    status: item.status || 'unknown',
    pendingCount: Number(item.pending_count || 0),
    approvedCount: Number(item.approved_count || 0),
    rejectedCount: Number(item.rejected_count || 0),
    appliedCount: Number(item.applied_count || 0),
    supersededCount: Number(item.superseded_count || 0),
    items: (item.items || []).map(normalizeCandidateItem),
    proposalTypes: item.proposal_types || [],
    isCanonicalSelf: Boolean(item.is_canonical_self),
    applyReadinessHighCount: Number(item.apply_readiness_high_count || 0),
    applyReadinessMediumCount: Number(item.apply_readiness_medium_count || 0),
    applyReadinessLowCount: Number(item.apply_readiness_low_count || 0),
    currentApplyReadiness: item.current_apply_readiness || 'low',
    currentApplyReason: item.current_apply_reason || 'still-tentative',
    source: item.source || '/mc/runtime-contract',
    summary: item.summary || 'No pending workflow items.',
  }
}

function normalizeCandidateItem(item = {}) {
  return {
    candidateId: item.candidate_id || '',
    candidateType: item.candidate_type || '',
    targetFile: item.target_file || '',
    status: item.status || 'unknown',
    sourceKind: item.source_kind || '',
    sourceMode: item.source_mode || '',
    actor: item.actor || '',
    sessionId: item.session_id || '',
    runId: item.run_id || '',
    canonicalKey: item.canonical_key || '',
    summary: item.summary || 'Candidate detail',
    reason: item.reason || '',
    evidenceSummary: item.evidence_summary || '',
    supportSummary: item.support_summary || '',
    statusReason: item.status_reason || '',
    proposedValue: item.proposed_value || '',
    writeSection: item.write_section || '',
    confidence: item.confidence || '',
    evidenceClass: item.evidence_class || '',
    supportCount: Number(item.support_count || 0),
    sessionCount: Number(item.session_count || 0),
    mergeCount: Number(item.merge_count || 0),
    applyReadiness: item.apply_readiness || 'low',
    applyReason: item.apply_reason || 'needs-review',
    source: item.source || '/mc/runtime-contract',
    createdAt: item.created_at || '',
    updatedAt: item.updated_at || '',
  }
}

function normalizeContractWrite(item = {}) {
  return {
    writeId: item.write_id || '',
    candidateId: item.candidate_id || '',
    targetFile: item.target_file || '',
    canonicalKey: item.canonical_key || '',
    writeStatus: item.write_status || 'unknown',
    actor: item.actor || '',
    summary: item.summary || 'Contract file write',
    contentLine: item.content_line || '',
    source: item.source || '/mc/runtime-contract',
    createdAt: item.created_at || '',
  }
}

function normalizeHeartbeatState(item = {}) {
  return {
    enabled: Boolean(item.enabled),
    killSwitch: item.kill_switch || 'enabled',
    intervalMinutes: Number(item.interval_minutes || 0),
    scheduleStatus: item.schedule_status || 'unknown',
    scheduleState: item.schedule_state || item.schedule_status || 'unknown',
    due: Boolean(item.due),
    currentlyTicking: Boolean(item.currently_ticking),
    schedulerActive: Boolean(item.scheduler_active),
    schedulerStartedAt: item.scheduler_started_at || '',
    schedulerStoppedAt: item.scheduler_stopped_at || '',
    schedulerHealth: item.scheduler_health || '',
    recoveryStatus: item.recovery_status || '',
    lastRecoveryAt: item.last_recovery_at || '',
    lastTickId: item.last_tick_id || '',
    lastTickAt: item.last_tick_at || '',
    nextTickAt: item.next_tick_at || '',
    lastTriggerSource: item.last_trigger_source || '',
    lastDecisionType: item.last_decision_type || '',
    lastResult: item.last_result || '',
    blockedReason: item.blocked_reason || '',
    provider: item.provider || '',
    model: item.model || '',
    lane: item.lane || '',
    modelSource: item.model_source || '',
    resolutionStatus: item.resolution_status || '',
    fallbackUsed: Boolean(item.fallback_used),
    executionStatus: item.execution_status || '',
    parseStatus: item.parse_status || '',
    budgetStatus: item.budget_status || '',
    policySummary: item.policy_summary || '',
    lastPingEligible: Boolean(item.last_ping_eligible),
    lastPingResult: item.last_ping_result || '',
    lastActionType: item.last_action_type || '',
    lastActionStatus: item.last_action_status || '',
    lastActionSummary: item.last_action_summary || '',
    lastActionArtifact: item.last_action_artifact || '',
    livenessState: item.liveness_state || 'quiet',
    livenessPressure: item.liveness_pressure || 'low',
    livenessReason: item.liveness_reason || '',
    livenessSummary: item.liveness_summary || '',
    livenessConfidence: item.liveness_confidence || 'low',
    livenessThresholdState: item.liveness_threshold_state || 'quiet-threshold',
    livenessScore: Number(item.liveness_score || 0),
    livenessSignalCount: Number(item.liveness_signal_count || 0),
    livenessCorePressureCount: Number(item.liveness_core_pressure_count || 0),
    livenessProposeGateCount: Number(item.liveness_propose_gate_count || 0),
    companionPressureState: item.companion_pressure_state || 'inactive',
    companionPressureReason: item.companion_pressure_reason || 'no-bounded-companion-pressure',
    companionPressureWeight: Number(item.companion_pressure_weight || 0),
    idlePresenceState: item.idle_presence_state || 'inactive',
    checkinWorthiness: item.checkin_worthiness || 'low',
    livenessDebugSummary: item.liveness_debug_summary || '',
    sourceAnchor: item.source_anchor || '',
    plannerAuthorityState: item.planner_authority_state || 'not-planner-authority',
    canonicalSelfState: item.canonical_self_state || 'not-canonical-self-truth',
    summary: item.summary || 'No heartbeat activity yet.',
    stateFile: item.state_file || '',
    source: item.source || '/mc/jarvis::heartbeat',
    updatedAt: item.updated_at || '',
  }
}

function normalizeEmbodiedState(item = {}) {
  const freshness = item.freshness || {}
  const facts = item.facts || {}
  const seamUsage = item.seam_usage || {}

  const normalizeFact = (fact = {}) => ({
    bucket: fact.bucket || 'unavailable',
    source: fact.source || 'unknown',
    load1m: Number(fact.load_1m || 0),
    cpuCount: Number(fact.cpu_count || 0),
    loadPerCpu: Number(fact.load_per_cpu || 0),
    pressureRatio: Number(fact.pressure_ratio || 0),
    totalBytes: Number(fact.total_bytes || 0),
    availableBytes: Number(fact.available_bytes || 0),
    usedRatio: Number(fact.used_ratio || 0),
    freeBytes: Number(fact.free_bytes || 0),
    celsius: Number(fact.celsius || 0),
  })

  return {
    state: item.state || 'unknown',
    primaryState: item.primary_state || item.state || 'unknown',
    strainLevel: item.strain_level || 'unknown',
    recoveryState: item.recovery_state || 'steady',
    stability: item.stability || 'unknown',
    authority: item.authority || 'authoritative',
    visibility: item.visibility || 'internal-only',
    kind: item.kind || 'embodied-runtime-state',
    summary: item.summary || 'No embodied host/body state recorded yet.',
    source: item.source || '/mc/embodied-state',
    builtAt: freshness.built_at || '',
    sampledAt: freshness.sampled_at || '',
    ageSeconds: Number(freshness.age_seconds || 0),
    freshnessState: freshness.state || 'unknown',
    facts: {
      cpu: normalizeFact(facts.cpu || {}),
      memory: normalizeFact(facts.memory || {}),
      disk: normalizeFact(facts.disk || {}),
      thermal: normalizeFact(facts.thermal || {}),
    },
    seamUsage: {
      runtimeSelfModel: Boolean(seamUsage.runtime_self_model),
      missionControlRuntimeTruth: Boolean(seamUsage.mission_control_runtime_truth),
      heartbeatContext: Boolean(seamUsage.heartbeat_context),
      heartbeatPromptGrounding: Boolean(seamUsage.heartbeat_prompt_grounding),
    },
    createdAt: freshness.built_at || freshness.sampled_at || '',
  }
}

function normalizeLoopRuntime(item = {}) {
  const summary = item.summary || {}
  const freshness = item.freshness || {}
  const seamUsage = item.seam_usage || {}

  return {
    active: Boolean(item.active),
    authority: item.authority || 'authoritative',
    visibility: item.visibility || 'internal-only',
    kind: item.kind || 'loop-runtime-state',
    source: item.source || '/mc/loop-runtime',
    summary: {
      activeCount: Number(summary.active_count || 0),
      standbyCount: Number(summary.standby_count || 0),
      resumedCount: Number(summary.resumed_count || 0),
      closedCount: Number(summary.closed_count || 0),
      currentLoop: summary.current_loop || 'No active runtime loop',
      currentStatus: summary.current_status || 'none',
      currentKind: summary.current_kind || 'none',
      currentReason: summary.current_reason || 'none',
      loopCount: Number(summary.loop_count || 0),
    },
    freshnessState: freshness.state || 'unknown',
    builtAt: freshness.built_at || '',
    seamUsage: {
      runtimeSelfModel: Boolean(seamUsage.runtime_self_model),
      missionControlRuntimeTruth: Boolean(seamUsage.mission_control_runtime_truth),
      heartbeatContext: Boolean(seamUsage.heartbeat_context),
      heartbeatPromptGrounding: Boolean(seamUsage.heartbeat_prompt_grounding),
    },
    items: (item.items || []).map((loopItem) => ({
      loopId: loopItem.loop_id || '',
      title: loopItem.title || 'Runtime loop',
      runtimeStatus: loopItem.runtime_status || 'unknown',
      loopKind: loopItem.loop_kind || 'runtime-loop',
      sourceType: loopItem.source_type || '',
      sourceStatus: loopItem.source_status || '',
      canonicalKey: loopItem.canonical_key || '',
      reasonCode: loopItem.reason_code || '',
      summary: loopItem.summary || 'Inspect loop runtime detail',
      updatedAt: loopItem.updated_at || '',
      boundary: loopItem.boundary || 'not-memory-not-identity-not-action',
      source: item.source || '/mc/loop-runtime',
    })),
    createdAt: freshness.built_at || '',
  }
}

function normalizeIdleConsolidation(item = {}) {
  const summary = item.summary || {}
  const cadence = item.cadence || {}
  const lastResult = item.last_result || {}
  const latestArtifact = item.latest_artifact || {}

  return {
    active: Boolean(item.active),
    authority: item.authority || 'authoritative',
    visibility: item.visibility || 'internal-only',
    kind: item.kind || 'sleep-consolidation-light',
    boundary: item.boundary || 'not-memory-not-identity-not-action',
    source: item.source || '/mc/idle-consolidation',
    lastRunAt: item.last_run_at || '',
    builtAt: item.built_at || '',
    cadence: {
      cooldownMinutes: Number(cadence.cooldown_minutes || 0),
      visibleGraceMinutes: Number(cadence.visible_grace_minutes || 0),
      adjacentProducerGraceMinutes: Number(cadence.adjacent_producer_grace_minutes || 0),
      minSourceInputs: Number(cadence.min_source_inputs || 0),
    },
    summary: {
      lastState: summary.last_state || 'idle',
      lastReason: summary.last_reason || 'no-run-yet',
      lastOutputKind: summary.last_output_kind || 'private-brain-sleep-consolidation',
      sourceInputCount: Number(summary.source_input_count || 0),
      latestRecordId: summary.latest_record_id || '',
      latestSummary: summary.latest_summary || 'No idle consolidation artifact recorded yet.',
    },
    lastResult: {
      producer: lastResult.producer || '',
      daemonRan: Boolean(lastResult.daemon_ran),
      consolidationCreated: Boolean(lastResult.consolidation_created),
      consolidationState: lastResult.consolidation_state || 'idle',
      cadenceState: lastResult.cadence_state || '',
      reason: lastResult.reason || 'no-run-yet',
      elapsedMinutes: Number(lastResult.elapsed_minutes || 0),
      outputKind: lastResult.output_kind || '',
      trigger: lastResult.trigger || '',
      recordId: lastResult.record_id || '',
      recordSummary: lastResult.record_summary || '',
      boundary: lastResult.boundary || item.boundary || 'not-memory-not-identity-not-action',
      sourceInputs: (lastResult.source_inputs || []).map((sourceInput) => ({
        source: sourceInput.source || '',
        signal: sourceInput.signal || '',
      })),
    },
    latestArtifact: {
      recordId: latestArtifact.record_id || '',
      recordType: latestArtifact.record_type || '',
      layer: latestArtifact.layer || '',
      sessionId: latestArtifact.session_id || '',
      runId: latestArtifact.run_id || '',
      focus: latestArtifact.focus || '',
      summary: latestArtifact.summary || '',
      detail: latestArtifact.detail || '',
      sourceSignals: latestArtifact.source_signals || '',
      confidence: latestArtifact.confidence || '',
      status: latestArtifact.status || '',
      createdAt: latestArtifact.created_at || '',
      updatedAt: latestArtifact.updated_at || '',
    },
    createdAt: item.last_run_at || item.built_at || '',
  }
}

function normalizeDreamArticulation(item = {}) {
  const summary = item.summary || {}
  const cadence = item.cadence || {}
  const lastResult = item.last_result || {}
  const latestArtifact = item.latest_artifact || {}

  return {
    active: Boolean(item.active),
    authority: item.authority || 'authoritative-runtime-observability',
    visibility: item.visibility || 'internal-only',
    truth: item.truth || 'candidate-only',
    kind: item.kind || 'dream-articulation-light',
    boundary: item.boundary || 'not-memory-not-identity-not-action',
    source: item.source || '/mc/dream-articulation',
    lastRunAt: item.last_run_at || '',
    builtAt: item.built_at || '',
    cadence: {
      cooldownMinutes: Number(cadence.cooldown_minutes || 0),
      visibleGraceMinutes: Number(cadence.visible_grace_minutes || 0),
      adjacentProducerGraceMinutes: Number(cadence.adjacent_producer_grace_minutes || 0),
      minSourceInputs: Number(cadence.min_source_inputs || 0),
    },
    summary: {
      lastState: summary.last_state || 'idle',
      lastReason: summary.last_reason || 'no-run-yet',
      lastOutputKind: summary.last_output_kind || 'runtime-dream-hypothesis',
      sourceInputCount: Number(summary.source_input_count || 0),
      latestSignalId: summary.latest_signal_id || '',
      latestSummary: summary.latest_summary || 'No dream articulation candidate recorded yet.',
      candidateTruth: summary.candidate_truth || item.truth || 'candidate-only',
    },
    lastResult: {
      producer: lastResult.producer || '',
      daemonRan: Boolean(lastResult.daemon_ran),
      candidateCreated: Boolean(lastResult.candidate_created),
      candidateState: lastResult.candidate_state || 'idle',
      cadenceState: lastResult.cadence_state || '',
      reason: lastResult.reason || 'no-run-yet',
      elapsedMinutes: Number(lastResult.elapsed_minutes || 0),
      outputKind: lastResult.output_kind || '',
      trigger: lastResult.trigger || '',
      signalId: lastResult.signal_id || '',
      signalSummary: lastResult.signal_summary || '',
      signalType: lastResult.signal_type || '',
      candidateTruth: lastResult.candidate_truth || item.truth || 'candidate-only',
      candidateVisibility: lastResult.candidate_visibility || item.visibility || 'internal-only',
      boundary: lastResult.boundary || item.boundary || 'not-memory-not-identity-not-action',
      sourceInputs: (lastResult.source_inputs || []).map((sourceInput) => ({
        source: sourceInput.source || '',
        signal: sourceInput.signal || '',
      })),
    },
    latestArtifact: {
      signalId: latestArtifact.signal_id || '',
      signalType: latestArtifact.signal_type || '',
      canonicalKey: latestArtifact.canonical_key || '',
      title: latestArtifact.title || '',
      summary: latestArtifact.summary || '',
      rationale: latestArtifact.rationale || '',
      confidence: latestArtifact.confidence || '',
      supportCount: Number(latestArtifact.support_count || 0),
      sourceKind: latestArtifact.source_kind || '',
      status: latestArtifact.status || '',
      createdAt: latestArtifact.created_at || '',
      updatedAt: latestArtifact.updated_at || '',
    },
    createdAt: item.last_run_at || item.built_at || '',
  }
}

function normalizePromptEvolution(item = {}) {
  const summary = item.summary || {}
  const cadence = item.cadence || {}
  const lastResult = item.last_result || {}
  const latestProposal = item.latest_proposal || {}
  const learningInfluence = item.learning_influence || {}
  const dreamInfluence = item.dream_influence || {}
  const fragmentGrounding = item.fragment_grounding || {}
  const reviewLight = item.review_light || {}

  return {
    active: Boolean(item.active),
    authority: item.authority || 'authoritative-runtime-observability',
    visibility: item.visibility || 'internal-only',
    truth: item.truth || 'candidate-only',
    proposalMode: item.proposal_mode || 'proposal-only',
    kind: item.kind || 'runtime-prompt-evolution-light',
    boundary: item.boundary || 'not-memory-not-identity-not-action-not-applied-prompt',
    source: item.source || '/mc/prompt-evolution',
    lastRunAt: item.last_run_at || '',
    builtAt: item.built_at || '',
    cadence: {
      cooldownMinutes: Number(cadence.cooldown_minutes || 0),
      visibleGraceMinutes: Number(cadence.visible_grace_minutes || 0),
      adjacentProducerGraceMinutes: Number(cadence.adjacent_producer_grace_minutes || 0),
      minSourceInputs: Number(cadence.min_source_inputs || 0),
    },
    summary: {
      lastState: summary.last_state || 'idle',
      lastReason: summary.last_reason || 'no-run-yet',
      lastOutputKind: summary.last_output_kind || 'self-authored-prompt-proposal',
      sourceInputCount: Number(summary.source_input_count || 0),
      latestProposalId: summary.latest_proposal_id || '',
      latestSummary: summary.latest_summary || 'No runtime prompt proposal recorded yet.',
      latestTargetAsset: summary.latest_target_asset || 'none',
      latestPromptTarget: summary.latest_prompt_target || 'none',
      latestLearningMode: summary.latest_learning_mode || 'none',
      latestReinforcementTarget: summary.latest_reinforcement_target || 'none',
      latestRetentionBias: summary.latest_retention_bias || 'light',
      latestDreamInfluenceState: summary.latest_dream_influence_state || dreamInfluence.influence_state || 'quiet',
      latestDreamInfluenceTarget: summary.latest_dream_influence_target || dreamInfluence.influence_target || 'none',
      latestDreamInfluenceMode: summary.latest_dream_influence_mode || dreamInfluence.influence_mode || 'stabilize',
      latestCandidateFragment: summary.latest_candidate_fragment || '',
      proposalDirection: summary.proposal_direction || reviewLight.proposal_direction || 'none',
      proposedChangeKind: summary.proposed_change_kind || reviewLight.proposed_change_kind || 'none',
      diffLightSummary: summary.diff_light_summary || reviewLight.diff_light_summary || '',
      fragmentTruth: summary.fragment_truth || item.fragment_truth || 'proposal-only',
      proposalTruth: summary.proposal_truth || item.proposal_mode || 'proposal-only',
    },
    learningInfluence: {
      learningEngineMode: learningInfluence.learning_engine_mode || 'none',
      reinforcementTarget: learningInfluence.reinforcement_target || 'none',
      retentionBias: learningInfluence.retention_bias || 'light',
      attenuationBias: learningInfluence.attenuation_bias || 'none',
      maturationState: learningInfluence.maturation_state || 'early',
    },
    dreamInfluence: {
      influenceState: dreamInfluence.influence_state || 'quiet',
      influenceTarget: dreamInfluence.influence_target || 'none',
      influenceMode: dreamInfluence.influence_mode || 'stabilize',
      influenceStrength: dreamInfluence.influence_strength || 'none',
      influenceHint: dreamInfluence.influence_hint || 'none',
    },
    candidateFragment: item.candidate_fragment || '',
    fragmentGrounding: {
      adaptiveLearning: fragmentGrounding.adaptive_learning || 'none',
      dreamInfluence: fragmentGrounding.dream_influence || 'none',
      guidedLearning: fragmentGrounding.guided_learning || 'none',
      adaptiveReasoning: fragmentGrounding.adaptive_reasoning || 'none',
    },
    fragmentTruth: item.fragment_truth || 'proposal-only',
    fragmentVisibility: item.fragment_visibility || item.visibility || 'internal-only',
    reviewLight: {
      proposalDirection: reviewLight.proposal_direction || 'none',
      proposedChangeKind: reviewLight.proposed_change_kind || 'none',
      diffLightSummary: reviewLight.diff_light_summary || '',
      reviewHint: reviewLight.review_hint || '',
    },
    lastResult: {
      producer: lastResult.producer || '',
      daemonRan: Boolean(lastResult.daemon_ran),
      proposalCreated: Boolean(lastResult.proposal_created),
      proposalState: lastResult.proposal_state || 'idle',
      cadenceState: lastResult.cadence_state || '',
      reason: lastResult.reason || 'no-run-yet',
      elapsedMinutes: Number(lastResult.elapsed_minutes || 0),
      outputKind: lastResult.output_kind || '',
      trigger: lastResult.trigger || '',
      proposalId: lastResult.proposal_id || '',
      proposalType: lastResult.proposal_type || '',
      proposalSummary: lastResult.proposal_summary || '',
      targetAsset: lastResult.target_asset || '',
      candidateFragment: lastResult.candidate_fragment || item.candidate_fragment || '',
      reviewLight: {
        proposalDirection: (lastResult.review_light || {}).proposal_direction || reviewLight.proposal_direction || 'none',
        proposedChangeKind: (lastResult.review_light || {}).proposed_change_kind || reviewLight.proposed_change_kind || 'none',
        diffLightSummary: (lastResult.review_light || {}).diff_light_summary || reviewLight.diff_light_summary || '',
        reviewHint: (lastResult.review_light || {}).review_hint || reviewLight.review_hint || '',
      },
      proposalTruth: lastResult.proposal_truth || item.proposal_mode || 'proposal-only',
      proposalVisibility: lastResult.proposal_visibility || item.visibility || 'internal-only',
      boundary: lastResult.boundary || item.boundary || 'not-memory-not-identity-not-action-not-applied-prompt',
      sourceInputs: (lastResult.source_inputs || []).map((sourceInput) => ({
        source: sourceInput.source || '',
        signal: sourceInput.signal || '',
      })),
    },
    latestProposal: {
      proposalId: latestProposal.proposal_id || '',
      proposalType: latestProposal.proposal_type || '',
      canonicalKey: latestProposal.canonical_key || '',
      status: latestProposal.status || '',
      title: latestProposal.title || '',
      summary: latestProposal.summary || '',
      rationale: latestProposal.rationale || '',
      sourceKind: latestProposal.source_kind || '',
      confidence: latestProposal.confidence || '',
      evidenceSummary: latestProposal.evidence_summary || '',
      supportSummary: latestProposal.support_summary || '',
      statusReason: latestProposal.status_reason || '',
      supportCount: Number(latestProposal.support_count || 0),
      sessionCount: Number(latestProposal.session_count || 0),
      createdAt: latestProposal.created_at || '',
      updatedAt: latestProposal.updated_at || '',
    },
    createdAt: item.last_run_at || item.built_at || '',
  }
}

function normalizeExperientialRuntimeContext(item = {}) {
  const seamUsage = item.seam_usage || {}
  const embodied = item.embodied_translation || {}
  const affective = item.affective_translation || {}
  const intermittence = item.intermittence_translation || {}
  const contextPressure = item.context_pressure_translation || {}

  return {
    authority: item.authority || 'derived-runtime-truth',
    visibility: item.visibility || 'internal-only',
    kind: item.kind || 'experiential-runtime-context',
    summary: item.summary || '',
    narrativeLines: item.narrative_lines || [],
    embodiedTranslation: {
      state: embodied.state || 'steady',
      initiativeGate: embodied.initiative_gate || 'clear',
      narrative: embodied.narrative || '',
    },
    affectiveTranslation: {
      state: affective.state || 'settled',
      bearing: affective.bearing || 'even',
      narrative: affective.narrative || '',
    },
    intermittenceTranslation: {
      state: intermittence.state || 'continuous',
      gapMinutes: Number(intermittence.gap_minutes || 0),
      narrative: intermittence.narrative || '',
    },
    contextPressureTranslation: {
      state: contextPressure.state || 'clear',
      continuityPressure: contextPressure.continuity_pressure || 'low',
      narrative: contextPressure.narrative || '',
    },
    seamUsage: {
      heartbeatRuntimeTruth: Boolean(seamUsage.heartbeat_runtime_truth),
      heartbeatPromptGrounding: Boolean(seamUsage.heartbeat_prompt_grounding),
      runtimeSelfModel: Boolean(seamUsage.runtime_self_model),
      missionControlRuntimeTruth: Boolean(seamUsage.mission_control_runtime_truth),
    },
    source: item.source || '/mc/experiential-runtime-context',
    builtAt: item.built_at || '',
    createdAt: item.built_at || '',
  }
}

function normalizeAffectiveMetaState(item = {}) {
  const freshness = item.freshness || {}
  const seamUsage = item.seam_usage || {}

  return {
    state: item.state || 'unknown',
    bearing: item.bearing || 'unknown',
    monitoringMode: item.monitoring_mode || 'unknown',
    reflectiveLoad: item.reflective_load || 'low',
    authority: item.authority || 'derived-runtime-truth',
    visibility: item.visibility || 'internal-only',
    kind: item.kind || 'affective-meta-runtime-state',
    summary: item.summary || 'No affective/meta runtime orientation recorded yet.',
    source: item.source || '/mc/affective-meta-state',
    sourceContributors: (item.source_contributors || []).map((sourceInput) => ({
      source: sourceInput.source || '',
      signal: sourceInput.signal || '',
    })),
    seamUsage: {
      runtimeSelfModel: Boolean(seamUsage.runtime_self_model),
      missionControlRuntimeTruth: Boolean(seamUsage.mission_control_runtime_truth),
      heartbeatContext: Boolean(seamUsage.heartbeat_context),
      heartbeatPromptGrounding: Boolean(seamUsage.heartbeat_prompt_grounding),
    },
    builtAt: freshness.built_at || '',
    freshnessState: freshness.state || 'unknown',
    createdAt: freshness.built_at || '',
  }
}

function normalizeEpistemicRuntimeState(item = {}) {
  const freshness = item.freshness || {}
  const seamUsage = item.seam_usage || {}

  return {
    wrongnessState: item.wrongness_state || 'clear',
    regretSignal: item.regret_signal || 'none',
    counterfactualMode: item.counterfactual_mode || 'none',
    counterfactualHint: item.counterfactual_hint || 'none',
    confidence: item.confidence || 'low',
    authority: item.authority || 'derived-runtime-truth',
    visibility: item.visibility || 'internal-only',
    boundary: item.boundary || 'not-memory-not-identity-not-action',
    kind: item.kind || 'epistemic-runtime-state',
    summary: item.summary || 'No epistemic runtime state recorded yet.',
    source: item.source || '/mc/epistemic-runtime-state',
    sourceContributors: (item.source_contributors || []).map((sourceInput) => ({
      source: sourceInput.source || '',
      signal: sourceInput.signal || '',
    })),
    seamUsage: {
      runtimeSelfModel: Boolean(seamUsage.runtime_self_model),
      missionControlRuntimeTruth: Boolean(seamUsage.mission_control_runtime_truth),
      heartbeatContext: Boolean(seamUsage.heartbeat_context),
      heartbeatPromptGrounding: Boolean(seamUsage.heartbeat_prompt_grounding),
    },
    builtAt: freshness.built_at || '',
    freshnessState: freshness.state || 'unknown',
    createdAt: freshness.built_at || '',
  }
}

function normalizeSubagentEcology(item = {}) {
  const summary = item.summary || {}
  const freshness = item.freshness || {}
  const seamUsage = item.seam_usage || {}

  return {
    authority: item.authority || 'derived-runtime-truth',
    visibility: item.visibility || 'internal-only',
    internalOnly: item.internal_only !== false,
    toolAccess: item.tool_access || 'none',
    boundary: item.boundary || 'not-memory-not-identity-not-action-not-tool-execution',
    kind: item.kind || 'subagent-ecology-light',
    summaryText: item.summary_text || 'No internal helper roles currently active.',
    source: item.source || '/mc/subagent-ecology',
    roles: (item.roles || []).map((role) => ({
      roleName: role.role_name || '',
      roleKind: role.role_kind || 'internal-role',
      currentStatus: role.current_status || 'idle',
      lastActivationAt: role.last_activation_at || '',
      activationReason: role.activation_reason || '',
      internalOnly: role.internal_only !== false,
      toolAccess: role.tool_access || 'none',
      influenceScope: role.influence_scope || 'bounded',
    })),
    summary: {
      roleCount: Number(summary.role_count || 0),
      activeCount: Number(summary.active_count || 0),
      idleCount: Number(summary.idle_count || 0),
      coolingCount: Number(summary.cooling_count || 0),
      blockedCount: Number(summary.blocked_count || 0),
      lastActiveRoleName: summary.last_active_role_name || 'none',
      lastActiveRoleStatus: summary.last_active_role_status || 'none',
      lastActivationReason: summary.last_activation_reason || 'none',
    },
    sourceContributors: (item.source_contributors || []).map((sourceInput) => ({
      source: sourceInput.source || '',
      signal: sourceInput.signal || '',
    })),
    seamUsage: {
      runtimeSelfModel: Boolean(seamUsage.runtime_self_model),
      missionControlRuntimeTruth: Boolean(seamUsage.mission_control_runtime_truth),
      heartbeatContext: Boolean(seamUsage.heartbeat_context),
      heartbeatPromptGrounding: Boolean(seamUsage.heartbeat_prompt_grounding),
    },
    builtAt: freshness.built_at || '',
    freshnessState: freshness.state || 'unknown',
    createdAt: freshness.built_at || '',
  }
}

function normalizeCouncilRuntime(item = {}) {
  const freshness = item.freshness || {}
  const seamUsage = item.seam_usage || {}

  return {
    councilState: item.council_state || 'quiet',
    participatingRoles: item.participating_roles || [],
    rolePositions: (item.role_positions || []).map((role) => ({
      roleName: role.role_name || '',
      roleKind: role.role_kind || 'internal-role',
      status: role.status || 'idle',
      position: role.position || 'hold',
      activationReason: role.activation_reason || '',
      toolAccess: role.tool_access || 'none',
      internalOnly: role.internal_only !== false,
    })),
    divergenceLevel: item.divergence_level || 'low',
    recommendation: item.recommendation || 'hold',
    recommendationReason: item.recommendation_reason || '',
    confidence: item.confidence || 'low',
    authority: item.authority || 'derived-runtime-truth',
    visibility: item.visibility || 'internal-only',
    internalOnly: item.internal_only !== false,
    toolAccess: item.tool_access || 'none',
    influenceScope: item.influence_scope || 'bounded',
    boundary: item.boundary || 'not-memory-not-identity-not-action-not-tool-execution',
    kind: item.kind || 'council-runtime-light',
    summary: item.summary || 'No bounded council runtime state recorded yet.',
    source: item.source || '/mc/council-runtime',
    sourceContributors: (item.source_contributors || []).map((sourceInput) => ({
      source: sourceInput.source || '',
      signal: sourceInput.signal || '',
    })),
    seamUsage: {
      runtimeSelfModel: Boolean(seamUsage.runtime_self_model),
      missionControlRuntimeTruth: Boolean(seamUsage.mission_control_runtime_truth),
      heartbeatContext: Boolean(seamUsage.heartbeat_context),
      heartbeatPromptGrounding: Boolean(seamUsage.heartbeat_prompt_grounding),
    },
    builtAt: freshness.built_at || item.last_council_at || '',
    freshnessState: freshness.state || 'unknown',
    createdAt: freshness.built_at || item.last_council_at || '',
  }
}

function normalizeAdaptivePlanner(item = {}) {
  const freshness = item.freshness || {}
  const seamUsage = item.seam_usage || {}

  return {
    plannerMode: item.planner_mode || 'incremental',
    planHorizon: item.plan_horizon || 'near',
    planningPosture: item.planning_posture || 'staged',
    riskPosture: item.risk_posture || 'balanced',
    nextPlanningBias: item.next_planning_bias || 'stepwise-progress',
    confidence: item.confidence || 'low',
    authority: item.authority || 'derived-runtime-truth',
    visibility: item.visibility || 'internal-only',
    boundary: item.boundary || 'not-memory-not-identity-not-action',
    kind: item.kind || 'adaptive-planner-runtime-state',
    summary: item.summary || 'No bounded adaptive planner state recorded yet.',
    source: item.source || '/mc/adaptive-planner',
    sourceContributors: (item.source_contributors || []).map((sourceInput) => ({
      source: sourceInput.source || '',
      signal: sourceInput.signal || '',
    })),
    seamUsage: {
      runtimeSelfModel: Boolean(seamUsage.runtime_self_model),
      missionControlRuntimeTruth: Boolean(seamUsage.mission_control_runtime_truth),
      heartbeatContext: Boolean(seamUsage.heartbeat_context),
      heartbeatPromptGrounding: Boolean(seamUsage.heartbeat_prompt_grounding),
    },
    builtAt: freshness.built_at || '',
    freshnessState: freshness.state || 'unknown',
    createdAt: freshness.built_at || '',
  }
}

function normalizeAdaptiveReasoning(item = {}) {
  const freshness = item.freshness || {}
  const seamUsage = item.seam_usage || {}

  return {
    reasoningMode: item.reasoning_mode || 'direct',
    reasoningPosture: item.reasoning_posture || 'balanced',
    certaintyStyle: item.certainty_style || 'cautious',
    explorationBias: item.exploration_bias || 'minimal',
    constraintBias: item.constraint_bias || 'moderate',
    confidence: item.confidence || 'low',
    authority: item.authority || 'derived-runtime-truth',
    visibility: item.visibility || 'internal-only',
    boundary: item.boundary || 'not-memory-not-identity-not-action',
    kind: item.kind || 'adaptive-reasoning-runtime-state',
    summary: item.summary || 'No bounded adaptive reasoning state recorded yet.',
    source: item.source || '/mc/adaptive-reasoning',
    sourceContributors: (item.source_contributors || []).map((sourceInput) => ({
      source: sourceInput.source || '',
      signal: sourceInput.signal || '',
    })),
    seamUsage: {
      runtimeSelfModel: Boolean(seamUsage.runtime_self_model),
      missionControlRuntimeTruth: Boolean(seamUsage.mission_control_runtime_truth),
      heartbeatContext: Boolean(seamUsage.heartbeat_context),
      heartbeatPromptGrounding: Boolean(seamUsage.heartbeat_prompt_grounding),
    },
    builtAt: freshness.built_at || '',
    freshnessState: freshness.state || 'unknown',
    createdAt: freshness.built_at || '',
  }
}

function normalizeDreamInfluence(item = {}) {
  const freshness = item.freshness || {}
  const seamUsage = item.seam_usage || {}

  return {
    influenceState: item.influence_state || 'quiet',
    influenceTarget: item.influence_target || 'none',
    influenceMode: item.influence_mode || 'stabilize',
    influenceStrength: item.influence_strength || 'none',
    influenceHint: item.influence_hint || 'no-bounded-dream-pull',
    confidence: item.confidence || 'low',
    authority: item.authority || 'derived-runtime-truth',
    visibility: item.visibility || 'internal-only',
    boundary: item.boundary || 'not-memory-not-identity-not-action',
    kind: item.kind || 'dream-influence-runtime-state',
    summary: item.summary || 'No bounded dream influence state recorded yet.',
    source: item.source || '/mc/dream-influence',
    sourceContributors: (item.source_contributors || []).map((sourceInput) => ({
      source: sourceInput.source || '',
      signal: sourceInput.signal || '',
    })),
    seamUsage: {
      guidedLearningEnrichment: Boolean(seamUsage.guided_learning_enrichment),
      runtimeSelfModel: Boolean(seamUsage.runtime_self_model),
      missionControlRuntimeTruth: Boolean(seamUsage.mission_control_runtime_truth),
      heartbeatContext: Boolean(seamUsage.heartbeat_context),
      heartbeatPromptGrounding: Boolean(seamUsage.heartbeat_prompt_grounding),
    },
    builtAt: freshness.built_at || '',
    freshnessState: freshness.state || 'unknown',
    createdAt: freshness.built_at || '',
  }
}

function normalizeGuidedLearning(item = {}) {
  const freshness = item.freshness || {}
  const seamUsage = item.seam_usage || {}

  return {
    learningMode: item.learning_mode || 'reinforce',
    learningFocus: item.learning_focus || 'reasoning',
    learningPosture: item.learning_posture || 'gentle',
    nextLearningBias: item.next_learning_bias || 'keep-current-shape',
    learningPressure: item.learning_pressure || 'low',
    confidence: item.confidence || 'low',
    authority: item.authority || 'derived-runtime-truth',
    visibility: item.visibility || 'internal-only',
    boundary: item.boundary || 'not-memory-not-identity-not-action',
    kind: item.kind || 'guided-learning-runtime-state',
    summary: item.summary || 'No bounded guided learning state recorded yet.',
    source: item.source || '/mc/guided-learning',
    sourceContributors: (item.source_contributors || []).map((sourceInput) => ({
      source: sourceInput.source || '',
      signal: sourceInput.signal || '',
    })),
    seamUsage: {
      runtimeSelfModel: Boolean(seamUsage.runtime_self_model),
      missionControlRuntimeTruth: Boolean(seamUsage.mission_control_runtime_truth),
      heartbeatContext: Boolean(seamUsage.heartbeat_context),
      heartbeatPromptGrounding: Boolean(seamUsage.heartbeat_prompt_grounding),
    },
    builtAt: freshness.built_at || '',
    freshnessState: freshness.state || 'unknown',
    createdAt: freshness.built_at || '',
  }
}

function normalizeAdaptiveLearning(item = {}) {
  const freshness = item.freshness || {}
  const seamUsage = item.seam_usage || {}

  return {
    learningEngineMode: item.learning_engine_mode || 'retain',
    reinforcementTarget: item.reinforcement_target || 'reasoning',
    retentionBias: item.retention_bias || 'light',
    attenuationBias: item.attenuation_bias || 'none',
    maturationState: item.maturation_state || 'early',
    confidence: item.confidence || 'low',
    authority: item.authority || 'derived-runtime-truth',
    visibility: item.visibility || 'internal-only',
    boundary: item.boundary || 'not-memory-not-identity-not-action',
    kind: item.kind || 'adaptive-learning-runtime-state',
    summary: item.summary || 'No bounded adaptive learning state recorded yet.',
    source: item.source || '/mc/adaptive-learning',
    sourceContributors: (item.source_contributors || []).map((sourceInput) => ({
      source: sourceInput.source || '',
      signal: sourceInput.signal || '',
    })),
    seamUsage: {
      runtimeSelfModel: Boolean(seamUsage.runtime_self_model),
      missionControlRuntimeTruth: Boolean(seamUsage.mission_control_runtime_truth),
      heartbeatContext: Boolean(seamUsage.heartbeat_context),
      heartbeatPromptGrounding: Boolean(seamUsage.heartbeat_prompt_grounding),
      guidedLearningEnrichment: Boolean(seamUsage.guided_learning_enrichment),
    },
    builtAt: freshness.built_at || '',
    freshnessState: freshness.state || 'unknown',
    createdAt: freshness.built_at || '',
  }
}

function normalizeSelfSystemCodeAwareness(item = {}) {
  const repoObservation = item.repo_observation || {}
  const hostContext = item.host_context || {}
  const seamUsage = item.seam_usage || []

  return {
    systemAwarenessState: item.system_awareness_state || 'host-limited',
    codeAwarenessState: item.code_awareness_state || 'repo-unavailable',
    repoStatus: item.repo_status || 'not-git',
    localChangeState: item.local_change_state || 'unknown',
    upstreamAwareness: item.upstream_awareness || 'unknown',
    concernState: item.concern_state || 'notice',
    concernHint: item.concern_hint || 'No bounded system/code concern recorded yet.',
    actionRequiresApproval: item.action_requires_approval !== false,
    confidence: item.confidence || 'low',
    authority: item.authority || 'derived-runtime-truth',
    visibility: item.visibility || 'internal-only',
    truth: item.truth || 'read-only-observation',
    kind: item.kind || 'self-system-code-awareness-light',
    observationMode: item.observation_mode || 'read-only',
    approvalBoundary: item.approval_boundary || 'Observation is read-only and any repo/system action would require approval.',
    sourceContributors: (item.source_contributors || []).map((source) => ({ source: String(source || ''), signal: '' })),
    source: item.source || '/mc/self-system-code-awareness',
    seamUsage: {
      heartbeatGrounding: Array.isArray(seamUsage) ? seamUsage.includes('heartbeat-grounding') : Boolean(seamUsage.heartbeat_grounding),
      promptContractRuntimeTruth: Array.isArray(seamUsage) ? seamUsage.includes('prompt-contract-runtime-truth') : Boolean(seamUsage.prompt_contract_runtime_truth),
      runtimeSelfModel: Array.isArray(seamUsage) ? seamUsage.includes('runtime-self-model') : Boolean(seamUsage.runtime_self_model),
      missionControlRuntime: Array.isArray(seamUsage) ? seamUsage.includes('mission-control-runtime') : Boolean(seamUsage.mission_control_runtime),
    },
    repoObservation: {
      branchName: repoObservation.branch_name || 'none',
      upstreamRef: repoObservation.upstream_ref || '',
      aheadCount: Number(repoObservation.ahead_count || 0),
      behindCount: Number(repoObservation.behind_count || 0),
      dirtyWorkingTree: Boolean(repoObservation.dirty_working_tree),
      untrackedPresent: Boolean(repoObservation.untracked_present),
      modifiedPresent: Boolean(repoObservation.modified_present),
      recentLocalChangesPresent: Boolean(repoObservation.recent_local_changes_present),
      repoRootDetected: Boolean(repoObservation.repo_root_detected),
      approvalRequiredCapabilityCount: Number(repoObservation.approval_required_capability_count || 0),
    },
    hostContext: {
      hostname: hostContext.hostname || '',
      platform: hostContext.platform || 'unknown',
      cwd: hostContext.cwd || '',
      workspaceRoot: hostContext.workspace_root || '',
      repoRoot: hostContext.repo_root || '',
      gitPresent: Boolean(hostContext.git_present),
    },
    builtAt: item.built_at || '',
    createdAt: item.built_at || '',
  }
}

function normalizeToolIntent(item = {}) {
  const mutationTargetFiles = Array.isArray(item.mutation_target_files)
    ? item.mutation_target_files.filter(Boolean)
    : []
  const mutationTargetPaths = Array.isArray(item.mutation_target_paths)
    ? item.mutation_target_paths.filter(Boolean)
    : []
  const hasMutationIntentSurface = [
    'mutation_intent_state',
    'mutation_intent_classification',
    'mutation_near',
    'mutation_target_files',
    'mutation_target_paths',
    'mutation_repo_scope',
    'mutation_system_scope',
    'mutation_sudo_required',
    'mutation_critical',
    'mutation_execution_permitted',
  ].some((key) => Object.prototype.hasOwnProperty.call(item, key))
  const hasMutatingExecProposalSurface = [
    'mutating_exec_proposal_state',
    'mutating_exec_proposal_command',
    'mutating_exec_proposal_summary',
    'mutating_exec_proposal_scope',
    'mutating_exec_proposal_reason',
    'mutating_exec_requires_approval',
    'mutating_exec_requires_sudo',
    'mutating_exec_criticality',
  ].some((key) => Object.prototype.hasOwnProperty.call(item, key))
  const hasSudoExecProposalSurface = [
    'sudo_exec_proposal_state',
    'sudo_exec_proposal_command',
    'sudo_exec_proposal_summary',
    'sudo_exec_proposal_scope',
    'sudo_exec_proposal_reason',
    'sudo_exec_requires_approval',
    'sudo_exec_requires_sudo',
    'sudo_exec_criticality',
  ].some((key) => Object.prototype.hasOwnProperty.call(item, key))
  const hasSudoApprovalWindowSurface = [
    'sudo_approval_window_state',
    'sudo_approval_window_scope',
    'sudo_approval_window_started_at',
    'sudo_approval_window_expires_at',
    'sudo_approval_window_remaining_seconds',
    'sudo_approval_window_source',
    'sudo_approval_window_reusable',
  ].some((key) => Object.prototype.hasOwnProperty.call(item, key))
  const hasMutatingExecExecutionSurface = (
    String(item.execution_mode || '') === 'mutating-exec'
    || String(item.execution_state || '').startsWith('mutating-exec-')
  )
  const mutatingExecRepoStewardshipDomain = item.mutating_exec_repo_stewardship_domain || 'none'
  const mutatingExecGitMutationClass = item.mutating_exec_git_mutation_class || 'none'
  const hasGitRepoStewardshipProposalSurface = (
    hasMutatingExecProposalSurface
    && mutatingExecRepoStewardshipDomain === 'git'
    && mutatingExecGitMutationClass !== 'none'
  )
  const mutatingExecExecutionState = hasMutatingExecExecutionSurface
    ? (item.execution_state || 'mutating-exec')
    : 'not-executed'
  const mutatingExecExecutionCommand = hasMutatingExecExecutionSurface
    ? (
      item.mutating_exec_proposal_command
      || item.execution_target
      || ''
    )
    : ''
  const mutatingExecExecutionSucceeded = mutatingExecExecutionState === 'mutating-exec-completed'
  const mutatingExecApprovalMatched = Boolean(
    hasMutatingExecExecutionSurface
    && item.approval_state === 'approved'
    && !item.mutating_exec_requires_sudo
  )

  return {
    intentState: item.intent_state || 'idle',
    intentType: item.intent_type || 'inspect-repo-status',
    intentTarget: item.intent_target || 'workspace',
    intentReason: item.intent_reason || 'No bounded tool intent is active right now.',
    approvalRequired: item.approval_required !== false,
    approvalState: item.approval_state || 'none',
    approvalSource: item.approval_source || 'none',
    approvalScope: item.approval_scope || 'repo-read',
    approvalRequestedAt: item.approval_requested_at || '',
    approvalExpiresAt: item.approval_expires_at || '',
    approvalResolvedAt: item.approval_resolved_at || '',
    approvalResolutionReason: item.approval_resolution_reason || '',
    approvalResolutionMessage: item.approval_resolution_message || '',
    approvalLifecycle: item.approval_lifecycle || 'bounded-approval-surface-light',
    approvalSemantics: item.approval_semantics || {},
    urgency: item.urgency || 'low',
    confidence: item.confidence || 'low',
    authority: item.authority || 'derived-runtime-truth',
    visibility: item.visibility || 'internal-only',
    truth: item.truth || 'proposal-only',
    kind: item.kind || 'approval-gated-tool-intent-light',
    executionState: item.execution_state || 'not-executed',
    executionMode: item.execution_mode || 'read-only',
    executionTarget: item.execution_target || item.intent_target || 'workspace',
    executionSummary: item.execution_summary || 'No bounded repo inspection has been executed.',
    executionStartedAt: item.execution_started_at || '',
    executionFinishedAt: item.execution_finished_at || '',
    executionConfidence: item.execution_confidence || item.confidence || 'low',
    executionOperation: item.execution_operation || item.intent_type || 'inspect-repo-status',
    executionExcerpt: Array.isArray(item.execution_excerpt) ? item.execution_excerpt : [],
    mutationPermitted: Boolean(item.mutation_permitted),
    hasMutationIntentSurface,
    mutationIntentState: item.mutation_intent_state || 'idle',
    mutationIntentClassification: item.mutation_intent_classification || 'none',
    mutationNear: Boolean(item.mutation_near),
    mutationProposalOnly: Boolean(item.mutation_proposal_only),
    mutationExecutionState: item.mutation_execution_state || 'not-executed',
    mutationExecutionPermitted: Boolean(item.mutation_execution_permitted),
    mutationSummary: item.mutation_summary || '',
    mutationTargetFiles,
    mutationTargetPaths,
    mutationRepoScope: item.mutation_repo_scope || '',
    mutationSystemScope: item.mutation_system_scope || '',
    mutationSudoRequired: Boolean(item.mutation_sudo_required),
    mutationCritical: Boolean(item.mutation_critical),
    mutationBoundary: item.mutation_boundary || '',
    hasMutatingExecProposalSurface,
    hasSudoExecProposalSurface,
    hasSudoApprovalWindowSurface,
    hasMutatingExecExecutionSurface,
    hasGitRepoStewardshipProposalSurface,
    mutatingExecProposalState: item.mutating_exec_proposal_state || 'none',
    mutatingExecProposalCommand: item.mutating_exec_proposal_command || '',
    mutatingExecProposalSummary: item.mutating_exec_proposal_summary || '',
    mutatingExecProposalScope: item.mutating_exec_proposal_scope || 'none',
    mutatingExecProposalReason: item.mutating_exec_proposal_reason || '',
    mutatingExecRequiresApproval: Boolean(item.mutating_exec_requires_approval),
    mutatingExecRequiresSudo: Boolean(item.mutating_exec_requires_sudo),
    mutatingExecCriticality: item.mutating_exec_criticality || 'none',
    mutatingExecConfidence: item.mutating_exec_confidence || 'low',
    mutatingExecCommandFingerprint: item.mutating_exec_command_fingerprint || '',
    mutatingExecRepoStewardshipDomain,
    mutatingExecGitMutationClass,
    mutatingExecExecutionState,
    mutatingExecExecutionCommand,
    mutatingExecExecutionScope: item.mutating_exec_proposal_scope || 'none',
    mutatingExecExecutionSucceeded,
    mutatingExecApprovalMatched,
    mutatingExecSourceContributors: Array.isArray(item.mutating_exec_source_contributors)
      ? item.mutating_exec_source_contributors.filter(Boolean)
      : [],
    sudoExecProposalState: item.sudo_exec_proposal_state || 'none',
    sudoExecProposalCommand: item.sudo_exec_proposal_command || '',
    sudoExecProposalSummary: item.sudo_exec_proposal_summary || '',
    sudoExecProposalScope: item.sudo_exec_proposal_scope || 'none',
    sudoExecProposalReason: item.sudo_exec_proposal_reason || '',
    sudoExecRequiresApproval: Boolean(item.sudo_exec_requires_approval),
    sudoExecRequiresSudo: Boolean(item.sudo_exec_requires_sudo),
    sudoExecCriticality: item.sudo_exec_criticality || 'none',
    sudoExecConfidence: item.sudo_exec_confidence || 'low',
    sudoExecCommandFingerprint: item.sudo_exec_command_fingerprint || '',
    sudoExecSourceContributors: Array.isArray(item.sudo_exec_source_contributors)
      ? item.sudo_exec_source_contributors.filter(Boolean)
      : [],
    sudoApprovalWindowState: item.sudo_approval_window_state || 'none',
    sudoApprovalWindowScope: item.sudo_approval_window_scope || 'none',
    sudoApprovalWindowStartedAt: item.sudo_approval_window_started_at || '',
    sudoApprovalWindowExpiresAt: item.sudo_approval_window_expires_at || '',
    sudoApprovalWindowRemainingSeconds: Number(item.sudo_approval_window_remaining_seconds || 0),
    sudoApprovalWindowSource: item.sudo_approval_window_source || 'none',
    sudoApprovalWindowReusable: Boolean(item.sudo_approval_window_reusable),
    boundary: item.boundary || 'Intent is proposal-only and approval-gated; no action has been performed.',
    sourceContributors: (item.source_contributors || []).map((source) => ({ source: String(source || ''), signal: '' })),
    source: item.source || '/mc/tool-intent',
    seamUsage: {
      heartbeatGrounding: (item.seam_usage || []).includes?.('heartbeat-grounding') || false,
      promptContractRuntimeTruth: (item.seam_usage || []).includes?.('prompt-contract-runtime-truth') || false,
      runtimeSelfModel: (item.seam_usage || []).includes?.('runtime-self-model') || false,
      missionControlRuntime: (item.seam_usage || []).includes?.('mission-control-runtime') || false,
    },
    builtAt: item.built_at || '',
    createdAt: item.built_at || '',
    summary:
      item.summary
      || [
        item.intent_state ? `state ${item.intent_state}` : '',
        item.intent_type ? `type ${item.intent_type}` : '',
        item.execution_state ? `execution ${item.execution_state}` : '',
      ].filter(Boolean).join(' · '),
  }
}

function normalizeInternalCadence(item = {}) {
  return {
    lastTickAt: item.last_tick_at || '',
    producerCount: Number(item.producer_count || 0),
    lastTickSummary: {
      ran: item.last_tick_summary?.ran || [],
      coolingDown: item.last_tick_summary?.cooling_down || [],
      visibleGrace: item.last_tick_summary?.visible_grace || [],
      blocked: item.last_tick_summary?.blocked || [],
      errors: item.last_tick_summary?.errors || [],
    },
    producers: (item.producers || []).map((producer) => ({
      name: producer.name || '',
      cooldownMinutes: Number(producer.cooldown_minutes || 0),
      visibleGraceMinutes: Number(producer.visible_grace_minutes || 0),
      priority: Number(producer.priority || 0),
      dependsOn: producer.depends_on || [],
      lastRunAt: producer.last_run_at || '',
      lastTickStatus: {
        status: producer.last_tick_status?.status || 'unknown',
        reason: producer.last_tick_status?.reason || '',
      },
    })),
    source: '/mc/internal-cadence',
  }
}

function normalizeHeartbeatPolicy(item = {}) {
  return {
    workspace: item.workspace || '',
    heartbeatFile: item.heartbeat_file || '',
    present: Boolean(item.present),
    enabled: Boolean(item.enabled),
    intervalMinutes: Number(item.interval_minutes || 0),
    allowPropose: Boolean(item.allow_propose),
    allowExecute: Boolean(item.allow_execute),
    allowPing: Boolean(item.allow_ping),
    pingChannel: item.ping_channel || 'none',
    budgetStatus: item.budget_status || '',
    killSwitch: item.kill_switch || 'enabled',
    summary: item.summary || 'Heartbeat policy summary unavailable.',
    source: item.source || '/mc/jarvis::heartbeat',
  }
}

function normalizeHeartbeatTick(item = {}) {
  return {
    tickId: item.tick_id || '',
    trigger: item.trigger || '',
    tickStatus: item.tick_status || 'unknown',
    decisionType: item.decision_type || '',
    decisionSummary: item.decision_summary || '',
    decisionReason: item.decision_reason || '',
    blockedReason: item.blocked_reason || '',
    provider: item.provider || '',
    model: item.model || '',
    lane: item.lane || '',
    modelSource: item.model_source || '',
    resolutionStatus: item.resolution_status || '',
    fallbackUsed: Boolean(item.fallback_used),
    executionStatus: item.execution_status || '',
    parseStatus: item.parse_status || '',
    budgetStatus: item.budget_status || '',
    pingEligible: Boolean(item.ping_eligible),
    pingResult: item.ping_result || '',
    actionStatus: item.action_status || '',
    actionSummary: item.action_summary || '',
    actionType: item.action_type || '',
    actionArtifact: item.action_artifact || '',
    rawResponse: item.raw_response || '',
    inputTokens: Number(item.input_tokens || 0),
    outputTokens: Number(item.output_tokens || 0),
    costUsd: Number(item.cost_usd || 0),
    startedAt: item.started_at || '',
    finishedAt: item.finished_at || '',
    source: '/mc/jarvis::heartbeat',
    createdAt: item.finished_at || item.started_at || '',
    summary: item.action_summary || item.decision_summary || 'Heartbeat tick detail',
  }
}

function normalizeDevelopmentFocus(item = {}) {
  return {
    focusId: item.focus_id || '',
    focusType: item.focus_type || '',
    canonicalKey: item.canonical_key || '',
    status: item.status || 'unknown',
    title: item.title || item.summary || 'Development focus',
    summary: item.summary || item.title || 'Development focus detail',
    rationale: item.rationale || '',
    sourceKind: item.source_kind || '',
    confidence: item.confidence || '',
    evidenceSummary: item.evidence_summary || '',
    supportSummary: item.support_summary || '',
    statusReason: item.status_reason || '',
    supportCount: Number(item.support_count || 0),
    sessionCount: Number(item.session_count || 0),
    mergeCount: Number(item.merge_count || 0),
    runId: item.run_id || '',
    sessionId: item.session_id || '',
    source: item.source || '/mc/jarvis::development-focus',
    createdAt: item.created_at || '',
    updatedAt: item.updated_at || '',
  }
}

function normalizeReflectiveCritic(item = {}) {
  return {
    criticId: item.critic_id || '',
    criticType: item.critic_type || '',
    canonicalKey: item.canonical_key || '',
    status: item.status || 'unknown',
    title: item.title || item.summary || 'Reflective critic',
    summary: item.summary || item.title || 'Reflective critic detail',
    rationale: item.rationale || '',
    sourceKind: item.source_kind || '',
    confidence: item.confidence || '',
    evidenceSummary: item.evidence_summary || '',
    supportSummary: item.support_summary || '',
    statusReason: item.status_reason || '',
    supportCount: Number(item.support_count || 0),
    sessionCount: Number(item.session_count || 0),
    mergeCount: Number(item.merge_count || 0),
    runId: item.run_id || '',
    sessionId: item.session_id || '',
    source: item.source || '/mc/jarvis::reflective-critic',
    createdAt: item.created_at || '',
    updatedAt: item.updated_at || '',
  }
}

function normalizeWorldModelSignal(item = {}) {
  return {
    signalId: item.signal_id || '',
    signalType: item.signal_type || '',
    canonicalKey: item.canonical_key || '',
    status: item.status || 'unknown',
    title: item.title || item.summary || 'World-model signal',
    summary: item.summary || item.title || 'World-model signal detail',
    rationale: item.rationale || '',
    sourceKind: item.source_kind || '',
    confidence: item.confidence || '',
    evidenceSummary: item.evidence_summary || '',
    supportSummary: item.support_summary || '',
    statusReason: item.status_reason || '',
    supportCount: Number(item.support_count || 0),
    sessionCount: Number(item.session_count || 0),
    mergeCount: Number(item.merge_count || 0),
    runId: item.run_id || '',
    sessionId: item.session_id || '',
    source: item.source || '/mc/jarvis::world-model-signal',
    createdAt: item.created_at || '',
    updatedAt: item.updated_at || '',
  }
}

function normalizeSelfModelSignal(item = {}) {
  return {
    signalId: item.signal_id || '',
    signalType: item.signal_type || '',
    canonicalKey: item.canonical_key || '',
    status: item.status || 'unknown',
    title: item.title || item.summary || 'Self-model signal',
    summary: item.summary || item.title || 'Self-model signal detail',
    rationale: item.rationale || '',
    sourceKind: item.source_kind || '',
    confidence: item.confidence || '',
    evidenceSummary: item.evidence_summary || '',
    supportSummary: item.support_summary || '',
    statusReason: item.status_reason || '',
    supportCount: Number(item.support_count || 0),
    sessionCount: Number(item.session_count || 0),
    mergeCount: Number(item.merge_count || 0),
    runId: item.run_id || '',
    sessionId: item.session_id || '',
    source: item.source || '/mc/jarvis::self-model-signal',
    createdAt: item.created_at || '',
    updatedAt: item.updated_at || '',
  }
}

function normalizeGoalSignal(item = {}) {
  return {
    goalId: item.goal_id || '',
    goalType: item.goal_type || '',
    canonicalKey: item.canonical_key || '',
    status: item.status || 'unknown',
    title: item.title || item.summary || 'Goal signal',
    summary: item.summary || item.title || 'Goal signal detail',
    rationale: item.rationale || '',
    sourceKind: item.source_kind || '',
    confidence: item.confidence || '',
    evidenceSummary: item.evidence_summary || '',
    supportSummary: item.support_summary || '',
    statusReason: item.status_reason || '',
    supportCount: Number(item.support_count || 0),
    sessionCount: Number(item.session_count || 0),
    mergeCount: Number(item.merge_count || 0),
    runId: item.run_id || '',
    sessionId: item.session_id || '',
    source: item.source || '/mc/jarvis::goal-signal',
    createdAt: item.created_at || '',
    updatedAt: item.updated_at || '',
  }
}

function normalizeTemporalRecurrenceSignal(item = {}) {
  return {
    signalId: item.signal_id || '',
    signalType: item.signal_type || '',
    canonicalKey: item.canonical_key || '',
    status: item.status || 'unknown',
    title: item.title || item.summary || 'Temporal recurrence signal',
    summary: item.summary || item.title || 'Temporal recurrence signal detail',
    rationale: item.rationale || '',
    sourceKind: item.source_kind || '',
    confidence: item.confidence || '',
    evidenceSummary: item.evidence_summary || '',
    supportSummary: item.support_summary || '',
    statusReason: item.status_reason || '',
    supportCount: Number(item.support_count || 0),
    sessionCount: Number(item.session_count || 0),
    mergeCount: Number(item.merge_count || 0),
    runId: item.run_id || '',
    sessionId: item.session_id || '',
    source: item.source || '/mc/jarvis::temporal-recurrence-signal',
    createdAt: item.created_at || '',
    updatedAt: item.updated_at || '',
  }
}

function normalizeWitnessSignal(item = {}) {
  return {
    signalId: item.signal_id || '',
    signalType: item.signal_type || '',
    canonicalKey: item.canonical_key || '',
    status: item.status || 'unknown',
    title: item.title || 'Witness Signal',
    summary: item.persistence_summary || item.maturation_summary || item.becoming_summary || item.summary || '',
    rationale: item.rationale || '',
    sourceKind: item.source_kind || '',
    confidence: item.confidence || '',
    evidenceSummary: item.evidence_summary || '',
    supportSummary: item.support_summary || '',
    statusReason: item.status_reason || '',
    runId: item.run_id || '',
    sessionId: item.session_id || '',
    supportCount: Number(item.support_count || 0),
    sessionCount: Number(item.session_count || 0),
    mergeCount: Number(item.merge_count || 0),
    becomingDirection: item.becoming_direction || 'none',
    becomingWeight: item.becoming_weight || 'low',
    becomingSummary: item.becoming_summary || '',
    maturationHint: item.maturation_hint || 'none',
    maturationState: item.maturation_state || 'none',
    maturationMarker: item.maturation_marker || 'none',
    maturationWeight: item.maturation_weight || item.becoming_weight || 'low',
    maturationSummary: item.maturation_summary || '',
    persistenceState: item.persistence_state || 'none',
    persistenceMarker: item.persistence_marker || 'none',
    persistenceWeight: item.persistence_weight || item.becoming_weight || 'low',
    persistenceSummary: item.persistence_summary || '',
    witnessConfidence: item.witness_confidence || item.confidence || 'low',
    sourceAnchor: item.source_anchor || '',
    authority: item.authority || 'non-authoritative',
    layerRole: item.layer_role || 'runtime-support',
    canonicalIdentityState: item.canonical_identity_state || 'not-canonical-identity-truth',
    proposalState: item.proposal_state || 'not-selfhood-proposal',
    moralAuthorityState: item.moral_authority_state || 'not-moral-authority',
    source: item.source || '/mc/jarvis.development.witness_signals',
    createdAt: item.created_at || '',
    updatedAt: item.updated_at || '',
  }
}

function normalizeMetabolismStateSignal(item = {}) {
  return {
    signalId: item.signal_id || '',
    signalType: item.signal_type || '',
    canonicalKey: item.canonical_key || '',
    status: item.status || 'unknown',
    title: item.title || 'Metabolism Signal',
    summary: item.metabolism_summary || item.summary || '',
    rationale: item.rationale || '',
    sourceKind: item.source_kind || '',
    confidence: item.confidence || '',
    evidenceSummary: item.evidence_summary || '',
    supportSummary: item.support_summary || '',
    statusReason: item.status_reason || '',
    runId: item.run_id || '',
    sessionId: item.session_id || '',
    supportCount: Number(item.support_count || 0),
    sessionCount: Number(item.session_count || 0),
    mergeCount: Number(item.merge_count || 0),
    metabolismState: item.metabolism_state || 'none',
    metabolismDirection: item.metabolism_direction || 'none',
    metabolismWeight: item.metabolism_weight || 'low',
    metabolismSummary: item.metabolism_summary || '',
    metabolismConfidence: item.metabolism_confidence || item.confidence || 'low',
    sourceAnchor: item.source_anchor || '',
    authority: item.authority || 'non-authoritative',
    layerRole: item.layer_role || 'runtime-support',
    canonicalDeleteState: item.canonical_delete_state || 'not-canonical-deletion',
    selfErasureState: item.self_erasure_state || 'not-self-erasure',
    source: item.source || '/mc/jarvis.development.metabolism_state_signals',
    createdAt: item.created_at || '',
    updatedAt: item.updated_at || '',
  }
}

function normalizeReleaseMarkerSignal(item = {}) {
  return {
    signalId: item.signal_id || '',
    signalType: item.signal_type || '',
    canonicalKey: item.canonical_key || '',
    status: item.status || 'unknown',
    title: item.title || 'Release Marker',
    summary: item.release_summary || item.summary || '',
    rationale: item.rationale || '',
    sourceKind: item.source_kind || '',
    confidence: item.confidence || '',
    evidenceSummary: item.evidence_summary || '',
    supportSummary: item.support_summary || '',
    statusReason: item.status_reason || '',
    runId: item.run_id || '',
    sessionId: item.session_id || '',
    supportCount: Number(item.support_count || 0),
    sessionCount: Number(item.session_count || 0),
    mergeCount: Number(item.merge_count || 0),
    releaseState: item.release_state || 'none',
    releaseDirection: item.release_direction || 'none',
    releaseWeight: item.release_weight || 'low',
    releaseSummary: item.release_summary || '',
    releaseConfidence: item.release_confidence || item.confidence || 'low',
    sourceAnchor: item.source_anchor || '',
    authority: item.authority || 'non-authoritative',
    layerRole: item.layer_role || 'runtime-support',
    canonicalDeleteState: item.canonical_delete_state || 'not-canonical-deletion',
    selfErasureState: item.self_erasure_state || 'not-self-erasure',
    selectiveForgettingState: item.selective_forgetting_state || 'not-selective-forgetting-execution',
    source: item.source || '/mc/jarvis.development.release_marker_signals',
    createdAt: item.created_at || '',
    updatedAt: item.updated_at || '',
  }
}

function normalizeConsolidationTargetSignal(item = {}) {
  return {
    signalId: item.signal_id || '',
    signalType: item.signal_type || '',
    canonicalKey: item.canonical_key || '',
    status: item.status || 'unknown',
    title: item.title || 'Consolidation Target',
    summary: item.consolidation_summary || item.summary || '',
    rationale: item.rationale || '',
    sourceKind: item.source_kind || '',
    confidence: item.confidence || '',
    evidenceSummary: item.evidence_summary || '',
    supportSummary: item.support_summary || '',
    statusReason: item.status_reason || '',
    runId: item.run_id || '',
    sessionId: item.session_id || '',
    supportCount: Number(item.support_count || 0),
    sessionCount: Number(item.session_count || 0),
    mergeCount: Number(item.merge_count || 0),
    consolidationState: item.consolidation_state || 'none',
    consolidationFocus: item.consolidation_focus || 'none',
    consolidationWeight: item.consolidation_weight || 'low',
    consolidationSummary: item.consolidation_summary || '',
    consolidationConfidence: item.consolidation_confidence || item.confidence || 'low',
    sourceAnchor: item.source_anchor || '',
    authority: item.authority || 'non-authoritative',
    layerRole: item.layer_role || 'runtime-support',
    writebackState: item.writeback_state || 'not-writeback',
    canonicalMutationState: item.canonical_mutation_state || 'not-canonical-mutation',
    source: item.source || '/mc/jarvis.development.consolidation_target_signals',
    createdAt: item.created_at || '',
    updatedAt: item.updated_at || '',
  }
}

function normalizeSelectiveForgettingCandidate(item = {}) {
  return {
    signalId: item.signal_id || '',
    signalType: item.signal_type || '',
    canonicalKey: item.canonical_key || '',
    status: item.status || 'unknown',
    title: item.title || 'Selective Forgetting Candidate',
    summary: item.forgetting_candidate_summary || item.summary || '',
    rationale: item.rationale || '',
    sourceKind: item.source_kind || '',
    confidence: item.confidence || '',
    evidenceSummary: item.evidence_summary || '',
    supportSummary: item.support_summary || '',
    statusReason: item.status_reason || '',
    runId: item.run_id || '',
    sessionId: item.session_id || '',
    supportCount: Number(item.support_count || 0),
    sessionCount: Number(item.session_count || 0),
    mergeCount: Number(item.merge_count || 0),
    forgettingCandidateState: item.forgetting_candidate_state || 'none',
    forgettingCandidateReason: item.forgetting_candidate_reason || 'none',
    forgettingCandidateWeight: item.forgetting_candidate_weight || 'low',
    forgettingCandidateSummary: item.forgetting_candidate_summary || '',
    forgettingCandidateConfidence: item.forgetting_candidate_confidence || item.confidence || 'low',
    sourceAnchor: item.source_anchor || '',
    authority: item.authority || 'non-authoritative',
    layerRole: item.layer_role || 'runtime-support',
    canonicalDeleteState: item.canonical_delete_state || 'not-deletion',
    selfErasureState: item.self_erasure_state || 'not-self-erasure',
    selectiveForgettingState: item.selective_forgetting_state || 'not-selective-forgetting-execution',
    source: item.source || '/mc/jarvis.development.selective_forgetting_candidates',
    createdAt: item.created_at || '',
    updatedAt: item.updated_at || '',
  }
}

function normalizeOpenLoopSignal(item = {}) {
  return {
    signalId: item.signal_id || '',
    signalType: item.signal_type || '',
    canonicalKey: item.canonical_key || '',
    status: item.status || 'unknown',
    title: item.title || item.summary || 'Open loop',
    summary: item.summary || item.title || 'Open loop detail',
    rationale: item.rationale || '',
    sourceKind: item.source_kind || '',
    confidence: item.confidence || '',
    evidenceSummary: item.evidence_summary || '',
    supportSummary: item.support_summary || '',
    statusReason: item.status_reason || '',
    closureReadiness: item.closure_readiness || 'low',
    closureConfidence: item.closure_confidence || 'low',
    closureReason: item.closure_reason || '',
    runId: item.run_id || '',
    sessionId: item.session_id || '',
    supportCount: Number(item.support_count || 0),
    sessionCount: Number(item.session_count || 0),
    mergeCount: Number(item.merge_count || 0),
    source: item.source || '/mc/jarvis::open-loop-signal',
    createdAt: item.created_at || '',
    updatedAt: item.updated_at || '',
  }
}

function normalizeEmergentSignal(item = {}) {
  return {
    signalId: item.id || '',
    canonicalKey: item.canonical_key || '',
    signalFamily: item.signal_family || '',
    status: item.signal_status || 'candidate',
    lifecycleState: item.lifecycle_state || 'none',
    interpretationState: item.interpretation_state || 'none',
    title: item.short_summary || 'Emergent inner signal',
    summary: item.short_summary || 'Emergent inner signal detail',
    salience: Number(item.salience || 0),
    intensity: item.intensity || 'low',
    sourceHints: Array.isArray(item.source_hints) ? item.source_hints : [],
    provenance: item.provenance || {},
    influencedLayer: item.influenced_layer || '',
    adoptedBy: item.adopted_by || '',
    truth: item.truth || 'candidate-only',
    visibility: item.visibility || 'internal-only',
    identityBoundary: item.identity_boundary || 'not-canonical-identity-truth',
    memoryBoundary: item.memory_boundary || 'not-workspace-memory',
    actionBoundary: item.action_boundary || 'not-action',
    expiryState: item.expiry_state || 'live',
    authoritative: Boolean(item.authoritative),
    source: item.source || '/mc/runtime.emergent_signal',
    createdAt: item.created_at || '',
    updatedAt: item.updated_at || '',
  }
}

function normalizeOpenLoopClosureProposal(item = {}) {
  return {
    proposalId: item.proposal_id || '',
    proposalType: item.proposal_type || '',
    canonicalKey: item.canonical_key || '',
    status: item.status || 'unknown',
    title: item.title || item.summary || 'Loop closure proposal',
    summary: item.summary || item.title || 'Loop closure proposal detail',
    rationale: item.rationale || '',
    sourceKind: item.source_kind || '',
    confidence: item.confidence || '',
    evidenceSummary: item.evidence_summary || '',
    supportSummary: item.support_summary || '',
    statusReason: item.status_reason || '',
    domain: item.domain || '',
    loopStatus: item.loop_status || 'open',
    closureReadiness: item.closure_readiness || 'low',
    closureConfidence: item.closure_confidence || 'low',
    proposalReason: item.proposal_reason || item.summary || '',
    reviewAnchor: item.review_anchor || '',
    runId: item.run_id || '',
    sessionId: item.session_id || '',
    supportCount: Number(item.support_count || 0),
    sessionCount: Number(item.session_count || 0),
    mergeCount: Number(item.merge_count || 0),
    source: item.source || '/mc/jarvis::open-loop-closure-proposal',
    createdAt: item.created_at || '',
    updatedAt: item.updated_at || '',
  }
}

function normalizeInternalOppositionSignal(item = {}) {
  return {
    signalId: item.signal_id || '',
    signalType: item.signal_type || '',
    canonicalKey: item.canonical_key || '',
    status: item.status || 'unknown',
    title: item.title || item.summary || 'Internal opposition',
    summary: item.summary || item.title || 'Internal opposition detail',
    rationale: item.rationale || '',
    sourceKind: item.source_kind || '',
    confidence: item.confidence || '',
    evidenceSummary: item.evidence_summary || '',
    supportSummary: item.support_summary || '',
    statusReason: item.status_reason || '',
    runId: item.run_id || '',
    sessionId: item.session_id || '',
    supportCount: Number(item.support_count || 0),
    sessionCount: Number(item.session_count || 0),
    mergeCount: Number(item.merge_count || 0),
    source: item.source || '/mc/jarvis::internal-opposition-signal',
    createdAt: item.created_at || '',
    updatedAt: item.updated_at || '',
  }
}

function normalizeSelfReviewSignal(item = {}) {
  return {
    signalId: item.signal_id || '',
    signalType: item.signal_type || '',
    canonicalKey: item.canonical_key || '',
    status: item.status || 'unknown',
    title: item.title || item.summary || 'Self review signal',
    summary: item.summary || item.title || 'Self review detail',
    rationale: item.rationale || '',
    sourceKind: item.source_kind || '',
    confidence: item.confidence || '',
    evidenceSummary: item.evidence_summary || '',
    supportSummary: item.support_summary || '',
    statusReason: item.status_reason || '',
    runId: item.run_id || '',
    sessionId: item.session_id || '',
    supportCount: Number(item.support_count || 0),
    sessionCount: Number(item.session_count || 0),
    mergeCount: Number(item.merge_count || 0),
    source: item.source || '/mc/jarvis::self-review-signal',
    createdAt: item.created_at || '',
    updatedAt: item.updated_at || '',
  }
}

function normalizeSelfReviewRecord(item = {}) {
  return {
    recordId: item.record_id || '',
    recordType: item.record_type || '',
    canonicalKey: item.canonical_key || '',
    status: item.status || 'unknown',
    title: item.title || item.summary || 'Self review brief',
    summary: item.summary || item.title || 'Self review brief detail',
    rationale: item.rationale || '',
    sourceKind: item.source_kind || '',
    confidence: item.confidence || '',
    evidenceSummary: item.evidence_summary || '',
    supportSummary: item.support_summary || '',
    statusReason: item.status_reason || '',
    reviewType: item.review_type || item.record_type || '',
    trigger: item.trigger || item.record_type || '',
    domain: item.domain || '',
    openLoopStatus: item.open_loop_status || 'none',
    oppositionStatus: item.opposition_status || 'none',
    closureReadiness: item.closure_readiness || 'low',
    closureConfidence: item.closure_confidence || 'low',
    shortReason: item.short_reason || '',
    runId: item.run_id || '',
    sessionId: item.session_id || '',
    supportCount: Number(item.support_count || 0),
    sessionCount: Number(item.session_count || 0),
    mergeCount: Number(item.merge_count || 0),
    source: item.source || '/mc/jarvis::self-review-record',
    createdAt: item.created_at || '',
    updatedAt: item.updated_at || '',
  }
}

function normalizeSelfReviewRun(item = {}) {
  return {
    runId: item.run_id || '',
    runType: item.run_type || '',
    canonicalKey: item.canonical_key || '',
    status: item.status || 'unknown',
    title: item.title || item.summary || 'Self review snapshot',
    summary: item.summary || item.title || 'Self review snapshot detail',
    rationale: item.rationale || '',
    sourceKind: item.source_kind || '',
    confidence: item.confidence || '',
    evidenceSummary: item.evidence_summary || '',
    supportSummary: item.support_summary || '',
    statusReason: item.status_reason || '',
    recordRunId: item.record_run_id || '',
    reviewType: item.review_type || item.run_type || '',
    domain: item.domain || '',
    reviewFocus: item.review_focus || '',
    openLoopStatus: item.open_loop_status || 'none',
    oppositionStatus: item.opposition_status || 'none',
    closureConfidence: item.closure_confidence || 'low',
    shortOutlook: item.short_outlook || '',
    shortReviewNote: item.short_review_note || '',
    sessionId: item.session_id || '',
    supportCount: Number(item.support_count || 0),
    sessionCount: Number(item.session_count || 0),
    mergeCount: Number(item.merge_count || 0),
    source: item.source || '/mc/jarvis::self-review-run',
    createdAt: item.created_at || '',
    updatedAt: item.updated_at || '',
  }
}

function normalizeSelfReviewOutcome(item = {}) {
  return {
    outcomeId: item.outcome_id || '',
    outcomeType: item.outcome_type || '',
    canonicalKey: item.canonical_key || '',
    status: item.status || 'unknown',
    title: item.title || item.summary || 'Self review outcome',
    summary: item.summary || item.title || 'Self review outcome detail',
    rationale: item.rationale || '',
    sourceKind: item.source_kind || '',
    confidence: item.confidence || '',
    evidenceSummary: item.evidence_summary || '',
    supportSummary: item.support_summary || '',
    statusReason: item.status_reason || '',
    reviewRunId: item.review_run_id || '',
    reviewType: item.review_type || '',
    domain: item.domain || '',
    reviewFocus: item.review_focus || '',
    closureConfidence: item.closure_confidence || 'low',
    shortOutcome: item.short_outcome || '',
    sessionId: item.session_id || '',
    supportCount: Number(item.support_count || 0),
    sessionCount: Number(item.session_count || 0),
    mergeCount: Number(item.merge_count || 0),
    source: item.source || '/mc/jarvis::self-review-outcome',
    createdAt: item.created_at || '',
    updatedAt: item.updated_at || '',
  }
}

function normalizeSelfReviewCadenceSignal(item = {}) {
  return {
    signalId: item.signal_id || '',
    signalType: item.signal_type || '',
    canonicalKey: item.canonical_key || '',
    status: item.status || 'unknown',
    title: item.title || item.summary || 'Self review cadence',
    summary: item.summary || item.title || 'Self review cadence detail',
    rationale: item.rationale || '',
    sourceKind: item.source_kind || '',
    confidence: item.confidence || '',
    evidenceSummary: item.evidence_summary || '',
    supportSummary: item.support_summary || '',
    statusReason: item.status_reason || '',
    cadenceState: item.cadence_state || '',
    cadenceReason: item.cadence_reason || item.summary || '',
    domain: item.domain || '',
    lastReviewedAt: item.last_reviewed_at || '',
    dueHint: item.due_hint || '',
    runId: item.run_id || '',
    sessionId: item.session_id || '',
    supportCount: Number(item.support_count || 0),
    sessionCount: Number(item.session_count || 0),
    mergeCount: Number(item.merge_count || 0),
    source: item.source || '/mc/jarvis::self-review-cadence-signal',
    createdAt: item.created_at || '',
    updatedAt: item.updated_at || '',
  }
}

function normalizeDreamHypothesisSignal(item = {}) {
  return {
    signalId: item.signal_id || '',
    signalType: item.signal_type || '',
    canonicalKey: item.canonical_key || '',
    status: item.status || 'unknown',
    title: item.title || item.summary || 'Dream hypothesis',
    summary: item.summary || item.title || 'Dream hypothesis detail',
    rationale: item.rationale || '',
    sourceKind: item.source_kind || '',
    confidence: item.confidence || '',
    evidenceSummary: item.evidence_summary || '',
    supportSummary: item.support_summary || '',
    statusReason: item.status_reason || '',
    domain: item.domain || '',
    hypothesisType: item.hypothesis_type || item.signal_type || '',
    hypothesisNote: item.hypothesis_note || item.summary || '',
    hypothesisAnchor: item.hypothesis_anchor || '',
    runId: item.run_id || '',
    sessionId: item.session_id || '',
    supportCount: Number(item.support_count || 0),
    sessionCount: Number(item.session_count || 0),
    mergeCount: Number(item.merge_count || 0),
    source: item.source || '/mc/jarvis::dream-hypothesis-signal',
    createdAt: item.created_at || '',
    updatedAt: item.updated_at || '',
  }
}

function normalizeDreamAdoptionCandidate(item = {}) {
  return {
    candidateId: item.candidate_id || '',
    candidateType: item.candidate_type || '',
    canonicalKey: item.canonical_key || '',
    status: item.status || 'unknown',
    title: item.title || item.summary || 'Dream adoption candidate',
    summary: item.summary || item.title || 'Dream adoption candidate detail',
    rationale: item.rationale || '',
    sourceKind: item.source_kind || '',
    confidence: item.confidence || '',
    evidenceSummary: item.evidence_summary || '',
    supportSummary: item.support_summary || '',
    statusReason: item.status_reason || '',
    domain: item.domain || '',
    hypothesisType: item.hypothesis_type || '',
    adoptionState: item.adoption_state || item.candidate_type || '',
    adoptionReason: item.adoption_reason || item.summary || '',
    adoptionConfidence: item.adoption_confidence || 'low',
    adoptionAnchor: item.adoption_anchor || '',
    runId: item.run_id || '',
    sessionId: item.session_id || '',
    supportCount: Number(item.support_count || 0),
    sessionCount: Number(item.session_count || 0),
    mergeCount: Number(item.merge_count || 0),
    source: item.source || '/mc/jarvis::dream-adoption-candidate',
    createdAt: item.created_at || '',
    updatedAt: item.updated_at || '',
  }
}

function normalizeDreamInfluenceProposal(item = {}) {
  return {
    proposalId: item.proposal_id || '',
    proposalType: item.proposal_type || '',
    canonicalKey: item.canonical_key || '',
    status: item.status || 'unknown',
    title: item.title || item.summary || 'Dream influence proposal',
    summary: item.summary || item.title || 'Dream influence proposal detail',
    rationale: item.rationale || '',
    sourceKind: item.source_kind || '',
    confidence: item.confidence || '',
    evidenceSummary: item.evidence_summary || '',
    supportSummary: item.support_summary || '',
    statusReason: item.status_reason || '',
    domain: item.domain || '',
    hypothesisType: item.hypothesis_type || '',
    candidateState: item.candidate_state || '',
    influenceTarget: item.influence_target || '',
    influenceConfidence: item.influence_confidence || 'low',
    proposalReason: item.proposal_reason || item.summary || '',
    influenceAnchor: item.influence_anchor || '',
    runId: item.run_id || '',
    sessionId: item.session_id || '',
    supportCount: Number(item.support_count || 0),
    sessionCount: Number(item.session_count || 0),
    mergeCount: Number(item.merge_count || 0),
    source: item.source || '/mc/jarvis::dream-influence-proposal',
    createdAt: item.created_at || '',
    updatedAt: item.updated_at || '',
  }
}

function normalizeSelfAuthoredPromptProposal(item = {}) {
  const supportFields = parseSupportSummary(item.support_summary || '')
  return {
    proposalId: item.proposal_id || '',
    proposalType: item.proposal_type || '',
    canonicalKey: item.canonical_key || '',
    status: item.status || 'unknown',
    title: item.title || item.summary || 'Self-authored prompt proposal',
    summary: item.summary || item.title || 'Self-authored prompt proposal detail',
    rationale: item.rationale || '',
    sourceKind: item.source_kind || '',
    confidence: item.confidence || '',
    evidenceSummary: item.evidence_summary || '',
    supportSummary: item.support_summary || '',
    statusReason: item.status_reason || '',
    domain: item.domain || '',
    hypothesisType: item.hypothesis_type || '',
    influenceTarget: item.influence_target || '',
    promptTarget: item.prompt_target || '',
    proposedNudge: item.proposed_nudge || '',
    candidateFragment: item.candidate_fragment || supportFields.candidate_fragment || '',
    fragmentGrounding: {
      adaptiveLearning: supportFields.adaptive_learning || 'none',
      dreamInfluence: supportFields.dream_influence || 'none',
      guidedLearning: supportFields.guided_learning || 'none',
      adaptiveReasoning: supportFields.adaptive_reasoning || 'none',
    },
    dreamInfluence: {
      influenceState: supportFields.dream_influence_state || 'quiet',
      influenceTarget: supportFields.dream_influence_target || 'none',
      influenceMode: supportFields.dream_influence_mode || 'stabilize',
      influenceStrength: supportFields.dream_influence_strength || 'none',
    },
    reviewLight: {
      proposalDirection: supportFields.proposal_direction || 'none',
      proposedChangeKind: supportFields.proposed_change_kind || 'none',
      diffLightSummary: supportFields.diff_light_summary || '',
      reviewHint: supportFields.review_hint || '',
    },
    fragmentTruth: item.fragment_truth || 'proposal-only',
    fragmentVisibility: item.fragment_visibility || 'internal-only',
    proposalReason: item.proposal_reason || item.summary || '',
    proposalConfidence: item.proposal_confidence || 'low',
    influenceAnchor: item.influence_anchor || '',
    runId: item.run_id || '',
    sessionId: item.session_id || '',
    supportCount: Number(item.support_count || 0),
    sessionCount: Number(item.session_count || 0),
    mergeCount: Number(item.merge_count || 0),
    source: item.source || '/mc/jarvis::self-authored-prompt-proposal',
    createdAt: item.created_at || '',
    updatedAt: item.updated_at || '',
  }
}

function parseSupportSummary(text = '') {
  return String(text)
    .split(' | ')
    .reduce((acc, chunk) => {
      if (!chunk || !chunk.includes('=')) return acc
      const [rawKey, ...rest] = chunk.split('=')
      const key = rawKey.trim()
      const value = rest.join('=').trim()
      if (key) acc[key] = value
      return acc
    }, {})
}

function normalizeUserMdUpdateProposal(item = {}) {
  return {
    proposalId: item.proposal_id || '',
    proposalType: item.proposal_type || '',
    canonicalKey: item.canonical_key || '',
    status: item.status || 'unknown',
    title: item.title || item.summary || 'USER.md update proposal',
    summary: item.summary || item.title || 'USER.md update proposal detail',
    rationale: item.rationale || '',
    sourceKind: item.source_kind || '',
    confidence: item.confidence || '',
    evidenceSummary: item.evidence_summary || '',
    supportSummary: item.support_summary || '',
    statusReason: item.status_reason || '',
    userDimension: item.user_dimension || '',
    proposedUpdate: item.proposed_update || '',
    proposalReason: item.proposal_reason || item.summary || '',
    proposalConfidence: item.proposal_confidence || 'low',
    sourceAnchor: item.source_anchor || '',
    runId: item.run_id || '',
    sessionId: item.session_id || '',
    supportCount: Number(item.support_count || 0),
    sessionCount: Number(item.session_count || 0),
    mergeCount: Number(item.merge_count || 0),
    source: item.source || '/mc/jarvis::user-md-update-proposal',
    createdAt: item.created_at || '',
    updatedAt: item.updated_at || '',
  }
}

function normalizeUserUnderstandingSignal(item = {}) {
  return {
    signalId: item.signal_id || '',
    signalType: item.signal_type || '',
    canonicalKey: item.canonical_key || '',
    status: item.status || 'unknown',
    title: item.title || item.summary || 'User understanding signal',
    summary: item.summary || item.title || 'User understanding signal detail',
    rationale: item.rationale || '',
    sourceKind: item.source_kind || '',
    confidence: item.confidence || '',
    evidenceSummary: item.evidence_summary || '',
    supportSummary: item.support_summary || '',
    statusReason: item.status_reason || '',
    userDimension: item.user_dimension || '',
    signalSummary: item.signal_summary || item.summary || '',
    signalConfidence: item.signal_confidence || item.confidence || 'low',
    sourceAnchor: item.source_anchor || '',
    runId: item.run_id || '',
    sessionId: item.session_id || '',
    supportCount: Number(item.support_count || 0),
    sessionCount: Number(item.session_count || 0),
    mergeCount: Number(item.merge_count || 0),
    source: item.source || '/mc/jarvis::user-understanding-signal',
    createdAt: item.created_at || '',
    updatedAt: item.updated_at || '',
  }
}

function normalizeSelfhoodProposal(item = {}) {
  return {
    proposalId: item.proposal_id || '',
    proposalType: item.proposal_type || '',
    canonicalKey: item.canonical_key || '',
    status: item.status || 'unknown',
    title: item.title || item.summary || 'Selfhood proposal',
    summary: item.summary || item.title || 'Selfhood proposal detail',
    rationale: item.rationale || '',
    sourceKind: item.source_kind || '',
    confidence: item.confidence || '',
    evidenceSummary: item.evidence_summary || '',
    supportSummary: item.support_summary || '',
    statusReason: item.status_reason || '',
    domain: item.domain || '',
    selfhoodTarget: item.selfhood_target || '',
    proposedShift: item.proposed_shift || '',
    proposalReason: item.proposal_reason || item.summary || '',
    proposalConfidence: item.proposal_confidence || 'low',
    sourceAnchor: item.source_anchor || '',
    runId: item.run_id || '',
    sessionId: item.session_id || '',
    supportCount: Number(item.support_count || 0),
    sessionCount: Number(item.session_count || 0),
    mergeCount: Number(item.merge_count || 0),
    source: item.source || '/mc/jarvis::selfhood-proposal',
    createdAt: item.created_at || '',
    updatedAt: item.updated_at || '',
  }
}

function normalizeRuntimeAwarenessSignal(item = {}) {
  return {
    signalId: item.signal_id || '',
    signalType: item.signal_type || '',
    canonicalKey: item.canonical_key || '',
    status: item.status || 'unknown',
    title: item.title || item.summary || 'Runtime Awareness Signal',
    summary: item.summary || item.title || 'Runtime awareness detail',
    rationale: item.rationale || '',
    sourceKind: item.source_kind || '',
    confidence: item.confidence || '',
    evidenceSummary: item.evidence_summary || '',
    supportSummary: item.support_summary || '',
    statusReason: item.status_reason || '',
    supportCount: Number(item.support_count || 0),
    sessionCount: Number(item.session_count || 0),
    mergeCount: Number(item.merge_count || 0),
    runId: item.run_id || '',
    sessionId: item.session_id || '',
    source: item.source || '/mc/jarvis::runtime-awareness-signal',
    createdAt: item.created_at || '',
    updatedAt: item.updated_at || '',
  }
}

function normalizeRuntimeAwarenessHistoryItem(item = {}) {
  return {
    signalId: item.signal_id || '',
    signalType: item.signal_type || '',
    title: item.title || item.summary || 'Runtime awareness update',
    status: item.status || 'unknown',
    confidence: item.confidence || '',
    summary: item.summary || '',
    statusReason: item.status_reason || '',
    source: item.source || '/mc/jarvis::runtime-awareness-history',
    createdAt: item.created_at || '',
    updatedAt: item.updated_at || '',
  }
}

function normalizeReflectionSignal(item = {}) {
  return {
    signalId: item.signal_id || '',
    signalType: item.signal_type || '',
    canonicalKey: item.canonical_key || '',
    status: item.status || 'unknown',
    title: item.title || item.summary || 'Reflection signal',
    summary: item.summary || item.title || 'Reflection signal detail',
    rationale: item.rationale || '',
    sourceKind: item.source_kind || '',
    confidence: item.confidence || '',
    evidenceSummary: item.evidence_summary || '',
    supportSummary: item.support_summary || '',
    statusReason: item.status_reason || '',
    supportCount: Number(item.support_count || 0),
    sessionCount: Number(item.session_count || 0),
    mergeCount: Number(item.merge_count || 0),
    runId: item.run_id || '',
    sessionId: item.session_id || '',
    source: item.source || '/mc/jarvis::reflection-signal',
    createdAt: item.created_at || '',
    updatedAt: item.updated_at || '',
  }
}

function normalizeReflectionHistoryItem(item = {}) {
  return {
    signalId: item.signal_id || '',
    signalType: item.signal_type || '',
    title: item.title || item.summary || 'Reflection update',
    status: item.status || 'unknown',
    transition: item.transition || '',
    confidence: item.confidence || '',
    summary: item.summary || '',
    statusReason: item.status_reason || '',
    source: item.source || '/mc/jarvis::reflection-signal-history',
    createdAt: item.created_at || '',
    updatedAt: item.updated_at || '',
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
      if (eventName === 'working_step') handlers.onWorkingStep?.(payload)
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
    const [operations, toolIntent] = await Promise.all([
      requestJson('/mc/operations'),
      requestJson('/mc/tool-intent').catch(() => null),
    ])
    return normalizeMissionControlOperationsPayload({
      ...operations,
      toolIntent: toolIntent || operations?.runtime?.runtime_tool_intent || {},
    })
  },

  async getMissionControlObservability() {
    const [events, costs, operations] = await Promise.all([
      requestJson('/mc/events?limit=80'),
      requestJson('/mc/costs?limit=40'),
      requestJson('/mc/operations'),
    ])

    const runtime = operations?.runtime || {}
    const runs = operations?.runs || {}

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
      visibleTrace: normalizeVisibleExecutionTrace(
        runs?.last_execution_trace ||
        runs?.last_capability_use?.trace ||
        {}
      ),
      runEvidence: {
        recentEvents: (runs?.recent_events || []).map(normalizeEventItem),
        recentWorkUnits: runs?.recent_work_units || [],
        recentWorkNotes: runs?.recent_work_notes || [],
      },
    }
  },

  async getMissionControlJarvis() {
    const [payload, contractPayload, attentionPayload, conflictPayload, guardPayload, selfModelPayload, internalCadencePayload, dreamInfluencePayload, selfSystemCodeAwarenessPayload, experientialRuntimeContextPayload] = await Promise.all([
      requestJson('/mc/jarvis'),
      requestJson('/mc/runtime-contract'),
      requestJson('/mc/attention-budget').catch(() => null),
      requestJson('/mc/conflict-resolution').catch(() => null),
      requestJson('/mc/self-deception-guard').catch(() => null),
      requestJson('/mc/runtime-self-model').catch(() => null),
      requestJson('/mc/internal-cadence').catch(() => null),
      requestJson('/mc/dream-influence').catch(() => null),
      requestJson('/mc/self-system-code-awareness').catch(() => null),
      requestJson('/mc/experiential-runtime-context').catch(() => null),
    ])
    const state = payload?.state || {}
    const memory = payload?.memory || {}
    const development = payload?.development || {}
    const continuity = payload?.continuity || {}
    const heartbeat = payload?.heartbeat || {}
    const contract = contractPayload || {}
    const embodiedStateSource =
      heartbeat?.embodied_state ||
      selfModelPayload?.embodied_state ||
      null
    const loopRuntimeSource =
      heartbeat?.loop_runtime ||
      selfModelPayload?.loop_runtime ||
      null
    const idleConsolidationSource =
      heartbeat?.idle_consolidation ||
      selfModelPayload?.idle_consolidation ||
      null
    const dreamArticulationSource =
      heartbeat?.dream_articulation ||
      selfModelPayload?.dream_articulation ||
      null
    const promptEvolutionSource =
      heartbeat?.prompt_evolution ||
      development?.prompt_evolution ||
      selfModelPayload?.prompt_evolution ||
      null
    const affectiveMetaSource =
      heartbeat?.affective_meta_state ||
      development?.affective_meta_state ||
      selfModelPayload?.affective_meta_state ||
      null
    const epistemicSource =
      heartbeat?.epistemic_runtime_state ||
      development?.epistemic_runtime_state ||
      selfModelPayload?.epistemic_runtime_state ||
      null
    const subagentEcologySource =
      heartbeat?.subagent_ecology ||
      development?.subagent_ecology ||
      selfModelPayload?.subagent_ecology ||
      null
    const councilRuntimeSource =
      heartbeat?.council_runtime ||
      development?.council_runtime ||
      selfModelPayload?.council_runtime ||
      null
    const adaptivePlannerSource =
      heartbeat?.adaptive_planner ||
      development?.adaptive_planner ||
      selfModelPayload?.adaptive_planner ||
      null
    const adaptiveReasoningSource =
      heartbeat?.adaptive_reasoning ||
      development?.adaptive_reasoning ||
      selfModelPayload?.adaptive_reasoning ||
      null
    const dreamInfluenceSource =
      dreamInfluencePayload ||
      heartbeat?.dream_influence ||
      selfModelPayload?.dream_influence ||
      null
    const guidedLearningSource =
      heartbeat?.guided_learning ||
      development?.guided_learning ||
      selfModelPayload?.guided_learning ||
      null
    const adaptiveLearningSource =
      heartbeat?.adaptive_learning ||
      development?.adaptive_learning ||
      selfModelPayload?.adaptive_learning ||
      null
    const selfSystemCodeAwarenessSource =
      selfSystemCodeAwarenessPayload ||
      heartbeat?.self_system_code_awareness ||
      continuity?.self_system_code_awareness ||
      selfModelPayload?.self_system_code_awareness ||
      null
    const experientialRuntimeContextSource =
      experientialRuntimeContextPayload ||
      null

    return {
      fetchedAt: new Date().toISOString(),
      summary: payload?.summary || {},
      contract: {
        summary: contract.summary || {},
        bootstrap: normalizeJarvisItem(contract.bootstrap || {}, {
          source: contract.bootstrap?.source || '/mc/runtime-contract',
          summary: contract.bootstrap?.summary || 'Bootstrap contract state',
        }),
        capabilityContract: normalizeCapabilityContract(contract.capability_contract || {}),
        files: {
          canonical: (contract.files?.canonical || []).map(normalizeContractFile),
          derived: (contract.files?.derived || []).map(normalizeContractFile),
          referenceOnly: (contract.files?.reference_only || []).map(normalizeContractFile),
        },
        promptModes: Object.values(contract.prompt_modes || {}).map(normalizePromptMode),
        pendingWrites: Object.values(contract.pending_writes || {}).map(normalizePendingWrite),
        writeHistory: {
          total: Number(contract.write_history?.total || 0),
          counts: contract.write_history?.counts || {},
          summary: contract.write_history?.summary || 'No applied file writes recorded yet.',
          items: (contract.write_history?.items || []).map(normalizeContractWrite),
        },
        roles: contract.roles || {},
        contractVersion: contract.contract_version || 'unknown',
      },
      state: {
        visibleIdentity: normalizeJarvisItem(state.visible_identity || {}, {
          summary: `workspace ${state?.visible_identity?.workspace || 'unknown'}`,
        }),
        privateState: normalizeJarvisItem(state.private_state?.current || {}, {
          source: state.private_state?.current?.source || '/mc/runtime.private_state',
          summary: `${state.private_state?.current?.confidence || 'unknown'} confidence · frustration ${state.private_state?.current?.frustration || 'unknown'}`,
        }),
        protectedInnerVoice: normalizeJarvisItem(state.protected_inner_voice?.current || {}, {
          source: state.protected_inner_voice?.current?.source || '/mc/runtime.protected_inner_voice',
          summary: state.protected_inner_voice?.current?.current_pull || 'No current pull',
        }),
        innerInterplay: normalizeJarvisItem(state.inner_interplay?.current || {}, {
          source: state.inner_interplay?.current?.source || '/mc/runtime.private_inner_interplay',
          summary: state.inner_interplay?.current?.retained_pattern || 'No retained pattern',
        }),
        initiativeTension: normalizeJarvisItem(state.initiative_tension?.current || {}, {
          source: state.initiative_tension?.current?.source || '/mc/runtime.private_initiative_tension',
          summary: `${state.initiative_tension?.current?.tension_kind || 'unknown'} · ${state.initiative_tension?.current?.tension_level || 'unknown'}`,
        }),
      },
      memory: {
        retainedProjection: normalizeJarvisItem(memory.retained_projection?.current || memory.retained_projection || {}, {
          source: memory.retained_projection?.source || '/mc/runtime.private_retained_memory_projection',
          summary: memory.retained_projection?.retained_focus || memory.retained_projection?.current?.retained_value || 'No retained focus',
        }),
        retainedRecord: normalizeJarvisItem(memory.retained_record?.current || {}, {
          source: memory.retained_record?.current?.source || '/mc/runtime.private_retained_memory_record',
          summary: memory.retained_record?.current?.retained_value || 'No retained record',
        }),
        recentRecords: (memory.retained_record?.recent_records || []).map((record) => normalizeJarvisItem(record, {
          source: record.source || '/mc/runtime.private_retained_memory_record',
          summary: record.retained_value || 'No retained value',
        })),
        capabilityContinuity: normalizeJarvisItem(memory.visible_capability_continuity || {}, {
          source: memory.visible_capability_continuity?.source || '/mc/runtime.visible_capability_continuity',
          summary: `${memory.visible_capability_continuity?.included_rows || 0} capability rows`,
        }),
      },
      development: {
        selfModel: normalizeJarvisItem(development.self_model?.current || {}, {
          source: development.self_model?.current?.source || '/mc/runtime.private_self_model',
          summary: development.self_model?.current?.growth_direction || 'No growth direction',
        }),
        developmentState: normalizeJarvisItem(development.development_state?.current || {}, {
          source: development.development_state?.current?.source || '/mc/runtime.private_development_state',
          summary: development.development_state?.current?.preferred_direction || 'No preferred direction',
        }),
        privateInnerNoteSupport: normalizeJarvisItem((development.private_inner_note_signals?.items || [])[0] || {}, {
          source: ((development.private_inner_note_signals?.items || [])[0] || {}).source || '/mc/runtime.private_inner_note_signal',
          summary: ((development.private_inner_note_signals?.items || [])[0] || {}).note_summary || 'No bounded inner-note support',
        }),
        privateInitiativeTensionSupport: normalizeJarvisItem((development.private_initiative_tension_signals?.items || [])[0] || {}, {
          source: ((development.private_initiative_tension_signals?.items || [])[0] || {}).source || '/mc/runtime.private_initiative_tension_signal',
          summary: ((development.private_initiative_tension_signals?.items || [])[0] || {}).tension_summary || 'No bounded initiative tension support',
        }),
        privateInnerInterplaySupport: normalizeJarvisItem((development.private_inner_interplay_signals?.items || [])[0] || {}, {
          source: ((development.private_inner_interplay_signals?.items || [])[0] || {}).source || '/mc/runtime.private_inner_interplay_signal',
          summary: ((development.private_inner_interplay_signals?.items || [])[0] || {}).interplay_summary || 'No bounded inner interplay support',
        }),
        privateStateSnapshot: normalizeJarvisItem((development.private_state_snapshots?.items || [])[0] || {}, {
          source: ((development.private_state_snapshots?.items || [])[0] || {}).source || '/mc/runtime.private_state_snapshot',
          summary: ((development.private_state_snapshots?.items || [])[0] || {}).state_summary || 'No bounded private-state snapshot',
        }),
        diarySynthesisSupport: normalizeJarvisItem((development.diary_synthesis_signals?.items || [])[0] || {}, {
          source: ((development.diary_synthesis_signals?.items || [])[0] || {}).source || '/mc/runtime.diary_synthesis_signal',
          summary: ((development.diary_synthesis_signals?.items || [])[0] || {}).diary_summary || 'No diary synthesis reflection',
        }),
        privateTemporalCuriosityState: normalizeJarvisItem((development.private_temporal_curiosity_states?.items || [])[0] || {}, {
          source: ((development.private_temporal_curiosity_states?.items || [])[0] || {}).source || '/mc/runtime.private_temporal_curiosity_state',
          summary: ((development.private_temporal_curiosity_states?.items || [])[0] || {}).curiosity_summary || 'No bounded temporal curiosity support',
        }),
        innerVisibleSupport: normalizeJarvisItem((development.inner_visible_support_signals?.items || [])[0] || {}, {
          source: ((development.inner_visible_support_signals?.items || [])[0] || {}).source || '/mc/runtime.inner_visible_support_signal',
          summary: ((development.inner_visible_support_signals?.items || [])[0] || {}).support_summary || 'No bounded inner-visible support',
        }),
        regulationHomeostasisSupport: normalizeJarvisItem((development.regulation_homeostasis_signals?.items || [])[0] || {}, {
          source: ((development.regulation_homeostasis_signals?.items || [])[0] || {}).source || '/mc/runtime.regulation_homeostasis_signal',
          summary: ((development.regulation_homeostasis_signals?.items || [])[0] || {}).regulation_summary || 'No bounded regulation/homeostasis support',
        }),
        relationStateSupport: normalizeJarvisItem((development.relation_state_signals?.items || [])[0] || {}, {
          source: ((development.relation_state_signals?.items || [])[0] || {}).source || '/mc/runtime.relation_state_signal',
          summary: ((development.relation_state_signals?.items || [])[0] || {}).relation_summary || 'No bounded relation-state support',
        }),
        relationContinuitySupport: normalizeJarvisItem((development.relation_continuity_signals?.items || [])[0] || {}, {
          source: ((development.relation_continuity_signals?.items || [])[0] || {}).source || '/mc/runtime.relation_continuity_signal',
          summary: ((development.relation_continuity_signals?.items || [])[0] || {}).continuity_summary || 'No bounded relation continuity support',
        }),
        meaningSignificanceSupport: normalizeJarvisItem((development.meaning_significance_signals?.items || [])[0] || {}, {
          source: ((development.meaning_significance_signals?.items || [])[0] || {}).source || '/mc/runtime.meaning_significance_signal',
          summary: ((development.meaning_significance_signals?.items || [])[0] || {}).meaning_summary || 'No bounded meaning/significance support',
        }),
        temperamentTendencySupport: normalizeJarvisItem((development.temperament_tendency_signals?.items || [])[0] || {}, {
          source: ((development.temperament_tendency_signals?.items || [])[0] || {}).source || '/mc/runtime.temperament_tendency_signal',
          summary: ((development.temperament_tendency_signals?.items || [])[0] || {}).temperament_summary || 'No bounded temperament support',
        }),
        selfNarrativeContinuitySupport: normalizeJarvisItem((development.self_narrative_continuity_signals?.items || [])[0] || {}, {
          source: ((development.self_narrative_continuity_signals?.items || [])[0] || {}).source || '/mc/runtime.self_narrative_continuity_signal',
          summary: ((development.self_narrative_continuity_signals?.items || [])[0] || {}).narrative_summary || 'No bounded self-narrative continuity support',
        }),
        metabolismStateSupport: normalizeJarvisItem((development.metabolism_state_signals?.items || [])[0] || {}, {
          source: ((development.metabolism_state_signals?.items || [])[0] || {}).source || '/mc/runtime.metabolism_state_signal',
          summary: ((development.metabolism_state_signals?.items || [])[0] || {}).metabolism_summary || 'No bounded metabolism support',
        }),
        releaseMarkerSupport: normalizeJarvisItem((development.release_marker_signals?.items || [])[0] || {}, {
          source: ((development.release_marker_signals?.items || [])[0] || {}).source || '/mc/runtime.release_marker_signal',
          summary: ((development.release_marker_signals?.items || [])[0] || {}).release_summary || 'No bounded release support',
        }),
        consolidationTargetSupport: normalizeJarvisItem((development.consolidation_target_signals?.items || [])[0] || {}, {
          source: ((development.consolidation_target_signals?.items || [])[0] || {}).source || '/mc/runtime.consolidation_target_signal',
          summary: ((development.consolidation_target_signals?.items || [])[0] || {}).consolidation_summary || 'No bounded consolidation-target support',
        }),
        selectiveForgettingCandidateSupport: normalizeJarvisItem((development.selective_forgetting_candidates?.items || [])[0] || {}, {
          source: ((development.selective_forgetting_candidates?.items || [])[0] || {}).source || '/mc/runtime.selective_forgetting_candidate',
          summary: ((development.selective_forgetting_candidates?.items || [])[0] || {}).forgetting_candidate_summary || 'No bounded selective-forgetting candidate',
        }),
        attachmentTopologySupport: normalizeJarvisItem((development.attachment_topology_signals?.items || [])[0] || {}, {
          source: ((development.attachment_topology_signals?.items || [])[0] || {}).source || '/mc/runtime.attachment_topology_signal',
          summary: ((development.attachment_topology_signals?.items || [])[0] || {}).attachment_summary || 'No bounded attachment-topology support',
        }),
        loyaltyGradientSupport: normalizeJarvisItem((development.loyalty_gradient_signals?.items || [])[0] || {}, {
          source: ((development.loyalty_gradient_signals?.items || [])[0] || {}).source || '/mc/runtime.loyalty_gradient_signal',
          summary: ((development.loyalty_gradient_signals?.items || [])[0] || {}).gradient_summary || 'No bounded loyalty-gradient support',
        }),
        autonomyPressureSupport: normalizeJarvisItem((development.autonomy_pressure_signals?.items || [])[0] || {}, {
          source: ((development.autonomy_pressure_signals?.items || [])[0] || {}).source || '/mc/runtime.autonomy_pressure_signal',
          summary: ((development.autonomy_pressure_signals?.items || [])[0] || {}).autonomy_pressure_summary || 'No bounded autonomy-pressure support',
        }),
        proactiveLoopLifecycleSupport: normalizeJarvisItem((development.proactive_loop_lifecycle_signals?.items || [])[0] || {}, {
          source: ((development.proactive_loop_lifecycle_signals?.items || [])[0] || {}).source || '/mc/runtime.proactive_loop_lifecycle',
          summary: ((development.proactive_loop_lifecycle_signals?.items || [])[0] || {}).loop_summary || 'No bounded proactive-loop lifecycle support',
        }),
        proactiveQuestionGateSupport: normalizeJarvisItem((development.proactive_question_gates?.items || [])[0] || {}, {
          source: ((development.proactive_question_gates?.items || [])[0] || {}).source || '/mc/runtime.proactive_question_gate',
          summary: ((development.proactive_question_gates?.items || [])[0] || {}).question_gate_summary || 'No bounded proactive-question gate support',
        }),
        emergentSignalSupport: normalizeJarvisItem((development.emergent_signals?.items || [])[0] || {}, {
          source: ((development.emergent_signals?.items || [])[0] || {}).source || '/mc/runtime.emergent_signal',
          summary: ((development.emergent_signals?.items || [])[0] || {}).short_summary || 'No active emergent inner signal',
        }),
        webchatExecutionPilotSupport: normalizeJarvisItem((development.webchat_execution_pilot?.items || [])[0] || {}, {
          source: ((development.webchat_execution_pilot?.items || [])[0] || {}).source || '/mc/runtime.execution_pilot',
          summary: ((development.webchat_execution_pilot?.items || [])[0] || {}).execution_summary || 'No tiny governed webchat execution pilot',
        }),
        selfNarrativeReviewBridgeSupport: normalizeJarvisItem((development.self_narrative_self_model_review_bridge?.items || [])[0] || {}, {
          source: ((development.self_narrative_self_model_review_bridge?.items || [])[0] || {}).source || '/mc/runtime.self_narrative_self_model_review_bridge',
          summary: ((development.self_narrative_self_model_review_bridge?.items || [])[0] || {}).proposal_input_summary || ((development.self_narrative_self_model_review_bridge?.items || [])[0] || {}).sharpening_input_summary || ((development.self_narrative_self_model_review_bridge?.items || [])[0] || {}).review_input_summary || ((development.self_narrative_self_model_review_bridge?.items || [])[0] || {}).pattern_summary || ((development.self_narrative_self_model_review_bridge?.items || [])[0] || {}).bridge_summary || 'No bounded self-narrative review bridge',
        }),
        executiveContradictionSupport: normalizeJarvisItem((development.executive_contradiction_signals?.items || [])[0] || {}, {
          source: ((development.executive_contradiction_signals?.items || [])[0] || {}).source || '/mc/runtime.executive_contradiction_signal',
          summary: ((development.executive_contradiction_signals?.items || [])[0] || {}).control_summary || 'No bounded executive contradiction support',
        }),
        privateTemporalPromotionSignal: normalizeJarvisItem((development.private_temporal_promotion_signals?.items || [])[0] || {}, {
          source: ((development.private_temporal_promotion_signals?.items || [])[0] || {}).source || '/mc/runtime.private_temporal_promotion_signal',
          summary: ((development.private_temporal_promotion_signals?.items || [])[0] || {}).promotion_summary || 'No bounded temporal promotion support',
        }),
        chronicleConsolidationSupport: normalizeJarvisItem((development.chronicle_consolidation_signals?.items || [])[0] || {}, {
          source: ((development.chronicle_consolidation_signals?.items || [])[0] || {}).source || '/mc/runtime.chronicle_consolidation_signal',
          summary: ((development.chronicle_consolidation_signals?.items || [])[0] || {}).chronicle_summary || 'No bounded chronicle/consolidation support',
        }),
        chronicleConsolidationBrief: normalizeJarvisItem((development.chronicle_consolidation_briefs?.items || [])[0] || {}, {
          source: ((development.chronicle_consolidation_briefs?.items || [])[0] || {}).source || '/mc/runtime.chronicle_consolidation_brief',
          summary: ((development.chronicle_consolidation_briefs?.items || [])[0] || {}).brief_reason || 'No bounded chronicle/consolidation brief',
        }),
        chronicleConsolidationProposal: normalizeJarvisItem((development.chronicle_consolidation_proposals?.items || [])[0] || {}, {
          source: ((development.chronicle_consolidation_proposals?.items || [])[0] || {}).source || '/mc/runtime.chronicle_consolidation_proposal',
          summary: ((development.chronicle_consolidation_proposals?.items || [])[0] || {}).proposal_reason || 'No bounded chronicle/consolidation proposal',
        }),
        growthNote: normalizeJarvisItem((development.growth_note?.recent_notes || [])[0] || {}, {
          source: ((development.growth_note?.recent_notes || [])[0] || {}).source || '/mc/runtime.private_growth_note',
          summary: ((development.growth_note?.recent_notes || [])[0] || {}).lesson || 'No recent lesson',
        }),
        reflectiveSelection: normalizeJarvisItem((development.reflective_selection?.recent_signals || [])[0] || {}, {
          source: ((development.reflective_selection?.recent_signals || [])[0] || {}).source || '/mc/runtime.private_reflective_selection',
          summary: ((development.reflective_selection?.recent_signals || [])[0] || {}).reinforce || 'No reinforce signal',
        }),
        operationalPreference: normalizeJarvisItem(development.operational_preference?.current || {}, {
          source: development.operational_preference?.current?.source || '/mc/runtime.private_operational_preference',
          summary: development.operational_preference?.current?.preference_reason || 'No preference reason',
        }),
        operationalAlignment: normalizeJarvisItem(development.operational_alignment?.current || {}, {
          source: '/mc/runtime.operational_preference_alignment',
          summary: development.operational_alignment?.current?.mismatch_reason || development.operational_alignment?.current?.alignment_status || 'No alignment signal',
        }),
        temporalCuriosity: normalizeJarvisItem(development.temporal_curiosity?.current || {}, {
          source: development.temporal_curiosity?.current?.source || '/mc/runtime.private_temporal_curiosity_state',
          summary: `${development.temporal_curiosity?.current?.rhythm_state || 'unknown'} · ${development.temporal_curiosity?.current?.curiosity_level || 'unknown'}`,
        }),
        developmentFocuses: {
          active: Boolean(development.development_focuses?.active),
          summary: development.development_focuses?.summary || {},
          items: (development.development_focuses?.items || []).map(normalizeDevelopmentFocus),
        },
        privateInnerNoteSignals: {
          active: Boolean(development.private_inner_note_signals?.active),
          authority: development.private_inner_note_signals?.authority || 'non-authoritative',
          layerRole: development.private_inner_note_signals?.layer_role || 'runtime-support',
          summary: development.private_inner_note_signals?.summary || {},
          items: (development.private_inner_note_signals?.items || []).map((item) => normalizeJarvisItem(item, {
            source: item.source || '/mc/runtime.private_inner_note_signal',
            summary: item.note_summary || item.summary || 'Inspect bounded inner-note support',
          })),
        },
        privateInitiativeTensionSignals: {
          active: Boolean(development.private_initiative_tension_signals?.active),
          authority: development.private_initiative_tension_signals?.authority || 'non-authoritative',
          layerRole: development.private_initiative_tension_signals?.layer_role || 'runtime-support',
          summary: development.private_initiative_tension_signals?.summary || {},
          items: (development.private_initiative_tension_signals?.items || []).map((item) => normalizeJarvisItem(item, {
            source: item.source || '/mc/runtime.private_initiative_tension_signal',
            summary: item.tension_summary || item.summary || 'Inspect bounded initiative tension support',
          })),
        },
        privateInnerInterplaySignals: {
          active: Boolean(development.private_inner_interplay_signals?.active),
          authority: development.private_inner_interplay_signals?.authority || 'non-authoritative',
          layerRole: development.private_inner_interplay_signals?.layer_role || 'runtime-support',
          summary: development.private_inner_interplay_signals?.summary || {},
          items: (development.private_inner_interplay_signals?.items || []).map((item) => normalizeJarvisItem(item, {
            source: item.source || '/mc/runtime.private_inner_interplay_signal',
            summary: item.interplay_summary || item.summary || 'Inspect bounded inner interplay support',
          })),
        },
        privateStateSnapshots: {
          active: Boolean(development.private_state_snapshots?.active),
          authority: development.private_state_snapshots?.authority || 'non-authoritative',
          layerRole: development.private_state_snapshots?.layer_role || 'runtime-support',
          summary: development.private_state_snapshots?.summary || {},
          items: (development.private_state_snapshots?.items || []).map((item) => normalizeJarvisItem(item, {
            source: item.source || '/mc/runtime.private_state_snapshot',
            summary: item.state_summary || item.summary || 'Inspect bounded private-state snapshot',
          })),
        },
        diarySynthesisSignals: {
          active: Boolean(development.diary_synthesis_signals?.active),
          authority: development.diary_synthesis_signals?.authority || 'non-authoritative',
          layerRole: development.diary_synthesis_signals?.layer_role || 'runtime-support',
          summary: development.diary_synthesis_signals?.summary || {},
          items: (development.diary_synthesis_signals?.items || []).map((item) => normalizeJarvisItem(item, {
            source: item.source || '/mc/runtime.diary_synthesis_signal',
            summary: item.diary_summary || item.summary || 'Inspect diary synthesis reflection',
          })),
        },
        privateTemporalCuriosityStates: {
          active: Boolean(development.private_temporal_curiosity_states?.active),
          authority: development.private_temporal_curiosity_states?.authority || 'non-authoritative',
          layerRole: development.private_temporal_curiosity_states?.layer_role || 'runtime-support',
          summary: development.private_temporal_curiosity_states?.summary || {},
          items: (development.private_temporal_curiosity_states?.items || []).map((item) => normalizeJarvisItem(item, {
            source: item.source || '/mc/runtime.private_temporal_curiosity_state',
            summary: item.curiosity_summary || item.summary || 'Inspect bounded temporal curiosity support',
          })),
        },
        innerVisibleSupportSignals: {
          active: Boolean(development.inner_visible_support_signals?.active),
          authority: development.inner_visible_support_signals?.authority || 'non-authoritative',
          layerRole: development.inner_visible_support_signals?.layer_role || 'runtime-support',
          promptBridgeState: development.inner_visible_support_signals?.prompt_bridge_state || 'not-yet-bridged',
          summary: development.inner_visible_support_signals?.summary || {},
          items: (development.inner_visible_support_signals?.items || []).map((item) => normalizeJarvisItem(item, {
            source: item.source || '/mc/runtime.inner_visible_support_signal',
            summary: item.support_summary || item.summary || 'Inspect bounded inner-visible support',
          })),
        },
        regulationHomeostasisSignals: {
          active: Boolean(development.regulation_homeostasis_signals?.active),
          authority: development.regulation_homeostasis_signals?.authority || 'non-authoritative',
          layerRole: development.regulation_homeostasis_signals?.layer_role || 'runtime-support',
          canonicalMoodState: development.regulation_homeostasis_signals?.canonical_mood_state || 'not-canonical-mood-or-personality',
          summary: development.regulation_homeostasis_signals?.summary || {},
          items: (development.regulation_homeostasis_signals?.items || []).map((item) => normalizeJarvisItem(item, {
            source: item.source || '/mc/runtime.regulation_homeostasis_signal',
            summary: item.regulation_summary || item.summary || 'Inspect bounded regulation/homeostasis support',
          })),
        },
        relationStateSignals: {
          active: Boolean(development.relation_state_signals?.active),
          authority: development.relation_state_signals?.authority || 'non-authoritative',
          layerRole: development.relation_state_signals?.layer_role || 'runtime-support',
          canonicalRelationState: development.relation_state_signals?.canonical_relation_state || 'not-canonical-relationship-truth',
          summary: development.relation_state_signals?.summary || {},
          items: (development.relation_state_signals?.items || []).map((item) => normalizeJarvisItem(item, {
            source: item.source || '/mc/runtime.relation_state_signal',
            summary: item.relation_summary || item.summary || 'Inspect bounded relation-state support',
          })),
        },
        relationContinuitySignals: {
          active: Boolean(development.relation_continuity_signals?.active),
          authority: development.relation_continuity_signals?.authority || 'non-authoritative',
          layerRole: development.relation_continuity_signals?.layer_role || 'runtime-support',
          canonicalRelationState: development.relation_continuity_signals?.canonical_relation_state || 'not-canonical-relationship-truth',
          summary: development.relation_continuity_signals?.summary || {},
          items: (development.relation_continuity_signals?.items || []).map((item) => normalizeJarvisItem(item, {
            source: item.source || '/mc/runtime.relation_continuity_signal',
            summary: item.continuity_summary || item.summary || 'Inspect bounded relation continuity support',
          })),
        },
        meaningSignificanceSignals: {
          active: Boolean(development.meaning_significance_signals?.active),
          authority: development.meaning_significance_signals?.authority || 'non-authoritative',
          layerRole: development.meaning_significance_signals?.layer_role || 'runtime-support',
          canonicalValueState: development.meaning_significance_signals?.canonical_value_state || 'not-canonical-value-or-moral-truth',
          summary: development.meaning_significance_signals?.summary || {},
          items: (development.meaning_significance_signals?.items || []).map((item) => normalizeJarvisItem(item, {
            source: item.source || '/mc/runtime.meaning_significance_signal',
            summary: item.meaning_summary || item.summary || 'Inspect bounded meaning/significance support',
          })),
        },
        temperamentTendencySignals: {
          active: Boolean(development.temperament_tendency_signals?.active),
          authority: development.temperament_tendency_signals?.authority || 'non-authoritative',
          layerRole: development.temperament_tendency_signals?.layer_role || 'runtime-support',
          canonicalPersonalityState: development.temperament_tendency_signals?.canonical_personality_state || 'not-canonical-personality-truth',
          summary: development.temperament_tendency_signals?.summary || {},
          items: (development.temperament_tendency_signals?.items || []).map((item) => normalizeJarvisItem(item, {
            source: item.source || '/mc/runtime.temperament_tendency_signal',
            summary: item.temperament_summary || item.summary || 'Inspect bounded temperament support',
          })),
        },
        selfNarrativeContinuitySignals: {
          active: Boolean(development.self_narrative_continuity_signals?.active),
          authority: development.self_narrative_continuity_signals?.authority || 'non-authoritative',
          layerRole: development.self_narrative_continuity_signals?.layer_role || 'runtime-support',
          canonicalIdentityState: development.self_narrative_continuity_signals?.canonical_identity_state || 'not-canonical-identity-truth',
          summary: development.self_narrative_continuity_signals?.summary || {},
          items: (development.self_narrative_continuity_signals?.items || []).map((item) => normalizeJarvisItem(item, {
            source: item.source || '/mc/runtime.self_narrative_continuity_signal',
            summary: item.narrative_summary || item.summary || 'Inspect bounded self-narrative continuity support',
          })),
        },
        metabolismStateSignals: {
          active: Boolean(development.metabolism_state_signals?.active),
          authority: development.metabolism_state_signals?.authority || 'non-authoritative',
          layerRole: development.metabolism_state_signals?.layer_role || 'runtime-support',
          canonicalDeleteState: development.metabolism_state_signals?.canonical_delete_state || 'not-canonical-deletion',
          selfErasureState: development.metabolism_state_signals?.self_erasure_state || 'not-self-erasure',
          summary: development.metabolism_state_signals?.summary || {},
          items: (development.metabolism_state_signals?.items || []).map((item) => normalizeMetabolismStateSignal(item)),
        },
        releaseMarkerSignals: {
          active: Boolean(development.release_marker_signals?.active),
          authority: development.release_marker_signals?.authority || 'non-authoritative',
          layerRole: development.release_marker_signals?.layer_role || 'runtime-support',
          canonicalDeleteState: development.release_marker_signals?.canonical_delete_state || 'not-canonical-deletion',
          selfErasureState: development.release_marker_signals?.self_erasure_state || 'not-self-erasure',
          selectiveForgettingState: development.release_marker_signals?.selective_forgetting_state || 'not-selective-forgetting-execution',
          summary: development.release_marker_signals?.summary || {},
          items: (development.release_marker_signals?.items || []).map((item) => normalizeReleaseMarkerSignal(item)),
        },
        consolidationTargetSignals: {
          active: Boolean(development.consolidation_target_signals?.active),
          authority: development.consolidation_target_signals?.authority || 'non-authoritative',
          layerRole: development.consolidation_target_signals?.layer_role || 'runtime-support',
          writebackState: development.consolidation_target_signals?.writeback_state || 'not-writeback',
          canonicalMutationState: development.consolidation_target_signals?.canonical_mutation_state || 'not-canonical-mutation',
          summary: development.consolidation_target_signals?.summary || {},
          items: (development.consolidation_target_signals?.items || []).map((item) => normalizeConsolidationTargetSignal(item)),
        },
        selectiveForgettingCandidates: {
          active: Boolean(development.selective_forgetting_candidates?.active),
          authority: development.selective_forgetting_candidates?.authority || 'non-authoritative',
          layerRole: development.selective_forgetting_candidates?.layer_role || 'runtime-support',
          canonicalDeleteState: development.selective_forgetting_candidates?.canonical_delete_state || 'not-deletion',
          selfErasureState: development.selective_forgetting_candidates?.self_erasure_state || 'not-self-erasure',
          selectiveForgettingState: development.selective_forgetting_candidates?.selective_forgetting_state || 'not-selective-forgetting-execution',
          summary: development.selective_forgetting_candidates?.summary || {},
          items: (development.selective_forgetting_candidates?.items || []).map((item) => normalizeSelectiveForgettingCandidate(item)),
        },
        attachmentTopologySignals: {
          active: Boolean(development.attachment_topology_signals?.active),
          authority: development.attachment_topology_signals?.authority || 'non-authoritative',
          layerRole: development.attachment_topology_signals?.layer_role || 'runtime-support',
          plannerPriorityState: development.attachment_topology_signals?.planner_priority_state || 'not-planner-priority',
          canonicalPreferenceState: development.attachment_topology_signals?.canonical_preference_state || 'not-canonical-preference-truth',
          summary: development.attachment_topology_signals?.summary || {},
          items: (development.attachment_topology_signals?.items || []).map((item) => normalizeJarvisItem(item, {
            source: item.source || '/mc/runtime.attachment_topology_signal',
            summary: item.attachment_summary || item.summary || 'Inspect bounded attachment-topology support',
          })),
        },
        loyaltyGradientSignals: {
          active: Boolean(development.loyalty_gradient_signals?.active),
          authority: development.loyalty_gradient_signals?.authority || 'non-authoritative',
          layerRole: development.loyalty_gradient_signals?.layer_role || 'runtime-support',
          plannerPriorityState: development.loyalty_gradient_signals?.planner_priority_state || 'not-planner-priority',
          canonicalPreferenceState: development.loyalty_gradient_signals?.canonical_preference_state || 'not-canonical-preference-truth',
          promptInclusionState: development.loyalty_gradient_signals?.prompt_inclusion_state || 'not-prompt-included',
          workflowBridgeState: development.loyalty_gradient_signals?.workflow_bridge_state || 'not-workflow-bridge',
          summary: development.loyalty_gradient_signals?.summary || {},
          items: (development.loyalty_gradient_signals?.items || []).map((item) => normalizeJarvisItem(item, {
            source: item.source || '/mc/runtime.loyalty_gradient_signal',
            summary: item.gradient_summary || item.summary || 'Inspect bounded loyalty-gradient support',
          })),
        },
        autonomyPressureSignals: {
          active: Boolean(development.autonomy_pressure_signals?.active),
          authority: development.autonomy_pressure_signals?.authority || 'non-authoritative',
          layerRole: development.autonomy_pressure_signals?.layer_role || 'runtime-support',
          plannerAuthorityState: development.autonomy_pressure_signals?.planner_authority_state || 'not-planner-authority',
          proactiveExecutionState: development.autonomy_pressure_signals?.proactive_execution_state || 'not-proactive-execution',
          canonicalIntentionState: development.autonomy_pressure_signals?.canonical_intention_state || 'not-canonical-intention-truth',
          promptInclusionState: development.autonomy_pressure_signals?.prompt_inclusion_state || 'not-prompt-included',
          workflowBridgeState: development.autonomy_pressure_signals?.workflow_bridge_state || 'not-workflow-bridge',
          summary: development.autonomy_pressure_signals?.summary || {},
          items: (development.autonomy_pressure_signals?.items || []).map((item) => normalizeJarvisItem(item, {
            source: item.source || '/mc/runtime.autonomy_pressure_signal',
            summary: item.autonomy_pressure_summary || item.summary || 'Inspect bounded autonomy-pressure support',
          })),
        },
        proactiveLoopLifecycleSignals: {
          active: Boolean(development.proactive_loop_lifecycle_signals?.active),
          authority: development.proactive_loop_lifecycle_signals?.authority || 'non-authoritative',
          layerRole: development.proactive_loop_lifecycle_signals?.layer_role || 'runtime-support',
          plannerAuthorityState: development.proactive_loop_lifecycle_signals?.planner_authority_state || 'not-planner-authority',
          proactiveExecutionState: development.proactive_loop_lifecycle_signals?.proactive_execution_state || 'not-proactive-execution',
          canonicalIntentionState: development.proactive_loop_lifecycle_signals?.canonical_intention_state || 'not-canonical-intention-truth',
          promptInclusionState: development.proactive_loop_lifecycle_signals?.prompt_inclusion_state || 'not-prompt-included',
          workflowBridgeState: development.proactive_loop_lifecycle_signals?.workflow_bridge_state || 'not-workflow-bridge',
          summary: development.proactive_loop_lifecycle_signals?.summary || {},
          items: (development.proactive_loop_lifecycle_signals?.items || []).map((item) => normalizeJarvisItem(item, {
            source: item.source || '/mc/runtime.proactive_loop_lifecycle',
            summary: item.loop_summary || item.summary || 'Inspect bounded proactive-loop lifecycle support',
          })),
        },
        proactiveQuestionGates: {
          active: Boolean(development.proactive_question_gates?.active),
          authority: development.proactive_question_gates?.authority || 'non-authoritative',
          layerRole: development.proactive_question_gates?.layer_role || 'runtime-support',
          plannerAuthorityState: development.proactive_question_gates?.planner_authority_state || 'not-planner-authority',
          proactiveExecutionState: development.proactive_question_gates?.proactive_execution_state || 'not-proactive-execution',
          canonicalIntentionState: development.proactive_question_gates?.canonical_intention_state || 'not-canonical-intention-truth',
          promptInclusionState: development.proactive_question_gates?.prompt_inclusion_state || 'not-prompt-included',
          workflowBridgeState: development.proactive_question_gates?.workflow_bridge_state || 'not-workflow-bridge',
          summary: development.proactive_question_gates?.summary || {},
          items: (development.proactive_question_gates?.items || []).map((item) => normalizeJarvisItem(item, {
            source: item.source || '/mc/runtime.proactive_question_gate',
            summary: item.question_gate_summary || item.summary || 'Inspect bounded proactive-question gate support',
          })),
        },
        webchatExecutionPilot: {
          active: Boolean(development.webchat_execution_pilot?.active),
          authority: development.webchat_execution_pilot?.authority || 'non-authoritative',
          layerRole: development.webchat_execution_pilot?.layer_role || 'runtime-support',
          plannerAuthorityState: development.webchat_execution_pilot?.planner_authority_state || 'not-planner-authority',
          proactiveExecutionState: development.webchat_execution_pilot?.proactive_execution_state || 'tiny-governed-webchat-only',
          canonicalIntentionState: development.webchat_execution_pilot?.canonical_intention_state || 'not-canonical-intention-truth',
          promptInclusionState: development.webchat_execution_pilot?.prompt_inclusion_state || 'not-prompt-included',
          workflowBridgeState: development.webchat_execution_pilot?.workflow_bridge_state || 'not-workflow-bridge',
          discordExecutionState: development.webchat_execution_pilot?.discord_execution_state || 'not-enabled',
          summary: development.webchat_execution_pilot?.summary || {},
          items: (development.webchat_execution_pilot?.items || []).map((item) => normalizeJarvisItem(item, {
            source: item.source || '/mc/runtime.execution_pilot',
            summary: item.execution_summary || item.summary || 'Inspect tiny governed webchat execution pilot',
          })),
        },
        selfNarrativeSelfModelReviewBridge: {
          active: Boolean(development.self_narrative_self_model_review_bridge?.active),
          authority: development.self_narrative_self_model_review_bridge?.authority || 'non-authoritative',
          layerRole: development.self_narrative_self_model_review_bridge?.layer_role || 'runtime-support',
          reviewMode: development.self_narrative_self_model_review_bridge?.review_mode || 'read-only-review-support',
          proposalState: development.self_narrative_self_model_review_bridge?.proposal_state || 'not-selfhood-proposal',
          canonicalIdentityState: development.self_narrative_self_model_review_bridge?.canonical_identity_state || 'not-canonical-identity-truth',
          summary: development.self_narrative_self_model_review_bridge?.summary || {},
          patterns: development.self_narrative_self_model_review_bridge?.patterns || [],
          reviewInputs: development.self_narrative_self_model_review_bridge?.review_inputs || [],
          sharpeningInputs: development.self_narrative_self_model_review_bridge?.sharpening_inputs || [],
          proposalInputs: development.self_narrative_self_model_review_bridge?.proposal_inputs || [],
          items: (development.self_narrative_self_model_review_bridge?.items || []).map((item) => normalizeJarvisItem(item, {
            source: item.source || '/mc/runtime.self_narrative_self_model_review_bridge',
            summary: item.proposal_input_summary || item.sharpening_input_summary || item.review_input_summary || item.pattern_summary || item.bridge_summary || item.summary || 'Inspect bounded self-narrative review bridge',
          })),
        },
        executiveContradictionSignals: {
          active: Boolean(development.executive_contradiction_signals?.active),
          authority: development.executive_contradiction_signals?.authority || 'non-authoritative',
          layerRole: development.executive_contradiction_signals?.layer_role || 'runtime-support',
          executionVetoState: development.executive_contradiction_signals?.execution_veto_state || 'not-authorized',
          summary: development.executive_contradiction_signals?.summary || {},
          items: (development.executive_contradiction_signals?.items || []).map((item) => normalizeJarvisItem(item, {
            source: item.source || '/mc/runtime.executive_contradiction_signal',
            summary: item.control_summary || item.summary || 'Inspect bounded executive contradiction support',
          })),
        },
        privateTemporalPromotionSignals: {
          active: Boolean(development.private_temporal_promotion_signals?.active),
          authority: development.private_temporal_promotion_signals?.authority || 'non-authoritative',
          layerRole: development.private_temporal_promotion_signals?.layer_role || 'runtime-support',
          summary: development.private_temporal_promotion_signals?.summary || {},
          items: (development.private_temporal_promotion_signals?.items || []).map((item) => normalizeJarvisItem(item, {
            source: item.source || '/mc/runtime.private_temporal_promotion_signal',
            summary: item.promotion_summary || item.summary || 'Inspect bounded temporal promotion support',
          })),
        },
        chronicleConsolidationSignals: {
          active: Boolean(development.chronicle_consolidation_signals?.active),
          authority: development.chronicle_consolidation_signals?.authority || 'non-authoritative',
          layerRole: development.chronicle_consolidation_signals?.layer_role || 'runtime-support',
          writebackState: development.chronicle_consolidation_signals?.writeback_state || 'not-writing-to-canonical-files',
          summary: development.chronicle_consolidation_signals?.summary || {},
          items: (development.chronicle_consolidation_signals?.items || []).map((item) => normalizeJarvisItem(item, {
            source: item.source || '/mc/runtime.chronicle_consolidation_signal',
            summary: item.chronicle_summary || item.summary || 'Inspect bounded chronicle/consolidation support',
          })),
        },
        chronicleConsolidationBriefs: {
          active: Boolean(development.chronicle_consolidation_briefs?.active),
          authority: development.chronicle_consolidation_briefs?.authority || 'non-authoritative',
          layerRole: development.chronicle_consolidation_briefs?.layer_role || 'runtime-support',
          writebackState: development.chronicle_consolidation_briefs?.writeback_state || 'not-writing-to-canonical-files',
          summary: development.chronicle_consolidation_briefs?.summary || {},
          items: (development.chronicle_consolidation_briefs?.items || []).map((item) => normalizeJarvisItem(item, {
            source: item.source || '/mc/runtime.chronicle_consolidation_brief',
            summary: item.brief_reason || item.summary || 'Inspect bounded chronicle/consolidation brief',
          })),
        },
        chronicleConsolidationProposals: {
          active: Boolean(development.chronicle_consolidation_proposals?.active),
          authority: development.chronicle_consolidation_proposals?.authority || 'non-authoritative',
          layerRole: development.chronicle_consolidation_proposals?.layer_role || 'runtime-support',
          writebackState: development.chronicle_consolidation_proposals?.writeback_state || 'not-writing-to-canonical-files',
          summary: development.chronicle_consolidation_proposals?.summary || {},
          items: (development.chronicle_consolidation_proposals?.items || []).map((item) => normalizeJarvisItem(item, {
            source: item.source || '/mc/runtime.chronicle_consolidation_proposal',
            summary: item.proposal_reason || item.summary || 'Inspect bounded chronicle/consolidation proposal',
          })),
        },
        reflectiveCritics: {
          active: Boolean(development.reflective_critics?.active),
          summary: development.reflective_critics?.summary || {},
          items: (development.reflective_critics?.items || []).map(normalizeReflectiveCritic),
        },
        selfModelSignals: {
          active: Boolean(development.self_model_signals?.active),
          summary: development.self_model_signals?.summary || {},
          items: (development.self_model_signals?.items || []).map(normalizeSelfModelSignal),
        },
        goalSignals: {
          active: Boolean(development.goal_signals?.active),
          summary: development.goal_signals?.summary || {},
          items: (development.goal_signals?.items || []).map(normalizeGoalSignal),
        },
        reflectionSignals: {
          active: Boolean(development.reflection_signals?.active),
          summary: development.reflection_signals?.summary || {},
          items: (development.reflection_signals?.items || []).map(normalizeReflectionSignal),
          recentHistory: (development.reflection_signals?.recent_history || []).map(normalizeReflectionHistoryItem),
        },
        temporalRecurrenceSignals: {
          active: Boolean(development.temporal_recurrence_signals?.active),
          summary: development.temporal_recurrence_signals?.summary || {},
          items: (development.temporal_recurrence_signals?.items || []).map(normalizeTemporalRecurrenceSignal),
        },
        witnessSignals: {
          active: Boolean(development.witness_signals?.active),
          summary: development.witness_signals?.summary || {},
          items: (development.witness_signals?.items || []).map(normalizeWitnessSignal),
        },
        openLoopSignals: {
          active: Boolean(development.open_loop_signals?.active),
          summary: development.open_loop_signals?.summary || {},
          items: (development.open_loop_signals?.items || []).map(normalizeOpenLoopSignal),
        },
        openLoopClosureProposals: {
          active: Boolean(development.open_loop_closure_proposals?.active),
          summary: development.open_loop_closure_proposals?.summary || {},
          items: (development.open_loop_closure_proposals?.items || []).map(normalizeOpenLoopClosureProposal),
        },
        internalOppositionSignals: {
          active: Boolean(development.internal_opposition_signals?.active),
          summary: development.internal_opposition_signals?.summary || {},
          items: (development.internal_opposition_signals?.items || []).map(normalizeInternalOppositionSignal),
        },
        selfReviewSignals: {
          active: Boolean(development.self_review_signals?.active),
          summary: development.self_review_signals?.summary || {},
          items: (development.self_review_signals?.items || []).map(normalizeSelfReviewSignal),
        },
        selfReviewRecords: {
          active: Boolean(development.self_review_records?.active),
          summary: development.self_review_records?.summary || {},
          items: (development.self_review_records?.items || []).map(normalizeSelfReviewRecord),
        },
        selfReviewRuns: {
          active: Boolean(development.self_review_runs?.active),
          summary: development.self_review_runs?.summary || {},
          items: (development.self_review_runs?.items || []).map(normalizeSelfReviewRun),
        },
        selfReviewOutcomes: {
          active: Boolean(development.self_review_outcomes?.active),
          summary: development.self_review_outcomes?.summary || {},
          items: (development.self_review_outcomes?.items || []).map(normalizeSelfReviewOutcome),
        },
        selfReviewCadenceSignals: {
          active: Boolean(development.self_review_cadence_signals?.active),
          summary: development.self_review_cadence_signals?.summary || {},
          items: (development.self_review_cadence_signals?.items || []).map(normalizeSelfReviewCadenceSignal),
        },
        dreamHypothesisSignals: {
          active: Boolean(development.dream_hypothesis_signals?.active),
          summary: development.dream_hypothesis_signals?.summary || {},
          items: (development.dream_hypothesis_signals?.items || []).map(normalizeDreamHypothesisSignal),
        },
        dreamAdoptionCandidates: {
          active: Boolean(development.dream_adoption_candidates?.active),
          summary: development.dream_adoption_candidates?.summary || {},
          items: (development.dream_adoption_candidates?.items || []).map(normalizeDreamAdoptionCandidate),
        },
        dreamInfluenceProposals: {
          active: Boolean(development.dream_influence_proposals?.active),
          summary: development.dream_influence_proposals?.summary || {},
          items: (development.dream_influence_proposals?.items || []).map(normalizeDreamInfluenceProposal),
        },
        selfAuthoredPromptProposals: {
          active: Boolean(development.self_authored_prompt_proposals?.active),
          summary: development.self_authored_prompt_proposals?.summary || {},
          items: (development.self_authored_prompt_proposals?.items || []).map(normalizeSelfAuthoredPromptProposal),
        },
        promptEvolution: normalizePromptEvolution(development.prompt_evolution || promptEvolutionSource || {}),
        affectiveMetaState: normalizeAffectiveMetaState(development.affective_meta_state || affectiveMetaSource || {}),
        epistemicRuntimeState: normalizeEpistemicRuntimeState(development.epistemic_runtime_state || epistemicSource || {}),
        subagentEcology: normalizeSubagentEcology(development.subagent_ecology || subagentEcologySource || {}),
        councilRuntime: normalizeCouncilRuntime(development.council_runtime || councilRuntimeSource || {}),
        adaptivePlanner: normalizeAdaptivePlanner(development.adaptive_planner || adaptivePlannerSource || {}),
        adaptiveReasoning: normalizeAdaptiveReasoning(development.adaptive_reasoning || adaptiveReasoningSource || {}),
        dreamInfluence: normalizeDreamInfluence(dreamInfluenceSource || {}),
        guidedLearning: normalizeGuidedLearning(development.guided_learning || guidedLearningSource || {}),
        adaptiveLearning: normalizeAdaptiveLearning(development.adaptive_learning || adaptiveLearningSource || {}),
        userUnderstandingSignals: {
          active: Boolean(development.user_understanding_signals?.active),
          summary: development.user_understanding_signals?.summary || {},
          items: (development.user_understanding_signals?.items || []).map(normalizeUserUnderstandingSignal),
        },
        userMdUpdateProposals: {
          active: Boolean(development.user_md_update_proposals?.active),
          summary: development.user_md_update_proposals?.summary || {},
          items: (development.user_md_update_proposals?.items || []).map(normalizeUserMdUpdateProposal),
        },
        selfhoodProposals: {
          active: Boolean(development.selfhood_proposals?.active),
          summary: development.selfhood_proposals?.summary || {},
          items: (development.selfhood_proposals?.items || []).map(normalizeSelfhoodProposal),
        },
        emergentSignals: {
          active: Boolean(development.emergent_signals?.active),
          authority: development.emergent_signals?.authority || 'candidate-only',
          layerRole: development.emergent_signals?.layer_role || 'runtime-support',
          visibility: development.emergent_signals?.visibility || 'internal-only',
          identityBoundary: development.emergent_signals?.identity_boundary || 'not-canonical-identity-truth',
          memoryBoundary: development.emergent_signals?.memory_boundary || 'not-workspace-memory',
          actionBoundary: development.emergent_signals?.action_boundary || 'not-action',
          lastDaemonRunAt: development.emergent_signals?.last_daemon_run_at || '',
          lastDaemonResult: development.emergent_signals?.last_daemon_result || null,
          summary: development.emergent_signals?.summary || {},
          items: (development.emergent_signals?.items || []).map((item) => normalizeEmergentSignal(item)),
          recentReleased: (development.emergent_signals?.recent_released || []).map((item) => normalizeEmergentSignal(item)),
        },
      },
      continuity: {
        visibleSession: normalizeJarvisItem(continuity.visible_session || {}, {
          source: continuity.visible_session?.source || '/mc/runtime.visible_session_continuity',
          summary: continuity.visible_session?.latest_text_preview || 'No recent session continuity',
        }),
        visibleContinuity: normalizeJarvisItem(continuity.visible_continuity || {}, {
          source: continuity.visible_continuity?.source || '/mc/runtime.visible_continuity',
          summary: `${continuity.visible_continuity?.included_rows || 0} recent visible continuity rows`,
        }),
        relationState: normalizeJarvisItem(continuity.relation_state?.current || {}, {
          source: continuity.relation_state?.current?.source || '/mc/runtime.private_relation_state',
          summary: continuity.relation_state?.current?.relation_pull || 'No relation pull',
        }),
        promotionSignal: normalizeJarvisItem(continuity.promotion_signal?.current || {}, {
          source: continuity.promotion_signal?.current?.source || '/mc/runtime.private_temporal_promotion_signal',
          summary: continuity.promotion_signal?.current?.promotion_target || 'No promotion target',
        }),
        promotionDecision: normalizeJarvisItem(continuity.promotion_decision?.current || {}, {
          source: continuity.promotion_decision?.current?.source || '/mc/runtime.private_promotion_decision',
          summary: continuity.promotion_decision?.current?.promotion_target || 'No promotion decision',
        }),
        worldModelSignals: {
          active: Boolean(continuity.world_model_signals?.active),
          summary: continuity.world_model_signals?.summary || {},
          items: (continuity.world_model_signals?.items || []).map(normalizeWorldModelSignal),
        },
        runtimeAwarenessSignals: {
          active: Boolean(continuity.runtime_awareness_signals?.active),
          summary: continuity.runtime_awareness_signals?.summary || {},
          items: (continuity.runtime_awareness_signals?.items || []).map(normalizeRuntimeAwarenessSignal),
          recentHistory: (continuity.runtime_awareness_signals?.recent_history || []).map(normalizeRuntimeAwarenessHistoryItem),
        },
        selfSystemCodeAwareness: normalizeSelfSystemCodeAwareness(selfSystemCodeAwarenessSource || {}),
      },
      heartbeat: {
        state: normalizeHeartbeatState(heartbeat.state || {}),
        policy: normalizeHeartbeatPolicy(heartbeat.policy || {}),
        recentTicks: (heartbeat.recent_ticks || []).map(normalizeHeartbeatTick),
        recentEvents: (heartbeat.recent_events || []).map(normalizeEventItem),
        embodiedState: normalizeEmbodiedState(heartbeat.embodied_state || embodiedStateSource || {}),
        loopRuntime: normalizeLoopRuntime(heartbeat.loop_runtime || loopRuntimeSource || {}),
        idleConsolidation: normalizeIdleConsolidation(heartbeat.idle_consolidation || idleConsolidationSource || {}),
        dreamArticulation: normalizeDreamArticulation(heartbeat.dream_articulation || dreamArticulationSource || {}),
        promptEvolution: normalizePromptEvolution(heartbeat.prompt_evolution || promptEvolutionSource || {}),
        affectiveMetaState: normalizeAffectiveMetaState(heartbeat.affective_meta_state || affectiveMetaSource || {}),
        epistemicRuntimeState: normalizeEpistemicRuntimeState(heartbeat.epistemic_runtime_state || epistemicSource || {}),
        subagentEcology: normalizeSubagentEcology(heartbeat.subagent_ecology || subagentEcologySource || {}),
        councilRuntime: normalizeCouncilRuntime(heartbeat.council_runtime || councilRuntimeSource || {}),
        adaptivePlanner: normalizeAdaptivePlanner(heartbeat.adaptive_planner || adaptivePlannerSource || {}),
        adaptiveReasoning: normalizeAdaptiveReasoning(heartbeat.adaptive_reasoning || adaptiveReasoningSource || {}),
        dreamInfluence: normalizeDreamInfluence(heartbeat.dream_influence || dreamInfluenceSource || {}),
        guidedLearning: normalizeGuidedLearning(heartbeat.guided_learning || guidedLearningSource || {}),
        adaptiveLearning: normalizeAdaptiveLearning(heartbeat.adaptive_learning || adaptiveLearningSource || {}),
        selfSystemCodeAwareness: normalizeSelfSystemCodeAwareness(heartbeat.self_system_code_awareness || selfSystemCodeAwarenessSource || {}),
      },
      embodiedState: normalizeEmbodiedState(embodiedStateSource || {}),
      loopRuntime: normalizeLoopRuntime(loopRuntimeSource || {}),
      idleConsolidation: normalizeIdleConsolidation(idleConsolidationSource || {}),
      dreamArticulation: normalizeDreamArticulation(dreamArticulationSource || {}),
      promptEvolution: normalizePromptEvolution(promptEvolutionSource || {}),
      affectiveMetaState: normalizeAffectiveMetaState(affectiveMetaSource || {}),
      epistemicRuntimeState: normalizeEpistemicRuntimeState(epistemicSource || {}),
      subagentEcology: normalizeSubagentEcology(subagentEcologySource || {}),
      councilRuntime: normalizeCouncilRuntime(councilRuntimeSource || {}),
      adaptivePlanner: normalizeAdaptivePlanner(adaptivePlannerSource || {}),
      adaptiveReasoning: normalizeAdaptiveReasoning(adaptiveReasoningSource || {}),
      dreamInfluence: normalizeDreamInfluence(dreamInfluenceSource || {}),
      guidedLearning: normalizeGuidedLearning(guidedLearningSource || {}),
      adaptiveLearning: normalizeAdaptiveLearning(adaptiveLearningSource || {}),
      selfSystemCodeAwareness: normalizeSelfSystemCodeAwareness(selfSystemCodeAwarenessSource || {}),
      experientialRuntimeContext: normalizeExperientialRuntimeContext(experientialRuntimeContextSource || {}),
      internalCadence: normalizeInternalCadence(internalCadencePayload || {}),
      attentionTraces: attentionPayload?.live_traces || {},
      conflictResolution: conflictPayload?.trace || null,
      deceptionGuard: guardPayload?.trace || null,
      runtimeSelfModel: selfModelPayload || null,
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

  async getMissionControlPhaseB({ selection } = {}) {
    const [overview, operations, observability, jarvis] = await Promise.all([
      this.getMissionControlOverview({ selection }),
      this.getMissionControlOperations(),
      this.getMissionControlObservability(),
      this.getMissionControlJarvis(),
    ])
    return { overview, operations, observability, jarvis }
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

  async approveToolIntent() {
    return requestJson('/mc/tool-intent/approve', {
      method: 'POST',
    })
  },

  async denyToolIntent() {
    return requestJson('/mc/tool-intent/deny', {
      method: 'POST',
    })
  },

  async completeDevelopmentFocus(focusId) {
    return requestJson(`/mc/development-focus/${focusId}/complete`, {
      method: 'POST',
    })
  },

  async approveRuntimeContractCandidate(candidateId) {
    return requestJson(`/mc/runtime-contract/candidates/${candidateId}/approve`, {
      method: 'POST',
    })
  },

  async rejectRuntimeContractCandidate(candidateId) {
    return requestJson(`/mc/runtime-contract/candidates/${candidateId}/reject`, {
      method: 'POST',
    })
  },

  async applyRuntimeContractCandidate(candidateId) {
    return requestJson(`/mc/runtime-contract/candidates/${candidateId}/apply`, {
      method: 'POST',
    })
  },

  async runHeartbeatTick() {
    return requestJson('/mc/heartbeat/tick', {
      method: 'POST',
    })
  },

  subscribeMissionControlEvents(onEvent) {
    missionControlEventListeners.add(onEvent)
    ensureMissionControlSocket()

    return () => {
      missionControlEventListeners.delete(onEvent)
      if (missionControlEventListeners.size > 0) return
      if (missionControlReconnectTimer) {
        window.clearTimeout(missionControlReconnectTimer)
        missionControlReconnectTimer = null
      }
      missionControlRetryDelay = 1000
      if (missionControlSocket) {
        missionControlSocket.close()
        missionControlSocket = null
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

  async streamMessage({ sessionId, content, onRun, onDelta, onDone, onFailed, onWorkingStep }) {
    const response = await fetch('/chat/stream', {
      method: 'POST',
      headers: JSON_HEADERS,
      body: JSON.stringify({ message: content, session_id: sessionId }),
    })
    if (!response.ok) {
      throw new Error(`/chat/stream: ${response.status} ${response.statusText}`)
    }
    return readSseStream(response, { onRun, onDelta, onDone, onFailed, onWorkingStep })
  },

  async getSystemHealth() {
    try {
      return await requestJson('/mc/system/health')
    } catch {
      return { cpu_pct: 0, ram_pct: 0, disk_free_mb: 0 }
    }
  },

  async getCostSummary() {
    try {
      const data = await requestJson('/mc/cost/summary')
      return data
    } catch {
      return { cost_24h_usd: 0, tokens_24h: 0, unknown_pricing_24h: 0, providers: [] }
    }
  },
}
