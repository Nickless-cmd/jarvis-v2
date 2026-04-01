import { ChevronRight } from 'lucide-react'
import { formatFreshness, sectionTitleWithMeta } from './meta'

/* ─── Shared helpers ─── */

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

function detailRow(item, label, onOpen) {
  if (!item || !Object.keys(item).length) {
    return (
      <div className="mc-empty-state">
        <strong>No current signal</strong>
        <p className="muted">This Jarvis surface has not produced a current record yet.</p>
      </div>
    )
  }

  return (
    <button
      className="mc-list-row"
      onClick={() => onOpen(label, item)}
      title={sectionTitleWithMeta({
        source: item.source,
        fetchedAt: item.createdAt,
        mode: 'detail drawer',
      })}
    >
      <div>
        <strong>{label}</strong>
        <span>{item.summary || 'Inspect detail'}</span>
      </div>
      <div className="mc-row-meta">
        <small>{item.createdAt || 'current'}</small>
        <ChevronRight size={14} />
      </div>
    </button>
  )
}

function subsectionHeader(kicker, title) {
  return (
    <div className="support-card-header">
      <span className="support-card-kicker">{kicker}</span>
      <strong>{title}</strong>
    </div>
  )
}

/* ─── Row renderers ─── */

function developmentSnapshotRow({ focusSummary, goalSummary, criticSummary, reflectionSummary }, onOpen) {
  const activeFocusCount = focusSummary?.active_count || 0
  const activeGoalCount = goalSummary?.active_count || 0
  const blockedGoalCount = goalSummary?.blocked_count || 0
  const activeCriticCount = criticSummary?.active_count || 0
  const integratingReflectionCount = reflectionSummary?.integrating_count || 0
  const settledReflectionCount = reflectionSummary?.settled_count || 0

  let mode = 'stable'
  let summaryLine = focusSummary?.current_focus || goalSummary?.current_goal || 'No active development focus'
  if (activeCriticCount > 0 || blockedGoalCount > 0) {
    mode = 'pressured'
    summaryLine = criticSummary?.current_critic || goalSummary?.current_goal || summaryLine
  } else if (integratingReflectionCount > 0) {
    mode = 'integrating'
    summaryLine = reflectionSummary?.current_signal || summaryLine
  } else if (settledReflectionCount > 0) {
    mode = 'in-shift'
    summaryLine = reflectionSummary?.current_signal || summaryLine
  }

  const detailText = [
    activeFocusCount ? `${activeFocusCount} focus` : '',
    activeGoalCount || blockedGoalCount ? `${activeGoalCount + blockedGoalCount} goal threads` : '',
    activeCriticCount ? `${activeCriticCount} active critic` : '',
    integratingReflectionCount ? `${integratingReflectionCount} integrating reflection` : '',
  ].filter(Boolean).join(' · ')

  return (
    <button
      className="mc-list-row"
      onClick={() => onOpen('Development Snapshot', {
        source: '/mc/jarvis::development',
        summary: summaryLine,
        mode,
        activeFocusCount,
        activeGoalCount,
        blockedGoalCount,
        activeCriticCount,
        integratingReflectionCount,
        settledReflectionCount,
      })}
      title={sectionTitleWithMeta({
        source: '/mc/jarvis::development',
        fetchedAt: '',
        mode: 'development snapshot summary',
      })}
    >
      <div>
        <strong>Development Snapshot</strong>
        <span>{summaryLine}</span>
      </div>
      <div className="mc-row-meta">
        <StatusPill status={mode} />
        {detailText ? <small>{detailText}</small> : null}
        <ChevronRight size={14} />
      </div>
    </button>
  )
}

