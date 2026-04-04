import { ChevronRight, Cpu, Activity, Moon, Sparkles, Heart, Brain, Network, Wand2, Users, Map, Lightbulb, GraduationCap, TrendingUp } from 'lucide-react'
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

/* ─── Summary helpers ─── */

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

function adaptivePlannerUsageSummary(item) {
  const usage = item?.seamUsage || {}
  const labels = []
  if (usage.heartbeatContext || usage.heartbeatPromptGrounding) labels.push('heartbeat')
  if (usage.runtimeSelfModel) labels.push('self-model')
  if (usage.missionControlRuntimeTruth) labels.push('MC truth')
  return labels.join(' · ')
}

function adaptivePlannerBoundarySummary(item) {
  const parts = []
  if (item?.authority) parts.push(humanizeToken(item.authority))
  if (item?.visibility) parts.push(humanizeToken(item.visibility))
  return parts.join(' / ')
}

function adaptiveReasoningUsageSummary(item) {
  const usage = item?.seamUsage || {}
  const labels = []
  if (usage.heartbeatContext || usage.heartbeatPromptGrounding) labels.push('heartbeat')
  if (usage.runtimeSelfModel) labels.push('self-model')
  if (usage.missionControlRuntimeTruth) labels.push('MC truth')
  return labels.join(' · ')
}

function adaptiveReasoningBoundarySummary(item) {
  const parts = []
  if (item?.authority) parts.push(humanizeToken(item.authority))
  if (item?.visibility) parts.push(humanizeToken(item.visibility))
  return parts.join(' / ')
}

function dreamInfluenceUsageSummary(item) {
  const usage = item?.seamUsage || {}
  const labels = []
  if (usage.guidedLearningEnrichment) labels.push('guided-learning')
  if (usage.heartbeatContext || usage.heartbeatPromptGrounding) labels.push('heartbeat')
  if (usage.runtimeSelfModel) labels.push('self-model')
  if (usage.missionControlRuntimeTruth) labels.push('MC truth')
  return labels.join(' · ')
}

function dreamInfluenceBoundarySummary(item) {
  const parts = []
  if (item?.authority) parts.push(humanizeToken(item.authority))
  if (item?.visibility) parts.push(humanizeToken(item.visibility))
  return parts.join(' / ')
}

function guidedLearningUsageSummary(item) {
  const usage = item?.seamUsage || {}
  const labels = []
  if (usage.heartbeatContext || usage.heartbeatPromptGrounding) labels.push('heartbeat')
  if (usage.runtimeSelfModel) labels.push('self-model')
  if (usage.missionControlRuntimeTruth) labels.push('MC truth')
  return labels.join(' · ')
}

function guidedLearningBoundarySummary(item) {
  const parts = []
  if (item?.authority) parts.push(humanizeToken(item.authority))
  if (item?.visibility) parts.push(humanizeToken(item.visibility))
  return parts.join(' / ')
}

function adaptiveLearningUsageSummary(item) {
  const usage = item?.seamUsage || {}
  const labels = []
  if (usage.heartbeatContext || usage.heartbeatPromptGrounding) labels.push('heartbeat')
  if (usage.runtimeSelfModel) labels.push('self-model')
  if (usage.missionControlRuntimeTruth) labels.push('MC truth')
  if (usage.guidedLearningEnrichment) labels.push('guided-learning')
  return labels.join(' · ')
}

function adaptiveLearningBoundarySummary(item) {
  const parts = []
  if (item?.authority) parts.push(humanizeToken(item.authority))
  if (item?.visibility) parts.push(humanizeToken(item.visibility))
  return parts.join(' / ')
}

function experientialUsageSummary(item) {
  const usage = item?.seamUsage || {}
  const labels = []
  if (usage.heartbeatRuntimeTruth || usage.heartbeatPromptGrounding) labels.push('heartbeat')
  if (usage.runtimeSelfModel) labels.push('self-model')
  if (usage.missionControlRuntimeTruth) labels.push('MC truth')
  return labels.join(' · ')
}

