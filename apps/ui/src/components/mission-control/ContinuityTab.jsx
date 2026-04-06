import { ChevronRight } from 'lucide-react'
import { formatFreshness, sectionTitleWithMeta } from './meta'

function StatusPill({ status }) {
  if (!status) return null
  const normalizedStatus = String(status).toLowerCase().replace(/[-_\s]+/g, '-')
  return <span className={`mc-status-pill status-${normalizedStatus}`}>{status}</span>
}

function humanizeToken(value) {
  return String(value || '')
    .replace(/[-_]+/g, ' ')
    .trim()
}

function selfSystemCodeAwarenessRow(item, onOpen) {
  if (!item || (!item.codeAwarenessState && !item.repoStatus)) return null

  const detailText = [
    item.concernHint,
    [
      item.repoObservation?.branchName && item.repoObservation.branchName !== 'none' ? `branch ${item.repoObservation.branchName}` : '',
      item.repoStatus ? `repo ${humanizeToken(item.repoStatus)}` : '',
      item.localChangeState ? `changes ${humanizeToken(item.localChangeState)}` : '',
      item.upstreamAwareness ? `upstream ${humanizeToken(item.upstreamAwareness)}` : '',
    ].filter(Boolean).join(' · '),
  ].filter(Boolean)[0] || 'Inspect bounded self system/code awareness'

  return (
    <button
      className="mc-list-row"
      onClick={() => onOpen('Self System / Code Awareness', item)}
      title={sectionTitleWithMeta({
        source: item.source,
        fetchedAt: item.createdAt,
        mode: 'self system / code awareness detail',
      })}
    >
      <div>
        <strong>Self System / Code Awareness</strong>
        <span>{detailText}</span>
      </div>
      <div className="mc-row-meta">
        <StatusPill status={item.concernState || 'notice'} />
        {item.codeAwarenessState ? <small>{humanizeToken(item.codeAwarenessState)}</small> : null}
        {item.repoStatus ? <small>{humanizeToken(item.repoStatus)}</small> : null}
        {item.localChangeState ? <small>{humanizeToken(item.localChangeState)}</small> : null}
        {item.upstreamAwareness ? <small>{humanizeToken(item.upstreamAwareness)}</small> : null}
        {item.actionRequiresApproval ? <small>approval required</small> : null}
        {item.createdAt ? <small>{formatFreshness(item.createdAt)}</small> : null}
        <ChevronRight size={14} />
      </div>
    </button>
  )
}

function worldModelContextRow({ summary, currentSignal, uncertainCount, correctedCount }, onOpen) {
  const detailText = [
    uncertainCount ? `${uncertainCount} uncertain` : '',
    correctedCount ? `${correctedCount} corrected` : '',
    'World-model signals remain bounded situational understanding, not hidden authority.',
  ].filter(Boolean).join(' · ')
  return (
    <button
      className="mc-list-row"
      onClick={() => onOpen('Current World View', {
        source: '/mc/jarvis::continuity',
        summary: currentSignal || 'No active world-model signal',
        currentSignal,
        uncertainCount,
        correctedCount,
        currentStatus: summary?.current_status || 'none',
      })}
      title={sectionTitleWithMeta({
        source: '/mc/jarvis::continuity',
        fetchedAt: '',
        mode: 'world-model context summary',
      })}
    >
      <div>
        <strong>Current World View</strong>
        <span>{currentSignal || 'No active world-model signal'}</span>
      </div>
      <div className="mc-row-meta">
        {summary?.current_status ? <StatusPill status={summary.current_status} /> : null}
        {detailText ? <small>{detailText}</small> : null}
        <ChevronRight size={14} />
      </div>
    </button>
  )
}