function developmentFocusRow(item, onOpen) {
  const sourceLabel = item.sourceKind ? item.sourceKind.replace(/-/g, ' ') : ''
  return (
    <button
      className="mc-list-row mc-list-row-subtle"
      key={item.focusId || item.title}
      onClick={() => onOpen(item.title || 'Development Focus', item)}
      title={sectionTitleWithMeta({
        source: item.source,
        fetchedAt: item.updatedAt || item.createdAt,
        mode: 'development focus detail',
      })}
    >
      <div>
        <strong>{item.title || 'Development Focus'}</strong>
        <span>{item.statusReason || item.rationale || item.supportSummary || 'Inspect development focus evidence'}</span>
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

function goalDirectionRow({ summary, currentGoal, blockedCount, completedCount }, onOpen) {
  const detailText = [
    blockedCount ? `${blockedCount} blocked` : '',
    completedCount ? `${completedCount} completed` : '',
    'Goal signals remain bounded runtime direction, not hidden planning.',
  ].filter(Boolean).join(' · ')
  return (
    <button
      className="mc-list-row"
      onClick={() => onOpen('Current Direction', {
        source: '/mc/jarvis::development',
        summary: currentGoal || 'No active goal signal',
        currentGoal,
        blockedCount,
        completedCount,
        currentStatus: summary?.current_status || 'none',
      })}
      title={sectionTitleWithMeta({
        source: '/mc/jarvis::development',
        fetchedAt: '',
        mode: 'goal direction summary',
      })}
    >
      <div>
        <strong>Current Direction</strong>
        <span>{currentGoal || 'No active goal signal'}</span>
      </div>
      <div className="mc-row-meta">
        {summary?.current_status ? <StatusPill status={summary.current_status} /> : null}
        {detailText ? <small>{detailText}</small> : null}
        <ChevronRight size={14} />
      </div>
    </button>
  )
}

function goalSignalRow(item, onOpen) {
  const sourceLabel = item.sourceKind ? item.sourceKind.replace(/-/g, ' ') : ''
  const supportMeta = []
  if (item.supportCount) supportMeta.push(`${item.supportCount} support`)
  if (item.sessionCount) supportMeta.push(`${item.sessionCount} session${item.sessionCount === 1 ? '' : 's'}`)
  const lifecycleLabel = item.status === 'blocked'
    ? 'Blocked goal thread'
    : item.status === 'completed'
      ? 'Completed goal thread'
      : item.status === 'superseded'
        ? 'Superseded goal thread'
        : item.status === 'stale'
          ? 'Stale goal thread'
          : 'Active goal thread'
  const detailText = [
    lifecycleLabel,
    item.statusReason,
    item.rationale,
    supportMeta.length ? supportMeta.join(' · ') : '',
    item.supportSummary,
  ].filter(Boolean)[0] || 'Inspect goal-signal evidence'
  return (
    <button
      className="mc-list-row mc-list-row-subtle"
      key={item.goalId || item.title}
      onClick={() => onOpen(item.title || 'Goal Signal', item)}
      title={sectionTitleWithMeta({
        source: item.source,
        fetchedAt: item.updatedAt || item.createdAt,
        mode: 'goal signal detail',
      })}
    >
      <div>
        <strong>{item.title || 'Goal Signal'}</strong>
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

function selfModelCalibrationRow({ summary, currentSignal, uncertainCount, correctedCount }, onOpen) {
  const detailText = [
    uncertainCount ? `${uncertainCount} uncertain` : '',
    correctedCount ? `${correctedCount} corrected` : '',
    'Self-model signals remain bounded runtime calibration, not identity authority.',
  ].filter(Boolean).join(' · ')
  return (
    <button
      className="mc-list-row"
      onClick={() => onOpen('Current Calibration', {
        source: '/mc/jarvis::development',
        summary: currentSignal || 'No active self-model signal',
        currentSignal,
        uncertainCount,
        correctedCount,
        currentStatus: summary?.current_status || 'none',
      })}
      title={sectionTitleWithMeta({
        source: '/mc/jarvis::development',
        fetchedAt: '',
        mode: 'self-model calibration summary',
      })}
    >
      <div>
        <strong>Current Calibration</strong>
        <span>{currentSignal || 'No active self-model signal'}</span>
      </div>
      <div className="mc-row-meta">
        {summary?.current_status ? <StatusPill status={summary.current_status} /> : null}
        {detailText ? <small>{detailText}</small> : null}
        <ChevronRight size={14} />
      </div>
    </button>
  )
}

function selfModelSignalRow(item, onOpen) {
  const sourceLabel = item.sourceKind ? item.sourceKind.replace(/-/g, ' ') : ''
  const supportMeta = []
  if (item.supportCount) supportMeta.push(`${item.supportCount} support`)
  if (item.sessionCount) supportMeta.push(`${item.sessionCount} session${item.sessionCount === 1 ? '' : 's'}`)
  const detailText = [
    item.statusReason,
    item.rationale,
    supportMeta.length ? supportMeta.join(' · ') : '',
    item.supportSummary,
  ].filter(Boolean)[0] || 'Inspect self-model evidence'
  return (
    <button
      className="mc-list-row mc-list-row-subtle"
      key={item.signalId || item.title}
      onClick={() => onOpen(item.title || 'Self-Model Signal', item)}
      title={sectionTitleWithMeta({
        source: item.source,
        fetchedAt: item.updatedAt || item.createdAt,
        mode: 'self-model signal detail',
      })}
    >
      <div>
        <strong>{item.title || 'Self-Model Signal'}</strong>
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

function criticPressureRow({ summary, currentCritic, resolvedCount, staleCount }, onOpen) {
  const detailText = [
    resolvedCount ? `${resolvedCount} resolved` : '',
    staleCount ? `${staleCount} stale` : '',
    'Reflective critic signals remain bounded corrective pressure, not hidden control.',
  ].filter(Boolean).join(' · ')
  return (
    <button
      className="mc-list-row"
      onClick={() => onOpen('Current Friction', {
        source: '/mc/jarvis::development',
        summary: currentCritic || 'No active critic signal',
        currentCritic,
        resolvedCount,
        staleCount,
        currentStatus: summary?.current_status || 'none',
      })}
      title={sectionTitleWithMeta({
        source: '/mc/jarvis::development',
        fetchedAt: '',
        mode: 'critic pressure summary',
      })}
    >
      <div>
        <strong>Current Friction</strong>
        <span>{currentCritic || 'No active critic signal'}</span>
      </div>
      <div className="mc-row-meta">
        {summary?.current_status ? <StatusPill status={summary.current_status} /> : null}
        {detailText ? <small>{detailText}</small> : null}
        <ChevronRight size={14} />
      </div>
    </button>
  )
}

function reflectiveCriticRow(item, onOpen) {
  const sourceLabel = item.sourceKind ? item.sourceKind.replace(/-/g, ' ') : ''
  return (
    <button
      className="mc-list-row mc-list-row-subtle"
      key={item.criticId || item.title}
      onClick={() => onOpen(item.title || 'Reflective Critic', item)}
      title={sectionTitleWithMeta({
        source: item.source,
        fetchedAt: item.updatedAt || item.createdAt,
        mode: 'reflective critic detail',
      })}
    >
      <div>
        <strong>{item.title || 'Reflective Critic'}</strong>
        <span>{item.statusReason || item.rationale || item.supportSummary || 'Inspect reflective critic evidence'}</span>
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

function reflectionSignalRow(item, onOpen) {
  const sourceLabel = item.sourceKind ? item.sourceKind.replace(/-/g, ' ') : ''
  const lifecycleLabel = item.status === 'integrating'
    ? 'Integrating reflection thread'
    : item.status === 'settled'
      ? 'Settled reflection thread'
      : item.status === 'superseded'
        ? 'Superseded reflection thread'
        : item.status === 'stale'
          ? 'Stale reflection thread'
          : 'Active reflection thread'
  const supportMeta = []
  if (item.supportCount) supportMeta.push(`${item.supportCount} support`)
  if (item.sessionCount) supportMeta.push(`${item.sessionCount} session${item.sessionCount === 1 ? '' : 's'}`)
  const detailText = [
    lifecycleLabel,
    item.statusReason,
    item.rationale,
    item.evidenceSummary,
    supportMeta.length ? supportMeta.join(' · ') : '',
    item.supportSummary,
  ].filter(Boolean)[0] || 'Inspect bounded reflection evidence'
  return (
    <button
      className="mc-list-row mc-list-row-subtle"
      key={item.signalId || item.title}
      onClick={() => onOpen(item.title || 'Reflection Signal', item)}
      title={sectionTitleWithMeta({
        source: item.source,
        fetchedAt: item.updatedAt || item.createdAt,
        mode: 'reflection signal detail',
      })}
    >
      <div>
        <strong>{item.title || 'Reflection Signal'}</strong>
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

function reflectionHistoryRow(item, onOpen) {
  const detailText = [
    item.transition,
    item.statusReason,
    item.summary,
  ].filter(Boolean)[0] || 'Inspect reflection history detail'
  return (
    <button
      className="mc-list-row mc-list-row-subtle"
      key={`${item.signalId || item.title}-${item.updatedAt || item.createdAt || 'history'}`}
      onClick={() => onOpen(item.title || 'Reflection History', item)}
      title={sectionTitleWithMeta({
        source: item.source,
        fetchedAt: item.updatedAt || item.createdAt,
        mode: 'reflection history detail',
      })}
    >
      <div>
        <strong>{item.title || 'Reflection History'}</strong>
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

function witnessSignalRow(item, onOpen) {
  const sourceLabel = item.sourceKind ? item.sourceKind.replace(/-/g, ' ') : ''
  const lifecycleLabel = item.status === 'carried'
    ? 'Carried witness thread'
    : item.status === 'fading'
      ? 'Fading witness thread'
      : item.status === 'superseded'
        ? 'Superseded witness thread'
        : 'Fresh witness thread'
  const detailText = [
    lifecycleLabel,
    item.statusReason,
    item.rationale,
    item.supportSummary,
  ].filter(Boolean)[0] || 'Inspect witnessed development turn'
  return (
    <button
      className="mc-list-row mc-list-row-subtle"
      key={item.signalId || item.title}
      onClick={() => onOpen(item.title || 'Witness Signal', item)}
      title={sectionTitleWithMeta({
        source: item.source,
        fetchedAt: item.updatedAt || item.createdAt,
        mode: 'witness signal detail',
      })}
    >
      <div>
        <strong>{item.title || 'Witness Signal'}</strong>
        <span>{detailText}</span>
      </div>
      <div className="mc-row-meta">
        <StatusPill status={item.status || 'fresh'} />
        {item.confidence ? <small>{item.confidence}</small> : null}
        {sourceLabel ? <small>{sourceLabel}</small> : null}
        {item.updatedAt ? <small>{formatFreshness(item.updatedAt)}</small> : null}
        <ChevronRight size={14} />
      </div>
    </button>
  )
}

function temporalRecurrenceSignalRow(item, onOpen) {
  const sourceLabel = item.sourceKind ? item.sourceKind.replace(/-/g, ' ') : ''
  const detailText = [
    item.statusReason,
    item.rationale,
    item.supportSummary,
  ].filter(Boolean)[0] || 'Inspect recurring thread evidence'
  return (
    <button
      className="mc-list-row mc-list-row-subtle"
      key={item.signalId || item.title}
      onClick={() => onOpen(item.title || 'Temporal Recurrence Signal', item)}
      title={sectionTitleWithMeta({
        source: item.source,
        fetchedAt: item.updatedAt || item.createdAt,
        mode: 'temporal recurrence detail',
      })}
    >
      <div>
        <strong>{item.title || 'Temporal Recurrence Signal'}</strong>
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

function openLoopSignalRow(item, onOpen) {
  const sourceLabel = item.sourceKind ? item.sourceKind.replace(/-/g, ' ') : ''
  const lifecycleLabel = item.status === 'softening'
    ? 'Softening loop'
    : item.status === 'closed'
      ? 'Closed loop'
      : item.status === 'stale'
        ? 'Stale loop'
        : item.status === 'superseded'
          ? 'Superseded loop'
          : 'Open loop'
  const detailText = [
    lifecycleLabel,
    item.closureReason,
    item.statusReason,
    item.rationale,
    item.supportSummary,
  ].filter(Boolean)[0] || 'Inspect bounded open-loop evidence'
  return (
    <button
      className="mc-list-row mc-list-row-subtle"
      key={item.signalId || item.title}
      onClick={() => onOpen(item.title || 'Open Loop', item)}
      title={sectionTitleWithMeta({
        source: item.source,
        fetchedAt: item.updatedAt || item.createdAt,
        mode: 'open loop detail',
      })}
    >
      <div>
        <strong>{item.title || 'Open Loop'}</strong>
        <span>{detailText}</span>
      </div>
      <div className="mc-row-meta">
        <StatusPill status={item.status || 'open'} />
        {item.closureReadiness ? <small>{`closure ${item.closureReadiness}`}</small> : null}
        {item.confidence ? <small>{item.confidence}</small> : null}
        {sourceLabel ? <small>{sourceLabel}</small> : null}
        {item.updatedAt ? <small>{formatFreshness(item.updatedAt)}</small> : null}
        <ChevronRight size={14} />
      </div>
    </button>
  )
}

function openLoopClosureProposalRow(item, onOpen) {
  const sourceLabel = item.sourceKind ? item.sourceKind.replace(/-/g, ' ') : ''
  const lifecycleLabel = item.status === 'active'
    ? 'Active closure proposal'
    : item.status === 'fading'
      ? 'Fading closure proposal'
      : item.status === 'stale'
        ? 'Stale closure proposal'
        : item.status === 'superseded'
          ? 'Superseded closure proposal'
          : 'Fresh closure proposal'
  const detailText = [
    item.proposalReason,
    item.reviewAnchor,
    lifecycleLabel,
  ].filter(Boolean)[0] || 'Inspect bounded loop-closure proposal'
  return (
    <button
      className="mc-list-row mc-list-row-subtle"
      key={item.proposalId || item.title}
      onClick={() => onOpen(item.title || 'Loop Closure Proposal', item)}
      title={sectionTitleWithMeta({
        source: item.source,
        fetchedAt: item.updatedAt || item.createdAt,
        mode: 'loop closure proposal',
      })}
    >
      <div>
        <strong>{item.title || 'Loop Closure Proposal'}</strong>
        <span>{detailText}</span>
      </div>
      <div className="mc-row-meta">
        <StatusPill status={item.status || 'fresh'} />
        {item.closureConfidence ? <small>{`closure ${item.closureConfidence}`}</small> : null}
        {sourceLabel ? <small>{sourceLabel}</small> : null}
        {item.updatedAt ? <small>{formatFreshness(item.updatedAt)}</small> : null}
        <ChevronRight size={14} />
      </div>
    </button>
  )
}

function internalOppositionSignalRow(item, onOpen) {
  const sourceLabel = item.sourceKind ? item.sourceKind.replace(/-/g, ' ') : ''
  const lifecycleLabel = item.status === 'softening'
    ? 'Softening challenge need'
    : item.status === 'stale'
      ? 'Stale challenge need'
      : item.status === 'superseded'
        ? 'Superseded challenge need'
        : 'Active challenge need'
  const detailText = [
    lifecycleLabel,
    item.statusReason,
    item.rationale,
    item.supportSummary,
  ].filter(Boolean)[0] || 'Inspect bounded internal opposition need'
  return (
    <button
      className="mc-list-row mc-list-row-subtle"
      key={item.signalId || item.title}
      onClick={() => onOpen(item.title || 'Internal Opposition Signal', item)}
      title={sectionTitleWithMeta({
        source: item.source,
        fetchedAt: item.updatedAt || item.createdAt,
        mode: 'internal opposition detail',
      })}
    >
      <div>
        <strong>{item.title || 'Internal Opposition Signal'}</strong>
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

function emergentSignalRow(item, onOpen) {
  const lifecycleLabel = item.lifecycleState === 'strengthening'
    ? 'Strengthening grounded candidate'
    : item.lifecycleState === 'fading'
      ? 'Fading bounded thread'
      : item.lifecycleState === 'released'
        ? 'Released bounded thread'
        : item.lifecycleState === 'candidate'
          ? 'Candidate inner signal'
          : (item.lifecycleState || 'Inner signal').replace(/-/g, ' ')
  const sourceHintLabel = (item.sourceHints || []).slice(0, 2).join(' + ')
  const detailText = [
    lifecycleLabel,
    sourceHintLabel ? `from ${sourceHintLabel}` : '',
    item.influencedLayer ? `layer ${item.influencedLayer.replace(/-/g, ' ')}` : '',
    `${item.truth || 'candidate-only'} · ${item.visibility || 'internal-only'}`,
  ].filter(Boolean).join(' · ')
  const salienceLabel = item.salience > 0 ? `${Math.round(item.salience * 100)}%` : ''
  return (
    <button
      className="mc-list-row mc-list-row-subtle"
      key={item.signalId || item.canonicalKey || item.title}
      onClick={() => onOpen(item.title || 'Emergent Inner Signal', item)}
      title={sectionTitleWithMeta({
        source: item.source,
        fetchedAt: item.updatedAt || item.createdAt,
        mode: 'emergent inner signal detail',
      })}
    >
      <div>
        <strong>{item.title || 'Emergent Inner Signal'}</strong>
        <span>{detailText || 'Inspect bounded emergent inner-signal detail'}</span>
      </div>
      <div className="mc-row-meta">
        <StatusPill status={item.status || 'candidate'} />
        {item.lifecycleState ? <small>{item.lifecycleState.replace(/-/g, ' ')}</small> : null}
        {item.intensity ? <small>{item.intensity}</small> : null}
        {salienceLabel ? <small>{salienceLabel}</small> : null}
        {item.updatedAt ? <small>{formatFreshness(item.updatedAt)}</small> : null}
        <ChevronRight size={14} />
      </div>
    </button>
  )
}

function dreamHypothesisSignalRow(item, onOpen) {
  const sourceLabel = item.sourceKind ? item.sourceKind.replace(/-/g, ' ') : ''
  const lifecycleLabel = item.status === 'integrating'
    ? 'Integrating dream hypothesis'
    : item.status === 'fading'
      ? 'Fading dream hypothesis'
      : item.status === 'stale'
        ? 'Stale dream hypothesis'
        : item.status === 'superseded'
          ? 'Superseded dream hypothesis'
          : 'Active dream hypothesis'
  const detailText = [
    item.hypothesisNote,
    item.hypothesisAnchor,
    lifecycleLabel,
  ].filter(Boolean)[0] || 'Inspect bounded dream hypothesis'
  return (
    <button
      className="mc-list-row mc-list-row-subtle"
      key={item.signalId || item.title}
      onClick={() => onOpen(item.title || 'Dream Hypothesis', item)}
      title={sectionTitleWithMeta({
        source: item.source,
        fetchedAt: item.updatedAt || item.createdAt,
        mode: 'dream hypothesis',
      })}
    >
      <div>
        <strong>{item.title || 'Dream Hypothesis'}</strong>
        <span>{detailText}</span>
      </div>
      <div className="mc-row-meta">
        <StatusPill status={item.status || 'active'} />
        {item.hypothesisType ? <small>{item.hypothesisType}</small> : null}
        {sourceLabel ? <small>{sourceLabel}</small> : null}
        {item.updatedAt ? <small>{formatFreshness(item.updatedAt)}</small> : null}
        <ChevronRight size={14} />
      </div>
    </button>
  )
}

function dreamAdoptionCandidateRow(item, onOpen) {
  const sourceLabel = item.sourceKind ? item.sourceKind.replace(/-/g, ' ') : ''
  const lifecycleLabel = item.status === 'active'
    ? 'Active adoption candidate'
    : item.status === 'fading'
      ? 'Fading adoption candidate'
      : item.status === 'stale'
        ? 'Stale adoption candidate'
        : item.status === 'superseded'
          ? 'Superseded adoption candidate'
          : 'Fresh adoption candidate'
  const detailText = [
    item.adoptionReason,
    item.adoptionAnchor,
    lifecycleLabel,
  ].filter(Boolean)[0] || 'Inspect bounded dream adoption candidate'
  return (
    <button
      className="mc-list-row mc-list-row-subtle"
      key={item.candidateId || item.title}
      onClick={() => onOpen(item.title || 'Dream Adoption Candidate', item)}
      title={sectionTitleWithMeta({
        source: item.source,
        fetchedAt: item.updatedAt || item.createdAt,
        mode: 'dream adoption candidate',
      })}
    >
      <div>
        <strong>{item.title || 'Dream Adoption Candidate'}</strong>
        <span>{detailText}</span>
      </div>
      <div className="mc-row-meta">
        <StatusPill status={item.status || 'fresh'} />
        {item.adoptionConfidence ? <small>{`adoption ${item.adoptionConfidence}`}</small> : null}
        {sourceLabel ? <small>{sourceLabel}</small> : null}
        {item.updatedAt ? <small>{formatFreshness(item.updatedAt)}</small> : null}
        <ChevronRight size={14} />
      </div>
    </button>
  )
}

function dreamInfluenceProposalRow(item, onOpen) {
  const sourceLabel = item.sourceKind ? item.sourceKind.replace(/-/g, ' ') : ''
  const lifecycleLabel = item.status === 'active'
    ? 'Active influence proposal'
    : item.status === 'fading'
      ? 'Fading influence proposal'
      : item.status === 'stale'
        ? 'Stale influence proposal'
        : item.status === 'superseded'
          ? 'Superseded influence proposal'
          : 'Fresh influence proposal'
  const detailText = [
    item.proposalReason,
    item.influenceAnchor,
    lifecycleLabel,
  ].filter(Boolean)[0] || 'Inspect bounded dream influence proposal'
  return (
    <button
      className="mc-list-row mc-list-row-subtle"
      key={item.proposalId || item.title}
      onClick={() => onOpen(item.title || 'Dream Influence Proposal', item)}
      title={sectionTitleWithMeta({
        source: item.source,
        fetchedAt: item.updatedAt || item.createdAt,
        mode: 'dream influence proposal',
      })}
    >
      <div>
        <strong>{item.title || 'Dream Influence Proposal'}</strong>
        <span>{detailText}</span>
      </div>
      <div className="mc-row-meta">
        <StatusPill status={item.status || 'fresh'} />
        {item.influenceConfidence ? <small>{`influence ${item.influenceConfidence}`}</small> : null}
        {sourceLabel ? <small>{sourceLabel}</small> : null}
        {item.updatedAt ? <small>{formatFreshness(item.updatedAt)}</small> : null}
        <ChevronRight size={14} />
      </div>
    </button>
  )
}

function selfAuthoredPromptProposalRow(item, onOpen) {
  const sourceLabel = item.sourceKind ? item.sourceKind.replace(/-/g, ' ') : ''
  const lifecycleLabel = item.status === 'active'
    ? 'Active prompt proposal'
    : item.status === 'fading'
      ? 'Fading prompt proposal'
      : item.status === 'stale'
        ? 'Stale prompt proposal'
        : item.status === 'superseded'
          ? 'Superseded prompt proposal'
          : 'Fresh prompt proposal'
  const detailText = [
    item.proposalReason,
    item.proposedNudge,
    lifecycleLabel,
  ].filter(Boolean)[0] || 'Inspect bounded self-authored prompt proposal'
  return (
    <button
      className="mc-list-row mc-list-row-subtle"
      key={item.proposalId || item.title}
      onClick={() => onOpen(item.title || 'Self-Authored Prompt Proposal', item)}
      title={sectionTitleWithMeta({
        source: item.source,
        fetchedAt: item.updatedAt || item.createdAt,
        mode: 'self-authored prompt proposal',
      })}
    >
      <div>
        <strong>{item.title || 'Self-Authored Prompt Proposal'}</strong>
        <span>{detailText}</span>
      </div>
      <div className="mc-row-meta">
        <StatusPill status={item.status || 'fresh'} />
        {item.proposalConfidence ? <small>{`proposal ${item.proposalConfidence}`}</small> : null}
        {sourceLabel ? <small>{sourceLabel}</small> : null}
        {item.updatedAt ? <small>{formatFreshness(item.updatedAt)}</small> : null}
        <ChevronRight size={14} />
      </div>
    </button>
  )
}

function userMdUpdateProposalRow(item, onOpen) {
  const sourceLabel = item.sourceKind ? item.sourceKind.replace(/-/g, ' ') : ''
  const lifecycleLabel = item.status === 'active'
    ? 'Active USER.md proposal'
    : item.status === 'fading'
      ? 'Fading USER.md proposal'
      : item.status === 'stale'
        ? 'Stale USER.md proposal'
        : item.status === 'superseded'
          ? 'Superseded USER.md proposal'
          : 'Fresh USER.md proposal'
  const detailText = [
    item.proposalReason,
    item.sourceAnchor,
    lifecycleLabel,
  ].filter(Boolean)[0] || 'Inspect bounded USER.md update proposal'
  return (
    <button
      className="mc-list-row mc-list-row-subtle"
      key={item.proposalId || item.title}
      onClick={() => onOpen(item.title || 'USER.md Update Proposal', item)}
      title={sectionTitleWithMeta({
        source: item.source,
        fetchedAt: item.updatedAt || item.createdAt,
        mode: 'user md update proposal',
      })}
    >
      <div>
        <strong>{item.title || 'USER.md Update Proposal'}</strong>
        <span>{detailText}</span>
      </div>
      <div className="mc-row-meta">
        <StatusPill status={item.status || 'fresh'} />
        {item.proposalConfidence ? <small>{`proposal ${item.proposalConfidence}`}</small> : null}
        {sourceLabel ? <small>{sourceLabel}</small> : null}
        {item.updatedAt ? <small>{formatFreshness(item.updatedAt)}</small> : null}
        <ChevronRight size={14} />
      </div>
    </button>
  )
}

function userUnderstandingSignalRow(item, onOpen) {
  const sourceLabel = item.sourceKind ? item.sourceKind.replace(/-/g, ' ') : ''
  const lifecycleLabel = item.status === 'active'
    ? 'Active user-understanding signal'
    : item.status === 'softening'
      ? 'Softening user-understanding signal'
      : item.status === 'stale'
        ? 'Stale user-understanding signal'
        : item.status === 'superseded'
          ? 'Superseded user-understanding signal'
          : 'User-understanding signal'
  const detailText = [
    item.signalSummary,
    item.sourceAnchor,
    lifecycleLabel,
  ].filter(Boolean)[0] || 'Inspect bounded user-understanding signal'
  return (
    <button
      className="mc-list-row mc-list-row-subtle"
      key={item.signalId || item.title}
      onClick={() => onOpen(item.title || 'User Understanding Signal', item)}
      title={sectionTitleWithMeta({
        source: item.source,
        fetchedAt: item.updatedAt || item.createdAt,
        mode: 'user understanding signal',
      })}
    >
      <div>
        <strong>{item.title || 'User Understanding Signal'}</strong>
        <span>{detailText}</span>
      </div>
      <div className="mc-row-meta">
        <StatusPill status={item.status || 'active'} />
        {item.signalConfidence ? <small>{`signal ${item.signalConfidence}`}</small> : null}
        {item.userDimension ? <small>{item.userDimension}</small> : null}
        {sourceLabel ? <small>{sourceLabel}</small> : null}
        {item.updatedAt ? <small>{formatFreshness(item.updatedAt)}</small> : null}
        <ChevronRight size={14} />
      </div>
    </button>
  )
}

function selfhoodProposalRow(item, onOpen) {
  const sourceLabel = item.sourceKind ? item.sourceKind.replace(/-/g, ' ') : ''
  const lifecycleLabel = item.status === 'active'
    ? 'Active selfhood proposal'
    : item.status === 'fading'
      ? 'Fading selfhood proposal'
      : item.status === 'stale'
        ? 'Stale selfhood proposal'
        : item.status === 'superseded'
          ? 'Superseded selfhood proposal'
          : 'Fresh selfhood proposal'
  const detailText = [
    item.proposalReason,
    item.sourceAnchor,
    lifecycleLabel,
  ].filter(Boolean)[0] || 'Inspect bounded selfhood proposal'
  return (
    <button
      className="mc-list-row mc-list-row-subtle"
      key={item.proposalId || item.title}
      onClick={() => onOpen(item.title || 'Selfhood Proposal', item)}
      title={sectionTitleWithMeta({
        source: item.source,
        fetchedAt: item.updatedAt || item.createdAt,
        mode: 'selfhood proposal',
      })}
    >
      <div>
        <strong>{item.title || 'Selfhood Proposal'}</strong>
        <span>{detailText}</span>
      </div>
      <div className="mc-row-meta">
        <StatusPill status={item.status || 'fresh'} />
        {item.proposalConfidence ? <small>{`proposal ${item.proposalConfidence}`}</small> : null}
        {item.selfhoodTarget ? <small>{item.selfhoodTarget}</small> : null}
        {sourceLabel ? <small>{sourceLabel}</small> : null}
        {item.updatedAt ? <small>{formatFreshness(item.updatedAt)}</small> : null}
        <ChevronRight size={14} />
      </div>
    </button>
  )
}

/* ─── Main tab component ─── */

export function DevelopmentTab({ data, onOpenItem }) {
  const summary = data?.summary || {}
  const developmentFocuses = data?.development?.developmentFocuses || { items: [], summary: {} }
  const reflectiveCritics = data?.development?.reflectiveCritics || { items: [], summary: {} }
  const selfModelSignals = data?.development?.selfModelSignals || { items: [], summary: {} }
  const goalSignals = data?.development?.goalSignals || { items: [], summary: {} }
  const reflectionSignals = data?.development?.reflectionSignals || { items: [], summary: {} }
  const temporalRecurrenceSignals = data?.development?.temporalRecurrenceSignals || { items: [], summary: {} }
  const witnessSignals = data?.development?.witnessSignals || { items: [], summary: {} }
  const openLoopSignals = data?.development?.openLoopSignals || { items: [], summary: {} }
  const openLoopClosureProposals = data?.development?.openLoopClosureProposals || { items: [], summary: {} }
  const internalOppositionSignals = data?.development?.internalOppositionSignals || { items: [], summary: {} }
  const emergentSignals = data?.development?.emergentSignals || { items: [], recentReleased: [], summary: {} }
  const dreamHypothesisSignals = data?.development?.dreamHypothesisSignals || { items: [], summary: {} }
  const dreamAdoptionCandidates = data?.development?.dreamAdoptionCandidates || { items: [], summary: {} }
  const dreamInfluenceProposals = data?.development?.dreamInfluenceProposals || { items: [], summary: {} }
  const selfAuthoredPromptProposals = data?.development?.selfAuthoredPromptProposals || { items: [], summary: {} }
  const userMdUpdateProposals = data?.development?.userMdUpdateProposals || { items: [], summary: {} }
  const userUnderstandingSignals = data?.development?.userUnderstandingSignals || { items: [], summary: {} }
  const selfhoodProposals = data?.development?.selfhoodProposals || { items: [], summary: {} }
  const privateInnerNoteSignals = data?.development?.privateInnerNoteSignals || { items: [], summary: {} }
  const privateInitiativeTensionSignals = data?.development?.privateInitiativeTensionSignals || { items: [], summary: {} }
  const privateInnerInterplaySignals = data?.development?.privateInnerInterplaySignals || { items: [], summary: {} }
  const privateStateSnapshots = data?.development?.privateStateSnapshots || { items: [], summary: {} }
  const diarySynthesisSignals = data?.development?.diarySynthesisSignals || { items: [], summary: {} }
  const privateTemporalCuriosityStates = data?.development?.privateTemporalCuriosityStates || { items: [], summary: {} }
  const innerVisibleSupportSignals = data?.development?.innerVisibleSupportSignals || { items: [], summary: {} }
  const regulationHomeostasisSignals = data?.development?.regulationHomeostasisSignals || { items: [], summary: {} }
  const relationStateSignals = data?.development?.relationStateSignals || { items: [], summary: {} }
  const relationContinuitySignals = data?.development?.relationContinuitySignals || { items: [], summary: {} }
  const meaningSignificanceSignals = data?.development?.meaningSignificanceSignals || { items: [], summary: {} }
  const selfNarrativeContinuitySignals = data?.development?.selfNarrativeContinuitySignals || { items: [], summary: {} }
  const selfNarrativeSelfModelReviewBridge = data?.development?.selfNarrativeSelfModelReviewBridge || { items: [], summary: {} }
  const chronicleConsolidationSignals = data?.development?.chronicleConsolidationSignals || { items: [], summary: {} }
  const chronicleConsolidationBriefs = data?.development?.chronicleConsolidationBriefs || { items: [], summary: {} }
  const chronicleConsolidationProposals = data?.development?.chronicleConsolidationProposals || { items: [], summary: {} }
  const reflectionHistory = reflectionSignals?.recentHistory || []

  return (
    <div className="mc-tab-page">
      {/* ─── Summary stats ─── */}
      <section className="mc-summary-grid">
        <article className="mc-stat tone-amber" title={sectionTitleWithMeta({
          source: '/mc/jarvis::development',
          fetchedAt: data?.fetchedAt,
          mode: 'snapshot summary',
        })}>
          <span>Direction</span>
          <strong>{summary?.development?.direction || 'unknown'}</strong>
          <small className="muted">{summary?.development?.identity_focus || 'No identity focus'}</small>
        </article>
        <article className="mc-stat tone-blue" title={sectionTitleWithMeta({
          source: '/mc/jarvis::development',
          fetchedAt: data?.fetchedAt,
          mode: 'snapshot summary',
        })}>
          <span>Work Mode</span>
          <strong>{summary?.development?.work_mode || 'unknown'}</strong>
          <small className="muted">{summary?.development?.tension || 'No tension'}</small>
        </article>
        <article className="mc-stat tone-green" title={sectionTitleWithMeta({
          source: '/mc/jarvis::development',
          fetchedAt: data?.fetchedAt,
          mode: 'snapshot summary',
        })}>
          <span>Focus Threads</span>
          <strong>{developmentFocuses?.summary?.active_count || 0}</strong>
          <small className="muted">{developmentFocuses?.summary?.current_focus || 'No active development focus'}</small>
        </article>
        <article className="mc-stat tone-accent" title={sectionTitleWithMeta({
          source: '/mc/jarvis::development',
          fetchedAt: data?.fetchedAt,
          mode: 'snapshot summary',
        })}>
          <span>Goal Threads</span>
          <strong>{(goalSignals?.summary?.active_count || 0) + (goalSignals?.summary?.blocked_count || 0)}</strong>
          <small className="muted">{goalSignals?.summary?.current_goal || 'No active goal signal'}</small>
        </article>
      </section>

      {/* ─── Main grid ─── */}
      <section className="mc-section-grid">
        {/* ─── Snapshot card ─── */}
        <article className="support-card" title={sectionTitleWithMeta({
          source: '/mc/jarvis::development',
          fetchedAt: data?.fetchedAt,
          mode: 'snapshot + metrics',
        })}>
          <div className="panel-header">
            <div>
              <h3>Snapshot</h3>
              <p className="muted">Development direction, private layers, and aggregate signal counts.</p>
            </div>
            <span className="mc-section-hint">Read-only</span>
          </div>
          <div className="compact-grid">
            <div className="compact-metric">
              <span>Inner Note Support</span>
              <strong>{(privateInnerNoteSignals?.summary?.active_count || 0) + (privateInnerNoteSignals?.summary?.stale_count || 0)}</strong>
              <p>{privateInnerNoteSignals?.summary?.current_signal || 'No bounded private inner note support'}</p>
              <p>
                {privateInnerNoteSignals?.summary?.authority || 'non-authoritative'} · {privateInnerNoteSignals?.summary?.layer_role || 'runtime-support'}
              </p>
            </div>
            <div className="compact-metric">
              <span>Initiative Tension</span>
              <strong>{(privateInitiativeTensionSignals?.summary?.active_count || 0) + (privateInitiativeTensionSignals?.summary?.stale_count || 0)}</strong>
              <p>{privateInitiativeTensionSignals?.summary?.current_signal || 'No bounded initiative tension support'}</p>
              <p>
                type {privateInitiativeTensionSignals?.summary?.current_tension_type || 'none'} · intensity {privateInitiativeTensionSignals?.summary?.current_intensity || 'low'}
              </p>
            </div>
            <div className="compact-metric" title="Internal-only candidate layer with bounded lifecycle; never identity or action authority">
              <span>Emergent Signals</span>
              <strong>{emergentSignals?.summary?.active_count || 0}</strong>
              <p>{emergentSignals?.summary?.current_signal || 'No active emergent inner signal'}</p>
              <p>
                {emergentSignals?.summary?.candidate_count || 0} candidate · {emergentSignals?.summary?.emergent_count || 0} emergent · {emergentSignals?.summary?.fading_count || 0} fading
              </p>
            </div>
            {((privateInnerInterplaySignals?.summary?.active_count || 0) + (privateInnerInterplaySignals?.summary?.stale_count || 0)) > 0 ? (
            <div className="compact-metric">
              <span>Inner Interplay</span>
              <strong>{(privateInnerInterplaySignals?.summary?.active_count || 0) + (privateInnerInterplaySignals?.summary?.stale_count || 0)}</strong>
              <p>{privateInnerInterplaySignals?.summary?.current_signal || 'No bounded inner interplay support'}</p>
            </div>
            ) : null}
            <div className="compact-metric">
              <span>Private State</span>
              <strong>{(privateStateSnapshots?.summary?.active_count || 0) + (privateStateSnapshots?.summary?.stale_count || 0)}</strong>
              <p>{privateStateSnapshots?.summary?.current_snapshot || 'No bounded private-state snapshot'}</p>
              <p>
                tone {privateStateSnapshots?.summary?.current_tone || 'none'} · pressure {privateStateSnapshots?.summary?.current_pressure || 'low'}
              </p>
            </div>
            {((privateTemporalCuriosityStates?.summary?.active_count || 0) + (privateTemporalCuriosityStates?.summary?.stale_count || 0)) > 0 ? (
            <div className="compact-metric">
              <span>Temporal Curiosity</span>
              <strong>{(privateTemporalCuriosityStates?.summary?.active_count || 0) + (privateTemporalCuriosityStates?.summary?.stale_count || 0)}</strong>
              <p>{privateTemporalCuriosityStates?.summary?.current_state || 'No bounded temporal curiosity support'}</p>
            </div>
            ) : null}
            {((innerVisibleSupportSignals?.summary?.active_count || 0) + (regulationHomeostasisSignals?.summary?.active_count || 0)) > 0 ? (
            <div className="compact-metric">
              <span>Internal Support</span>
              <strong>{(innerVisibleSupportSignals?.summary?.active_count || 0) + (regulationHomeostasisSignals?.summary?.active_count || 0)}</strong>
              <p>
                {innerVisibleSupportSignals?.summary?.active_count || 0} inner-visible · {regulationHomeostasisSignals?.summary?.active_count || 0} regulation
              </p>
            </div>
            ) : null}
            {((relationStateSignals?.summary?.active_count || 0) + (relationContinuitySignals?.summary?.active_count || 0)) > 0 ? (
            <div className="compact-metric">
              <span>Relation</span>
              <strong>{(relationStateSignals?.summary?.active_count || 0) + (relationContinuitySignals?.summary?.active_count || 0)}</strong>
              <p>
                {relationStateSignals?.summary?.active_count || 0} state · {relationContinuitySignals?.summary?.active_count || 0} continuity
              </p>
            </div>
            ) : null}
            {((chronicleConsolidationSignals?.summary?.active_count || 0) + (chronicleConsolidationBriefs?.summary?.active_count || 0) + (chronicleConsolidationProposals?.summary?.active_count || 0)) > 0 ? (
            <div className="compact-metric">
              <span>Chronicle</span>
              <strong>{(chronicleConsolidationSignals?.summary?.active_count || 0) + (chronicleConsolidationBriefs?.summary?.active_count || 0) + (chronicleConsolidationProposals?.summary?.active_count || 0)}</strong>
              <p>
                {chronicleConsolidationSignals?.summary?.active_count || 0} signals · {chronicleConsolidationBriefs?.summary?.active_count || 0} briefs · {chronicleConsolidationProposals?.summary?.active_count || 0} proposals
              </p>
            </div>
            ) : null}
            {((meaningSignificanceSignals?.summary?.active_count || 0) + (meaningSignificanceSignals?.summary?.softening_count || 0)) > 0 ? (
            <div className="compact-metric">
              <span>Meaning</span>
              <strong>{(meaningSignificanceSignals?.summary?.active_count || 0) + (meaningSignificanceSignals?.summary?.softening_count || 0)}</strong>
              <p>{meaningSignificanceSignals?.summary?.current_signal || 'No bounded meaning/significance support'}</p>
            </div>
            ) : null}
            {((selfNarrativeContinuitySignals?.summary?.active_count || 0) + (selfNarrativeContinuitySignals?.summary?.softening_count || 0)) > 0 ? (
            <div className="compact-metric">
              <span>Self-Narrative</span>
              <strong>{(selfNarrativeContinuitySignals?.summary?.active_count || 0) + (selfNarrativeContinuitySignals?.summary?.softening_count || 0)}</strong>
              <p>{selfNarrativeContinuitySignals?.summary?.current_signal || 'No bounded self-narrative continuity support'}</p>
            </div>
            ) : null}
            <div className="compact-metric">
              <span>Reflective Critic</span>
              <strong>{reflectiveCritics?.summary?.active_count || summary?.development?.critic_count || 0}</strong>
              <p>{reflectiveCritics?.summary?.current_critic || summary?.development?.current_critic || 'No active critic signal'}</p>
              <p>
                {reflectiveCritics?.summary?.stale_count || 0} stale · {reflectiveCritics?.summary?.resolved_count || 0} resolved
              </p>
            </div>
            <div className="compact-metric">
              <span>Self-Model Signals</span>
              <strong>{selfModelSignals?.summary?.active_count || summary?.development?.self_model_signal_count || 0}</strong>
              <p>{selfModelSignals?.summary?.current_signal || summary?.development?.current_self_model_signal || 'No active self-model signal'}</p>
              <p>
                {selfModelSignals?.summary?.uncertain_count || 0} uncertain · {selfModelSignals?.summary?.corrected_count || 0} corrected
              </p>
            </div>
            {((selfNarrativeSelfModelReviewBridge?.summary?.active_count || 0) + (selfNarrativeSelfModelReviewBridge?.summary?.softening_count || 0)) > 0 ? (
            <div className="compact-metric">
              <span>Self-Review Bridge</span>
              <strong>{(selfNarrativeSelfModelReviewBridge?.summary?.active_count || 0) + (selfNarrativeSelfModelReviewBridge?.summary?.softening_count || 0)}</strong>
              <p>{selfNarrativeSelfModelReviewBridge?.summary?.current_bridge || 'No bounded self-narrative review bridge'}</p>
            </div>
            ) : null}
            <div className="compact-metric">
              <span>Reflection Signals</span>
              <strong>{(reflectionSignals?.summary?.active_count || 0) + (reflectionSignals?.summary?.integrating_count || 0) + (reflectionSignals?.summary?.settled_count || 0)}</strong>
              <p>{reflectionSignals?.summary?.current_signal || 'No active reflection signal'}</p>
              <p>
                {reflectionSignals?.summary?.integrating_count || 0} integrating · {reflectionSignals?.summary?.settled_count || 0} settled
              </p>
            </div>
            {((temporalRecurrenceSignals?.summary?.active_count || 0) + (temporalRecurrenceSignals?.summary?.softening_count || 0)) > 0 ? (
            <div className="compact-metric">
              <span>Recurring Patterns</span>
              <strong>{(temporalRecurrenceSignals?.summary?.active_count || 0) + (temporalRecurrenceSignals?.summary?.softening_count || 0)}</strong>
              <p>{temporalRecurrenceSignals?.summary?.current_signal || 'No active temporal recurrence signal'}</p>
            </div>
            ) : null}
            <div className="compact-metric">
              <span>Open Loops</span>
              <strong>{(openLoopSignals?.summary?.open_count || 0) + (openLoopSignals?.summary?.softening_count || 0) + (openLoopSignals?.summary?.closed_count || 0)}</strong>
              <p>{openLoopSignals?.summary?.current_signal || 'No active open loop'}</p>
              <p>
                {openLoopSignals?.summary?.open_count || 0} open · {openLoopSignals?.summary?.softening_count || 0} softening · {openLoopSignals?.summary?.closed_count || 0} closed
              </p>
            </div>
            {(() => {
              const uuActive = (userUnderstandingSignals?.summary?.active_count || 0) + (userUnderstandingSignals?.summary?.softening_count || 0)
              const uuSignal = userUnderstandingSignals?.summary?.current_signal || ''
              const umActive = (userMdUpdateProposals?.summary?.fresh_count || 0) + (userMdUpdateProposals?.summary?.active_count || 0) + (userMdUpdateProposals?.summary?.fading_count || 0)
              const umProposal = userMdUpdateProposals?.summary?.current_proposal || ''
              const hasAny = uuActive > 0 || umActive > 0
              return hasAny ? (
            <div className="compact-metric">
              <span>User Learning</span>
              <strong>{uuActive > 0 ? `${uuActive} noticed` : ''}{uuActive > 0 && umActive > 0 ? ' · ' : ''}{umActive > 0 ? `${umActive} proposed` : ''}</strong>
              {uuSignal ? <p>Noticed: {uuSignal.replace(/^User-understanding signal: /i, '').slice(0, 80)}</p> : null}
              {umProposal ? <p>Proposal: {umProposal.replace(/^USER\.md update proposal: /i, '').slice(0, 80)}</p> : null}
              <p className="muted">Bounded runtime observations — not applied preferences</p>
            </div>
              ) : (
            <div className="compact-metric">
              <span>User Learning</span>
              <strong>Listening</strong>
              <p className="muted">No user preferences noticed yet</p>
            </div>
              )
            })()}
            <div className="compact-metric">
              <span>Lifecycle</span>
              <strong>
                {developmentFocuses?.summary?.stale_count || 0} stale · {developmentFocuses?.summary?.completed_count || 0} done
              </strong>
              <p>{developmentFocuses?.summary?.superseded_count || 0} superseded focus records retained for continuity.</p>
              <p>{selfModelSignals?.summary?.stale_count || 0} stale self-assessments retained for bounded continuity.</p>
            </div>
          </div>
        </article>

        {/* ─── Focus & Goals card ─── */}
        <article className="support-card" title={sectionTitleWithMeta({
          source: '/mc/jarvis::development',
          fetchedAt: data?.fetchedAt,
          mode: 'snapshot + drilldown',
        })}>
          <div className="panel-header">
            <div>
              <h3>Focus &amp; Goals</h3>
              <p className="muted">Active development focus threads and goal-direction signals.</p>
            </div>
            <span className="mc-section-hint">Read-only</span>
          </div>
          <div className="mc-list">
            {developmentSnapshotRow({
              focusSummary: developmentFocuses?.summary || {},
              goalSummary: goalSignals?.summary || {},
              criticSummary: reflectiveCritics?.summary || {},
              reflectionSummary: reflectionSignals?.summary || {},
            }, onOpenItem)}
            <div className="mc-inline-group">
              {subsectionHeader('Core State', 'Direction And Calibration')}
              {detailRow(data?.development?.selfModel, 'Self Model', onOpenItem)}
              {detailRow(data?.development?.developmentState, 'Development State', onOpenItem)}
              {detailRow(data?.development?.privateInnerNoteSupport, 'Private Inner Note Support', onOpenItem)}
              {detailRow(data?.development?.privateInitiativeTensionSupport, 'Private Initiative Tension Support', onOpenItem)}
              {detailRow(data?.development?.privateStateSnapshot, 'Private State Snapshot', onOpenItem)}
              {detailRow(data?.development?.diarySynthesisSupport, 'Diary Synthesis', onOpenItem)}
              {detailRow(data?.development?.autonomyPressureSupport, 'Autonomy Pressure Support', onOpenItem)}
              {detailRow(data?.development?.proactiveLoopLifecycleSupport, 'Proactive Loop Support', onOpenItem)}
              {detailRow(data?.development?.proactiveQuestionGateSupport, 'Proactive Question Gate', onOpenItem)}
              {detailRow(data?.development?.operationalPreference, 'Operational Preference', onOpenItem)}
              {detailRow(data?.development?.operationalAlignment, 'Preference Alignment', onOpenItem)}
              {detailRow(data?.development?.growthNote, 'Latest Growth Note', onOpenItem)}
              {detailRow(data?.development?.reflectiveSelection, 'Latest Reflective Selection', onOpenItem)}
              <details className="mc-dormant-details">
                <summary className="mc-dormant-summary">Readiness &amp; dormant support layers</summary>
                {detailRow(data?.development?.privateInnerInterplaySupport, 'Private Inner Interplay Support', onOpenItem)}
                {detailRow(data?.development?.privateTemporalCuriosityState, 'Private Temporal Curiosity State', onOpenItem)}
                {detailRow(data?.development?.innerVisibleSupport, 'Inner Visible Support', onOpenItem)}
                {detailRow(data?.development?.regulationHomeostasisSupport, 'Regulation/Homeostasis Support', onOpenItem)}
                {detailRow(data?.development?.relationStateSupport, 'Relation State Support', onOpenItem)}
                {detailRow(data?.development?.relationContinuitySupport, 'Relation Continuity Support', onOpenItem)}
                {detailRow(data?.development?.meaningSignificanceSupport, 'Meaning/Significance Support', onOpenItem)}
                {detailRow(data?.development?.selfNarrativeContinuitySupport, 'Self-Narrative Continuity Support', onOpenItem)}
                {detailRow(data?.development?.selfNarrativeReviewBridgeSupport, 'Self-Narrative Review Bridge', onOpenItem)}
                {detailRow(data?.development?.metabolismStateSupport, 'Metabolism Support', onOpenItem)}
                {detailRow(data?.development?.consolidationTargetSupport, 'Consolidation Support', onOpenItem)}
                {detailRow(data?.development?.selectiveForgettingCandidateSupport, 'Forgetting Candidate Support', onOpenItem)}
                {detailRow(data?.development?.releaseMarkerSupport, 'Release Support', onOpenItem)}
                {detailRow(data?.development?.temperamentTendencySupport, 'Temperament Support', onOpenItem)}
                {detailRow(data?.development?.attachmentTopologySupport, 'Attachment Support', onOpenItem)}
                {detailRow(data?.development?.loyaltyGradientSupport, 'Loyalty Gradient Support', onOpenItem)}
                {detailRow(data?.development?.executiveContradictionSupport, 'Executive Contradiction Support', onOpenItem)}
                {detailRow(data?.development?.privateTemporalPromotionSignal, 'Private Temporal Promotion Signal', onOpenItem)}
              </details>
            </div>

            <div className="mc-inline-group">
              {subsectionHeader('Live Threads', 'What Jarvis Is Working And Carrying')}
              {developmentFocuses.items.length === 0 ? (
                <div className="mc-empty-state">
                  <strong>No active development focus</strong>
                  <p className="muted">Jarvis has not accumulated a bounded development focus yet.</p>
                </div>
              ) : developmentFocuses.items.slice(0, 3).map((item) => developmentFocusRow(item, onOpenItem))}
              {goalDirectionRow({
                summary: goalSignals?.summary || {},
                currentGoal: goalSignals?.summary?.current_goal || summary?.development?.current_goal || 'No active goal signal',
                blockedCount: goalSignals?.summary?.blocked_count || 0,
                completedCount: goalSignals?.summary?.completed_count || 0,
              }, onOpenItem)}
              {goalSignals.items.length === 0 ? (
                <div className="mc-empty-state">
                  <strong>No active goal signal</strong>
                  <p className="muted">Jarvis has not accumulated a bounded current aim yet.</p>
                </div>
              ) : goalSignals.items.slice(0, 3).map((item) => goalSignalRow(item, onOpenItem))}
            </div>
          </div>
        </article>

        {/* ─── Reflection & Critics card ─── */}
        <article className="support-card" title={sectionTitleWithMeta({
          source: '/mc/jarvis::development',
          fetchedAt: data?.fetchedAt,
          mode: 'snapshot + drilldown',
        })}>
          <div className="panel-header">
            <div>
              <h3>Reflection &amp; Critics</h3>
              <p className="muted">Friction, limits, slow settling, and recurring patterns.</p>
            </div>
            <span className="mc-section-hint">Read-only</span>
          </div>
          <div className="mc-list">
            {criticPressureRow({
              summary: reflectiveCritics?.summary || {},
              currentCritic: reflectiveCritics?.summary?.current_critic || summary?.development?.current_critic || 'No active critic signal',
              resolvedCount: reflectiveCritics?.summary?.resolved_count || 0,
              staleCount: reflectiveCritics?.summary?.stale_count || 0,
            }, onOpenItem)}
            {reflectiveCritics.items.length === 0 ? (
              <div className="mc-empty-state">
                <strong>No active critic signal</strong>
                <p className="muted">Jarvis has not accumulated a bounded reflective mismatch signal yet.</p>
              </div>
            ) : reflectiveCritics.items.slice(0, 3).map((item) => reflectiveCriticRow(item, onOpenItem))}
            {selfModelCalibrationRow({
              summary: selfModelSignals?.summary || {},
              currentSignal: selfModelSignals?.summary?.current_signal || summary?.development?.current_self_model_signal || 'No active self-model signal',
              uncertainCount: selfModelSignals?.summary?.uncertain_count || 0,
              correctedCount: selfModelSignals?.summary?.corrected_count || 0,
            }, onOpenItem)}
            {selfModelSignals.items.length === 0 ? (
              <div className="mc-empty-state">
                <strong>No active self-model signal</strong>
                <p className="muted">Jarvis has not accumulated a bounded self-assessment yet.</p>
              </div>
            ) : selfModelSignals.items.slice(0, 3).map((item) => selfModelSignalRow(item, onOpenItem))}
            {reflectionSignals.items.length === 0 ? (
              <div className="mc-empty-state">
                <strong>No active reflection signal</strong>
                <p className="muted">Jarvis has not accumulated a bounded slow-integration reflection thread yet.</p>
              </div>
            ) : reflectionSignals.items.slice(0, 3).map((item) => reflectionSignalRow(item, onOpenItem))}
            {reflectionHistory.length > 0 ? subsectionHeader('Recent Reflection', 'History') : null}
            {reflectionHistory.slice(0, 4).map((item) => reflectionHistoryRow(item, onOpenItem))}
            {temporalRecurrenceSignals.items.length > 0 ? subsectionHeader('Recurring Patterns', 'What Keeps Returning') : null}
            {temporalRecurrenceSignals.items.slice(0, 3).map((item) => temporalRecurrenceSignalRow(item, onOpenItem))}
          </div>
        </article>

        {/* ─── Inner Signals card ─── */}
        <article className="support-card" title={sectionTitleWithMeta({
          source: '/mc/jarvis::development',
          fetchedAt: data?.fetchedAt,
          mode: 'snapshot + drilldown',
        })}>
          <div className="panel-header">
            <div>
              <h3>Inner Signals</h3>
              <p className="muted">Open loops, emergent threads, opposition, and witnessed turns.</p>
            </div>
            <span className="mc-section-hint">Read-only</span>
          </div>
          <div className="mc-list">
            {openLoopSignals.items.length > 0 ? subsectionHeader('Open Loops', 'What Remains Unresolved') : null}
            {openLoopSignals.items.slice(0, 3).map((item) => openLoopSignalRow(item, onOpenItem))}
            {openLoopClosureProposals.items.length > 0 ? subsectionHeader('Closure Proposals', 'Bounded Proposals Only — Not Automatic Closure') : null}
            {openLoopClosureProposals.items.slice(0, 3).map((item) => openLoopClosureProposalRow(item, onOpenItem))}
            {subsectionHeader('Emergent Signals', 'Internal-Only Candidate Threads With Bounded Lifecycle')}
            {emergentSignals.items.length === 0 ? (
              <div className="mc-empty-state">
                <strong>No active emergent inner signal</strong>
                <p className="muted">Unknown is allowed, but silence is not: this bounded layer is currently quiet and remains candidate-only when active.</p>
              </div>
            ) : emergentSignals.items.slice(0, 3).map((item) => emergentSignalRow(item, onOpenItem))}
            {emergentSignals.recentReleased.length > 0 ? subsectionHeader('Recently Released', 'Signals That Faded Out Without Authority') : null}
            {emergentSignals.recentReleased.slice(0, 2).map((item) => emergentSignalRow(item, onOpenItem))}
            {internalOppositionSignals.items.length > 0 ? subsectionHeader('Internal Opposition', 'What Should Be Challenged Internally') : null}
            {internalOppositionSignals.items.slice(0, 3).map((item) => internalOppositionSignalRow(item, onOpenItem))}
            {witnessSignals.items.length > 0 ? subsectionHeader('Witnessed Turns', 'Development Turns Jarvis Has Witnessed') : null}
            {witnessSignals.items.slice(0, 3).map((item) => witnessSignalRow(item, onOpenItem))}
          </div>
        </article>

        {/* ─── Proposals card ─── */}
        <article className="support-card" title={sectionTitleWithMeta({
          source: '/mc/jarvis::development',
          fetchedAt: data?.fetchedAt,
          mode: 'snapshot + drilldown',
        })}>
          <div className="panel-header">
            <div>
              <h3>Proposals</h3>
              <p className="muted">Dream hypotheses, prompt proposals, user learning, and selfhood proposals.</p>
            </div>
            <span className="mc-section-hint">Read-only</span>
          </div>
          <div className="mc-list">
            {dreamHypothesisSignals.items.length > 0 ? subsectionHeader('Dream Hypotheses', 'Bounded Dream-Layer Candidates') : null}
            {dreamHypothesisSignals.items.slice(0, 3).map((item) => dreamHypothesisSignalRow(item, onOpenItem))}
            {dreamAdoptionCandidates.items.length > 0 ? subsectionHeader('Dream Adoption', 'Candidates For Dream-To-Waking Adoption') : null}
            {dreamAdoptionCandidates.items.slice(0, 3).map((item) => dreamAdoptionCandidateRow(item, onOpenItem))}
            {dreamInfluenceProposals.items.length > 0 ? subsectionHeader('Dream Influence', 'Bounded Dream Influence Proposals') : null}
            {dreamInfluenceProposals.items.slice(0, 3).map((item) => dreamInfluenceProposalRow(item, onOpenItem))}
            {selfAuthoredPromptProposals.items.length > 0 ? subsectionHeader('Prompt Proposals', 'Self-Authored Prompt Nudges') : null}
            {selfAuthoredPromptProposals.items.slice(0, 3).map((item) => selfAuthoredPromptProposalRow(item, onOpenItem))}
            {userUnderstandingSignals.items.length > 0 ? subsectionHeader('User Insight', 'Bounded User-Understanding Signals') : null}
            {userUnderstandingSignals.items.slice(0, 3).map((item) => userUnderstandingSignalRow(item, onOpenItem))}
            {userMdUpdateProposals.items.length > 0 ? subsectionHeader('USER.md Proposals', 'Bounded USER.md Update Proposals') : null}
            {userMdUpdateProposals.items.slice(0, 3).map((item) => userMdUpdateProposalRow(item, onOpenItem))}
            {selfhoodProposals.items.length > 0 ? subsectionHeader('Selfhood Proposals', 'Bounded Identity Evolution Proposals') : null}
            {selfhoodProposals.items.slice(0, 3).map((item) => selfhoodProposalRow(item, onOpenItem))}
            {(dreamHypothesisSignals.items.length === 0 && dreamAdoptionCandidates.items.length === 0 && dreamInfluenceProposals.items.length === 0 && selfAuthoredPromptProposals.items.length === 0 && userUnderstandingSignals.items.length === 0 && userMdUpdateProposals.items.length === 0 && selfhoodProposals.items.length === 0) ? (
              <div className="mc-empty-state">
                <strong>No active proposals</strong>
                <p className="muted">No bounded dream, prompt, user-learning, or selfhood proposals are active right now.</p>
              </div>
            ) : null}
          </div>
        </article>
      </section>
    </div>
  )
}