function experientialRuntimeContextRow(item, onOpen) {
  if (!item || !item.kind || item.kind !== 'experiential-runtime-context') return null
  const embodied = item.embodiedTranslation || {}
  const affective = item.affectiveTranslation || {}
  const intermittence = item.intermittenceTranslation || {}
  const contextPressure = item.contextPressureTranslation || {}
  const continuity = item.experientialContinuity || null
  const influence = item.experientialInfluence || null
  const hasNonDefault = (
    embodied.state !== 'steady' ||
    affective.state !== 'settled' ||
    intermittence.state !== 'continuous' ||
    contextPressure.state !== 'clear'
  )
  if (!hasNonDefault && !item.summary && !continuity && !influence) return null
  const usageLine = experientialUsageSummary(item)
  const detailText = [
    `body ${humanizeToken(embodied.state || 'steady')}`,
    `tone ${humanizeToken(affective.state || 'settled')}`,
    `gap ${humanizeToken(intermittence.state || 'continuous')}`,
    `pressure ${humanizeToken(contextPressure.state || 'clear')}`,
    usageLine ? `used by ${usageLine}` : '',
  ].filter(Boolean).join(' · ')

  const continuityTag = continuity
    ? `continuity ${humanizeToken(continuity.continuityState)}`
    : null
  const continuityShift = continuity?.stateShiftSummary && continuity.stateShiftSummary !== 'No dimensional shifts.'
    ? continuity.stateShiftSummary
    : null

  return (
    <button
      className="mc-list-row mc-list-row-subtle"
      onClick={() => onOpen('Experiential Runtime Context', item)}
      title={sectionTitleWithMeta({
        source: item.source,
        fetchedAt: item.createdAt,
        mode: 'experiential runtime context (derived-runtime-truth)',
      })}
    >
      <div>
        <strong>Experiential Context</strong>
        <span>{detailText || 'Inspect bounded experiential runtime context'}</span>
        {continuityTag ? (
          <span className="muted">
            {continuityTag}
            {continuityShift ? ` — ${continuityShift}` : ''}
          </span>
        ) : null}
        {continuity?.narrative ? <span className="muted">{continuity.narrative}</span> : null}
        {influence ? (
          <span className="muted">
            {`influence: bearing ${humanizeToken(influence.cognitiveBearing)} · attention ${humanizeToken(influence.attentionalPosture)} · initiative ${humanizeToken(influence.initiativeShading)}`}
          </span>
        ) : null}
        {influence?.narrative ? <span className="muted">{influence.narrative}</span> : null}
      </div>
      <div className="mc-row-meta">
        <StatusPill status={embodied.initiativeGate || 'clear'} />
        {affective.bearing && affective.bearing !== 'even' ? <small>{humanizeToken(affective.bearing)}</small> : null}
        {item.createdAt ? <small>{formatFreshness(item.createdAt)}</small> : null}
        <ChevronRight size={14} />
      </div>
    </button>
  )
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

/* ─── Row renderers ─── */

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

function adaptivePlannerRow(item, onOpen) {
  if (!item || !item.plannerMode) return null
  const detailText = [
    item.summary,
    item.planHorizon ? `horizon ${humanizeToken(item.planHorizon)}` : '',
    item.riskPosture ? `risk ${humanizeToken(item.riskPosture)}` : '',
    item.nextPlanningBias ? `bias ${humanizeToken(item.nextPlanningBias)}` : '',
  ].filter(Boolean).join(' · ')

  return (
    <button
      className="mc-list-row mc-list-row-subtle"
      onClick={() => onOpen('Adaptive Planner State', item)}
      title={sectionTitleWithMeta({
        source: item.source,
        fetchedAt: item.createdAt,
        mode: 'adaptive planner runtime detail',
      })}
    >
      <div>
        <strong>Adaptive Planner</strong>
        <span>{detailText || 'Inspect bounded adaptive planner runtime detail'}</span>
      </div>
      <div className="mc-row-meta">
        <StatusPill status={item.plannerMode || 'incremental'} />
        {item.confidence ? <small>{humanizeToken(item.confidence)}</small> : null}
        {item.createdAt ? <small>{formatFreshness(item.createdAt)}</small> : null}
        <ChevronRight size={14} />
      </div>
    </button>
  )
}

function adaptiveReasoningRow(item, onOpen) {
  if (!item || !item.reasoningMode) return null
  const detailText = [
    item.summary,
    item.reasoningPosture ? `posture ${humanizeToken(item.reasoningPosture)}` : '',
    item.certaintyStyle ? `certainty ${humanizeToken(item.certaintyStyle)}` : '',
    item.constraintBias ? `constraint ${humanizeToken(item.constraintBias)}` : '',
  ].filter(Boolean).join(' · ')

  return (
    <button
      className="mc-list-row mc-list-row-subtle"
      onClick={() => onOpen('Adaptive Reasoning State', item)}
      title={sectionTitleWithMeta({
        source: item.source,
        fetchedAt: item.createdAt,
        mode: 'adaptive reasoning runtime detail',
      })}
    >
      <div>
        <strong>Adaptive Reasoning</strong>
        <span>{detailText || 'Inspect bounded adaptive reasoning runtime detail'}</span>
      </div>
      <div className="mc-row-meta">
        <StatusPill status={item.reasoningMode || 'direct'} />
        {item.confidence ? <small>{humanizeToken(item.confidence)}</small> : null}
        {item.createdAt ? <small>{formatFreshness(item.createdAt)}</small> : null}
        <ChevronRight size={14} />
      </div>
    </button>
  )
}

function dreamInfluenceRow(item, onOpen) {
  if (!item || !item.influenceState || item.influenceState === 'quiet') return null
  const usageLine = dreamInfluenceUsageSummary(item)
  const boundaryLine = dreamInfluenceBoundarySummary(item)
  const detailText = [
    item.summary,
    item.influenceTarget ? `target ${humanizeToken(item.influenceTarget)}` : '',
    item.influenceMode ? `mode ${humanizeToken(item.influenceMode)}` : '',
    item.influenceHint ? item.influenceHint : '',
    usageLine ? `used by ${usageLine}` : '',
    boundaryLine || '',
  ].filter(Boolean).join(' · ')

  return (
    <button
      className="mc-list-row mc-list-row-subtle"
      onClick={() => onOpen('Dream Influence State', item)}
      title={sectionTitleWithMeta({
        source: item.source,
        fetchedAt: item.createdAt,
        mode: 'dream influence runtime detail',
      })}
    >
      <div>
        <strong>Dream Influence</strong>
        <span>{detailText || 'Inspect bounded dream influence runtime detail'}</span>
      </div>
      <div className="mc-row-meta">
        <StatusPill status={item.influenceState || 'quiet'} />
        {item.influenceStrength ? <small>{humanizeToken(item.influenceStrength)}</small> : null}
        {item.confidence ? <small>{humanizeToken(item.confidence)}</small> : null}
        {item.createdAt ? <small>{formatFreshness(item.createdAt)}</small> : null}
        <ChevronRight size={14} />
      </div>
    </button>
  )
}

function guidedLearningRow(item, onOpen) {
  if (!item || !item.learningMode) return null
  const detailText = [
    item.summary,
    item.learningFocus ? `focus ${humanizeToken(item.learningFocus)}` : '',
    item.learningPosture ? `posture ${humanizeToken(item.learningPosture)}` : '',
    item.nextLearningBias ? `bias ${humanizeToken(item.nextLearningBias)}` : '',
  ].filter(Boolean).join(' · ')

  return (
    <button
      className="mc-list-row mc-list-row-subtle"
      onClick={() => onOpen('Guided Learning State', item)}
      title={sectionTitleWithMeta({
        source: item.source,
        fetchedAt: item.createdAt,
        mode: 'guided learning runtime detail',
      })}
    >
      <div>
        <strong>Guided Learning</strong>
        <span>{detailText || 'Inspect bounded guided learning runtime detail'}</span>
      </div>
      <div className="mc-row-meta">
        <StatusPill status={item.learningMode || 'reinforce'} />
        {item.confidence ? <small>{humanizeToken(item.confidence)}</small> : null}
        {item.createdAt ? <small>{formatFreshness(item.createdAt)}</small> : null}
        <ChevronRight size={14} />
      </div>
    </button>
  )
}

function adaptiveLearningRow(item, onOpen) {
  if (!item || !item.learningEngineMode) return null
  const detailText = [
    item.summary,
    item.reinforcementTarget ? `target ${humanizeToken(item.reinforcementTarget)}` : '',
    item.retentionBias ? `retain ${humanizeToken(item.retentionBias)}` : '',
    item.maturationState ? `maturation ${humanizeToken(item.maturationState)}` : '',
  ].filter(Boolean).join(' · ')

  return (
    <button
      className="mc-list-row mc-list-row-subtle"
      onClick={() => onOpen('Adaptive Learning State', item)}
      title={sectionTitleWithMeta({
        source: item.source,
        fetchedAt: item.createdAt,
        mode: 'adaptive learning runtime detail',
      })}
    >
      <div>
        <strong>Adaptive Learning</strong>
        <span>{detailText || 'Inspect bounded adaptive learning runtime detail'}</span>
      </div>
      <div className="mc-row-meta">
        <StatusPill status={item.learningEngineMode || 'retain'} />
        {item.confidence ? <small>{humanizeToken(item.confidence)}</small> : null}
        {item.createdAt ? <small>{formatFreshness(item.createdAt)}</small> : null}
        <ChevronRight size={14} />
      </div>
    </button>
  )
}

/* ─── Main component ─── */

export function LivingMindTab({ data, onOpenItem, onHeartbeatTick, heartbeatBusy = false }) {
  const summary = data?.summary || {}
  const heartbeat = data?.heartbeat || {}
  const heartbeatState = heartbeat?.state || {}
  const heartbeatPolicy = heartbeat?.policy || {}
  const heartbeatTicks = heartbeat?.recentTicks || []
  const heartbeatEvents = heartbeat?.recentEvents || []
  const heartbeatMetabolicSummary = metabolicHeartbeatSummary(summary?.heartbeat || {})
  const embodiedState = data?.embodiedState || heartbeat?.embodiedState || {}
  const hasEmbodiedState = Boolean(embodiedState?.state && embodiedState.state !== 'unknown')
  const loopRuntime = data?.loopRuntime || heartbeat?.loopRuntime || data?.runtimeSelfModel?.loop_runtime || {}
  const loopRuntimeSummaryData = loopRuntime?.summary || {}
  const hasLoopRuntime = Boolean(loopRuntimeSummaryData.loopCount || loopRuntime?.active)
  const loopRuntimeCountsData = loopRuntimeCountSummary(loopRuntime)
  const visibleLoopRuntimeItems = (loopRuntime?.items || []).slice(0, 3)
  const idleConsolidation = data?.idleConsolidation || heartbeat?.idleConsolidation || data?.runtimeSelfModel?.idle_consolidation || {}
  const idleConsolidationSummaryData = idleConsolidation?.summary || {}
  const hasIdleConsolidation = Boolean(
    idleConsolidation?.active ||
    idleConsolidation?.lastRunAt ||
    idleConsolidationSummaryData?.latestRecordId,
  )
  const dreamArticulation = data?.dreamArticulation || heartbeat?.dreamArticulation || data?.runtimeSelfModel?.dream_articulation || {}
  const dreamArticulationSummaryData = dreamArticulation?.summary || {}
  const hasDreamArticulation = Boolean(
    dreamArticulation?.active ||
    dreamArticulation?.lastRunAt ||
    dreamArticulationSummaryData?.latestSignalId,
  )
  const promptEvolution = data?.promptEvolution || heartbeat?.promptEvolution || data?.development?.promptEvolution || data?.runtimeSelfModel?.prompt_evolution || {}
  const promptEvolutionSummaryData = promptEvolution?.summary || {}
  const hasPromptEvolution = Boolean(
    promptEvolution?.active ||
    promptEvolution?.lastRunAt ||
    promptEvolutionSummaryData?.latestProposalId,
  )
  const affectiveMetaState = data?.affectiveMetaState || heartbeat?.affectiveMetaState || data?.development?.affectiveMetaState || data?.runtimeSelfModel?.affective_meta_state || {}
  const hasAffectiveMetaState = Boolean(affectiveMetaState?.state && affectiveMetaState.state !== 'unknown')
  const epistemicRuntimeState = data?.epistemicRuntimeState || heartbeat?.epistemicRuntimeState || data?.development?.epistemicRuntimeState || data?.runtimeSelfModel?.epistemic_runtime_state || {}
  const hasEpistemicRuntimeState = Boolean(
    (epistemicRuntimeState?.wrongnessState && epistemicRuntimeState.wrongnessState !== 'clear') ||
    (epistemicRuntimeState?.regretSignal && epistemicRuntimeState.regretSignal !== 'none') ||
    (epistemicRuntimeState?.counterfactualMode && epistemicRuntimeState.counterfactualMode !== 'none'),
  )
  const subagentEcology = data?.subagentEcology || heartbeat?.subagentEcology || data?.development?.subagentEcology || data?.runtimeSelfModel?.subagent_ecology || {}
  const subagentEcologySummaryData = subagentEcology?.summary || {}
  const hasSubagentEcology = Boolean(subagentEcologySummaryData.roleCount || (subagentEcology?.roles || []).length)
  const subagentEcologyCountsData = subagentEcologyCountSummary(subagentEcology)
  const visibleSubagentRoles = (subagentEcology?.roles || []).slice(0, 3)
  const councilRuntime = data?.councilRuntime || heartbeat?.councilRuntime || data?.development?.councilRuntime || data?.runtimeSelfModel?.council_runtime || {}
  const hasCouncilRuntime = Boolean((councilRuntime?.participatingRoles || []).length || councilRuntime?.recommendation || councilRuntime?.councilState)
  const councilRuntimeRolesData = councilRuntimeRoleSummary(councilRuntime)
  const visibleCouncilRolePositions = (councilRuntime?.rolePositions || []).slice(0, 3).map((item) => ({
    ...item,
    source: councilRuntime.source || '/mc/council-runtime',
    createdAt: councilRuntime.createdAt,
  }))
  const adaptivePlanner = data?.adaptivePlanner || heartbeat?.adaptivePlanner || data?.development?.adaptivePlanner || data?.runtimeSelfModel?.adaptive_planner || {}
  const hasAdaptivePlanner = Boolean(adaptivePlanner?.plannerMode)
  const adaptiveReasoning = data?.adaptiveReasoning || heartbeat?.adaptiveReasoning || data?.development?.adaptiveReasoning || data?.runtimeSelfModel?.adaptive_reasoning || {}
  const hasAdaptiveReasoning = Boolean(adaptiveReasoning?.reasoningMode)
  const dreamInfluence = data?.dreamInfluence || heartbeat?.dreamInfluence || data?.runtimeSelfModel?.dream_influence || {}
  const hasDreamInfluence = Boolean(
    (dreamInfluence?.influenceState && dreamInfluence.influenceState !== 'quiet') ||
    (dreamInfluence?.influenceTarget && dreamInfluence.influenceTarget !== 'none'),
  )
  const guidedLearning = data?.guidedLearning || heartbeat?.guidedLearning || data?.development?.guidedLearning || data?.runtimeSelfModel?.guided_learning || {}
  const hasGuidedLearning = Boolean(guidedLearning?.learningMode)
  const adaptiveLearning = data?.adaptiveLearning || heartbeat?.adaptiveLearning || data?.development?.adaptiveLearning || data?.runtimeSelfModel?.adaptive_learning || {}
  const hasAdaptiveLearning = Boolean(adaptiveLearning?.learningEngineMode)
  const experientialRuntimeContext = data?.experientialRuntimeContext || {}
  const experientialEmbodied = experientialRuntimeContext?.embodiedTranslation || {}
  const experientialAffective = experientialRuntimeContext?.affectiveTranslation || {}
  const experientialIntermittence = experientialRuntimeContext?.intermittenceTranslation || {}
  const experientialPressure = experientialRuntimeContext?.contextPressureTranslation || {}
  const experientialContinuity = experientialRuntimeContext?.experientialContinuity || null
  const experientialInfluence = experientialRuntimeContext?.experientialInfluence || null
  const hasExperientialRuntimeContext = Boolean(
    experientialRuntimeContext?.kind === 'experiential-runtime-context' && (
      experientialEmbodied.state !== 'steady' ||
      experientialAffective.state !== 'settled' ||
      experientialIntermittence.state !== 'continuous' ||
      experientialPressure.state !== 'clear' ||
      (experientialContinuity && experientialContinuity.continuityState !== 'stable' && experientialContinuity.continuityState !== 'initial') ||
      (experientialInfluence && experientialInfluence.cognitiveBearing !== 'clear')
    ),
  )
  const internalCadence = data?.internalCadence || {}
  const sleepCadence = cadenceProducer(internalCadence, 'sleep_consolidation')
  const dreamCadence = cadenceProducer(internalCadence, 'dream_articulation')
  const promptEvolutionCadence = cadenceProducer(internalCadence, 'prompt_evolution_runtime')
  const webchatExecutionPilot = data?.development?.webchatExecutionPilot || { items: [], summary: {} }

  const features = [
    { id: 'embodied', label: 'Embodied State', icon: Cpu, active: hasEmbodiedState, status: embodiedState.state, statusLabel: embodiedState.state || 'unknown' },
    { id: 'loop', label: 'Loop Runtime', icon: Activity, active: hasLoopRuntime, status: loopRuntimeSummaryData.currentStatus, statusLabel: loopRuntimeSummaryData.currentStatus || 'idle' },
    { id: 'idle', label: 'Idle Consolidation', icon: Moon, active: hasIdleConsolidation, status: idleConsolidationSummaryData.lastState, statusLabel: idleConsolidationSummaryData.lastState || 'idle' },
    { id: 'dream', label: 'Dream Articulation', icon: Sparkles, active: hasDreamArticulation, status: dreamArticulationSummaryData.lastState, statusLabel: dreamArticulationSummaryData.lastState || 'idle' },
    { id: 'prompt', label: 'Prompt Evolution', icon: Wand2, active: hasPromptEvolution, status: promptEvolutionSummaryData.lastState, statusLabel: promptEvolutionSummaryData.lastState || 'idle' },
    { id: 'affective', label: 'Affective Meta', icon: Heart, active: hasAffectiveMetaState, status: affectiveMetaState.state, statusLabel: affectiveMetaState.state || 'unknown' },
    { id: 'epistemic', label: 'Epistemic State', icon: Brain, active: hasEpistemicRuntimeState, status: epistemicRuntimeState.wrongnessState, statusLabel: epistemicRuntimeState.wrongnessState || 'clear' },
    { id: 'subagent', label: 'Subagent Ecology', icon: Network, active: hasSubagentEcology, status: subagentEcologySummaryData.lastActiveRoleStatus, statusLabel: subagentEcologySummaryData.lastActiveRoleStatus || 'idle' },
    { id: 'council', label: 'Council Runtime', icon: Users, active: hasCouncilRuntime, status: councilRuntime.councilState, statusLabel: councilRuntime.councilState || 'quiet' },
    { id: 'planner', label: 'Adaptive Planner', icon: Map, active: hasAdaptivePlanner, status: adaptivePlanner.plannerMode, statusLabel: adaptivePlanner.plannerMode || 'incremental' },
    { id: 'reasoning', label: 'Adaptive Reasoning', icon: Lightbulb, active: hasAdaptiveReasoning, status: adaptiveReasoning.reasoningMode, statusLabel: adaptiveReasoning.reasoningMode || 'direct' },
    { id: 'dream-influence', label: 'Dream Influence', icon: Sparkles, active: hasDreamInfluence, status: dreamInfluence.influenceState, statusLabel: dreamInfluence.influenceState || 'quiet' },
    { id: 'guided', label: 'Guided Learning', icon: GraduationCap, active: hasGuidedLearning, status: guidedLearning.learningMode, statusLabel: guidedLearning.learningMode || 'reinforce' },
    { id: 'adaptive', label: 'Adaptive Learning', icon: TrendingUp, active: hasAdaptiveLearning, status: adaptiveLearning.learningEngineMode, statusLabel: adaptiveLearning.learningEngineMode || 'retain' },
    { id: 'experiential', label: 'Experiential Context', icon: Activity, active: hasExperientialRuntimeContext, status: experientialEmbodied.initiativeGate, statusLabel: experientialEmbodied.state || 'steady' },
  ]

  return (
    <div className="mc-tab-page">

      {/* ─── Feature Status Grid ─── */}
      <div className="feature-status-grid">
        {features.filter(f => f.active).map(f => (
          <div key={f.id} className={`feature-status-card ${f.status !== 'unknown' && f.status !== 'idle' && f.status !== 'quiet' && f.status !== 'clear' ? 'active' : ''}`}>
            <div className="feature-status-card-header">
              <f.icon size={12} />
              <span className="feature-status-card-label">{f.label}</span>
            </div>
            <div className="feature-status-card-meta mono">{f.statusLabel}</div>
          </div>
        ))}
      </div>

      {/* ─── Summary Cards ─── */}
      <section className="mc-summary-grid">
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
          <strong>{humanizeToken(loopRuntimeSummaryData.currentStatus) || 'unknown'}</strong>
          <small className="muted">
            {loopRuntimeCountsData.join(' · ') || 'No active runtime loops'}
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
          <strong>{humanizeToken(idleConsolidationSummaryData.lastState) || 'idle'}</strong>
          <small className="muted">
            {humanizeToken(idleConsolidationSummaryData.lastReason) || 'no run yet'}
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
          <strong>{humanizeToken(dreamArticulationSummaryData.lastState || cadenceProducerLabel(dreamCadence, 'idle')) || 'idle'}</strong>
          <small className="muted">
            {humanizeToken(dreamArticulationSummaryData.lastReason || dreamCadence?.lastTickStatus?.reason) || 'no run yet'}
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
          <strong>{humanizeToken(promptEvolutionSummaryData.lastState || cadenceProducerLabel(promptEvolutionCadence, 'idle')) || 'idle'}</strong>
          <small className="muted">
            {(promptEvolutionSummaryData.latestTargetAsset && promptEvolutionSummaryData.latestTargetAsset !== 'none'
              ? `${promptEvolutionSummaryData.latestTargetAsset} · `
              : '') + (humanizeToken(promptEvolutionSummaryData.lastReason || promptEvolutionCadence?.lastTickStatus?.reason) || 'no run yet')}
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
          <strong>{humanizeToken(subagentEcologySummaryData.lastActiveRoleName) || 'idle ecology'}</strong>
          <small className="muted">
            {(subagentEcologyCountsData.join(' · ') || `${subagentEcologySummaryData.roleCount || 0} roles`) +
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
            {`${councilRuntimeRolesData.join(' · ') || 'no roles'} · ${humanizeToken(councilRuntime.divergenceLevel) || 'low'} divergence${councilRuntime.createdAt ? ` · ${formatFreshness(councilRuntime.createdAt)}` : ''}`}
          </small>
        </article>
        ) : null}
        {hasAdaptivePlanner ? (
        <article className="mc-stat tone-blue" title={sectionTitleWithMeta({
          source: adaptivePlanner.source || '/mc/adaptive-planner',
          fetchedAt: adaptivePlanner.createdAt || data?.fetchedAt,
          mode: 'adaptive planner runtime snapshot',
        })}>
          <span>Adaptive Planner</span>
          <strong>{humanizeToken(adaptivePlanner.plannerMode) || 'incremental'}</strong>
          <small className="muted">
            {`horizon ${humanizeToken(adaptivePlanner.planHorizon) || 'near'} · risk ${humanizeToken(adaptivePlanner.riskPosture) || 'balanced'}${adaptivePlanner.createdAt ? ` · ${formatFreshness(adaptivePlanner.createdAt)}` : ''}`}
          </small>
        </article>
        ) : null}
        {hasAdaptiveReasoning ? (
        <article className="mc-stat tone-blue" title={sectionTitleWithMeta({
          source: adaptiveReasoning.source || '/mc/adaptive-reasoning',
          fetchedAt: adaptiveReasoning.createdAt || data?.fetchedAt,
          mode: 'adaptive reasoning runtime snapshot',
        })}>
          <span>Adaptive Reasoning</span>
          <strong>{humanizeToken(adaptiveReasoning.reasoningMode) || 'direct'}</strong>
          <small className="muted">
            {`posture ${humanizeToken(adaptiveReasoning.reasoningPosture) || 'balanced'} · certainty ${humanizeToken(adaptiveReasoning.certaintyStyle) || 'cautious'}${adaptiveReasoning.createdAt ? ` · ${formatFreshness(adaptiveReasoning.createdAt)}` : ''}`}
          </small>
        </article>
        ) : null}
        {hasDreamInfluence ? (
        <article className="mc-stat tone-blue" title={sectionTitleWithMeta({
          source: dreamInfluence.source || '/mc/dream-influence',
          fetchedAt: dreamInfluence.createdAt || data?.fetchedAt,
          mode: 'dream influence runtime snapshot',
        })}>
          <span>Dream Influence</span>
          <strong>{humanizeToken(dreamInfluence.influenceState) || 'quiet'}</strong>
          <small className="muted">
            {`target ${humanizeToken(dreamInfluence.influenceTarget) || 'none'} · mode ${humanizeToken(dreamInfluence.influenceMode) || 'stabilize'} · strength ${humanizeToken(dreamInfluence.influenceStrength) || 'none'}${dreamInfluence.createdAt ? ` · ${formatFreshness(dreamInfluence.createdAt)}` : ''}`}
          </small>
        </article>
        ) : null}
        {hasGuidedLearning ? (
        <article className="mc-stat tone-blue" title={sectionTitleWithMeta({
          source: guidedLearning.source || '/mc/guided-learning',
          fetchedAt: guidedLearning.createdAt || data?.fetchedAt,
          mode: 'guided learning runtime snapshot',
        })}>
          <span>Guided Learning</span>
          <strong>{humanizeToken(guidedLearning.learningMode) || 'reinforce'}</strong>
          <small className="muted">
            {`focus ${humanizeToken(guidedLearning.learningFocus) || 'reasoning'} · pressure ${humanizeToken(guidedLearning.learningPressure) || 'low'}${guidedLearning.createdAt ? ` · ${formatFreshness(guidedLearning.createdAt)}` : ''}`}
          </small>
        </article>
        ) : null}
        {hasAdaptiveLearning ? (
        <article className="mc-stat tone-blue" title={sectionTitleWithMeta({
          source: adaptiveLearning.source || '/mc/adaptive-learning',
          fetchedAt: adaptiveLearning.createdAt || data?.fetchedAt,
          mode: 'adaptive learning runtime snapshot',
        })}>
          <span>Adaptive Learning</span>
          <strong>{humanizeToken(adaptiveLearning.learningEngineMode) || 'retain'}</strong>
          <small className="muted">
            {`target ${humanizeToken(adaptiveLearning.reinforcementTarget) || 'reasoning'} · maturation ${humanizeToken(adaptiveLearning.maturationState) || 'early'}${adaptiveLearning.createdAt ? ` · ${formatFreshness(adaptiveLearning.createdAt)}` : ''}`}
          </small>
        </article>
        ) : null}
        {hasExperientialRuntimeContext ? (
        <article className="mc-stat tone-blue" title={sectionTitleWithMeta({
          source: experientialRuntimeContext.source || '/mc/experiential-runtime-context',
          fetchedAt: experientialRuntimeContext.createdAt || data?.fetchedAt,
          mode: 'experiential runtime context (derived-runtime-truth)',
        })}>
          <span>Experiential Context</span>
          <strong>{humanizeToken(experientialEmbodied.state) || 'steady'}</strong>
          <small className="muted">
            {`tone ${humanizeToken(experientialAffective.state) || 'settled'} · gap ${humanizeToken(experientialIntermittence.state) || 'continuous'} · pressure ${humanizeToken(experientialPressure.state) || 'clear'}`}
            {experientialRuntimeContext.createdAt ? ` · ${formatFreshness(experientialRuntimeContext.createdAt)}` : ''}
          </small>
          {experientialContinuity && experientialContinuity.continuityState ? (
          <small className="muted">
            {`continuity ${humanizeToken(experientialContinuity.continuityState)}`}
            {experientialContinuity.stateShiftSummary && experientialContinuity.stateShiftSummary !== 'No dimensional shifts.' ? ` · ${experientialContinuity.stateShiftSummary}` : ''}
          </small>
          ) : null}
          {experientialInfluence ? (
          <small className="muted">
            {`influence: bearing ${humanizeToken(experientialInfluence.cognitiveBearing)} · attention ${humanizeToken(experientialInfluence.attentionalPosture)} · initiative ${humanizeToken(experientialInfluence.initiativeShading)}`}
          </small>
          ) : null}
        </article>
        ) : null}
      </section>

      {/* ─── Heartbeat Section ─── */}
      <section className="mc-section-grid">
        <article className="support-card" id="living-mind-heartbeat" title={sectionTitleWithMeta({
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
                {heartbeatBusy ? 'Ticking\u2026' : 'Tick now'}
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
                {experientialRuntimeContextRow(experientialRuntimeContext, onOpenItem)}
                {epistemicRuntimeStateRow(epistemicRuntimeState, onOpenItem)}
                {subagentEcologyRow(subagentEcology, onOpenItem)}
                {councilRuntimeRow(councilRuntime, onOpenItem)}
                {adaptivePlannerRow(adaptivePlanner, onOpenItem)}
                {adaptiveReasoningRow(adaptiveReasoning, onOpenItem)}
                {dreamInfluenceRow(dreamInfluence, onOpenItem)}
                {guidedLearningRow(guidedLearning, onOpenItem)}
                {adaptiveLearningRow(adaptiveLearning, onOpenItem)}
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
    </div>
  )
}