function worldModelSignalRow(item, onOpen) {
  const sourceLabel = item.sourceKind ? item.sourceKind.replace(/-/g, ' ') : ''
  return (
    <button
      className="mc-list-row mc-list-row-subtle"
      key={item.signalId || item.title}
      onClick={() => onOpen(item.title || 'World-Model Signal', item)}
      title={sectionTitleWithMeta({
        source: item.source,
        fetchedAt: item.updatedAt || item.createdAt,
        mode: 'world-model signal detail',
      })}
    >
      <div>
        <strong>{item.title || 'World-Model Signal'}</strong>
        <span>{item.statusReason || item.rationale || item.supportSummary || 'Inspect world-model evidence'}</span>
      </div>
      <div className="mc-row-meta">
        <StatusPill status={item.status || 'active'} />
        {item.confidence ? <small>{item.confidence}</small> : null}
        {sourceLabel ? <small>{sourceLabel}</small> : null}
        {item.updatedAt ? <small>{formatFreshness(item.updatedAt)}</small> : null}
        <ChevronRight size={14} />
      </div>
    </button>
  )
}

function runtimeAwarenessSignalRow(item, onOpen) {
  const sourceLabel = item.sourceKind ? item.sourceKind.replace(/-/g, ' ') : ''
  const lifecycleLabel = item.status === 'constrained'
    ? 'Constrained runtime thread'
    : item.status === 'recovered'
      ? 'Recovered runtime thread'
      : item.status === 'superseded'
        ? 'Superseded runtime thread'
        : item.status === 'stale'
          ? 'Stale runtime thread'
          : 'Active runtime thread'
  const detailText = [
    lifecycleLabel,
    item.statusReason,
    item.rationale,
    item.supportSummary,
  ].filter(Boolean)[0] || 'Inspect runtime-awareness evidence'
  return (
    <button
      className="mc-list-row mc-list-row-subtle"
      key={item.signalId || item.title}
      onClick={() => onOpen(item.title || 'Runtime Awareness Signal', item)}
      title={sectionTitleWithMeta({
        source: item.source,
        fetchedAt: item.updatedAt || item.createdAt,
        mode: 'runtime awareness signal detail',
      })}
    >
      <div>
        <strong>{item.title || 'Runtime Awareness Signal'}</strong>
        <span>{detailText}</span>
      </div>
      <div className="mc-row-meta">
        <StatusPill status={item.status || 'active'} />
        {item.confidence ? <small>{item.confidence}</small> : null}
        {sourceLabel ? <small>{sourceLabel}</small> : null}
        {item.updatedAt ? <small>{formatFreshness(item.updatedAt)}</small> : null}
        <ChevronRight size={14} />
      </div>
    </button>
  )
}

function runtimeAwarenessHistoryRow(item, onOpen) {
  const detailText = [
    item.statusReason,
    item.summary,
  ].filter(Boolean)[0] || 'Inspect machine-state history'
  return (
    <button
      className="mc-list-row mc-list-row-subtle"
      key={`${item.signalId || item.title}-${item.updatedAt || item.createdAt || 'runtime-history'}`}
      onClick={() => onOpen(item.title || 'Runtime Awareness History', item)}
      title={sectionTitleWithMeta({
        source: item.source,
        fetchedAt: item.updatedAt || item.createdAt,
        mode: 'runtime awareness history detail',
      })}
    >
      <div>
        <strong>{item.title || 'Runtime Awareness History'}</strong>
        <span>{detailText}</span>
      </div>
      <div className="mc-row-meta">
        <StatusPill status={item.status || 'unknown'} />
        {item.confidence ? <small>{item.confidence}</small> : null}
        {item.updatedAt ? <small>{formatFreshness(item.updatedAt)}</small> : null}
        <ChevronRight size={14} />
      </div>
    </button>
  )
}

function carriedForwardSummary({ relationState, promotionSignal, promotionDecision }) {
  return [
    relationState?.summary,
    promotionSignal?.summary,
    promotionDecision?.summary,
  ].find((value) => value && value !== 'No relation pull' && value !== 'No promotion target' && value !== 'No promotion decision') || 'No bounded carry-over is active right now.'
}

function recentShiftSummary({ visibleSession, visibleContinuity }) {
  const latestStatus = visibleSession?.latest_status || visibleSession?.latestStatus || ''
  if (latestStatus) {
    return `Latest visible turn is ${String(latestStatus).toLowerCase()}.`
  }
  const statuses = visibleContinuity?.statuses || []
  if (Array.isArray(statuses) && statuses.length > 0) {
    return `Recent visible run states: ${statuses.slice(0, 2).join(' · ')}.`
  }
  return 'No recent continuity shift is currently recorded.'
}

