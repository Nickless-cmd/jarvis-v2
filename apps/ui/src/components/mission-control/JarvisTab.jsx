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

function embodiedBucketSummary(item) {
  if (!item?.facts) return []
  return [
    ['cpu', item.facts.cpu?.bucket],
    ['memory', item.facts.memory?.bucket],
    ['disk', item.facts.disk?.bucket],
    ['thermal', item.facts.thermal?.bucket],
  ]
    .filter(([, bucket]) => bucket)
    .map(([label, bucket]) => `${label} ${humanizeToken(bucket)}`)
}

function embodiedUsageSummary(item) {
  const usage = item?.seamUsage || {}
  const labels = []
  if (usage.heartbeatContext || usage.heartbeatPromptGrounding) labels.push('heartbeat')
  if (usage.runtimeSelfModel) labels.push('self-model')
  if (usage.missionControlRuntimeTruth) labels.push('MC truth')
  return labels.join(' · ')
}

function loopRuntimeCounts(item) {
  const summary = item?.summary || {}
  return [
    ['active', summary.activeCount || 0],
    ['standby', summary.standbyCount || 0],
    ['resumed', summary.resumedCount || 0],
    ['closed', summary.closedCount || 0],
  ]
}

function loopRuntimeCountSummary(item) {
  return loopRuntimeCounts(item)
    .filter(([, count]) => count > 0)
    .map(([label, count]) => `${count} ${label}`)
}

function loopRuntimeUsageSummary(item) {
  const usage = item?.seamUsage || {}
  const labels = []
  if (usage.heartbeatContext || usage.heartbeatPromptGrounding) labels.push('heartbeat')
  if (usage.runtimeSelfModel) labels.push('self-model')
  if (usage.missionControlRuntimeTruth) labels.push('MC truth')
  return labels.join(' · ')
}

function idleConsolidationBoundarySummary(item) {
  return String(item?.boundary || '')
    .split('-')
    .filter((token) => token && token !== 'not')
    .join(' / ')
}

function dreamArticulationBoundarySummary(item) {
  const parts = []
  if (item?.truth) parts.push(humanizeToken(item.truth))
  if (item?.visibility) parts.push(humanizeToken(item.visibility))
  return parts.join(' / ')
}

function promptEvolutionBoundarySummary(item) {
  const parts = []
  if (item?.proposalMode) parts.push(humanizeToken(item.proposalMode))
  if (item?.visibility) parts.push(humanizeToken(item.visibility))
  return parts.join(' / ')
}

function affectiveMetaUsageSummary(item) {
  const usage = item?.seamUsage || {}
  const labels = []
  if (usage.heartbeatContext || usage.heartbeatPromptGrounding) labels.push('heartbeat')
  if (usage.runtimeSelfModel) labels.push('self-model')
  if (usage.missionControlRuntimeTruth) labels.push('MC truth')
  return labels.join(' · ')
}

function affectiveMetaBoundarySummary(item) {
  const parts = []
  if (item?.authority) parts.push(humanizeToken(item.authority))
  if (item?.visibility) parts.push(humanizeToken(item.visibility))
  return parts.join(' / ')
}

function epistemicRuntimeUsageSummary(item) {
  const usage = item?.seamUsage || {}
  const labels = []
  if (usage.heartbeatContext || usage.heartbeatPromptGrounding) labels.push('heartbeat')
  if (usage.runtimeSelfModel) labels.push('self-model')
  if (usage.missionControlRuntimeTruth) labels.push('MC truth')
  return labels.join(' · ')
}

function epistemicRuntimeBoundarySummary(item) {
  const parts = []
  if (item?.authority) parts.push(humanizeToken(item.authority))
  if (item?.visibility) parts.push(humanizeToken(item.visibility))
  return parts.join(' / ')
}

function subagentEcologyUsageSummary(item) {
  const usage = item?.seamUsage || {}
  const labels = []
  if (usage.heartbeatContext || usage.heartbeatPromptGrounding) labels.push('heartbeat')
  if (usage.runtimeSelfModel) labels.push('self-model')
  if (usage.missionControlRuntimeTruth) labels.push('MC truth')
  return labels.join(' · ')
}

function subagentEcologyBoundarySummary(item) {
  const parts = []
  if (item?.authority) parts.push(humanizeToken(item.authority))
  if (item?.visibility) parts.push(humanizeToken(item.visibility))
  if (item?.toolAccess) parts.push(`tool ${humanizeToken(item.toolAccess)}`)
  return parts.join(' / ')
}

function subagentEcologyCountSummary(item) {
  const summary = item?.summary || {}
  return [
    ['active', summary.activeCount || 0],
    ['cooling', summary.coolingCount || 0],
    ['blocked', summary.blockedCount || 0],
    ['idle', summary.idleCount || 0],
  ]
    .filter(([, count]) => count > 0)
    .map(([label, count]) => `${count} ${label}`)
}

function councilRuntimeUsageSummary(item) {
  const usage = item?.seamUsage || {}
  const labels = []
  if (usage.heartbeatContext || usage.heartbeatPromptGrounding) labels.push('heartbeat')
  if (usage.runtimeSelfModel) labels.push('self-model')
  if (usage.missionControlRuntimeTruth) labels.push('MC truth')
  return labels.join(' · ')
}

function councilRuntimeBoundarySummary(item) {
  const parts = []
  if (item?.authority) parts.push(humanizeToken(item.authority))
  if (item?.visibility) parts.push(humanizeToken(item.visibility))
  if (item?.toolAccess) parts.push(`tool ${humanizeToken(item.toolAccess)}`)
  return parts.join(' / ')
}

function councilRuntimeRoleSummary(item) {
  return (item?.participatingRoles || []).map((role) => humanizeToken(role)).filter(Boolean)
}

function cadenceProducer(item, name) {
  return (item?.producers || []).find((producer) => producer.name === name) || null
}

function cadenceProducerLabel(item, fallback = 'idle') {
  const status = item?.lastTickStatus?.status || ''
  return humanizeToken(status || fallback) || fallback
}

function cadenceProducerReason(item) {
  return humanizeToken(item?.lastTickStatus?.reason || '')
}

