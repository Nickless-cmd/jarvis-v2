import { ChevronRight } from 'lucide-react'
import { formatFreshness, sectionTitleWithMeta } from './meta'

function StatusPill({ status }) {
  if (!status) return null
  const normalizedStatus = String(status).toLowerCase().replace(/[-_\s]+/g, '-')
  return <span className={`mc-status-pill status-${normalizedStatus}`}>{status}</span>
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

function candidateRow(item, onOpen) {
  const evidenceLabel = item.evidenceClass
    ? item.evidenceClass.replace(/_/g, ' ')
    : (item.sourceKind || '')
  return (
    <button
      className="mc-list-row mc-list-row-subtle"
      key={item.candidateId || item.summary}
      onClick={() => onOpen(item.summary || 'Candidate', item)}
      title={sectionTitleWithMeta({
        source: item.source,
        fetchedAt: item.updatedAt || item.createdAt,
        mode: 'candidate detail',
      })}
    >
      <div>
        <strong>{item.summary || 'Candidate'}</strong>
        <span>{item.reason || item.evidenceSummary || 'Inspect candidate evidence'}</span>
      </div>
      <div className="mc-row-meta">
        <StatusPill status={item.status || 'proposed'} />
        {item.confidence ? <small>{item.confidence}</small> : null}
        {evidenceLabel ? <small>{evidenceLabel}</small> : null}
        {item.updatedAt ? <small>{formatFreshness(item.updatedAt)}</small> : null}
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

function selfReviewSignalRow(item, onOpen) {
  const sourceLabel = item.sourceKind ? item.sourceKind.replace(/-/g, ' ') : ''
  const lifecycleLabel = item.status === 'softening'
    ? 'Softening review need'
    : item.status === 'stale'
      ? 'Stale review need'
      : item.status === 'superseded'
        ? 'Superseded review need'
        : 'Active review need'
  const detailText = [
    lifecycleLabel,
    item.statusReason,
    item.rationale,
    item.supportSummary,
  ].filter(Boolean)[0] || 'Inspect bounded self-review need'
  return (
    <button
      className="mc-list-row mc-list-row-subtle"
      key={item.signalId || item.title}
      onClick={() => onOpen(item.title || 'Self Review Signal', item)}
      title={sectionTitleWithMeta({
        source: item.source,
        fetchedAt: item.updatedAt || item.createdAt,
        mode: 'self review detail',
      })}
    >
      <div>
        <strong>{item.title || 'Self Review Signal'}</strong>
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

function selfReviewRecordRow(item, onOpen) {
  const sourceLabel = item.sourceKind ? item.sourceKind.replace(/-/g, ' ') : ''
  const lifecycleLabel = item.status === 'active'
    ? 'Active review brief'
    : item.status === 'fading'
      ? 'Fading review brief'
      : item.status === 'stale'
        ? 'Stale review brief'
        : item.status === 'superseded'
          ? 'Superseded review brief'
          : 'Fresh review brief'
  const detailText = [
    item.shortReason,
    `${item.reviewType || 'review'} · loop ${item.openLoopStatus || 'none'} · opposition ${item.oppositionStatus || 'none'}`,
    lifecycleLabel,
  ].filter(Boolean)[0] || 'Inspect bounded self-review brief'
  return (
    <button
      className="mc-list-row mc-list-row-subtle"
      key={item.recordId || item.title}
      onClick={() => onOpen(item.title || 'Self Review Brief', item)}
      title={sectionTitleWithMeta({
        source: item.source,
        fetchedAt: item.updatedAt || item.createdAt,
        mode: 'self review brief',
      })}
    >
      <div>
        <strong>{item.title || 'Self Review Brief'}</strong>
        <span>{detailText}</span>
      </div>
      <div className="mc-row-meta">
        <StatusPill status={item.status || 'fresh'} />
        {item.closureConfidence ? <small>closure {item.closureConfidence}</small> : null}
        {sourceLabel ? <small>{sourceLabel}</small> : null}
        {item.updatedAt ? <small>{formatFreshness(item.updatedAt)}</small> : null}
        <ChevronRight size={14} />
      </div>
    </button>
  )
}

function selfReviewRunRow(item, onOpen) {
  const sourceLabel = item.sourceKind ? item.sourceKind.replace(/-/g, ' ') : ''
  const lifecycleLabel = item.status === 'active'
    ? 'Active review snapshot'
    : item.status === 'fading'
      ? 'Fading review snapshot'
      : item.status === 'stale'
        ? 'Stale review snapshot'
        : item.status === 'superseded'
          ? 'Superseded review snapshot'
          : 'Fresh review snapshot'
  const detailText = [
    item.shortReviewNote,
    item.reviewFocus,
    lifecycleLabel,
  ].filter(Boolean)[0] || 'Inspect bounded self-review snapshot'
  return (
    <button
      className="mc-list-row mc-list-row-subtle"
      key={item.runId || item.title}
      onClick={() => onOpen(item.title || 'Self Review Snapshot', item)}
      title={sectionTitleWithMeta({
        source: item.source,
        fetchedAt: item.updatedAt || item.createdAt,
        mode: 'self review snapshot',
      })}
    >
      <div>
        <strong>{item.title || 'Self Review Snapshot'}</strong>
        <span>{detailText}</span>
      </div>
      <div className="mc-row-meta">
        <StatusPill status={item.status || 'fresh'} />
        {item.closureConfidence ? <small>closure {item.closureConfidence}</small> : null}
        {sourceLabel ? <small>{sourceLabel}</small> : null}
        {item.updatedAt ? <small>{formatFreshness(item.updatedAt)}</small> : null}
        <ChevronRight size={14} />
      </div>
    </button>
  )
}

function selfReviewOutcomeRow(item, onOpen) {
  const sourceLabel = item.sourceKind ? item.sourceKind.replace(/-/g, ' ') : ''
  const lifecycleLabel = item.status === 'active'
    ? 'Active review outcome'
    : item.status === 'fading'
      ? 'Fading review outcome'
      : item.status === 'stale'
        ? 'Stale review outcome'
        : item.status === 'superseded'
          ? 'Superseded review outcome'
          : 'Fresh review outcome'
  const detailText = [
    item.shortOutcome,
    `${item.outcomeType || 'watch-closely'} · ${item.reviewFocus || 'bounded-self-review'}`,
    lifecycleLabel,
  ].filter(Boolean)[0] || 'Inspect bounded self-review outcome'
  return (
    <button
      className="mc-list-row mc-list-row-subtle"
      key={item.outcomeId || item.title}
      onClick={() => onOpen(item.title || 'Self Review Outcome', item)}
      title={sectionTitleWithMeta({
        source: item.source,
        fetchedAt: item.updatedAt || item.createdAt,
        mode: 'self review outcome',
      })}
    >
      <div>
        <strong>{item.title || 'Self Review Outcome'}</strong>
        <span>{detailText}</span>
      </div>
      <div className="mc-row-meta">
        <StatusPill status={item.status || 'fresh'} />
        {item.closureConfidence ? <small>closure {item.closureConfidence}</small> : null}
        {sourceLabel ? <small>{sourceLabel}</small> : null}
        {item.updatedAt ? <small>{formatFreshness(item.updatedAt)}</small> : null}
        <ChevronRight size={14} />
      </div>
    </button>
  )
}

function selfReviewCadenceSignalRow(item, onOpen) {
  const sourceLabel = item.sourceKind ? item.sourceKind.replace(/-/g, ' ') : ''
  const lifecycleLabel = item.status === 'softening'
    ? 'Recently reviewed cadence'
    : item.status === 'stale'
      ? 'Stale cadence signal'
      : item.status === 'superseded'
        ? 'Superseded cadence signal'
        : 'Active cadence signal'
  const detailText = [
    item.cadenceReason,
    `${item.cadenceState || 'due'} · ${item.dueHint || 'Inspect cadence hint'}`,
    lifecycleLabel,
  ].filter(Boolean)[0] || 'Inspect bounded self-review cadence'
  return (
    <button
      className="mc-list-row mc-list-row-subtle"
      key={item.signalId || item.title}
      onClick={() => onOpen(item.title || 'Self Review Cadence', item)}
      title={sectionTitleWithMeta({
        source: item.source,
        fetchedAt: item.updatedAt || item.createdAt,
        mode: 'self review cadence',
      })}
    >
      <div>
        <strong>{item.title || 'Self Review Cadence'}</strong>
        <span>{detailText}</span>
      </div>
      <div className="mc-row-meta">
        <StatusPill status={item.status || 'active'} />
        {item.cadenceState ? <small>{item.cadenceState}</small> : null}
        {sourceLabel ? <small>{sourceLabel}</small> : null}
        {item.updatedAt ? <small>{formatFreshness(item.updatedAt)}</small> : null}
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

function selfReviewFlowSummary({ signals, records, runs, outcomes, cadence }) {
  const signalCount = signals?.items?.length || 0
  const recordCount = records?.items?.length || 0
  const runCount = runs?.items?.length || 0
  const outcomeCount = outcomes?.items?.length || 0
  const cadenceCount = cadence?.items?.length || 0
  return (
    <div className="mc-flow-summary">
      <span><strong className="mc-flow-stage">{signalCount}</strong> need</span>
      <span className="mc-flow-sep">→</span>
      <span><strong className="mc-flow-stage">{recordCount}</strong> brief</span>
      <span className="mc-flow-sep">→</span>
      <span><strong className="mc-flow-stage">{runCount}</strong> snapshot</span>
      <span className="mc-flow-sep">→</span>
      <span><strong className="mc-flow-stage">{outcomeCount}</strong> outcome</span>
      <span className="mc-flow-sep">→</span>
      <span><strong className="mc-flow-stage">{cadenceCount}</strong> cadence</span>
    </div>
  )
}

function selfReviewStageLabel({ stage, count }) {
  if (!count) return null
  return <span className="mc-stage-label">{stage} · {count}</span>
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

export function JarvisTab({ data, onOpenItem, onHeartbeatTick, heartbeatBusy = false }) {
  const summary = data?.summary || {}
  const contract = data?.contract || {}
  const heartbeat = data?.heartbeat || {}
  const heartbeatState = heartbeat?.state || {}
  const heartbeatPolicy = heartbeat?.policy || {}
  const heartbeatTicks = heartbeat?.recentTicks || []
  const heartbeatEvents = heartbeat?.recentEvents || []
  const developmentFocuses = data?.development?.developmentFocuses || { items: [], summary: {} }
  const reflectiveCritics = data?.development?.reflectiveCritics || { items: [], summary: {} }
  const selfModelSignals = data?.development?.selfModelSignals || { items: [], summary: {} }
  const goalSignals = data?.development?.goalSignals || { items: [], summary: {} }
  const reflectionSignals = data?.development?.reflectionSignals || { items: [], summary: {} }
  const temporalRecurrenceSignals = data?.development?.temporalRecurrenceSignals || { items: [], summary: {} }
  const witnessSignals = data?.development?.witnessSignals || { items: [], summary: {} }
  const openLoopSignals = data?.development?.openLoopSignals || { items: [], summary: {} }
  const internalOppositionSignals = data?.development?.internalOppositionSignals || { items: [], summary: {} }
  const selfReviewSignals = data?.development?.selfReviewSignals || { items: [], summary: {} }
  const selfReviewRecords = data?.development?.selfReviewRecords || { items: [], summary: {} }
  const selfReviewRuns = data?.development?.selfReviewRuns || { items: [], summary: {} }
  const selfReviewOutcomes = data?.development?.selfReviewOutcomes || { items: [], summary: {} }
  const selfReviewCadenceSignals = data?.development?.selfReviewCadenceSignals || { items: [], summary: {} }
  const reflectionHistory = reflectionSignals?.recentHistory || []
  const worldModelSignals = data?.continuity?.worldModelSignals || { items: [], summary: {} }
  const runtimeAwarenessSignals = data?.continuity?.runtimeAwarenessSignals || { items: [], summary: {} }
  const runtimeAwarenessHistory = runtimeAwarenessSignals?.recentHistory || []
  const carriedForward = carriedForwardSummary({
    relationState: data?.continuity?.relationState,
    promotionSignal: data?.continuity?.promotionSignal,
    promotionDecision: data?.continuity?.promotionDecision,
  })
  const recentShift = recentShiftSummary({
    visibleSession: data?.continuity?.visibleSession,
    visibleContinuity: data?.continuity?.visibleContinuity,
  })
  const contractSummary = contract?.summary || {}
  const capabilityContract = contract?.capabilityContract || {}
  const promptModes = contract?.promptModes || []
  const pendingWrites = contract?.pendingWrites || []
  const canonicalFiles = contract?.files?.canonical || []
  const derivedFiles = contract?.files?.derived || []
  const referenceFiles = contract?.files?.referenceOnly || []
  const writeHistory = contract?.writeHistory || { items: [], total: 0, summary: '' }

  return (
    <div className="mc-tab-page">
      <section className="mc-summary-grid">
        <article className="mc-stat tone-accent" title={sectionTitleWithMeta({
          source: '/mc/jarvis',
          fetchedAt: data?.fetchedAt,
          mode: 'snapshot summary',
        })}>
          <span>State Signal</span>
          <strong>{summary?.state_signal?.mood_tone || 'unknown'}</strong>
          <small className="muted">{summary?.state_signal?.current_concern || 'No current concern'}</small>
        </article>
        <article className="mc-stat tone-blue" title={sectionTitleWithMeta({
          source: '/mc/jarvis',
          fetchedAt: data?.fetchedAt,
          mode: 'snapshot summary',
        })}>
          <span>Retained Memory</span>
          <strong>{summary?.retained_memory?.kind || 'unknown'}</strong>
          <small className="muted">{summary?.retained_memory?.focus || 'No retained focus'}</small>
        </article>
        <article className="mc-stat tone-amber" title={sectionTitleWithMeta({
          source: '/mc/jarvis',
          fetchedAt: data?.fetchedAt,
          mode: 'snapshot summary',
        })}>
          <span>Development</span>
          <strong>{summary?.development?.direction || 'unknown'}</strong>
          <small className="muted">{summary?.development?.identity_focus || 'No identity focus'}</small>
        </article>
        <article className="mc-stat tone-green" title={sectionTitleWithMeta({
          source: '/mc/jarvis',
          fetchedAt: data?.fetchedAt,
          mode: 'snapshot summary',
        })}>
          <span>Continuity</span>
          <strong>{summary?.continuity?.continuity_mode || 'unknown'}</strong>
          <small className="muted">{summary?.continuity?.relation_pull || 'No continuity pull'}</small>
        </article>
        <article className="mc-stat tone-accent" title={sectionTitleWithMeta({
          source: '/mc/jarvis::heartbeat',
          fetchedAt: data?.fetchedAt,
          mode: 'bounded heartbeat runtime',
        })}>
          <span>Heartbeat</span>
          <strong>{summary?.heartbeat?.status || heartbeatState.scheduleState || heartbeatState.scheduleStatus || 'unknown'}</strong>
          <small className="muted">
            {heartbeatState.currentlyTicking
              ? 'Tick in progress'
              : (summary?.heartbeat?.result || heartbeatState.summary || 'No heartbeat result yet')}
          </small>
        </article>
      </section>

      <section className="mc-section-grid">
        <article className="support-card" id="jarvis-contract" title={sectionTitleWithMeta({
          source: '/mc/runtime-contract',
          fetchedAt: data?.fetchedAt,
          mode: 'snapshot + drilldown',
        })}>
          <div className="panel-header">
            <div>
              <h3>Runtime Contract</h3>
              <p className="muted">Canonical files, bootstrap state, prompt modes, and governed USER/MEMORY workflow state.</p>
            </div>
            <span className="mc-section-hint">{contract?.contractVersion || 'contract'}</span>
          </div>
          <div className="compact-grid compact-grid-5">
            <div className="compact-metric">
              <span>Bootstrap</span>
              <strong>{contractSummary?.bootstrap_status || 'unknown'}</strong>
              <p>{contract?.bootstrap?.summary || 'No bootstrap state recorded.'}</p>
            </div>
            <div className="compact-metric">
              <span>Canonical Files</span>
              <strong>{contractSummary?.canonical_present || 0}/{contractSummary?.canonical_expected || canonicalFiles.length || 0}</strong>
              <p>Workspace truth files present and inspectable.</p>
            </div>
            <div className="compact-metric">
              <span>Prompt Modes</span>
              <strong>{contractSummary?.prompt_modes_active || 0}/{contractSummary?.prompt_modes_declared || promptModes.length || 0}</strong>
              <p>Active vs declared runtime prompt contracts.</p>
            </div>
            <div className="compact-metric">
              <span>Capability Authority</span>
              <strong>{capabilityContract?.availableNowCount || 0}</strong>
              <p>{capabilityContract?.summary || 'Runtime capability truth is authoritative.'}</p>
            </div>
            <div className="compact-metric">
              <span>Pending Writes</span>
              <strong>{contractSummary?.pending_write_count || 0}</strong>
              <p>Governed USER.md and MEMORY.md candidates await explicit approval and apply.</p>
            </div>
          </div>
          <div className="mc-contract-grid">
            <div className="mc-contract-column">
              <div className="support-card-header">
                <span className="support-card-kicker">Canonical</span>
                <strong>Workspace Files</strong>
              </div>
              <div className="mc-list compact-list">
                {canonicalFiles.map((item) => (
                  <button className="mc-list-row" key={item.name} onClick={() => onOpenItem(item.name, item)}>
                    <div>
                      <strong>{item.name}</strong>
                      <span>{item.summary}</span>
                    </div>
                    <div className="mc-row-meta">
                      <small>{item.present ? 'present' : 'missing'}</small>
                      <ChevronRight size={14} />
                    </div>
                  </button>
                ))}
              </div>
            </div>

            <div className="mc-contract-column">
              <div className="support-card-header">
                <span className="support-card-kicker">Modes</span>
                <strong>Prompt Contracts</strong>
              </div>
              <div className="mc-list compact-list">
                {promptModes.map((item) => (
                  <button className="mc-list-row" key={item.id} onClick={() => onOpenItem(item.label, item)}>
                    <div>
                      <strong>{item.label}</strong>
                      <span>{item.summary}</span>
                    </div>
                    <div className="mc-row-meta">
                      <small>{item.status}</small>
                      <ChevronRight size={14} />
                    </div>
                  </button>
                ))}
              </div>
            </div>

            <div className="mc-contract-column">
              <div className="support-card-header">
                <span className="support-card-kicker">Authority</span>
                <strong>Capabilities And Workflow</strong>
              </div>
              <div className="mc-list compact-list">
                <button className="mc-list-row" onClick={() => onOpenItem('Capability Authority', capabilityContract)}>
                  <div>
                    <strong>Capability Authority</strong>
                    <span>{capabilityContract?.summary || 'Runtime capability truth is authoritative.'}</span>
                  </div>
                  <div className="mc-row-meta">
                    <small>{capabilityContract?.authoritySource || 'runtime.workspace_capabilities'}</small>
                    <ChevronRight size={14} />
                  </div>
                </button>
                {detailRow(contract?.bootstrap, 'Bootstrap State', onOpenItem)}
                {pendingWrites.map((item) => (
                  <div key={item.id} className="mc-inline-group">
                    <button className="mc-list-row" onClick={() => onOpenItem(item.label, item)}>
                      <div>
                        <strong>{item.label}</strong>
                        <span>{item.summary}</span>
                      </div>
                      <div className="mc-row-meta">
                        {item.pendingCount ? <span className="mc-status-pill status-proposed">{item.pendingCount} proposed</span> : null}
                        {item.approvedCount ? <span className="mc-status-pill status-approved">{item.approvedCount} approved</span> : null}
                        <ChevronRight size={14} />
                      </div>
                    </button>
                    {(item.items || []).slice(0, 2).map((candidate) => candidateRow(candidate, onOpenItem))}
                  </div>
                ))}
                <button
                  className="mc-list-row"
                  onClick={() => onOpenItem('Runtime Contract File Writes', {
                    source: '/mc/runtime-contract',
                    summary: writeHistory.summary,
                    items: writeHistory.items,
                    total: writeHistory.total,
                    counts: writeHistory.counts,
                  })}
                >
                  <div>
                    <strong>Latest File Writes</strong>
                    <span>{writeHistory.summary}</span>
                  </div>
                  <div className="mc-row-meta">
                    <small>{writeHistory.total || 0} applied</small>
                    <ChevronRight size={14} />
                  </div>
                </button>
                <button
                  className="mc-list-row"
                  onClick={() => onOpenItem('Derived and Reference Files', {
                    source: '/mc/runtime-contract',
                    summary: `${derivedFiles.length} derived and ${referenceFiles.length} reference-only files tracked.`,
                    derivedFiles,
                    referenceFiles,
                  })}
                >
                  <div>
                    <strong>Derived and Reference Files</strong>
                    <span>Inspect non-canonical runtime artifacts and reference-only inputs.</span>
                  </div>
                  <div className="mc-row-meta">
                    <small>{derivedFiles.length + referenceFiles.length} tracked</small>
                    <ChevronRight size={14} />
                  </div>
                </button>
              </div>
            </div>
          </div>
        </article>
      </section>

      <section className="mc-section-grid">
        <article className="support-card" id="jarvis-heartbeat" title={sectionTitleWithMeta({
          source: '/mc/jarvis::heartbeat',
          fetchedAt: data?.fetchedAt,
          mode: 'manual bounded tick + runtime snapshot',
        })}>
          <div className="panel-header">
            <div>
              <h3>Heartbeat</h3>
              <p className="muted">Bounded proactive runtime with explicit policy gating, cadence, and recorded outcomes.</p>
            </div>
            <div className="mc-inline-actions">
              <span className="mc-section-hint">{heartbeatState.enabled ? 'Bounded' : 'Disabled'}</span>
              <button
                className="secondary-btn"
                onClick={() => onHeartbeatTick?.()}
                disabled={heartbeatBusy}
                title="Run one bounded heartbeat tick now"
              >
                {heartbeatBusy ? 'Ticking…' : 'Tick now'}
              </button>
            </div>
          </div>
          <div className="compact-grid compact-grid-4">
            <div className="compact-metric">
              <span>Schedule</span>
              <strong>{heartbeatState.scheduleState || heartbeatState.scheduleStatus || 'unknown'}</strong>
              <p>{heartbeatState.summary || 'No heartbeat state recorded yet.'}</p>
            </div>
            <div className="compact-metric">
              <span>Scheduler</span>
              <strong>{heartbeatState.schedulerHealth || (heartbeatState.schedulerActive ? 'active' : 'stopped') || 'unknown'}</strong>
              <p>
                {heartbeatState.schedulerActive
                  ? `Started ${heartbeatState.schedulerStartedAt || 'recently'}.`
                  : `Stopped ${heartbeatState.schedulerStoppedAt || 'not recorded'}.`}
              </p>
            </div>
            <div className="compact-metric">
              <span>Cadence</span>
              <strong>{heartbeatState.intervalMinutes || heartbeatPolicy.intervalMinutes || 0}m</strong>
              <p>
                {heartbeatState.currentlyTicking
                  ? 'Tick currently in progress.'
                  : `Next tick ${heartbeatState.nextTickAt || 'not scheduled'}.`}
              </p>
            </div>
            <div className="compact-metric">
              <span>Last Trigger</span>
              <strong>{heartbeatState.lastTriggerSource || summary?.heartbeat?.trigger || 'none'}</strong>
              <p>{heartbeatState.lastTickAt || 'No completed tick yet.'}</p>
            </div>
            <div className="compact-metric">
              <span>Last Decision</span>
              <strong>{heartbeatState.lastDecisionType || 'none'}</strong>
              <p>{heartbeatState.lastResult || heartbeatState.blockedReason || 'No heartbeat result yet.'}</p>
            </div>
            <div className="compact-metric">
              <span>Last Execute Action</span>
              <strong>{heartbeatState.lastActionType || 'none'}</strong>
              <p>{heartbeatState.lastActionSummary || heartbeatState.lastActionStatus || 'No execute action recorded yet.'}</p>
            </div>
            <div className="compact-metric">
              <span>Recovery</span>
              <strong>{heartbeatState.recoveryStatus || 'idle'}</strong>
              <p>{heartbeatState.lastRecoveryAt || 'No recovery activity recorded.'}</p>
            </div>
          </div>
          <div className="mc-contract-grid">
            <div className="mc-contract-column">
              <div className="support-card-header">
                <span className="support-card-kicker">Policy</span>
                <strong>Runtime State</strong>
              </div>
              <div className="mc-list compact-list">
                {detailRow({
                  ...heartbeatState,
                  createdAt: heartbeatState.updatedAt || heartbeatState.lastTickAt,
                  summary: heartbeatState.summary || 'Inspect merged heartbeat runtime state.',
                }, 'Heartbeat State', onOpenItem)}
                {detailRow({
                  ...heartbeatPolicy,
                  createdAt: heartbeatState.updatedAt || data?.fetchedAt,
                  summary: heartbeatPolicy.summary || 'Inspect HEARTBEAT.md-derived policy.',
                }, 'Heartbeat Policy', onOpenItem)}
              </div>
            </div>

            <div className="mc-contract-column">
              <div className="support-card-header">
                <span className="support-card-kicker">Ticks</span>
                <strong>Recent Decisions</strong>
              </div>
              <div className="mc-list compact-list">
                {heartbeatTicks.length === 0 ? (
                  <div className="mc-empty-state">
                    <strong>No heartbeat ticks yet</strong>
                    <p className="muted">Run a manual tick to record the first bounded heartbeat decision.</p>
                  </div>
                ) : heartbeatTicks.map((item) => (
                  <button className="mc-list-row" key={item.tickId || item.startedAt} onClick={() => onOpenItem('Heartbeat Tick', item)}>
                    <div>
                      <strong>
                        {item.actionType
                          ? `${item.decisionType || item.tickStatus || 'tick'} / ${item.actionType}`
                          : (item.decisionType || item.tickStatus || 'tick')}
                      </strong>
                      <span>{item.actionSummary || item.decisionSummary || item.blockedReason || 'Inspect heartbeat tick detail'}</span>
                    </div>
                    <div className="mc-row-meta">
                      <StatusPill status={item.actionStatus || item.tickStatus || 'unknown'} />
                      {item.startedAt ? <small>{formatFreshness(item.startedAt)}</small> : null}
                      <ChevronRight size={14} />
                    </div>
                  </button>
                ))}
              </div>
            </div>

            <div className="mc-contract-column">
              <div className="support-card-header">
                <span className="support-card-kicker">Events</span>
                <strong>Recent Heartbeat Events</strong>
              </div>
              <div className="mc-list compact-list">
                {heartbeatEvents.length === 0 ? (
                  <div className="mc-empty-state">
                    <strong>No heartbeat events</strong>
                    <p className="muted">Events will appear here when ticks start, block, or record outcomes.</p>
                  </div>
                ) : heartbeatEvents.slice(0, 5).map((item) => (
                  <button className="mc-list-row" key={item.id || item.createdAt} onClick={() => onOpenItem(item.kind || 'Heartbeat Event', item)}>
                    <div>
                      <strong>{item.kind || 'heartbeat.event'}</strong>
                      <span>{item.relativeTime || 'recent'} · inspect event payload and runtime context</span>
                    </div>
                    <div className="mc-row-meta">
                      <small>{item.family || 'heartbeat'}</small>
                      <ChevronRight size={14} />
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </article>
      </section>

      <section className="mc-section-grid">
        <article className="support-card" id="jarvis-state" title={sectionTitleWithMeta({
          source: '/mc/jarvis::state',
          fetchedAt: data?.fetchedAt,
          mode: 'snapshot + drilldown',
        })}>
          <div className="panel-header">
            <div>
              <h3>State</h3>
              <p className="muted">Visible and internal state signals for Jarvis right now.</p>
            </div>
            <span className="mc-section-hint">Read-only</span>
          </div>
          <div className="compact-grid">
            <div className="compact-metric">
              <span>Mood tone</span>
              <strong>{summary?.state_signal?.mood_tone || 'unknown'}</strong>
            </div>
            <div className="compact-metric">
              <span>Confidence</span>
              <strong>{summary?.state_signal?.confidence || 'unknown'}</strong>
            </div>
          </div>
          <div className="mc-list">
            {detailRow(data?.state?.visibleIdentity, 'Visible Identity', onOpenItem)}
            {detailRow(data?.state?.protectedInnerVoice, 'Protected Inner Voice', onOpenItem)}
            {detailRow(data?.state?.privateState, 'Private State', onOpenItem)}
            {detailRow(data?.state?.initiativeTension, 'Initiative Tension', onOpenItem)}
          </div>
        </article>

        <article className="support-card" id="jarvis-memory" title={sectionTitleWithMeta({
          source: '/mc/jarvis::memory',
          fetchedAt: data?.fetchedAt,
          mode: 'snapshot + drilldown',
        })}>
          <div className="panel-header">
            <div>
              <h3>Memory</h3>
              <p className="muted">Retained signals and current retained projection.</p>
            </div>
            <span className="mc-section-hint">Projection-first</span>
          </div>
          <div className="compact-grid">
            <div className="compact-metric">
              <span>Retention scope</span>
              <strong>{summary?.retained_memory?.scope || 'unknown'}</strong>
            </div>
            <div className="compact-metric">
              <span>Confidence</span>
              <strong>{summary?.retained_memory?.confidence || 'unknown'}</strong>
            </div>
          </div>
          <div className="mc-list">
            {detailRow(data?.memory?.retainedProjection, 'Retained Projection', onOpenItem)}
            {detailRow(data?.memory?.retainedRecord, 'Current Retained Record', onOpenItem)}
            {(data?.memory?.recentRecords || []).slice(0, 3).map((record) => (
              <button className="mc-list-row" key={record.record_id || record.recordId || record.createdAt} onClick={() => onOpenItem('Recent Retained Record', record)}>
                <div>
                  <strong>{record.retained_kind || 'retained-record'}</strong>
                  <span>{record.summary || 'Inspect retained record'}</span>
                </div>
                <div className="mc-row-meta">
                  <small>{record.createdAt || 'recent'}</small>
                  <ChevronRight size={14} />
                </div>
              </button>
            ))}
          </div>
        </article>
      </section>

      <section className="mc-section-grid">
        <article className="support-card" id="jarvis-development" title={sectionTitleWithMeta({
          source: '/mc/jarvis::development',
          fetchedAt: data?.fetchedAt,
          mode: 'snapshot + drilldown',
        })}>
          <div className="panel-header">
            <div>
              <h3>Development</h3>
              <p className="muted">Self-model, development direction, and operational preference signals.</p>
            </div>
            <span className="mc-section-hint">Read-only</span>
          </div>
          <div className="compact-grid">
            <div className="compact-metric">
              <span>Work mode</span>
              <strong>{summary?.development?.work_mode || 'unknown'}</strong>
            </div>
            <div className="compact-metric">
              <span>Recurring tension</span>
              <strong>{summary?.development?.tension || 'unknown'}</strong>
            </div>
            <div className="compact-metric">
              <span>Guided focus</span>
              <strong>{developmentFocuses?.summary?.active_count || summary?.development?.focus_count || 0}</strong>
              <p>{developmentFocuses?.summary?.current_focus || summary?.development?.current_focus || 'No active development focus'}</p>
            </div>
            <div className="compact-metric">
              <span>Goal Signals</span>
              <strong>{(goalSignals?.summary?.active_count || 0) + (goalSignals?.summary?.blocked_count || 0) || summary?.development?.goal_count || 0}</strong>
              <p>{goalSignals?.summary?.current_goal || summary?.development?.current_goal || 'No active goal signal'}</p>
              <p>
                {goalSignals?.summary?.blocked_count || 0} blocked · {goalSignals?.summary?.completed_count || 0} completed · {goalSignals?.summary?.superseded_count || 0} superseded
              </p>
            </div>
            <div className="compact-metric">
              <span>Reflective Critic</span>
              <strong>{reflectiveCritics?.summary?.active_count || summary?.development?.critic_count || 0}</strong>
              <p>{reflectiveCritics?.summary?.current_critic || summary?.development?.current_critic || 'No active critic signal'}</p>
              <p>
                {reflectiveCritics?.summary?.stale_count || 0} stale · {reflectiveCritics?.summary?.resolved_count || 0} resolved · {reflectiveCritics?.summary?.superseded_count || 0} superseded
              </p>
            </div>
            <div className="compact-metric">
              <span>Self-Model Signals</span>
              <strong>{selfModelSignals?.summary?.active_count || summary?.development?.self_model_signal_count || 0}</strong>
              <p>{selfModelSignals?.summary?.current_signal || summary?.development?.current_self_model_signal || 'No active self-model signal'}</p>
              <p>
                {selfModelSignals?.summary?.uncertain_count || 0} uncertain · {selfModelSignals?.summary?.corrected_count || 0} corrected · {selfModelSignals?.summary?.superseded_count || 0} superseded
              </p>
            </div>
            <div className="compact-metric">
              <span>Reflection Signals</span>
              <strong>{(reflectionSignals?.summary?.active_count || 0) + (reflectionSignals?.summary?.integrating_count || 0) + (reflectionSignals?.summary?.settled_count || 0) || summary?.development?.reflection_signal_count || 0}</strong>
              <p>{reflectionSignals?.summary?.current_signal || summary?.development?.current_reflection_signal || 'No active reflection signal'}</p>
              <p>
                {reflectionSignals?.summary?.integrating_count || 0} integrating · {reflectionSignals?.summary?.settled_count || 0} settled · {reflectionSignals?.summary?.superseded_count || 0} superseded
              </p>
            </div>
            <div className="compact-metric">
              <span>Recurring Patterns</span>
              <strong>{(temporalRecurrenceSignals?.summary?.active_count || 0) + (temporalRecurrenceSignals?.summary?.softening_count || 0)}</strong>
              <p>{temporalRecurrenceSignals?.summary?.current_signal || 'No active temporal recurrence signal'}</p>
              <p>
                {temporalRecurrenceSignals?.summary?.softening_count || 0} softening · {temporalRecurrenceSignals?.summary?.stale_count || 0} stale · {temporalRecurrenceSignals?.summary?.superseded_count || 0} superseded
              </p>
            </div>
            <div className="compact-metric">
              <span>Open Loops</span>
              <strong>{(openLoopSignals?.summary?.open_count || 0) + (openLoopSignals?.summary?.softening_count || 0) + (openLoopSignals?.summary?.closed_count || 0)}</strong>
              <p>{openLoopSignals?.summary?.current_signal || 'No active open loop'}</p>
              <p>
                {openLoopSignals?.summary?.open_count || 0} open · {openLoopSignals?.summary?.softening_count || 0} softening · {openLoopSignals?.summary?.closed_count || 0} closed
              </p>
              <p>
                {(openLoopSignals?.summary?.ready_count || 0)} high-readiness · current closure {openLoopSignals?.summary?.current_closure_confidence || 'low'}
              </p>
            </div>
            <div className="compact-metric">
              <span>Internal Opposition</span>
              <strong>{(internalOppositionSignals?.summary?.active_count || 0) + (internalOppositionSignals?.summary?.softening_count || 0)}</strong>
              <p>{internalOppositionSignals?.summary?.current_signal || 'No active internal opposition signal'}</p>
              <p>
                {internalOppositionSignals?.summary?.softening_count || 0} softening · {internalOppositionSignals?.summary?.stale_count || 0} stale · {internalOppositionSignals?.summary?.superseded_count || 0} superseded
              </p>
            </div>
            <div className="compact-metric">
              <span>Self Review Need</span>
              <strong>{(selfReviewSignals?.summary?.active_count || 0) + (selfReviewSignals?.summary?.softening_count || 0)}</strong>
              <p>{selfReviewSignals?.summary?.current_signal || 'No active self-review signal'}</p>
              <p>
                {selfReviewSignals?.summary?.softening_count || 0} softening · {selfReviewSignals?.summary?.stale_count || 0} stale · {selfReviewSignals?.summary?.superseded_count || 0} superseded
              </p>
            </div>
            <div className="compact-metric">
              <span>Self Review Briefs</span>
              <strong>{(selfReviewRecords?.summary?.fresh_count || 0) + (selfReviewRecords?.summary?.active_count || 0) + (selfReviewRecords?.summary?.fading_count || 0)}</strong>
              <p>{selfReviewRecords?.summary?.current_record || 'No active self-review brief'}</p>
              <p>
                {selfReviewRecords?.summary?.fresh_count || 0} fresh · {selfReviewRecords?.summary?.active_count || 0} active · {selfReviewRecords?.summary?.fading_count || 0} fading
              </p>
              <p>
                current type {selfReviewRecords?.summary?.current_review_type || 'none'}
              </p>
            </div>
            <div className="compact-metric">
              <span>Self Review Runs</span>
              <strong>{(selfReviewRuns?.summary?.fresh_count || 0) + (selfReviewRuns?.summary?.active_count || 0) + (selfReviewRuns?.summary?.fading_count || 0)}</strong>
              <p>{selfReviewRuns?.summary?.current_run || 'No active self-review snapshot'}</p>
              <p>
                {selfReviewRuns?.summary?.fresh_count || 0} fresh · {selfReviewRuns?.summary?.active_count || 0} active · {selfReviewRuns?.summary?.fading_count || 0} fading
              </p>
              <p>
                focus {selfReviewRuns?.summary?.current_review_focus || 'none'}
              </p>
            </div>
            <div className="compact-metric">
              <span>Review Outcomes</span>
              <strong>{(selfReviewOutcomes?.summary?.fresh_count || 0) + (selfReviewOutcomes?.summary?.active_count || 0) + (selfReviewOutcomes?.summary?.fading_count || 0)}</strong>
              <p>{selfReviewOutcomes?.summary?.current_outcome || 'No active self-review outcome'}</p>
              <p>
                {selfReviewOutcomes?.summary?.fresh_count || 0} fresh · {selfReviewOutcomes?.summary?.active_count || 0} active · {selfReviewOutcomes?.summary?.fading_count || 0} fading
              </p>
              <p>
                type {selfReviewOutcomes?.summary?.current_outcome_type || 'none'}
              </p>
            </div>
            <div className="compact-metric">
              <span>Review Cadence</span>
              <strong>{(selfReviewCadenceSignals?.summary?.active_count || 0) + (selfReviewCadenceSignals?.summary?.softening_count || 0)}</strong>
              <p>{selfReviewCadenceSignals?.summary?.current_signal || 'No active self-review cadence signal'}</p>
              <p>
                {selfReviewCadenceSignals?.summary?.softening_count || 0} softening · {selfReviewCadenceSignals?.summary?.stale_count || 0} stale · {selfReviewCadenceSignals?.summary?.superseded_count || 0} superseded
              </p>
              <p>
                state {selfReviewCadenceSignals?.summary?.current_cadence_state || 'none'}
              </p>
            </div>
            <div className="compact-metric">
              <span>Lifecycle</span>
              <strong>
                {developmentFocuses?.summary?.stale_count || 0} stale · {developmentFocuses?.summary?.completed_count || 0} done
              </strong>
              <p>{developmentFocuses?.summary?.superseded_count || 0} superseded focus records retained for continuity.</p>
              <p>{selfModelSignals?.summary?.stale_count || 0} stale self-assessments retained for bounded continuity.</p>
            </div>
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
              {detailRow(data?.development?.operationalPreference, 'Operational Preference', onOpenItem)}
              {detailRow(data?.development?.operationalAlignment, 'Preference Alignment', onOpenItem)}
              {detailRow(data?.development?.growthNote, 'Latest Growth Note', onOpenItem)}
              {detailRow(data?.development?.reflectiveSelection, 'Latest Reflective Selection', onOpenItem)}
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

            <div className="mc-inline-group">
              {subsectionHeader('Pressure And Integration', 'Friction, Limits, And Slow Settling')}
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
              {openLoopSignals.items.length > 0 ? subsectionHeader('Open Loops', 'What Remains Unresolved') : null}
              {openLoopSignals.items.slice(0, 3).map((item) => openLoopSignalRow(item, onOpenItem))}
              {internalOppositionSignals.items.length > 0 ? subsectionHeader('Internal Opposition', 'What Should Be Challenged Internally') : null}
              {internalOppositionSignals.items.slice(0, 3).map((item) => internalOppositionSignalRow(item, onOpenItem))}
              {(selfReviewSignals.items.length > 0 || selfReviewRecords.items.length > 0 || selfReviewRuns.items.length > 0 || selfReviewOutcomes.items.length > 0 || selfReviewCadenceSignals.items.length > 0) ? (
                <div className="mc-inline-group mc-inline-group-flush">
                  {subsectionHeader('Self Review', 'Bounded Review Flow')}
                  {selfReviewFlowSummary({
                    signals: selfReviewSignals,
                    records: selfReviewRecords,
                    runs: selfReviewRuns,
                    outcomes: selfReviewOutcomes,
                    cadence: selfReviewCadenceSignals,
                  })}
                  {selfReviewSignals.items.length > 0 ? selfReviewStageLabel({ stage: 'Need', count: selfReviewSignals.items.length }) : null}
                  {selfReviewSignals.items.slice(0, 2).map((item) => selfReviewSignalRow(item, onOpenItem))}
                  {selfReviewRecords.items.length > 0 ? selfReviewStageLabel({ stage: 'Brief', count: selfReviewRecords.items.length }) : null}
                  {selfReviewRecords.items.slice(0, 2).map((item) => selfReviewRecordRow(item, onOpenItem))}
                  {selfReviewRuns.items.length > 0 ? selfReviewStageLabel({ stage: 'Snapshot', count: selfReviewRuns.items.length }) : null}
                  {selfReviewRuns.items.slice(0, 2).map((item) => selfReviewRunRow(item, onOpenItem))}
                  {selfReviewOutcomes.items.length > 0 ? selfReviewStageLabel({ stage: 'Outcome', count: selfReviewOutcomes.items.length }) : null}
                  {selfReviewOutcomes.items.slice(0, 2).map((item) => selfReviewOutcomeRow(item, onOpenItem))}
                  {selfReviewCadenceSignals.items.length > 0 ? selfReviewStageLabel({ stage: 'Cadence', count: selfReviewCadenceSignals.items.length }) : null}
                  {selfReviewCadenceSignals.items.slice(0, 2).map((item) => selfReviewCadenceSignalRow(item, onOpenItem))}
                </div>
              ) : null}
            </div>
          </div>
        </article>

        <article className="support-card" id="jarvis-continuity" title={sectionTitleWithMeta({
          source: '/mc/jarvis::continuity',
          fetchedAt: data?.fetchedAt,
          mode: 'snapshot + drilldown',
        })}>
          <div className="panel-header">
            <div>
              <h3>Continuity</h3>
              <p className="muted">Session continuity, relation pull, and promotion-style signals.</p>
            </div>
            <span className="mc-section-hint">Read-only</span>
          </div>
          <div className="compact-grid">
            <div className="compact-metric">
              <span>Session status</span>
              <strong>{summary?.continuity?.session_status || 'unknown'}</strong>
            </div>
            <div className="compact-metric">
              <span>Interaction mode</span>
              <strong>{summary?.continuity?.interaction_mode || 'unknown'}</strong>
            </div>
            <div className="compact-metric">
              <span>Carried Forward</span>
              <strong>{summary?.continuity?.relation_pull || 'unknown'}</strong>
              <p>{carriedForward}</p>
            </div>
            <div className="compact-metric">
              <span>World Model</span>
              <strong>{worldModelSignals?.summary?.active_count || summary?.continuity?.world_model_count || 0}</strong>
              <p>{worldModelSignals?.summary?.current_signal || summary?.continuity?.current_world_model || 'No active world-model signal'}</p>
              <p>
                {worldModelSignals?.summary?.uncertain_count || 0} uncertain · {worldModelSignals?.summary?.corrected_count || 0} corrected · {worldModelSignals?.summary?.stale_count || 0} stale
              </p>
            </div>
            <div className="compact-metric">
              <span>Runtime Awareness</span>
              <strong>{(runtimeAwarenessSignals?.summary?.active_count || 0) + (runtimeAwarenessSignals?.summary?.constrained_count || 0) + (runtimeAwarenessSignals?.summary?.recovered_count || 0) || summary?.continuity?.runtime_awareness_count || 0}</strong>
              <p>{runtimeAwarenessSignals?.summary?.current_signal || summary?.continuity?.current_runtime_awareness || 'No active runtime-awareness signal'}</p>
              <p>
                {runtimeAwarenessSignals?.summary?.constrained_count || 0} constrained · {runtimeAwarenessSignals?.summary?.recovered_count || 0} recovered · {runtimeAwarenessSignals?.summary?.stale_count || 0} stale
              </p>
            </div>
            <div className="compact-metric">
              <span>Machine State</span>
              <strong>{runtimeAwarenessSignals?.summary?.machine_state || 'No machine signal'}</strong>
              <p>{runtimeAwarenessSignals?.summary?.machine_detail || 'No bounded local machine-state signal is active right now.'}</p>
            </div>
            <div className="compact-metric">
              <span>Recent Shift</span>
              <strong>{summary?.continuity?.session_status || 'unknown'}</strong>
              <p>{recentShift}</p>
            </div>
            <div className="compact-metric">
              <span>Witnessed Turns</span>
              <strong>{(witnessSignals?.summary?.fresh_count || 0) + (witnessSignals?.summary?.carried_count || 0)}</strong>
              <p>{witnessSignals?.summary?.current_signal || 'No witnessed development turn'}</p>
              <p>
                {witnessSignals?.summary?.fresh_count || 0} fresh · {witnessSignals?.summary?.carried_count || 0} carried · {witnessSignals?.summary?.fading_count || 0} fading
              </p>
            </div>
          </div>
          <div className="mc-list">
            {integrationCarryOverRow({
              reflectionSummary: reflectionSignals?.summary || {},
              reflectionHistory,
              carriedForward,
              recentShift,
            }, onOpenItem)}
            <div className="mc-inline-group">
              {subsectionHeader('Current Carry-Over', 'What Jarvis Is Still Holding')}
              {detailRow(data?.continuity?.relationState, 'Relation State', onOpenItem)}
              {detailRow(data?.continuity?.promotionSignal, 'Promotion Signal', onOpenItem)}
              {detailRow(data?.continuity?.promotionDecision, 'Promotion Decision', onOpenItem)}
              {worldModelContextRow({
                summary: worldModelSignals?.summary || {},
                currentSignal: worldModelSignals?.summary?.current_signal || summary?.continuity?.current_world_model || 'No active world-model signal',
                uncertainCount: worldModelSignals?.summary?.uncertain_count || 0,
                correctedCount: worldModelSignals?.summary?.corrected_count || 0,
              }, onOpenItem)}
              {worldModelSignals.items.length === 0 ? (
                <div className="mc-empty-state">
                  <strong>No active world-model signal</strong>
                  <p className="muted">Jarvis has not accumulated a bounded situational assumption yet.</p>
                </div>
              ) : worldModelSignals.items.slice(0, 3).map((item) => worldModelSignalRow(item, onOpenItem))}
              {witnessSignals.items.length > 0 ? subsectionHeader('Witnessed Turns', 'Small Bounded Development Milestones') : null}
              {witnessSignals.items.slice(0, 3).map((item) => witnessSignalRow(item, onOpenItem))}
            </div>

            <div className="mc-inline-group">
              {subsectionHeader('Recent Continuity', 'What Most Recently Shifted')}
              {detailRow(data?.continuity?.visibleSession, 'Visible Session Continuity', onOpenItem)}
              {detailRow(data?.continuity?.visibleContinuity, 'Visible Continuity', onOpenItem)}
              {runtimeAwarenessSignals.items.length === 0 ? (
                <div className="mc-empty-state">
                  <strong>No active runtime-awareness signal</strong>
                  <p className="muted">Jarvis has not accumulated a bounded machine/runtime situation signal yet.</p>
                </div>
              ) : runtimeAwarenessSignals.items.slice(0, 3).map((item) => runtimeAwarenessSignalRow(item, onOpenItem))}
              {runtimeAwarenessHistory.length > 0 ? subsectionHeader('Recent Machine State', 'Runtime History') : null}
              {runtimeAwarenessHistory.slice(0, 3).map((item) => runtimeAwarenessHistoryRow(item, onOpenItem))}
            </div>
          </div>
        </article>
      </section>
    </div>
  )
}