function integrationCarryOverRow({ reflectionSummary, reflectionHistory, carriedForward, recentShift }, onOpen) {
  const integratingCount = reflectionSummary?.integrating_count || 0
  const settledCount = reflectionSummary?.settled_count || 0
  const latestHistory = Array.isArray(reflectionHistory) ? reflectionHistory[0] : null

  let status = 'steady'
  let summaryLine = carriedForward || 'No bounded carry-over is active right now.'
  if (integratingCount > 0) {
    status = 'integrating'
    summaryLine = reflectionSummary?.current_signal || latestHistory?.title || summaryLine
  } else if (settledCount > 0 || latestHistory?.status === 'settled') {
    status = 'settling'
    summaryLine = latestHistory?.title || reflectionSummary?.current_signal || recentShift || summaryLine
  }

  const detailText = [
    integratingCount ? `${integratingCount} integrating` : '',
    settledCount ? `${settledCount} settled` : '',
    recentShift || '',
  ].filter(Boolean).join(' · ')

  return (
    <button
      className="mc-list-row"
      onClick={() => onOpen('Integration Carry-Over', {
        source: '/mc/jarvis::continuity',
        summary: summaryLine,
        status,
        integratingCount,
        settledCount,
        carriedForward,
        recentShift,
      })}
      title={sectionTitleWithMeta({
        source: '/mc/jarvis::continuity',
        fetchedAt: '',
        mode: 'reflection continuity summary',
      })}
    >
      <div>
        <strong>Integration Carry-Over</strong>
        <span>{summaryLine}</span>
      </div>
      <div className="mc-row-meta">
        <StatusPill status={status} />
        {detailText ? <small>{detailText}</small> : null}
        <ChevronRight size={14} />
      </div>
    </button>
  )
}