function metabolicHeartbeatSummary(summary = {}) {
  const parts = []
  if (summary.idle_consolidation) {
    parts.push(`sleep ${humanizeToken(summary.idle_consolidation)}`)
  }
  if (summary.dream_articulation) {
    parts.push(`dream ${humanizeToken(summary.dream_articulation)}`)
  }
  return parts.join(' · ')
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

function embodiedStateRow(item, onOpen) {
  if (!item || item.state === 'unknown') return null
  const bucketLine = embodiedBucketSummary(item).join(' · ')
  const usageLine = embodiedUsageSummary(item)
  const detailText = [
    item.summary,
    bucketLine,
    usageLine ? `used by ${usageLine}` : '',
  ].filter(Boolean).join(' · ')

  return (
    <button
      className="mc-list-row mc-list-row-subtle"
      onClick={() => onOpen('Embodied State', item)}
      title={sectionTitleWithMeta({
        source: item.source,
        fetchedAt: item.createdAt,
        mode: 'embodied runtime detail',
      })}
    >
      <div>
        <strong>Embodied State</strong>
        <span>{detailText || 'Inspect embodied runtime detail'}</span>
      </div>
      <div className="mc-row-meta">
        <StatusPill status={item.state} />
        {item.strainLevel ? <small>{`strain ${humanizeToken(item.strainLevel)}`}</small> : null}
        {item.recoveryState && item.recoveryState !== 'steady' ? <small>{`recovery ${humanizeToken(item.recoveryState)}`}</small> : null}
        {item.createdAt ? <small>{formatFreshness(item.createdAt)}</small> : null}
        <ChevronRight size={14} />
      </div>
    </button>
  )
}

function loopRuntimeRow(item, onOpen) {
  const summary = item?.summary || {}
  if (!item || !summary.loopCount) return null
  const countLine = loopRuntimeCountSummary(item).join(' · ')
  const usageLine = loopRuntimeUsageSummary(item)
  const detailText = [
    summary.currentLoop && summary.currentLoop !== 'No active runtime loop'
      ? `${summary.currentLoop} (${humanizeToken(summary.currentStatus) || 'unknown'})`
      : '',
    countLine,
    usageLine ? `used by ${usageLine}` : '',
  ].filter(Boolean).join(' · ')

  return (
    <button
      className="mc-list-row mc-list-row-subtle"
      onClick={() => onOpen('Loop Runtime', item)}
      title={sectionTitleWithMeta({
        source: item.source,
        fetchedAt: item.createdAt,
        mode: 'loop runtime detail',
      })}
    >
      <div>
        <strong>Loop Runtime</strong>
        <span>{detailText || 'Inspect bounded loop runtime detail'}</span>
      </div>
      <div className="mc-row-meta">
        <StatusPill status={summary.currentStatus || 'none'} />
        {summary.currentKind && summary.currentKind !== 'none' ? <small>{humanizeToken(summary.currentKind)}</small> : null}
        {item.createdAt ? <small>{formatFreshness(item.createdAt)}</small> : null}
        <ChevronRight size={14} />
      </div>
    </button>
  )
}

function loopRuntimeItemRow(item, onOpen) {
  if (!item?.loopId) return null
  const detailText = [
    item.summary,
    item.loopKind ? humanizeToken(item.loopKind) : '',
    item.reasonCode ? humanizeToken(item.reasonCode) : '',
  ].filter(Boolean).join(' · ')

  return (
    <button
      className="mc-list-row mc-list-row-subtle"
      key={item.loopId}
      onClick={() => onOpen(item.title || 'Runtime Loop', item)}
      title={sectionTitleWithMeta({
        source: item.source,
        fetchedAt: item.updatedAt,
        mode: 'loop item detail',
      })}
    >
      <div>
        <strong>{item.title || 'Runtime Loop'}</strong>
        <span>{detailText || 'Inspect loop runtime detail'}</span>
      </div>
      <div className="mc-row-meta">
        <StatusPill status={item.runtimeStatus || 'unknown'} />
        {item.updatedAt ? <small>{formatFreshness(item.updatedAt)}</small> : null}
        <ChevronRight size={14} />
      </div>
    </button>
  )
}

function idleConsolidationRow(item, onOpen) {
  const summary = item?.summary || {}
  const lastResult = item?.lastResult || {}
  if (!item || (!item.active && !item.lastRunAt && !summary.latestRecordId)) return null
  const detailText = [
    summary.latestSummary,
    summary.sourceInputCount ? `${summary.sourceInputCount} source input${summary.sourceInputCount === 1 ? '' : 's'}` : '',
    lastResult.reason ? humanizeToken(lastResult.reason) : '',
  ].filter(Boolean).join(' · ')

  return (
    <button
      className="mc-list-row mc-list-row-subtle"
      onClick={() => onOpen('Idle Consolidation', item)}
      title={sectionTitleWithMeta({
        source: item.source,
        fetchedAt: item.createdAt,
        mode: 'idle consolidation detail',
      })}
    >
      <div>
        <strong>Idle Consolidation</strong>
        <span>{detailText || 'Inspect bounded idle consolidation detail'}</span>
      </div>
      <div className="mc-row-meta">
        <StatusPill status={summary.lastState || 'idle'} />
        {summary.lastOutputKind ? <small>{humanizeToken(summary.lastOutputKind)}</small> : null}
        {item.createdAt ? <small>{formatFreshness(item.createdAt)}</small> : null}
        <ChevronRight size={14} />
      </div>
    </button>
  )
}

function dreamArticulationRow(item, onOpen) {
  const summary = item?.summary || {}
  const lastResult = item?.lastResult || {}
  const latestArtifact = item?.latestArtifact || {}
  if (!item || (!item.active && !item.lastRunAt && !summary.latestSignalId)) return null
  const detailText = [
    latestArtifact.title || lastResult.signalSummary || summary.latestSummary,
    summary.sourceInputCount ? `${summary.sourceInputCount} source input${summary.sourceInputCount === 1 ? '' : 's'}` : '',
    lastResult.reason ? humanizeToken(lastResult.reason) : '',
  ].filter(Boolean).join(' · ')

  return (
    <button
      className="mc-list-row mc-list-row-subtle"
      onClick={() => onOpen('Dream Articulation', item)}
      title={sectionTitleWithMeta({
        source: item.source,
        fetchedAt: item.createdAt,
        mode: 'dream articulation detail',
      })}
    >
      <div>
        <strong>Dream Articulation</strong>
        <span>{detailText || 'Inspect bounded dream articulation detail'}</span>
      </div>
      <div className="mc-row-meta">
        <StatusPill status={summary.lastState || 'idle'} />
        {item.truth ? <small>{humanizeToken(item.truth)}</small> : null}
        {item.visibility ? <small>{humanizeToken(item.visibility)}</small> : null}
        {summary.lastOutputKind ? <small>{humanizeToken(summary.lastOutputKind)}</small> : null}
        {item.createdAt ? <small>{formatFreshness(item.createdAt)}</small> : null}
        <ChevronRight size={14} />
      </div>
    </button>
  )
}

function promptEvolutionRow(item, onOpen) {
  const summary = item?.summary || {}
  const lastResult = item?.lastResult || {}
  const latestProposal = item?.latestProposal || {}
  if (!item || (!item.active && !item.lastRunAt && !summary.latestProposalId)) return null
  const detailText = [
    latestProposal.summary || lastResult.proposalSummary || summary.latestSummary,
    summary.latestTargetAsset && summary.latestTargetAsset !== 'none'
      ? `target ${summary.latestTargetAsset}`
      : '',
    summary.sourceInputCount ? `${summary.sourceInputCount} source input${summary.sourceInputCount === 1 ? '' : 's'}` : '',
    lastResult.reason ? humanizeToken(lastResult.reason) : '',
  ].filter(Boolean).join(' · ')

  return (
    <button
      className="mc-list-row mc-list-row-subtle"
      onClick={() => onOpen('Prompt Evolution', item)}
      title={sectionTitleWithMeta({
        source: item.source,
        fetchedAt: item.createdAt,
        mode: 'prompt evolution detail',
      })}
    >
      <div>
        <strong>Prompt Evolution</strong>
        <span>{detailText || 'Inspect bounded prompt evolution detail'}</span>
      </div>
      <div className="mc-row-meta">
        <StatusPill status={summary.lastState || 'idle'} />
        {summary.latestTargetAsset && summary.latestTargetAsset !== 'none' ? <small>{summary.latestTargetAsset}</small> : null}
        {item.proposalMode ? <small>{humanizeToken(item.proposalMode)}</small> : null}
        {item.createdAt ? <small>{formatFreshness(item.createdAt)}</small> : null}
        <ChevronRight size={14} />
      </div>
    </button>
  )
}

function affectiveMetaStateRow(item, onOpen) {
  if (!item || !item.state || item.state === 'unknown') return null
  const detailText = [
    item.summary,
    item.bearing ? `bearing ${humanizeToken(item.bearing)}` : '',
    item.monitoringMode ? `mode ${humanizeToken(item.monitoringMode)}` : '',
    item.reflectiveLoad ? `load ${humanizeToken(item.reflectiveLoad)}` : '',
  ].filter(Boolean).join(' · ')

  return (
    <button
      className="mc-list-row mc-list-row-subtle"
      onClick={() => onOpen('Affective Meta State', item)}
      title={sectionTitleWithMeta({
        source: item.source,
        fetchedAt: item.createdAt,
        mode: 'affective/meta runtime detail',
      })}
    >
      <div>
        <strong>Affective Meta State</strong>
        <span>{detailText || 'Inspect affective/meta runtime detail'}</span>
      </div>
      <div className="mc-row-meta">
        <StatusPill status={item.state} />
        {item.bearing ? <small>{humanizeToken(item.bearing)}</small> : null}
        {item.createdAt ? <small>{formatFreshness(item.createdAt)}</small> : null}
        <ChevronRight size={14} />
      </div>
    </button>
  )
}

function epistemicRuntimeStateRow(item, onOpen) {
  if (!item || !item.wrongnessState || item.wrongnessState === 'clear') return null
  const detailText = [
    item.summary,
    item.regretSignal && item.regretSignal !== 'none' ? `regret ${humanizeToken(item.regretSignal)}` : '',
    item.counterfactualMode && item.counterfactualMode !== 'none' ? `counterfactual ${humanizeToken(item.counterfactualMode)}` : '',
    item.counterfactualHint && item.counterfactualHint !== 'none' ? humanizeToken(item.counterfactualHint) : '',
  ].filter(Boolean).join(' · ')

  return (
    <button
      className="mc-list-row mc-list-row-subtle"
      onClick={() => onOpen('Epistemic Runtime State', item)}
      title={sectionTitleWithMeta({
        source: item.source,
        fetchedAt: item.createdAt,
        mode: 'epistemic runtime detail',
      })}
    >
      <div>
        <strong>Epistemic Runtime State</strong>
        <span>{detailText || 'Inspect epistemic runtime detail'}</span>
      </div>
      <div className="mc-row-meta">
        <StatusPill status={item.wrongnessState} />
        {item.confidence ? <small>{humanizeToken(item.confidence)}</small> : null}
        {item.createdAt ? <small>{formatFreshness(item.createdAt)}</small> : null}
        <ChevronRight size={14} />
      </div>
    </button>
  )
}

function subagentEcologyRow(item, onOpen) {
  const summary = item?.summary || {}
  if (!item || !(item.roles || []).length) return null
  const detailText = [
    item.summaryText,
    summary.lastActiveRoleName && summary.lastActiveRoleName !== 'none'
      ? `last ${humanizeToken(summary.lastActiveRoleName)}`
      : '',
    summary.lastActivationReason && summary.lastActivationReason !== 'none'
      ? humanizeToken(summary.lastActivationReason)
      : '',
  ].filter(Boolean).join(' · ')

  return (
    <button
      className="mc-list-row mc-list-row-subtle"
      onClick={() => onOpen('Subagent Ecology', item)}
      title={sectionTitleWithMeta({
        source: item.source,
        fetchedAt: item.createdAt,
        mode: 'subagent ecology detail',
      })}
    >
      <div>
        <strong>Subagent Ecology</strong>
        <span>{detailText || 'Inspect bounded internal helper-role ecology'}</span>
      </div>
      <div className="mc-row-meta">
        <StatusPill status={summary.lastActiveRoleStatus || 'idle'} />
        <small>{`${summary.activeCount || 0} active`}</small>
        {item.createdAt ? <small>{formatFreshness(item.createdAt)}</small> : null}
        <ChevronRight size={14} />
      </div>
    </button>
  )
}

function subagentRoleRow(item, onOpen) {
  if (!item?.roleName) return null
  const detailText = [
    humanizeToken(item.roleKind),
    item.activationReason ? humanizeToken(item.activationReason) : '',
    item.influenceScope ? `${humanizeToken(item.influenceScope)} influence` : '',
  ].filter(Boolean).join(' · ')

  return (
    <button
      className="mc-list-row mc-list-row-subtle"
      key={item.roleName}
      onClick={() => onOpen(humanizeToken(item.roleName) || 'Subagent Role', item)}
      title={sectionTitleWithMeta({
        source: item.source,
        fetchedAt: item.lastActivationAt,
        mode: 'subagent role detail',
      })}
    >
      <div>
        <strong>{humanizeToken(item.roleName) || 'Subagent Role'}</strong>
        <span>{detailText || 'Inspect bounded internal role detail'}</span>
      </div>
      <div className="mc-row-meta">
        <StatusPill status={item.currentStatus || 'idle'} />
        {item.toolAccess ? <small>{`tool ${humanizeToken(item.toolAccess)}`}</small> : null}
        {item.lastActivationAt ? <small>{formatFreshness(item.lastActivationAt)}</small> : null}
        <ChevronRight size={14} />
      </div>
    </button>
  )
}

function councilRuntimeRow(item, onOpen) {
  if (!item || !(item.participatingRoles || []).length) return null
  const detailText = [
    item.summary,
    item.recommendation ? `recommend ${humanizeToken(item.recommendation)}` : '',
    item.recommendationReason ? humanizeToken(item.recommendationReason) : '',
  ].filter(Boolean).join(' · ')

  return (
    <button
      className="mc-list-row mc-list-row-subtle"
      onClick={() => onOpen('Council Runtime', item)}
      title={sectionTitleWithMeta({
        source: item.source,
        fetchedAt: item.createdAt,
        mode: 'council runtime detail',
      })}
    >
      <div>
        <strong>Council Runtime</strong>
        <span>{detailText || 'Inspect bounded internal council runtime detail'}</span>
      </div>
      <div className="mc-row-meta">
        <StatusPill status={item.councilState || 'quiet'} />
        {item.divergenceLevel ? <small>{`${humanizeToken(item.divergenceLevel)} divergence`}</small> : null}
        {item.createdAt ? <small>{formatFreshness(item.createdAt)}</small> : null}
        <ChevronRight size={14} />
      </div>
    </button>
  )
}

function councilRolePositionRow(item, onOpen) {
  if (!item?.roleName) return null
  const detailText = [
    item.roleKind ? humanizeToken(item.roleKind) : '',
    item.position ? `${humanizeToken(item.position)} position` : '',
    item.activationReason ? humanizeToken(item.activationReason) : '',
  ].filter(Boolean).join(' · ')

  return (
    <button
      className="mc-list-row mc-list-row-subtle"
      key={`${item.roleName}-${item.position}`}
      onClick={() => onOpen(`${humanizeToken(item.roleName) || 'Council Role'} Position`, item)}
      title={sectionTitleWithMeta({
        source: item.source,
        fetchedAt: item.createdAt,
        mode: 'council role position detail',
      })}
    >
      <div>
        <strong>{humanizeToken(item.roleName) || 'Council Role'}</strong>
        <span>{detailText || 'Inspect bounded council role position detail'}</span>
      </div>
      <div className="mc-row-meta">
        <StatusPill status={item.status || 'idle'} />
        {item.position ? <small>{humanizeToken(item.position)}</small> : null}
        {item.toolAccess ? <small>{`tool ${humanizeToken(item.toolAccess)}`}</small> : null}
        <ChevronRight size={14} />
      </div>
    </button>
  )
}

function candidateRow(item, onOpen) {
  const evidenceLabel = item.evidenceClass
    ? item.evidenceClass.replace(/_/g, ' ')
    : (item.sourceKind || '')
  const applyLabel = item.applyReadiness ? `apply ${item.applyReadiness}` : ''
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
        {applyLabel ? <small>{applyLabel}</small> : null}
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

export function JarvisTab({ data, onOpenItem, onHeartbeatTick, heartbeatBusy = false, subTab = 'jarvis-core' }) {
  const summary = data?.summary || {}
  const contract = data?.contract || {}
  const heartbeat = data?.heartbeat || {}
  const heartbeatState = heartbeat?.state || {}
  const heartbeatPolicy = heartbeat?.policy || {}
  const heartbeatTicks = heartbeat?.recentTicks || []
  const heartbeatEvents = heartbeat?.recentEvents || []
  const heartbeatMetabolicSummary = metabolicHeartbeatSummary(summary?.heartbeat || {})
  const embodiedState = data?.embodiedState || heartbeat?.embodiedState || {}
  const hasEmbodiedState = Boolean(embodiedState?.state && embodiedState.state !== 'unknown')
  const embodiedBuckets = embodiedBucketSummary(embodiedState)
  const embodiedUsage = embodiedUsageSummary(embodiedState)
  const loopRuntime = data?.loopRuntime || heartbeat?.loopRuntime || data?.runtimeSelfModel?.loop_runtime || {}
  const loopRuntimeSummary = loopRuntime?.summary || {}
  const hasLoopRuntime = Boolean(loopRuntimeSummary.loopCount || loopRuntime?.active)
  const loopRuntimeCounts = loopRuntimeCountSummary(loopRuntime)
  const loopRuntimeUsage = loopRuntimeUsageSummary(loopRuntime)
  const visibleLoopRuntimeItems = (loopRuntime?.items || []).slice(0, 3)
  const idleConsolidation = data?.idleConsolidation || heartbeat?.idleConsolidation || data?.runtimeSelfModel?.idle_consolidation || {}
  const idleConsolidationSummary = idleConsolidation?.summary || {}
  const idleConsolidationLastResult = idleConsolidation?.lastResult || {}
  const hasIdleConsolidation = Boolean(
    idleConsolidation?.active ||
    idleConsolidation?.lastRunAt ||
    idleConsolidationSummary?.latestRecordId,
  )
  const idleConsolidationBoundary = idleConsolidationBoundarySummary(idleConsolidation)
  const dreamArticulation = data?.dreamArticulation || heartbeat?.dreamArticulation || data?.runtimeSelfModel?.dream_articulation || {}
  const dreamArticulationSummary = dreamArticulation?.summary || {}
  const dreamArticulationLastResult = dreamArticulation?.lastResult || {}
  const dreamArticulationLatestArtifact = dreamArticulation?.latestArtifact || {}
  const hasDreamArticulation = Boolean(
    dreamArticulation?.active ||
    dreamArticulation?.lastRunAt ||
    dreamArticulationSummary?.latestSignalId,
  )
  const dreamArticulationBoundary = dreamArticulationBoundarySummary(dreamArticulation)
  const promptEvolution = data?.promptEvolution || heartbeat?.promptEvolution || data?.development?.promptEvolution || data?.runtimeSelfModel?.prompt_evolution || {}
  const promptEvolutionSummary = promptEvolution?.summary || {}
  const promptEvolutionLastResult = promptEvolution?.lastResult || {}
  const promptEvolutionLatestProposal = promptEvolution?.latestProposal || {}
  const hasPromptEvolution = Boolean(
    promptEvolution?.active ||
    promptEvolution?.lastRunAt ||
    promptEvolutionSummary?.latestProposalId,
  )
  const promptEvolutionBoundary = promptEvolutionBoundarySummary(promptEvolution)
  const affectiveMetaState = data?.affectiveMetaState || heartbeat?.affectiveMetaState || data?.development?.affectiveMetaState || data?.runtimeSelfModel?.affective_meta_state || {}
  const hasAffectiveMetaState = Boolean(affectiveMetaState?.state && affectiveMetaState.state !== 'unknown')
  const affectiveMetaUsage = affectiveMetaUsageSummary(affectiveMetaState)
  const affectiveMetaBoundary = affectiveMetaBoundarySummary(affectiveMetaState)
  const epistemicRuntimeState = data?.epistemicRuntimeState || heartbeat?.epistemicRuntimeState || data?.development?.epistemicRuntimeState || data?.runtimeSelfModel?.epistemic_runtime_state || {}
  const hasEpistemicRuntimeState = Boolean(
    (epistemicRuntimeState?.wrongnessState && epistemicRuntimeState.wrongnessState !== 'clear') ||
    (epistemicRuntimeState?.regretSignal && epistemicRuntimeState.regretSignal !== 'none') ||
    (epistemicRuntimeState?.counterfactualMode && epistemicRuntimeState.counterfactualMode !== 'none'),
  )
  const epistemicRuntimeUsage = epistemicRuntimeUsageSummary(epistemicRuntimeState)
  const epistemicRuntimeBoundary = epistemicRuntimeBoundarySummary(epistemicRuntimeState)
  const subagentEcology = data?.subagentEcology || heartbeat?.subagentEcology || data?.development?.subagentEcology || data?.runtimeSelfModel?.subagent_ecology || {}
  const subagentEcologySummary = subagentEcology?.summary || {}
  const hasSubagentEcology = Boolean(subagentEcologySummary.roleCount || (subagentEcology?.roles || []).length)
  const subagentEcologyUsage = subagentEcologyUsageSummary(subagentEcology)
  const subagentEcologyBoundary = subagentEcologyBoundarySummary(subagentEcology)
  const subagentEcologyCounts = subagentEcologyCountSummary(subagentEcology)
  const visibleSubagentRoles = (subagentEcology?.roles || []).slice(0, 3)
  const councilRuntime = data?.councilRuntime || heartbeat?.councilRuntime || data?.development?.councilRuntime || data?.runtimeSelfModel?.council_runtime || {}
  const hasCouncilRuntime = Boolean((councilRuntime?.participatingRoles || []).length || councilRuntime?.recommendation || councilRuntime?.councilState)
  const councilRuntimeUsage = councilRuntimeUsageSummary(councilRuntime)
  const councilRuntimeBoundary = councilRuntimeBoundarySummary(councilRuntime)
  const councilRuntimeRoles = councilRuntimeRoleSummary(councilRuntime)
  const visibleCouncilRolePositions = (councilRuntime?.rolePositions || []).slice(0, 3).map((item) => ({
    ...item,
    source: councilRuntime.source || '/mc/council-runtime',
    createdAt: councilRuntime.createdAt,
  }))
  const internalCadence = data?.internalCadence || {}
  const sleepCadence = cadenceProducer(internalCadence, 'sleep_consolidation')
  const dreamCadence = cadenceProducer(internalCadence, 'dream_articulation')
  const promptEvolutionCadence = cadenceProducer(internalCadence, 'prompt_evolution_runtime')
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
  const selfReviewSignals = data?.development?.selfReviewSignals || { items: [], summary: {} }
  const selfReviewRecords = data?.development?.selfReviewRecords || { items: [], summary: {} }
  const selfReviewRuns = data?.development?.selfReviewRuns || { items: [], summary: {} }
  const selfReviewOutcomes = data?.development?.selfReviewOutcomes || { items: [], summary: {} }
  const selfReviewCadenceSignals = data?.development?.selfReviewCadenceSignals || { items: [], summary: {} }
  const dreamHypothesisSignals = data?.development?.dreamHypothesisSignals || { items: [], summary: {} }
  const dreamAdoptionCandidates = data?.development?.dreamAdoptionCandidates || { items: [], summary: {} }
  const dreamInfluenceProposals = data?.development?.dreamInfluenceProposals || { items: [], summary: {} }
  const selfAuthoredPromptProposals = data?.development?.selfAuthoredPromptProposals || { items: [], summary: {} }
  const userUnderstandingSignals = data?.development?.userUnderstandingSignals || { items: [], summary: {} }
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
  const temperamentTendencySignals = data?.development?.temperamentTendencySignals || { items: [], summary: {} }
  const selfNarrativeContinuitySignals = data?.development?.selfNarrativeContinuitySignals || { items: [], summary: {} }
  const metabolismStateSignals = data?.development?.metabolismStateSignals || { items: [], summary: {} }
  const releaseMarkerSignals = data?.development?.releaseMarkerSignals || { items: [], summary: {} }
  const consolidationTargetSignals = data?.development?.consolidationTargetSignals || { items: [], summary: {} }
  const selectiveForgettingCandidates = data?.development?.selectiveForgettingCandidates || { items: [], summary: {} }
  const attachmentTopologySignals = data?.development?.attachmentTopologySignals || { items: [], summary: {} }
  const loyaltyGradientSignals = data?.development?.loyaltyGradientSignals || { items: [], summary: {} }
  const autonomyPressureSignals = data?.development?.autonomyPressureSignals || { items: [], summary: {} }
  const proactiveLoopLifecycleSignals = data?.development?.proactiveLoopLifecycleSignals || { items: [], summary: {} }
  const proactiveQuestionGates = data?.development?.proactiveQuestionGates || { items: [], summary: {} }
  const webchatExecutionPilot = data?.development?.webchatExecutionPilot || { items: [], summary: {} }
  const selfNarrativeSelfModelReviewBridge = data?.development?.selfNarrativeSelfModelReviewBridge || { items: [], summary: {} }
  const executiveContradictionSignals = data?.development?.executiveContradictionSignals || { items: [], summary: {} }
  const privateTemporalPromotionSignals = data?.development?.privateTemporalPromotionSignals || { items: [], summary: {} }
  const chronicleConsolidationSignals = data?.development?.chronicleConsolidationSignals || { items: [], summary: {} }
  const chronicleConsolidationBriefs = data?.development?.chronicleConsolidationBriefs || { items: [], summary: {} }
  const chronicleConsolidationProposals = data?.development?.chronicleConsolidationProposals || { items: [], summary: {} }
  const userMdUpdateProposals = data?.development?.userMdUpdateProposals || { items: [], summary: {} }
  const selfhoodProposals = data?.development?.selfhoodProposals || { items: [], summary: {} }
  const emergentSignals = data?.development?.emergentSignals || { items: [], recentReleased: [], summary: {} }
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
          {heartbeatMetabolicSummary ? <small className="muted">{heartbeatMetabolicSummary}</small> : null}
        </article>
        {hasEmbodiedState ? (
        <article className="mc-stat tone-blue" title={sectionTitleWithMeta({
          source: embodiedState.source || '/mc/embodied-state',
          fetchedAt: embodiedState.createdAt || data?.fetchedAt,
          mode: 'embodied runtime snapshot',
        })}>
          <span>Embodied State</span>
          <strong>{humanizeToken(embodiedState.state) || 'unknown'}</strong>
          <small className="muted">
            {`strain ${humanizeToken(embodiedState.strainLevel) || 'unknown'}`}
            {embodiedState.recoveryState && embodiedState.recoveryState !== 'steady'
              ? ` · recovery ${humanizeToken(embodiedState.recoveryState)}`
              : ''}
            {embodiedState.createdAt ? ` · ${formatFreshness(embodiedState.createdAt)}` : ''}
          </small>
        </article>
        ) : null}
        {hasLoopRuntime ? (
        <article className="mc-stat tone-green" title={sectionTitleWithMeta({
          source: loopRuntime.source || '/mc/loop-runtime',
          fetchedAt: loopRuntime.createdAt || data?.fetchedAt,
          mode: 'loop runtime snapshot',
        })}>
          <span>Loop Runtime</span>
          <strong>{humanizeToken(loopRuntimeSummary.currentStatus) || 'unknown'}</strong>
          <small className="muted">
            {loopRuntimeCounts.join(' · ') || 'No active runtime loops'}
            {loopRuntime.createdAt ? ` · ${formatFreshness(loopRuntime.createdAt)}` : ''}
          </small>
        </article>
        ) : null}
        {hasIdleConsolidation ? (
        <article className="mc-stat tone-blue" title={sectionTitleWithMeta({
          source: idleConsolidation.source || '/mc/idle-consolidation',
          fetchedAt: idleConsolidation.createdAt || data?.fetchedAt,
          mode: 'idle consolidation snapshot',
        })}>
          <span>Idle Consolidation</span>
          <strong>{humanizeToken(idleConsolidationSummary.lastState) || 'idle'}</strong>
          <small className="muted">
            {humanizeToken(idleConsolidationSummary.lastReason) || 'no run yet'}
            {idleConsolidation.createdAt ? ` · ${formatFreshness(idleConsolidation.createdAt)}` : ''}
          </small>
        </article>
        ) : null}
        {(hasDreamArticulation || dreamCadence) ? (
        <article className="mc-stat tone-blue" title={sectionTitleWithMeta({
          source: dreamArticulation.source || internalCadence.source || '/mc/dream-articulation',
          fetchedAt: dreamArticulation.createdAt || internalCadence.lastTickAt || data?.fetchedAt,
          mode: 'dream articulation snapshot',
        })}>
          <span>Dream Articulation</span>
          <strong>{humanizeToken(dreamArticulationSummary.lastState || cadenceProducerLabel(dreamCadence, 'idle')) || 'idle'}</strong>
          <small className="muted">
            {humanizeToken(dreamArticulationSummary.lastReason || dreamCadence?.lastTickStatus?.reason) || 'no run yet'}
            {(dreamArticulation.createdAt || internalCadence.lastTickAt) ? ` · ${formatFreshness(dreamArticulation.createdAt || internalCadence.lastTickAt)}` : ''}
          </small>
        </article>
        ) : null}
        {(hasPromptEvolution || promptEvolutionCadence) ? (
        <article className="mc-stat tone-amber" title={sectionTitleWithMeta({
          source: promptEvolution.source || internalCadence.source || '/mc/prompt-evolution',
          fetchedAt: promptEvolution.createdAt || internalCadence.lastTickAt || data?.fetchedAt,
          mode: 'prompt evolution snapshot',
        })}>
          <span>Prompt Evolution</span>
          <strong>{humanizeToken(promptEvolutionSummary.lastState || cadenceProducerLabel(promptEvolutionCadence, 'idle')) || 'idle'}</strong>
          <small className="muted">
            {(promptEvolutionSummary.latestTargetAsset && promptEvolutionSummary.latestTargetAsset !== 'none'
              ? `${promptEvolutionSummary.latestTargetAsset} · `
              : '') + (humanizeToken(promptEvolutionSummary.lastReason || promptEvolutionCadence?.lastTickStatus?.reason) || 'no run yet')}
            {(promptEvolution.createdAt || internalCadence.lastTickAt) ? ` · ${formatFreshness(promptEvolution.createdAt || internalCadence.lastTickAt)}` : ''}
          </small>
        </article>
        ) : null}
        {hasAffectiveMetaState ? (
        <article className="mc-stat tone-green" title={sectionTitleWithMeta({
          source: affectiveMetaState.source || '/mc/affective-meta-state',
          fetchedAt: affectiveMetaState.createdAt || data?.fetchedAt,
          mode: 'affective/meta runtime snapshot',
        })}>
          <span>Affective Meta</span>
          <strong>{humanizeToken(affectiveMetaState.state) || 'unknown'}</strong>
          <small className="muted">
            {`bearing ${humanizeToken(affectiveMetaState.bearing) || 'unknown'} · mode ${humanizeToken(affectiveMetaState.monitoringMode) || 'unknown'}`}
            {affectiveMetaState.createdAt ? ` · ${formatFreshness(affectiveMetaState.createdAt)}` : ''}
          </small>
        </article>
        ) : null}
        {hasEpistemicRuntimeState ? (
        <article className="mc-stat tone-amber" title={sectionTitleWithMeta({
          source: epistemicRuntimeState.source || '/mc/epistemic-runtime-state',
          fetchedAt: epistemicRuntimeState.createdAt || data?.fetchedAt,
          mode: 'epistemic runtime snapshot',
        })}>
          <span>Epistemic State</span>
          <strong>{humanizeToken(epistemicRuntimeState.wrongnessState) || 'clear'}</strong>
          <small className="muted">
            {`regret ${humanizeToken(epistemicRuntimeState.regretSignal) || 'none'} · counterfactual ${humanizeToken(epistemicRuntimeState.counterfactualMode) || 'none'}`}
            {epistemicRuntimeState.createdAt ? ` · ${formatFreshness(epistemicRuntimeState.createdAt)}` : ''}
          </small>
        </article>
        ) : null}
        {hasSubagentEcology ? (
        <article className="mc-stat tone-green" title={sectionTitleWithMeta({
          source: subagentEcology.source || '/mc/subagent-ecology',
          fetchedAt: subagentEcology.createdAt || data?.fetchedAt,
          mode: 'subagent ecology snapshot',
        })}>
          <span>Subagent Ecology</span>
          <strong>{humanizeToken(subagentEcologySummary.lastActiveRoleName) || 'idle ecology'}</strong>
          <small className="muted">
            {(subagentEcologyCounts.join(' · ') || `${subagentEcologySummary.roleCount || 0} roles`) +
              (subagentEcology.createdAt ? ` · ${formatFreshness(subagentEcology.createdAt)}` : '')}
          </small>
        </article>
        ) : null}
        {hasCouncilRuntime ? (
        <article className="mc-stat tone-amber" title={sectionTitleWithMeta({
          source: councilRuntime.source || '/mc/council-runtime',
          fetchedAt: councilRuntime.createdAt || data?.fetchedAt,
          mode: 'council runtime snapshot',
        })}>
          <span>Council Runtime</span>
          <strong>{humanizeToken(councilRuntime.recommendation || councilRuntime.councilState) || 'quiet council'}</strong>
          <small className="muted">
            {`${councilRuntimeRoles.join(' · ') || 'no roles'} · ${humanizeToken(councilRuntime.divergenceLevel) || 'low'} divergence${councilRuntime.createdAt ? ` · ${formatFreshness(councilRuntime.createdAt)}` : ''}`}
          </small>
        </article>
        ) : null}
      </section>

      <section className="now-section">
        <div className="now-header">
          <h3>Now</h3>
          <p className="muted">What's important right now</p>
        </div>
        <div className="now-grid">
          <div className="now-card">
            <span>Current Focus</span>
            <strong>{developmentFocuses?.summary?.current_focus || developmentFocuses?.items?.[0]?.title || 'No active focus'}</strong>
            <small>{developmentFocuses?.summary?.active_count || 0} active focus{developmentFocuses?.summary?.active_count !== 1 ? 's' : ''}</small>
          </div>
          <div className="now-card">
            <span>Open Loops</span>
            <strong>{openLoopSignals?.summary?.open_count || 0} open{(openLoopSignals?.summary?.softening_count || 0) > 0 ? `, ${openLoopSignals.summary.softening_count} softening` : ''}</strong>
            <small>{(openLoopSignals?.summary?.open_count || 0) + (openLoopSignals?.summary?.softening_count || 0) === 0 ? 'no active loops' : `${openLoopSignals?.summary?.unresolved_count || 0} unresolved`}</small>
          </div>
          <div className="now-card">
            <span>Pressure</span>
            <strong>{privateInitiativeTensionSignals?.items?.[0]?.tension_type?.replace(/-/g, ' ') || privateInitiativeTensionSignals?.summary?.current_tension || 'Low'}</strong>
            <small>{privateInitiativeTensionSignals?.items?.length || 0} tension signal{privateInitiativeTensionSignals?.items?.length !== 1 ? 's' : ''}</small>
          </div>
          <div className="now-card">
            <span>Stability</span>
            <strong>{privateStateSnapshots?.summary?.current_state?.replace(/-/g, ' ') || privateStateSnapshots?.items?.[0]?.state_tone || 'Stable'}</strong>
            <small>{privateStateSnapshots?.summary?.active_count || 0} state signal{privateStateSnapshots?.summary?.active_count !== 1 ? 's' : ''}</small>
          </div>
          <div className={`now-card${recentShift?.label ? ' now-card-highlight' : ' now-card-muted'}`}>
            <span>Recent Shift</span>
            <strong>{recentShift?.label || 'No recent shifts'}</strong>
            <small>{recentShift?.time || ''}</small>
          </div>
          <div className="now-card">
            <span>Confidence</span>
            <strong>{diarySynthesisSignals?.summary?.current_confidence?.replace(/-/g, ' ') || privateStateSnapshots?.items?.[0]?.state_confidence || 'Medium'}</strong>
            <small>{diarySynthesisSignals?.summary?.active_count || 0} synthesis</small>
          </div>
          {(worldModelSignals?.summary?.active_count || 0) > 0 ? (
          <div className="now-card" title="Bounded runtime understanding — not hidden authority">
            <span>World View</span>
            <strong>{worldModelSignals?.summary?.current_signal?.replace(/^World-model signal: /i, '')?.slice(0, 48) || 'Active'}</strong>
            <small>{worldModelSignals?.summary?.active_count} assumption{worldModelSignals?.summary?.active_count !== 1 ? 's' : ''}</small>
          </div>
          ) : null}
        </div>
      </section>

      <section className="now-section">
        <div className="now-header">
          <h3>Runtime Lifecycle</h3>
          <p className="muted">Bounded runtime flow — observe, understand, carry, gate, act</p>
        </div>
        <div className="now-grid">
          {(() => {
            const stateSignal = summary?.state_signal?.mood_tone || ''
            const tensionSignal = privateInitiativeTensionSignals?.summary?.current_signal || ''
            const tensionActive = (privateInitiativeTensionSignals?.summary?.active_count || 0) > 0
            const observeActive = !!stateSignal || tensionActive
            const observeLabel = tensionActive
              ? (tensionSignal.replace(/^Private initiative tension support: /i, '').slice(0, 52) || stateSignal || 'Sensing')
              : (stateSignal || 'Quiet')
            return (
          <div className={`now-card${observeActive ? '' : ' now-card-muted'}`}>
            <span>Observe</span>
            <strong>{observeLabel}</strong>
            <small className="muted">{stateSignal ? `mood: ${stateSignal}` : 'no active state signal'}{tensionActive ? ' · tension active' : ''}</small>
          </div>
            )
          })()}
          {(() => {
            const wmActive = (worldModelSignals?.summary?.active_count || 0) > 0
            const wmSignal = worldModelSignals?.summary?.current_signal || ''
            const uuActive = (userUnderstandingSignals?.summary?.active_count || 0) > 0
            const uuSignal = userUnderstandingSignals?.summary?.current_signal || ''
            const hasUnderstanding = wmActive || uuActive
            const understandLabel = wmActive
              ? (wmSignal.replace(/^World-model signal: /i, '').slice(0, 52) || 'World view active')
              : uuActive
                ? (uuSignal.replace(/^User-understanding signal: /i, '').slice(0, 52) || 'User insight active')
                : 'Listening'
            return (
          <div className={`now-card${hasUnderstanding ? '' : ' now-card-muted'}`}>
            <span>Understand</span>
            <strong>{understandLabel}</strong>
            <small className="muted">{wmActive ? `${worldModelSignals.summary.active_count} assumption${worldModelSignals.summary.active_count !== 1 ? 's' : ''}` : ''}{wmActive && uuActive ? ' · ' : ''}{uuActive ? `${userUnderstandingSignals.summary.active_count} user insight${userUnderstandingSignals.summary.active_count !== 1 ? 's' : ''}` : ''}{!wmActive && !uuActive ? 'no active understanding' : ''}</small>
          </div>
            )
          })()}
          {(() => {
            const focusTitle = developmentFocuses?.summary?.current_focus || developmentFocuses?.items?.[0]?.title || ''
            const openCount = openLoopSignals?.summary?.open_count || 0
            const softeningCount = openLoopSignals?.summary?.softening_count || 0
            const loopCount = openCount + softeningCount
            const goalSignal = goalSignals?.summary?.current_goal || ''
            const closureProposalCount = (openLoopClosureProposals?.summary?.fresh_count || 0) + (openLoopClosureProposals?.summary?.active_count || 0)
            const hasCarry = !!focusTitle || loopCount > 0 || !!goalSignal
            const carryLabel = focusTitle
              ? focusTitle.slice(0, 52)
              : goalSignal
                ? goalSignal.slice(0, 52)
                : loopCount > 0
                  ? `${openCount} open${softeningCount > 0 ? `, ${softeningCount} softening` : ''}`
                  : 'Nothing carried'
            const carryDetail = [
              openCount > 0 ? `${openCount} open` : '',
              softeningCount > 0 ? `${softeningCount} softening` : '',
              closureProposalCount > 0 ? `${closureProposalCount} closure proposal${closureProposalCount !== 1 ? 's' : ''}` : '',
              goalSignal ? 'goal active' : '',
              !loopCount && !goalSignal && focusTitle ? 'focus active' : '',
              !loopCount && !goalSignal && !focusTitle ? 'no active threads' : '',
            ].filter(Boolean).join(' · ')
            return (
          <div className={`now-card${hasCarry ? '' : ' now-card-muted'}`}>
            <span>Carry</span>
            <strong>{carryLabel}</strong>
            <small className="muted">{carryDetail}</small>
          </div>
            )
          })()}
          {(() => {
            const pressureActive = (autonomyPressureSignals?.summary?.active_count || 0) > 0
            const pressureType = autonomyPressureSignals?.summary?.current_type || ''
            const loopState = proactiveLoopLifecycleSignals?.summary?.current_state || ''
            const loopKind = proactiveLoopLifecycleSignals?.summary?.current_kind || ''
            const gateState = proactiveQuestionGates?.summary?.current_state || ''
            const gateActive = (proactiveQuestionGates?.summary?.active_count || 0) > 0
            const hasGate = pressureActive || gateActive
            const gateLabel = gateActive
              ? (gateState === 'question-gated-candidate' ? 'Question capable' : 'Question held')
              : loopState === 'loop-question-worthy'
                ? 'Approaching question'
                : loopState === 'loop-closure-worthy'
                  ? 'Closure worthy'
                  : loopState
                    ? loopState.replace('loop-', '').replace(/-/g, ' ')
                    : pressureActive
                      ? pressureType.replace(/-/g, ' ')
                      : 'No pressure'
            const gateDetail = [
              pressureActive ? pressureType.replace(/-/g, ' ') : 'no pressure',
              loopKind ? loopKind.replace(/-/g, ' ') : '',
              gateActive ? (gateState === 'question-gated-candidate' ? 'gated · proposal only' : 'gated · held') : '',
            ].filter(Boolean).join(' · ')
            return (
          <div className={`now-card${hasGate ? ' now-card-highlight' : ' now-card-muted'}`}>
            <span>Gate</span>
            <strong>{gateLabel}</strong>
            <small className="muted">{gateDetail}</small>
          </div>
            )
          })()}
          {(() => {
            const hbState = heartbeatState.liveness_state || heartbeatState.scheduleState || 'quiet'
            const hbAction = heartbeatState.lastActionType || heartbeatState.lastDecisionType || ''
            const pilotActive = (webchatExecutionPilot?.summary?.active_count || 0) > 0
            const hbActive = hbState !== 'quiet' && hbState !== 'unknown'
            const actLabel = pilotActive
              ? 'Pilot ready'
              : heartbeatState.currentlyTicking
                ? 'Tick in progress'
                : hbState === 'propose-worthy'
                  ? 'Propose worthy'
                  : hbState === 'alive-pressure'
                    ? 'Alive pressure'
                    : hbState === 'watchful'
                      ? 'Watchful'
                      : hbActive
                        ? hbState.replace(/-/g, ' ')
                        : 'Waiting'
            return (
          <div className={`now-card${hbActive || pilotActive ? '' : ' now-card-muted'}`}>
            <span>Act</span>
            <strong>{actLabel}</strong>
            <small className="muted">{hbAction ? `last: ${hbAction.replace(/-/g, ' ')}` : 'bounded heartbeat'}{pilotActive ? ' · webchat pilot' : ''}</small>
          </div>
            )
          })()}
        </div>
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
                        {item.proposalTypes?.length > 0 ? (
                          <span className="mc-proposal-types">
                            {item.proposalTypes.join(' · ')}
                          </span>
                        ) : null}
                      </div>
                      <div className="mc-row-meta">
                        {item.isCanonicalSelf ? (
                          <span className="mc-status-pill status-approval-gated">explicit approval required</span>
                        ) : null}
                        {item.pendingCount ? <span className="mc-status-pill status-proposed">{item.pendingCount} proposed</span> : null}
                        {item.approvedCount ? <span className="mc-status-pill status-approved">{item.approvedCount} approved</span> : null}
                        {item.currentApplyReadiness ? <small>{`apply ${item.currentApplyReadiness}`}</small> : null}
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
              <span>Liveness</span>
              <strong>{heartbeatState.livenessState || 'quiet'}</strong>
              <p>{heartbeatState.livenessSummary || heartbeatState.livenessReason || 'No bounded liveness pressure recorded yet.'}</p>
              <p>
                pressure {heartbeatState.livenessPressure || 'low'} · confidence {heartbeatState.livenessConfidence || 'low'}
              </p>
              <p>
                threshold {heartbeatState.livenessThresholdState || 'quiet-threshold'}
              </p>
              <p>
                score {heartbeatState.livenessScore || 0} · signals {heartbeatState.livenessSignalCount || 0} · core {heartbeatState.livenessCorePressureCount || 0} · gates {heartbeatState.livenessProposeGateCount || 0}
              </p>
              <p>
                companion {heartbeatState.companionPressureState || 'inactive'} · weight {heartbeatState.companionPressureWeight || 0} · idle {heartbeatState.idlePresenceState || 'inactive'} · check-in {heartbeatState.checkinWorthiness || 'low'}
              </p>
              <p>
                {heartbeatState.companionPressureReason || 'No bounded companion-pressure recorded yet.'}
              </p>
            </div>
            <div className="compact-metric">
              <span>Last Execute Action</span>
              <strong>{heartbeatState.lastActionType || 'none'}</strong>
              <p>{heartbeatState.lastActionSummary || heartbeatState.lastActionStatus || 'No execute action recorded yet.'}</p>
            </div>
            <div className="compact-metric">
              <span>Execution Pilot</span>
              <strong>{webchatExecutionPilot?.summary?.current_delivery_state || 'none'}</strong>
              <p>{webchatExecutionPilot?.summary?.current_candidate || 'No tiny governed webchat execution pilot recorded yet.'}</p>
              <p>
                type {webchatExecutionPilot?.summary?.current_execution_type || 'none'} · channel {webchatExecutionPilot?.summary?.current_channel || 'webchat'}
              </p>
              <p>
                cooldown {webchatExecutionPilot?.summary?.current_cooldown_state || 'ready'} · kill switch {webchatExecutionPilot?.summary?.current_kill_switch_state || 'enabled'}
              </p>
              <p>
                {webchatExecutionPilot?.summary?.proactive_execution_state || 'tiny-governed-webchat-only'} · {webchatExecutionPilot?.summary?.planner_authority_state || 'not-planner-authority'}
              </p>
            </div>
            <div className="compact-metric">
              <span>Recovery</span>
              <strong>{heartbeatState.recoveryStatus || 'idle'}</strong>
              <p>{heartbeatState.lastRecoveryAt || 'No recovery activity recorded.'}</p>
              {heartbeatMetabolicSummary ? <p>{heartbeatMetabolicSummary}</p> : null}
            </div>
            {hasEmbodiedState ? (
            <div className="compact-metric" title="Authoritative internal-only host/body runtime state grounded in bounded host facts">
              <span>Embodied State</span>
              <strong>{humanizeToken(embodiedState.state) || 'unknown'}</strong>
              <p>{embodiedState.summary || 'No embodied host/body state recorded yet.'}</p>
              <p>{embodiedBuckets.join(' · ') || 'No source buckets available.'}</p>
              <p>
                {`strain ${humanizeToken(embodiedState.strainLevel) || 'unknown'} · recovery ${humanizeToken(embodiedState.recoveryState) || 'steady'}`}
              </p>
              <p>
                {embodiedState.createdAt ? `${formatFreshness(embodiedState.createdAt)} · ${humanizeToken(embodiedState.freshnessState)}` : humanizeToken(embodiedState.freshnessState) || 'unknown'}
              </p>
              {embodiedUsage ? <p>{`used by ${embodiedUsage}`}</p> : null}
            </div>
            ) : null}
            {hasLoopRuntime ? (
            <div className="compact-metric" title="Authoritative internal-only loop runtime state for bounded open and proactive loops">
              <span>Loop Runtime</span>
              <strong>{humanizeToken(loopRuntimeSummary.currentStatus) || 'unknown'}</strong>
              <p>{loopRuntimeSummary.currentLoop || 'No active runtime loop'}</p>
              <p>{loopRuntimeCounts.join(' · ') || 'No loop runtime counts available.'}</p>
              <p>
                {`kind ${humanizeToken(loopRuntimeSummary.currentKind) || 'none'} · reason ${humanizeToken(loopRuntimeSummary.currentReason) || 'none'}`}
              </p>
              <p>
                {loopRuntime.createdAt ? `${formatFreshness(loopRuntime.createdAt)} · ${humanizeToken(loopRuntime.freshnessState)}` : humanizeToken(loopRuntime.freshnessState) || 'unknown'}
              </p>
              {loopRuntimeUsage ? <p>{`used by ${loopRuntimeUsage}`}</p> : null}
            </div>
            ) : null}
            {hasIdleConsolidation ? (
            <div className="compact-metric" title="Authoritative internal-only metabolisk runtime process for bounded idle consolidation">
              <span>Idle Consolidation</span>
              <strong>{humanizeToken(idleConsolidationSummary.lastState) || 'idle'}</strong>
              <p>{idleConsolidationLastResult.recordSummary || idleConsolidationSummary.latestSummary || 'No idle consolidation artifact recorded yet.'}</p>
              <p>
                {`result ${humanizeToken(idleConsolidationLastResult.reason || idleConsolidationSummary.lastReason) || 'no run yet'} · inputs ${idleConsolidationSummary.sourceInputCount || 0}`}
              </p>
              {sleepCadence ? (
              <p>
                {`cadence ${cadenceProducerLabel(sleepCadence)}${cadenceProducerReason(sleepCadence) ? ` · ${cadenceProducerReason(sleepCadence)}` : ''}`}
              </p>
              ) : null}
              <p>
                {`output ${humanizeToken(idleConsolidationSummary.lastOutputKind) || 'private brain sleep consolidation'}${idleConsolidationSummary.latestRecordId ? ` · ${idleConsolidationSummary.latestRecordId}` : ''}`}
              </p>
              <p>
                {idleConsolidation.createdAt ? `${formatFreshness(idleConsolidation.createdAt)} · internal only` : 'internal only'}
              </p>
              {idleConsolidationBoundary ? <p>{idleConsolidationBoundary}</p> : null}
            </div>
            ) : null}
            {(hasDreamArticulation || dreamCadence) ? (
            <div className="compact-metric" title="Authoritative internal-only candidate runtime process for bounded dream articulation">
              <span>Dream Articulation</span>
              <strong>{humanizeToken(dreamArticulationSummary.lastState || cadenceProducerLabel(dreamCadence, 'idle')) || 'idle'}</strong>
              <p>{dreamArticulationLatestArtifact.title || dreamArticulationLastResult.signalSummary || dreamArticulationSummary.latestSummary || 'No dream articulation candidate recorded yet.'}</p>
              <p>
                {`result ${humanizeToken(dreamArticulationLastResult.reason || dreamArticulationSummary.lastReason || dreamCadence?.lastTickStatus?.reason) || 'no run yet'} · inputs ${dreamArticulationSummary.sourceInputCount || dreamArticulationLastResult.sourceInputs?.length || 0}`}
              </p>
              {dreamCadence ? (
              <p>
                {`cadence ${cadenceProducerLabel(dreamCadence)}${cadenceProducerReason(dreamCadence) ? ` · ${cadenceProducerReason(dreamCadence)}` : ''}`}
              </p>
              ) : null}
              <p>
                {`output ${humanizeToken(dreamArticulationSummary.lastOutputKind) || 'runtime dream hypothesis'}${dreamArticulationSummary.latestSignalId ? ` · ${dreamArticulationSummary.latestSignalId}` : ''}`}
              </p>
              <p>
                {(dreamArticulation.createdAt || internalCadence.lastTickAt) ? `${formatFreshness(dreamArticulation.createdAt || internalCadence.lastTickAt)} · candidate only · internal only` : 'candidate only · internal only'}
              </p>
              {dreamArticulationBoundary ? <p>{dreamArticulationBoundary}</p> : null}
            </div>
            ) : null}
            {(hasPromptEvolution || promptEvolutionCadence) ? (
            <div className="compact-metric" title="Authoritative internal-only proposal runtime process for bounded prompt evolution">
              <span>Prompt Evolution</span>
              <strong>{humanizeToken(promptEvolutionSummary.lastState || cadenceProducerLabel(promptEvolutionCadence, 'idle')) || 'idle'}</strong>
              <p>{promptEvolutionLatestProposal.summary || promptEvolutionLastResult.proposalSummary || promptEvolutionSummary.latestSummary || 'No runtime prompt proposal recorded yet.'}</p>
              <p>
                {`result ${humanizeToken(promptEvolutionLastResult.reason || promptEvolutionSummary.lastReason || promptEvolutionCadence?.lastTickStatus?.reason) || 'no run yet'} · inputs ${promptEvolutionSummary.sourceInputCount || promptEvolutionLastResult.sourceInputs?.length || 0}`}
              </p>
              {promptEvolutionCadence ? (
              <p>
                {`cadence ${cadenceProducerLabel(promptEvolutionCadence)}${cadenceProducerReason(promptEvolutionCadence) ? ` · ${cadenceProducerReason(promptEvolutionCadence)}` : ''}`}
              </p>
              ) : null}
              <p>
                {`proposal ${humanizeToken(promptEvolutionLastResult.proposalType || promptEvolutionLatestProposal.proposalType || 'self-authored-prompt-proposal')}${promptEvolutionSummary.latestTargetAsset && promptEvolutionSummary.latestTargetAsset !== 'none' ? ` · ${promptEvolutionSummary.latestTargetAsset}` : ''}`}
              </p>
              <p>
                {(promptEvolution.createdAt || internalCadence.lastTickAt)
                  ? `${formatFreshness(promptEvolution.createdAt || internalCadence.lastTickAt)} · proposal only · internal only`
                  : 'proposal only · internal only'}
              </p>
              {promptEvolutionBoundary ? <p>{promptEvolutionBoundary}</p> : null}
            </div>
            ) : null}
            {hasAffectiveMetaState ? (
            <div className="compact-metric" title="Derived internal-only runtime orientation state for bounded affective/meta bearing">
              <span>Affective Meta</span>
              <strong>{humanizeToken(affectiveMetaState.state) || 'unknown'}</strong>
              <p>{affectiveMetaState.summary || 'No affective/meta runtime orientation recorded yet.'}</p>
              <p>
                {`bearing ${humanizeToken(affectiveMetaState.bearing) || 'unknown'} · mode ${humanizeToken(affectiveMetaState.monitoringMode) || 'unknown'} · load ${humanizeToken(affectiveMetaState.reflectiveLoad) || 'low'}`}
              </p>
              <p>
                {affectiveMetaState.createdAt
                  ? `${formatFreshness(affectiveMetaState.createdAt)} · ${humanizeToken(affectiveMetaState.freshnessState) || 'unknown'}`
                  : humanizeToken(affectiveMetaState.freshnessState) || 'unknown'}
              </p>
              {affectiveMetaUsage ? <p>{`used by ${affectiveMetaUsage}`}</p> : null}
              {affectiveMetaBoundary ? <p>{affectiveMetaBoundary}</p> : null}
            </div>
            ) : null}
            {hasEpistemicRuntimeState ? (
            <div className="compact-metric" title="Derived internal-only runtime epistemic corrective state for bounded wrongness, regret, and counterfactual sense">
              <span>Epistemic State</span>
              <strong>{humanizeToken(epistemicRuntimeState.wrongnessState) || 'clear'}</strong>
              <p>{epistemicRuntimeState.summary || 'No epistemic runtime state recorded yet.'}</p>
              <p>
                {`regret ${humanizeToken(epistemicRuntimeState.regretSignal) || 'none'} · counterfactual ${humanizeToken(epistemicRuntimeState.counterfactualMode) || 'none'} · confidence ${humanizeToken(epistemicRuntimeState.confidence) || 'low'}`}
              </p>
              {epistemicRuntimeState.counterfactualHint && epistemicRuntimeState.counterfactualHint !== 'none' ? (
              <p>{`hint ${humanizeToken(epistemicRuntimeState.counterfactualHint)}`}</p>
              ) : null}
              <p>
                {epistemicRuntimeState.createdAt
                  ? `${formatFreshness(epistemicRuntimeState.createdAt)} · ${humanizeToken(epistemicRuntimeState.freshnessState) || 'unknown'}`
                  : humanizeToken(epistemicRuntimeState.freshnessState) || 'unknown'}
              </p>
              {epistemicRuntimeUsage ? <p>{`used by ${epistemicRuntimeUsage}`}</p> : null}
              {epistemicRuntimeBoundary ? <p>{epistemicRuntimeBoundary}</p> : null}
            </div>
            ) : null}
            {hasSubagentEcology ? (
            <div className="compact-metric" title="Derived internal-only runtime ecology of bounded helper roles with no tool execution">
              <span>Subagent Ecology</span>
              <strong>{humanizeToken(subagentEcologySummary.lastActiveRoleName) || 'idle ecology'}</strong>
              <p>{subagentEcology.summaryText || 'No internal helper roles currently active.'}</p>
              <p>
                {subagentEcologyCounts.join(' · ') || `${subagentEcologySummary.roleCount || 0} roles`}
              </p>
              <p>
                {`last ${humanizeToken(subagentEcologySummary.lastActiveRoleStatus) || 'idle'} · ${humanizeToken(subagentEcologySummary.lastActivationReason) || 'no recent activation'}`}
              </p>
              <p>
                {subagentEcology.createdAt
                  ? `${formatFreshness(subagentEcology.createdAt)} · ${humanizeToken(subagentEcology.freshnessState) || 'unknown'}`
                  : humanizeToken(subagentEcology.freshnessState) || 'unknown'}
              </p>
              <p>
                {`internal only · tool ${humanizeToken(subagentEcology.toolAccess) || 'none'} · ${humanizeToken((visibleSubagentRoles[0] || {}).influenceScope || 'bounded')} influence`}
              </p>
              {subagentEcologyUsage ? <p>{`used by ${subagentEcologyUsage}`}</p> : null}
              {subagentEcologyBoundary ? <p>{subagentEcologyBoundary}</p> : null}
            </div>
            ) : null}
            {hasCouncilRuntime ? (
            <div className="compact-metric" title="Derived internal-only council runtime for bounded recommendation across helper-role perspectives">
              <span>Council Runtime</span>
              <strong>{humanizeToken(councilRuntime.councilState) || 'quiet'}</strong>
              <p>{councilRuntime.summary || 'No bounded council runtime state recorded yet.'}</p>
              <p>
                {`roles ${councilRuntimeRoles.join(' · ') || 'none'} · divergence ${humanizeToken(councilRuntime.divergenceLevel) || 'low'}`}
              </p>
              <p>
                {`recommend ${humanizeToken(councilRuntime.recommendation) || 'hold'} · confidence ${humanizeToken(councilRuntime.confidence) || 'low'}`}
              </p>
              {councilRuntime.recommendationReason ? (
              <p>{humanizeToken(councilRuntime.recommendationReason)}</p>
              ) : null}
              <p>
                {councilRuntime.createdAt
                  ? `${formatFreshness(councilRuntime.createdAt)} · ${humanizeToken(councilRuntime.freshnessState) || 'unknown'}`
                  : humanizeToken(councilRuntime.freshnessState) || 'unknown'}
              </p>
              <p>
                {`internal only · tool ${humanizeToken(councilRuntime.toolAccess) || 'none'} · ${humanizeToken(councilRuntime.influenceScope) || 'bounded'} influence`}
              </p>
              {councilRuntimeUsage ? <p>{`used by ${councilRuntimeUsage}`}</p> : null}
              {councilRuntimeBoundary ? <p>{councilRuntimeBoundary}</p> : null}
            </div>
            ) : null}
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
                {embodiedStateRow(embodiedState, onOpenItem)}
                {loopRuntimeRow(loopRuntime, onOpenItem)}
                {idleConsolidationRow(idleConsolidation, onOpenItem)}
                {dreamArticulationRow(dreamArticulation, onOpenItem)}
                {promptEvolutionRow(promptEvolution, onOpenItem)}
                {affectiveMetaStateRow(affectiveMetaState, onOpenItem)}
                {epistemicRuntimeStateRow(epistemicRuntimeState, onOpenItem)}
                {subagentEcologyRow(subagentEcology, onOpenItem)}
                {councilRuntimeRow(councilRuntime, onOpenItem)}
                {sleepCadence ? detailRow({
                  ...sleepCadence,
                  createdAt: sleepCadence.lastRunAt || internalCadence.lastTickAt,
                  source: internalCadence.source || '/mc/internal-cadence',
                  summary: `${cadenceProducerLabel(sleepCadence)}${cadenceProducerReason(sleepCadence) ? ` · ${cadenceProducerReason(sleepCadence)}` : ''}`,
                }, 'Sleep Consolidation Cadence', onOpenItem) : null}
                {dreamCadence ? detailRow({
                  ...dreamCadence,
                  createdAt: dreamCadence.lastRunAt || internalCadence.lastTickAt,
                  source: internalCadence.source || '/mc/internal-cadence',
                  summary: `${cadenceProducerLabel(dreamCadence)}${cadenceProducerReason(dreamCadence) ? ` · ${cadenceProducerReason(dreamCadence)}` : ''}`,
                }, 'Dream Articulation Cadence', onOpenItem) : null}
                {promptEvolutionCadence ? detailRow({
                  ...promptEvolutionCadence,
                  createdAt: promptEvolutionCadence.lastRunAt || internalCadence.lastTickAt,
                  source: internalCadence.source || '/mc/internal-cadence',
                  summary: `${cadenceProducerLabel(promptEvolutionCadence)}${cadenceProducerReason(promptEvolutionCadence) ? ` · ${cadenceProducerReason(promptEvolutionCadence)}` : ''}`,
                }, 'Prompt Evolution Cadence', onOpenItem) : null}
                {visibleLoopRuntimeItems.map((item) => loopRuntimeItemRow(item, onOpenItem))}
                {visibleSubagentRoles.map((item) => subagentRoleRow({
                  ...item,
                  source: subagentEcology.source || '/mc/subagent-ecology',
                }, onOpenItem))}
                {visibleCouncilRolePositions.map((item) => councilRolePositionRow(item, onOpenItem))}
                {detailRow(data?.development?.webchatExecutionPilotSupport, 'Webchat Execution Pilot', onOpenItem)}
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

      {/* --- Runtime Self-Model --- */}
      {(() => {
        const sm = data?.runtimeSelfModel
        if (!sm || !sm.layers || !sm.layers.length) return null
        const layers = sm.layers
        const boundaries = sm.truth_boundaries || {}
        const summary = sm.summary || {}

        // Primary axis: visibility × role
        const visible = layers.filter(l => l.visibility === 'visible' || l.visibility === 'mixed')
        const internalOnly = layers.filter(l => l.visibility === 'internal-only' && l.role !== 'groundwork-only')
        const groundwork = layers.filter(l => l.role === 'groundwork-only')

        const roleIndicator = (role) => {
          if (role === 'active') return { symbol: '\u25CF', color: 'var(--success, #22c55e)' }
          if (role === 'cooling') return { symbol: '\u25CF', color: 'var(--warning, #e2a308)' }
          if (role === 'idle') return { symbol: '\u25CB', color: 'var(--muted, #888)' }
          if (role === 'gated') return { symbol: '\u25CB', color: 'var(--warning, #e2a308)' }
          if (role === 'unavailable') return { symbol: '\u25CF', color: 'var(--danger, #ef4444)' }
          return { symbol: '\u25CB', color: 'var(--muted, #888)' }
        }

        const layerPill = (layer) => {
          const ri = roleIndicator(layer.role)
          return (
            <button
              key={layer.id}
              className="mc-list-row"
              style={{ display: 'inline-flex', padding: '3px 8px', borderRadius: 4, fontSize: '0.82em', gap: 5, width: 'auto', minWidth: 0 }}
              onClick={() => onOpenItem(`Layer: ${layer.label}`, layer)}
              title={`${layer.kind} · ${layer.role} · ${layer.truth}`}
            >
              <span style={{ color: ri.color, fontWeight: 600 }}>{ri.symbol}</span>
              <span>{layer.label}</span>
              {layer.role !== 'active' && <span style={{ opacity: 0.5, fontSize: '0.85em' }}>{layer.role}</span>}
            </button>
          )
        }

        return (
          <section className="mc-section-grid">
            <article className="support-card" id="jarvis-self-model" title="Runtime self-model — typed layer snapshot of Jarvis' current system-self">
              <div className="panel-header">
                <div>
                  <h3>Runtime Self-Model</h3>
                  <p className="muted">{visible.length} visible · {internalOnly.length} internal-only · {groundwork.length} groundwork</p>
                </div>
                <span className="mc-section-hint">Runtime truth</span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', padding: '0 12px 12px' }}>

                {visible.length > 0 && (
                  <div>
                    <div style={{ fontSize: '0.78em', opacity: 0.6, marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Visible</div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>{visible.map(layerPill)}</div>
                  </div>
                )}

                {internalOnly.length > 0 && (
                  <div>
                    <div style={{ fontSize: '0.78em', opacity: 0.6, marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Internal-only</div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>{internalOnly.map(layerPill)}</div>
                  </div>
                )}

                {groundwork.length > 0 && (
                  <div>
                    <div style={{ fontSize: '0.78em', opacity: 0.6, marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Groundwork</div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                      {groundwork.map(g => (
                        <button
                          key={g.id}
                          className="mc-list-row now-card-muted"
                          style={{ display: 'inline-flex', padding: '3px 8px', borderRadius: 4, fontSize: '0.82em', gap: 5, width: 'auto', minWidth: 0 }}
                          onClick={() => onOpenItem(`Groundwork: ${g.label}`, g)}
                          title={g.detail || g.kind}
                        >
                          <span style={{ opacity: 0.4 }}>{'\u25CB'}</span>
                          <span>{g.label}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                <div style={{ fontSize: '0.78em', opacity: 0.6, display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                  {Object.entries(boundaries).map(([key, value]) => (
                    <span key={key} title={value} style={{ cursor: 'help' }}>
                      {key.replace(/_/g, ' ').replace(/vs/g, '\u2260')}
                    </span>
                  ))}
                </div>

                <button
                  className="mc-list-row"
                  onClick={() => onOpenItem('Runtime Self-Model (full)', sm)}
                >
                  <div>
                    <strong>Full snapshot</strong>
                    <span style={{ fontSize: '0.82em', opacity: 0.85 }}>
                      {summary.total_layers || 0} layers · {Object.keys(boundaries).length} boundaries
                    </span>
                  </div>
                  <div className="mc-row-meta">
                    <small>{sm.built_at ? formatFreshness(sm.built_at) : 'unknown'}</small>
                    <ChevronRight size={14} />
                  </div>
                </button>

              </div>
            </article>
          </section>
        )
      })()}

      {/* --- Attention Budget Traces + Conflict Resolution --- */}
      {(() => {
        const traces = data?.attentionTraces || {}
        const traceEntries = Object.entries(traces).filter(([, t]) => t && t.profile)
        const conflict = data?.conflictResolution
        if (!traceEntries.length && !conflict) return null
        return (
          <section className="mc-section-grid">
            {traceEntries.length > 0 && (
            <article className="support-card" id="jarvis-attention" title="Attention budget — authoritative prompt selection truth">
              <div className="panel-header">
                <div>
                  <h3>Attention Budget</h3>
                  <p className="muted">Authoritative prompt selection — what context Jarvis actually used.</p>
                </div>
                <span className="mc-section-hint">Runtime truth</span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', padding: '0 12px 12px' }}>
                {traceEntries.map(([profileKey, trace]) => {
                  const isFallback = trace.authority_mode === 'fallback_passthrough'
                  const hasOvershoot = Boolean(trace.budget_overshoot)
                  const included = trace.included || []
                  const trimmed = trace.trimmed || []
                  const omitted = trace.omitted || []
                  const utilPct = Math.round((trace.char_utilization || 0) * 100)
                  return (
                    <button
                      key={profileKey}
                      className={`mc-list-row ${isFallback ? 'now-card-muted' : ''}`}
                      onClick={() => onOpenItem(`Attention Trace: ${profileKey}`, trace)}
                    >
                      <div>
                        <strong>
                          {profileKey.replace(/_/g, ' ')}
                          {isFallback && <span style={{ color: 'var(--warning, #e2a308)', marginLeft: 6 }}>⚠ fallback</span>}
                          {hasOvershoot && <span style={{ color: 'var(--warning, #e2a308)', marginLeft: 6 }}>△ overshoot +{trace.overshoot_chars}ch</span>}
                        </strong>
                        <span style={{ fontSize: '0.82em', opacity: 0.85 }}>
                          {included.length} included{trimmed.length > 0 && ` · ${trimmed.length} trimmed`}{omitted.length > 0 && ` · ${omitted.length} omitted`}
                          {' · '}{utilPct}% of {trace.total_char_target || 0}ch budget
                        </span>
                      </div>
                      <div className="mc-row-meta">
                        <small>{trace.authority_mode || 'unknown'}</small>
                        <ChevronRight size={14} />
                      </div>
                    </button>
                  )
                })}
              </div>
            </article>
            )}
            {conflict && (
            <article className="support-card" id="jarvis-conflict" title="Conflict resolution — bounded heartbeat initiative arbitration">
              <div className="panel-header">
                <div>
                  <h3>Conflict Resolution</h3>
                  <p className="muted">Heartbeat initiative arbitration — what Jarvis chose and why.</p>
                </div>
                <span className="mc-section-hint">Runtime truth</span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', padding: '0 12px 12px' }}>
                <button
                  className="mc-list-row"
                  onClick={() => onOpenItem('Conflict Resolution Trace', conflict)}
                >
                  <div>
                    <strong>
                      {conflict.outcome || 'none'}
                      {conflict.blocked_by && (
                        <span style={{ color: 'var(--warning, #e2a308)', marginLeft: 6 }}>
                          blocked: {conflict.blocked_by}
                        </span>
                      )}
                    </strong>
                    <span style={{ fontSize: '0.82em', opacity: 0.85 }}>
                      {conflict.reason_code || 'no reason'}
                      {(conflict.competing_factors || []).length > 0 && (
                        ` · ${conflict.competing_factors.length} competing factors`
                      )}
                    </span>
                    {conflict.dominant_factor && (
                      <span style={{ fontSize: '0.78em', opacity: 0.7, display: 'block' }}>
                        dominant: {conflict.dominant_factor}
                      </span>
                    )}
                  </div>
                  <div className="mc-row-meta">
                    <small>{conflict.outcome || 'none'}</small>
                    <ChevronRight size={14} />
                  </div>
                </button>
                {(() => {
                  const qi = conflict.quiet_initiative
                  if (!qi || (!qi.active && qi.state === 'holding' && !qi.hold_count)) return null
                  const isActive = qi.active
                  const stateLabel = qi.state || 'none'
                  const isDone = stateLabel === 'promoted' || stateLabel === 'expired' || stateLabel.startsWith('max-') || stateLabel.startsWith('policy-')
                  return (
                    <button
                      className={`mc-list-row ${!isActive && isDone ? 'now-card-muted' : ''}`}
                      onClick={() => onOpenItem('Quiet Initiative', qi)}
                    >
                      <div>
                        <strong>
                          quiet initiative: {stateLabel}
                          {isActive && (
                            <span style={{ marginLeft: 6, opacity: 0.8 }}>
                              {qi.hold_count}/{qi.max_hold_count || 4}
                            </span>
                          )}
                          {stateLabel === 'promoted' && (
                            <span style={{ color: 'var(--success, #22c55e)', marginLeft: 6 }}>✓ promoted</span>
                          )}
                        </strong>
                        <span style={{ fontSize: '0.82em', opacity: 0.85 }}>
                          {qi.reason_code || 'no reason'}
                          {qi.focus && ` · focus: ${qi.focus}`}
                        </span>
                      </div>
                      <div className="mc-row-meta">
                        <small>{isActive ? 'holding' : stateLabel}</small>
                        <ChevronRight size={14} />
                      </div>
                    </button>
                  )
                })()}
              </div>
            </article>
            )}
            {(() => {
              const guard = data?.deceptionGuard
              if (!guard || !guard.constraints || !guard.constraints.length) return null
              const hasBlocks = guard.has_blocks
              const hasReframes = guard.has_reframes
              const isClean = !hasBlocks && !hasReframes
              if (isClean) return null
              const claimTypes = [...new Set(guard.constraints.filter(c => c.outcome !== 'allow').map(c => c.claim_type))].join(', ')
              const blockCount = guard.constraints.filter(c => c.outcome.startsWith('block_')).length
              const reframeCount = guard.constraints.filter(c => c.outcome.startsWith('reframe_')).length
              return (
                <article className="support-card" id="jarvis-guard" title="Self-deception guard — runtime truth constraint on user-facing stance">
                  <div className="panel-header">
                    <div>
                      <h3>Self-Deception Guard</h3>
                      <p className="muted">Runtime truth constraints on visible stance.</p>
                    </div>
                    <span className="mc-section-hint">Active</span>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', padding: '0 12px 12px' }}>
                    <button
                      className="mc-list-row"
                      onClick={() => onOpenItem('Self-Deception Guard Trace', guard)}
                    >
                      <div>
                        <strong>
                          {blockCount > 0 && <span style={{ color: 'var(--danger, #ef4444)', marginRight: 6 }}>{blockCount} blocked</span>}
                          {reframeCount > 0 && <span style={{ color: 'var(--warning, #e2a308)', marginRight: 6 }}>{reframeCount} reframed</span>}
                        </strong>
                        <span style={{ fontSize: '0.82em', opacity: 0.85 }}>
                          claims: {claimTypes || 'none'}
                          {guard.execution_evidence === false && ' · no execution evidence'}
                        </span>
                        <span style={{ fontSize: '0.78em', opacity: 0.7, display: 'block' }}>
                          capability: {guard.capability_state || 'unknown'} · permission: {guard.permission_state || 'unknown'}
                        </span>
                      </div>
                      <div className="mc-row-meta">
                        <small>{hasBlocks ? 'guarding' : 'reframing'}</small>
                        <ChevronRight size={14} />
                      </div>
                    </button>
                  </div>
                </article>
              )
            })()}
          </section>
        )
      })()}

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
            <div className="compact-metric">
              <span>Private source discipline</span>
              <strong>{data?.memory?.retainedProjection?.private_lane_source_state || data?.memory?.retainedRecord?.summary?.current_source_state || 'unknown'}</strong>
              <p>{data?.memory?.retainedProjection?.contamination_state || data?.memory?.retainedRecord?.summary?.current_contamination_state || 'unknown'}</p>
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
              <span>Inner Note Support</span>
              <strong>{(privateInnerNoteSignals?.summary?.active_count || 0) + (privateInnerNoteSignals?.summary?.stale_count || 0)}</strong>
              <p>{privateInnerNoteSignals?.summary?.current_signal || 'No bounded private inner note support'}</p>
              <p>
                {privateInnerNoteSignals?.summary?.stale_count || 0} stale · {privateInnerNoteSignals?.summary?.superseded_count || 0} superseded
              </p>
              <p>
                {privateInnerNoteSignals?.summary?.current_source_state || 'private-runtime-grounded'} · {privateInnerNoteSignals?.summary?.current_contamination_state || 'unknown'}
              </p>
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
              <p>
                {privateInitiativeTensionSignals?.summary?.authority || 'non-authoritative'} · {privateInitiativeTensionSignals?.summary?.layer_role || 'runtime-support'}
              </p>
            </div>
            <div className="compact-metric" title="Internal-only candidate layer with bounded lifecycle; never identity or action authority">
              <span>Emergent Signals</span>
              <strong>{emergentSignals?.summary?.active_count || 0}</strong>
              <p>{emergentSignals?.summary?.current_signal || 'No active emergent inner signal'}</p>
              <p>
                {emergentSignals?.summary?.candidate_count || 0} candidate · {emergentSignals?.summary?.emergent_count || 0} emergent · {emergentSignals?.summary?.fading_count || 0} fading
              </p>
              <p>
                {emergentSignals?.summary?.current_lifecycle_state || 'none'} · {emergentSignals?.summary?.authority || 'candidate-only'} · {emergentSignals?.summary?.visibility || 'internal-only'}
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
              <p>
                {privateStateSnapshots?.summary?.authority || 'non-authoritative'} · {privateStateSnapshots?.summary?.layer_role || 'runtime-support'}
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
            {((selfNarrativeSelfModelReviewBridge?.summary?.active_count || 0) + (selfNarrativeSelfModelReviewBridge?.summary?.softening_count || 0)) > 0 ? (
            <div className="compact-metric">
              <span>Self-Review Bridge</span>
              <strong>{(selfNarrativeSelfModelReviewBridge?.summary?.active_count || 0) + (selfNarrativeSelfModelReviewBridge?.summary?.softening_count || 0)}</strong>
              <p>{selfNarrativeSelfModelReviewBridge?.summary?.current_bridge || 'No bounded self-narrative review bridge'}</p>
            </div>
            ) : null}
            <div className="compact-metric">
              <span>Reflection Signals</span>
              <strong>{(reflectionSignals?.summary?.active_count || 0) + (reflectionSignals?.summary?.integrating_count || 0) + (reflectionSignals?.summary?.settled_count || 0) || summary?.development?.reflection_signal_count || 0}</strong>
              <p>{reflectionSignals?.summary?.current_signal || summary?.development?.current_reflection_signal || 'No active reflection signal'}</p>
              <p>
                {reflectionSignals?.summary?.integrating_count || 0} integrating · {reflectionSignals?.summary?.settled_count || 0} settled · {reflectionSignals?.summary?.superseded_count || 0} superseded
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
              <p>
                {(openLoopSignals?.summary?.ready_count || 0)} high-readiness · current closure {openLoopSignals?.summary?.current_closure_confidence || 'low'}
              </p>
            </div>
            {((openLoopClosureProposals?.summary?.fresh_count || 0) + (openLoopClosureProposals?.summary?.active_count || 0)) > 0 ? (
            <div className="compact-metric">
              <span>Closure Proposals</span>
              <strong>{(openLoopClosureProposals?.summary?.fresh_count || 0) + (openLoopClosureProposals?.summary?.active_count || 0) + (openLoopClosureProposals?.summary?.fading_count || 0)}</strong>
              <p>{openLoopClosureProposals?.summary?.current_proposal || 'No active loop-closure proposal'}</p>
              <p className="muted">Proposal only — not automatic closure</p>
            </div>
            ) : null}
            {((internalOppositionSignals?.summary?.active_count || 0) + (internalOppositionSignals?.summary?.softening_count || 0)) > 0 ? (
            <div className="compact-metric">
              <span>Internal Opposition</span>
              <strong>{(internalOppositionSignals?.summary?.active_count || 0) + (internalOppositionSignals?.summary?.softening_count || 0)}</strong>
              <p>{internalOppositionSignals?.summary?.current_signal || 'No active internal opposition signal'}</p>
            </div>
            ) : null}
            {(() => {
              const srTotal = (selfReviewSignals?.summary?.active_count || 0) + (selfReviewRecords?.summary?.active_count || selfReviewRecords?.summary?.fresh_count || 0) + (selfReviewRuns?.summary?.active_count || selfReviewRuns?.summary?.fresh_count || 0) + (selfReviewOutcomes?.summary?.active_count || selfReviewOutcomes?.summary?.fresh_count || 0) + (selfReviewCadenceSignals?.summary?.active_count || 0)
              return srTotal > 0 ? (
            <div className="compact-metric">
              <span>Self-Review</span>
              <strong>{srTotal}</strong>
              <p>
                {selfReviewSignals?.summary?.active_count || 0} need · {(selfReviewRecords?.summary?.fresh_count || 0) + (selfReviewRecords?.summary?.active_count || 0)} briefs · {(selfReviewRuns?.summary?.fresh_count || 0) + (selfReviewRuns?.summary?.active_count || 0)} runs · {(selfReviewOutcomes?.summary?.fresh_count || 0) + (selfReviewOutcomes?.summary?.active_count || 0)} outcomes
              </p>
            </div>
              ) : null
            })()}
            {(() => {
              const dreamTotal = (dreamHypothesisSignals?.summary?.active_count || 0) + (dreamAdoptionCandidates?.summary?.active_count || dreamAdoptionCandidates?.summary?.fresh_count || 0) + (dreamInfluenceProposals?.summary?.active_count || dreamInfluenceProposals?.summary?.fresh_count || 0)
              return dreamTotal > 0 ? (
            <div className="compact-metric">
              <span>Dreams</span>
              <strong>{dreamTotal}</strong>
              <p>
                {dreamHypothesisSignals?.summary?.active_count || 0} hypotheses · {(dreamAdoptionCandidates?.summary?.fresh_count || 0) + (dreamAdoptionCandidates?.summary?.active_count || 0)} adoption · {(dreamInfluenceProposals?.summary?.fresh_count || 0) + (dreamInfluenceProposals?.summary?.active_count || 0)} influence
              </p>
            </div>
              ) : null
            })()}
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
              {(selfReviewSignals.items.length > 0 || selfReviewRecords.items.length > 0 || selfReviewRuns.items.length > 0 || selfReviewOutcomes.items.length > 0 || selfReviewCadenceSignals.items.length > 0 || dreamHypothesisSignals.items.length > 0 || dreamAdoptionCandidates.items.length > 0 || dreamInfluenceProposals.items.length > 0 || selfAuthoredPromptProposals.items.length > 0 || userUnderstandingSignals.items.length > 0 || userMdUpdateProposals.items.length > 0 || selfhoodProposals.items.length > 0) ? (
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
                  {dreamHypothesisSignals.items.length > 0 ? selfReviewStageLabel({ stage: 'Hypothesis', count: dreamHypothesisSignals.items.length }) : null}
                  {dreamHypothesisSignals.items.slice(0, 2).map((item) => dreamHypothesisSignalRow(item, onOpenItem))}
                  {dreamAdoptionCandidates.items.length > 0 ? selfReviewStageLabel({ stage: 'Adoption', count: dreamAdoptionCandidates.items.length }) : null}
                  {dreamAdoptionCandidates.items.slice(0, 2).map((item) => dreamAdoptionCandidateRow(item, onOpenItem))}
                  {dreamInfluenceProposals.items.length > 0 ? selfReviewStageLabel({ stage: 'Influence', count: dreamInfluenceProposals.items.length }) : null}
                  {dreamInfluenceProposals.items.slice(0, 2).map((item) => dreamInfluenceProposalRow(item, onOpenItem))}
                  {selfAuthoredPromptProposals.items.length > 0 ? selfReviewStageLabel({ stage: 'Prompt', count: selfAuthoredPromptProposals.items.length }) : null}
                  {selfAuthoredPromptProposals.items.slice(0, 2).map((item) => selfAuthoredPromptProposalRow(item, onOpenItem))}
                  {userUnderstandingSignals.items.length > 0 ? selfReviewStageLabel({ stage: 'User Insight', count: userUnderstandingSignals.items.length }) : null}
                  {userUnderstandingSignals.items.slice(0, 2).map((item) => userUnderstandingSignalRow(item, onOpenItem))}
                  {userMdUpdateProposals.items.length > 0 ? selfReviewStageLabel({ stage: 'USER.md', count: userMdUpdateProposals.items.length }) : null}
                  {userMdUpdateProposals.items.slice(0, 2).map((item) => userMdUpdateProposalRow(item, onOpenItem))}
                  {selfhoodProposals.items.length > 0 ? selfReviewStageLabel({ stage: 'Selfhood', count: selfhoodProposals.items.length }) : null}
                  {selfhoodProposals.items.slice(0, 2).map((item) => selfhoodProposalRow(item, onOpenItem))}
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
            {(() => {
              const wmActive = worldModelSignals?.summary?.active_count || summary?.continuity?.world_model_count || 0
              const wmSignal = worldModelSignals?.summary?.current_signal || summary?.continuity?.current_world_model || ''
              const wmUncertain = worldModelSignals?.summary?.uncertain_count || 0
              const wmCorrected = worldModelSignals?.summary?.corrected_count || 0
              const wmStale = worldModelSignals?.summary?.stale_count || 0
              return (
            <div className="compact-metric">
              <span>World Model</span>
              <strong>{wmActive > 0 ? `${wmActive} active` : 'No assumptions'}</strong>
              {wmSignal ? <p>{wmSignal}</p> : <p className="muted">No bounded situational assumptions yet</p>}
              {(wmUncertain > 0 || wmCorrected > 0 || wmStale > 0) ? (
              <p>
                {wmUncertain > 0 ? `${wmUncertain} uncertain` : ''}{wmUncertain > 0 && (wmCorrected > 0 || wmStale > 0) ? ' · ' : ''}{wmCorrected > 0 ? `${wmCorrected} corrected` : ''}{wmCorrected > 0 && wmStale > 0 ? ' · ' : ''}{wmStale > 0 ? `${wmStale} stale` : ''}
              </p>
              ) : null}
            </div>
              )
            })()}
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
                persistence {witnessSignals?.summary?.current_persistence_state || 'none'} · marker {witnessSignals?.summary?.current_persistence_marker || 'none'}
              </p>
              <p>
                {witnessSignals?.summary?.fresh_count || 0} fresh · {witnessSignals?.summary?.carried_count || 0} carried · {witnessSignals?.summary?.fading_count || 0} fading
              </p>
            </div>
            {(() => {
              const lifecycleTotal = (metabolismStateSignals?.summary?.active_count || 0) + (releaseMarkerSignals?.summary?.active_count || 0) + (consolidationTargetSignals?.summary?.active_count || 0) + (selectiveForgettingCandidates?.summary?.active_count || 0)
              return lifecycleTotal > 0 ? (
            <div className="compact-metric">
              <span>Lifecycle Health</span>
              <strong>{lifecycleTotal}</strong>
              <p>
                {metabolismStateSignals?.summary?.active_count || 0} metabolism · {releaseMarkerSignals?.summary?.active_count || 0} release · {consolidationTargetSignals?.summary?.active_count || 0} consolidation · {selectiveForgettingCandidates?.summary?.active_count || 0} forgetting
              </p>
            </div>
              ) : null
            })()}
            <div className="compact-metric">
              <span>Autonomy Pressure</span>
              <strong>{(autonomyPressureSignals?.summary?.active_count || 0) + (autonomyPressureSignals?.summary?.softening_count || 0)}</strong>
              <p>{autonomyPressureSignals?.summary?.current_signal || 'No bounded autonomy-pressure support'}</p>
              <p>
                type {autonomyPressureSignals?.summary?.current_type || 'none'} · weight {autonomyPressureSignals?.summary?.current_weight || 'low'}
              </p>
              <p>
                {autonomyPressureSignals?.summary?.planner_authority_state || 'not-planner-authority'} · {autonomyPressureSignals?.summary?.proactive_execution_state || 'not-proactive-execution'}
              </p>
            </div>
            <div className="compact-metric">
              <span>Proactive Loops</span>
              <strong>{(proactiveLoopLifecycleSignals?.summary?.active_count || 0) + (proactiveLoopLifecycleSignals?.summary?.softening_count || 0)}</strong>
              <p>{proactiveLoopLifecycleSignals?.summary?.current_signal || 'No bounded proactive-loop lifecycle support'}</p>
              <p>
                kind {proactiveLoopLifecycleSignals?.summary?.current_kind || 'none'} · state {proactiveLoopLifecycleSignals?.summary?.current_state || 'none'}
              </p>
              <p>
                q {proactiveLoopLifecycleSignals?.summary?.current_question_readiness || 'low'} · c {proactiveLoopLifecycleSignals?.summary?.current_closure_readiness || 'low'}
              </p>
            </div>
            <div className="compact-metric">
              <span>Question Gates</span>
              <strong>{(proactiveQuestionGates?.summary?.active_count || 0) + (proactiveQuestionGates?.summary?.softening_count || 0)}</strong>
              <p>{proactiveQuestionGates?.summary?.current_gate || 'No bounded proactive-question gate support'}</p>
              <p>
                state {proactiveQuestionGates?.summary?.current_state || 'none'} · reason {proactiveQuestionGates?.summary?.current_reason || 'none'}
              </p>
              <p>
                {proactiveQuestionGates?.summary?.current_send_permission_state || 'not-granted'} · {proactiveQuestionGates?.summary?.proactive_execution_state || 'not-proactive-execution'}
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
              <p className="muted">
                {(data?.continuity?.promotionSignal?.summary?.current_source_state || data?.continuity?.promotionSignal?.current?.private_lane_source_state || 'unknown')} · {(data?.continuity?.promotionDecision?.summary?.current_contamination_state || data?.continuity?.promotionDecision?.current?.contamination_state || 'unknown')}
              </p>
              {worldModelContextRow({
                summary: worldModelSignals?.summary || {},
                currentSignal: worldModelSignals?.summary?.current_signal || summary?.continuity?.current_world_model || 'No active world-model signal',
                uncertainCount: worldModelSignals?.summary?.uncertain_count || 0,
                correctedCount: worldModelSignals?.summary?.corrected_count || 0,
              }, onOpenItem)}
              {worldModelSignals.items.length === 0 ? (
                <p className="muted" style={{ padding: '0.25rem 0' }}>No bounded situational assumptions yet.</p>
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
