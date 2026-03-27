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
    budgetStatus: item.budget_status || '',
    policySummary: item.policy_summary || '',
    lastPingEligible: Boolean(item.last_ping_eligible),
    lastPingResult: item.last_ping_result || '',
    lastActionType: item.last_action_type || '',
    lastActionStatus: item.last_action_status || '',
    lastActionSummary: item.last_action_summary || '',
    lastActionArtifact: item.last_action_artifact || '',
    summary: item.summary || 'No heartbeat activity yet.',
    stateFile: item.state_file || '',
    source: item.source || '/mc/jarvis::heartbeat',
    updatedAt: item.updated_at || '',
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
    summary: item.summary || '',
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
    source: item.source || '/mc/jarvis.development.witness_signals',
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

  async getMissionControlJarvis() {
    const [payload, contractPayload] = await Promise.all([
      requestJson('/mc/jarvis'),
      requestJson('/mc/runtime-contract'),
    ])
    const state = payload?.state || {}
    const memory = payload?.memory || {}
    const development = payload?.development || {}
    const continuity = payload?.continuity || {}
    const heartbeat = payload?.heartbeat || {}
    const contract = contractPayload || {}

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
      },
      heartbeat: {
        state: normalizeHeartbeatState(heartbeat.state || {}),
        policy: normalizeHeartbeatPolicy(heartbeat.policy || {}),
        recentTicks: (heartbeat.recent_ticks || []).map(normalizeHeartbeatTick),
        recentEvents: (heartbeat.recent_events || []).map(normalizeEventItem),
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