export function ContinuityTab({ data, onOpenItem }) {
  const worldModelSignals = data?.continuity?.worldModelSignals || { items: [], summary: {} }
  const runtimeAwarenessSignals = data?.continuity?.runtimeAwarenessSignals || { items: [], summary: {} }
  const runtimeAwarenessHistory = runtimeAwarenessSignals?.recentHistory || []
  const runtimeWork = data?.continuity?.runtimeWork || { summary: {}, tasks: {}, flows: {}, layeredMemory: {} }
  const heartbeat = data?.heartbeat || {}
  const selfSystemCodeAwareness =
    data?.continuity?.selfSystemCodeAwareness ||
    data?.selfSystemCodeAwareness ||
    heartbeat?.selfSystemCodeAwareness ||
    data?.runtimeSelfModel?.self_system_code_awareness ||
    {}
  const reflectionSignals = data?.development?.reflectionSignals || { items: [], summary: {} }
  const reflectionHistory = reflectionSignals?.recentHistory || []

  const carriedForward = carriedForwardSummary({
    relationState: data?.continuity?.relationState,
    promotionSignal: data?.continuity?.promotionSignal,
    promotionDecision: data?.continuity?.promotionDecision,
  })
  const recentShift = recentShiftSummary({
    visibleSession: data?.continuity?.visibleSession,
    visibleContinuity: data?.continuity?.visibleContinuity,
  })

  return (
    <div className="mc-tab-page">
      {/* Summary row — 2-col with world model context + integration carry-over */}
      <section className="mc-section-grid">
        <article className="support-card">
          <div className="panel-header">
            <div><h3>World View</h3><p className="muted">Current world-model context signal.</p></div>
          </div>
          <div className="mc-list">
            {worldModelContextRow({ summary: worldModelSignals.summary, currentSignal: worldModelSignals.summary?.current_signal, uncertainCount: worldModelSignals.summary?.uncertain_count, correctedCount: worldModelSignals.summary?.corrected_count }, onOpenItem)}
          </div>
        </article>
        <article className="support-card">
          <div className="panel-header">
            <div><h3>Integration Carry-Over</h3><p className="muted">Reflection continuity and carry-forward state.</p></div>
          </div>
          <div className="mc-list">
            {integrationCarryOverRow({ reflectionSummary: reflectionSignals.summary, reflectionHistory, carriedForward, recentShift }, onOpenItem)}
          </div>
        </article>
      </section>

      {(selfSystemCodeAwareness?.codeAwarenessState || selfSystemCodeAwareness?.repoStatus) && (
        <section className="support-card">
          <div className="panel-header">
            <div><h3>Self System / Code Awareness</h3><p className="muted">Read-only awareness of repo state, local changes, and approval boundary.</p></div>
            <span className="mc-section-hint">Read-only</span>
          </div>
          <div className="mc-list">
            {selfSystemCodeAwarenessRow(selfSystemCodeAwareness, onOpenItem)}
          </div>
        </section>
      )}

      {/* World-Model Signals */}
      <section className="support-card">
        <div className="panel-header">
          <div><h3>World-Model Signals</h3><p className="muted">Bounded situational assumptions.</p></div>
        </div>
        <div className="mc-list">
          {(worldModelSignals.items || []).map(item => worldModelSignalRow(item, onOpenItem))}
          {!(worldModelSignals.items || []).length && (
            <div className="mc-empty-state"><strong>No world-model signals</strong></div>
          )}
        </div>
      </section>

      {/* Runtime Awareness */}
      <section className="support-card">
        <div className="panel-header">
          <div><h3>Runtime Awareness</h3><p className="muted">Machine-state awareness signals.</p></div>
        </div>
        <div className="mc-list">
          {(runtimeAwarenessSignals.items || []).map(item => runtimeAwarenessSignalRow(item, onOpenItem))}
          {!(runtimeAwarenessSignals.items || []).length && (
            <div className="mc-empty-state"><strong>No runtime awareness signals</strong></div>
          )}
        </div>
      </section>

      <section className="support-card">
        <div className="panel-header">
          <div><h3>Runtime Work</h3><p className="muted">Durable tasks, flows, browser body, and layered memory state.</p></div>
        </div>
        <div className="mc-list">
          <button
            type="button"
            className="mc-row"
            onClick={() => onOpenItem?.(runtimeWork)}
          >
            <div>
              <strong>Current Runtime Work</strong>
              <span>{runtimeWork?.summary?.currentFocus || runtimeWork?.summary?.current_focus || 'No active runtime work'}</span>
            </div>
            <div className="mc-row-meta">
              <StatusPill status={runtimeWork?.active ? 'active' : 'idle'} />
              <small>
                {runtimeWork?.summary?.taskCount || runtimeWork?.summary?.task_count || 0} tasks · {runtimeWork?.summary?.flowCount || runtimeWork?.summary?.flow_count || 0} flows
              </small>
              <ChevronRight size={14} />
            </div>
          </button>
          <button
            type="button"
            className="mc-row"
            onClick={() => onOpenItem?.(runtimeWork?.browserBody || {})}
          >
            <div>
              <strong>Browser Body</strong>
              <span>{runtimeWork?.browserBody?.summary || runtimeWork?.browserBody?.last_url || 'No browser body state'}</span>
            </div>
            <div className="mc-row-meta">
              <StatusPill status={runtimeWork?.browserBody?.status || 'idle'} />
              <ChevronRight size={14} />
            </div>
          </button>
          <button
            type="button"
            className="mc-row"
            onClick={() => onOpenItem?.(runtimeWork?.layeredMemory || {})}
          >
            <div>
              <strong>Layered Memory</strong>
              <span>Daily memory is {runtimeWork?.layeredMemory?.daily_memory_exists ? 'present' : 'missing'} · Curated memory is {runtimeWork?.layeredMemory?.curated_memory_exists ? 'present' : 'missing'}</span>
            </div>
            <div className="mc-row-meta">
              <StatusPill status={runtimeWork?.layeredMemory?.daily_memory_exists ? 'active' : 'constrained'} />
              <ChevronRight size={14} />
            </div>
          </button>
        </div>
      </section>

      {/* Runtime Awareness History */}
      {runtimeAwarenessHistory.length > 0 && (
        <section className="support-card">
          <div className="panel-header">
            <div><h3>Runtime Awareness History</h3><p className="muted">Recent machine-state transitions.</p></div>
          </div>
          <div className="mc-list dense">
            {runtimeAwarenessHistory.map(item => runtimeAwarenessHistoryRow(item, onOpenItem))}
          </div>
        </section>
      )}
    </div>
  )
}
