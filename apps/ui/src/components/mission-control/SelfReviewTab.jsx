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

export function SelfReviewTab({ data, onOpenItem }) {
  const selfReviewSignals = data?.development?.selfReviewSignals || { items: [], summary: {} }
  const selfReviewRecords = data?.development?.selfReviewRecords || { items: [], summary: {} }
  const selfReviewRuns = data?.development?.selfReviewRuns || { items: [], summary: {} }
  const selfReviewOutcomes = data?.development?.selfReviewOutcomes || { items: [], summary: {} }
  const selfReviewCadenceSignals = data?.development?.selfReviewCadenceSignals || { items: [], summary: {} }

  return (
    <div className="mc-tab-page">
      {/* Flow pipeline at top */}
      {selfReviewFlowSummary({
        signals: selfReviewSignals,
        records: selfReviewRecords,
        runs: selfReviewRuns,
        outcomes: selfReviewOutcomes,
        cadence: selfReviewCadenceSignals,
      })}

      {/* Review Need Signals */}
      <section className="support-card">
        <div className="panel-header">
          <div><h3>Review Need Signals</h3><p className="muted">Active self-review trigger signals.</p></div>
        </div>
        <div className="mc-list">
          {(selfReviewSignals.items || []).map(item => selfReviewSignalRow(item, onOpenItem))}
          {!(selfReviewSignals.items || []).length && (
            <div className="mc-empty-state"><strong>No active review signals</strong></div>
          )}
        </div>
      </section>

      {/* Review Briefs */}
      <section className="support-card">
        <div className="panel-header">
          <div><h3>Review Briefs</h3><p className="muted">Bounded self-review brief records.</p></div>
        </div>
        <div className="mc-list">
          {(selfReviewRecords.items || []).map(item => selfReviewRecordRow(item, onOpenItem))}
          {!(selfReviewRecords.items || []).length && (
            <div className="mc-empty-state"><strong>No active review briefs</strong></div>
          )}
        </div>
      </section>

      {/* Review Snapshots */}
      <section className="support-card">
        <div className="panel-header">
          <div><h3>Review Snapshots</h3><p className="muted">Bounded self-review run snapshots.</p></div>
        </div>
        <div className="mc-list">
          {(selfReviewRuns.items || []).map(item => selfReviewRunRow(item, onOpenItem))}
          {!(selfReviewRuns.items || []).length && (
            <div className="mc-empty-state"><strong>No active review snapshots</strong></div>
          )}
        </div>
      </section>

      {/* Review Outcomes */}
      <section className="support-card">
        <div className="panel-header">
          <div><h3>Review Outcomes</h3><p className="muted">Bounded self-review outcome records.</p></div>
        </div>
        <div className="mc-list">
          {(selfReviewOutcomes.items || []).map(item => selfReviewOutcomeRow(item, onOpenItem))}
          {!(selfReviewOutcomes.items || []).length && (
            <div className="mc-empty-state"><strong>No active review outcomes</strong></div>
          )}
        </div>
      </section>

      {/* Review Cadence */}
      <section className="support-card">
        <div className="panel-header">
          <div><h3>Review Cadence</h3><p className="muted">Self-review cadence and scheduling signals.</p></div>
        </div>
        <div className="mc-list">
          {(selfReviewCadenceSignals.items || []).map(item => selfReviewCadenceSignalRow(item, onOpenItem))}
          {!(selfReviewCadenceSignals.items || []).length && (
            <div className="mc-empty-state"><strong>No active cadence signals</strong></div>
          )}
        </div>
      </section>
    </div>
  )
}
