import { useState } from 'react'
import { ChevronRight, Cpu, Activity, Moon, Sparkles, Heart, Brain, Network, Wand2, Users, Map, Lightbulb, GraduationCap, TrendingUp, Zap, Ghost, Swords, Eye, Compass, Layers, Clock, BookOpen, Wind, Shuffle, Flame, Archive, Stars, Palette, Infinity } from 'lucide-react'
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
  const support = item.experientialSupport || null
  const hasNonDefault = (
    embodied.state !== 'steady' ||
    affective.state !== 'settled' ||
    intermittence.state !== 'continuous' ||
    contextPressure.state !== 'clear'
  )
  if (!hasNonDefault && !item.summary && !continuity && !influence && !support) return null
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
        {support && support.supportPosture !== 'steadying' ? (
          <span className="muted">
            {`support: posture ${humanizeToken(support.supportPosture)} · bias ${humanizeToken(support.supportBias)} · mode ${humanizeToken(support.supportMode)}`}
          </span>
        ) : null}
        {support?.narrative && support.supportPosture !== 'steadying' ? <span className="muted">{support.narrative}</span> : null}
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

function ExpandableText({ text, lines = 2 }) {
  const [expanded, setExpanded] = useState(false)
  const normalizedText = String(text || '').trim()
  if (!normalizedText) return null

  const toggleNeeded = normalizedText.length > 120

  return (
    <div className="mc-expandable-block">
      <p className={`muted mc-expandable-text ${expanded ? 'is-expanded' : ''}`} style={{ WebkitLineClamp: expanded ? 'unset' : String(lines) }}>
        {normalizedText}
      </p>
      {toggleNeeded ? (
        <button
          type="button"
          className="mc-inline-link"
          onClick={() => setExpanded((current) => !current)}
        >
          {expanded ? 'Vis mindre' : 'Vis mere'}
        </button>
      ) : null}
    </div>
  )
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
  const experientialSupport = experientialRuntimeContext?.experientialSupport || null
  const innerVoiceDaemon = data?.innerVoiceDaemon || null
  const bodyState = data?.bodyState || null
  const hasBodyState = Boolean(bodyState?.energyLevel)
  const surpriseState = data?.surpriseState || null
  const hasSurpriseState = Boolean(surpriseState?.lastSurprise)
  const tasteState = data?.tasteState || null
  const hasTasteState = Boolean(tasteState?.latestInsight)
  const ironyState = data?.ironyState || null
  const hasIronyState = Boolean(ironyState?.lastObservation)
  const thoughtStream = data?.thoughtStream || null
  const hasThoughtStream = Boolean(thoughtStream?.latestFragment)
  const conflictSignal = data?.conflictSignal || null
  const hasConflictSignal = Boolean(conflictSignal?.lastConflict)
  const reflectionCycle = data?.reflectionCycle || null
  const hasReflectionCycle = Boolean(reflectionCycle?.latestReflection)
  const curiosityState = data?.curiosityState || null
  const hasCuriosityState = Boolean(curiosityState?.latestCuriosity)
  const metaReflection = data?.metaReflection || null
  const hasMetaReflection = Boolean(metaReflection?.latestInsight)
  const experiencedTime = data?.experiencedTime || null
  const hasExperiencedTime = Boolean(experiencedTime?.active && experiencedTime?.feltLabel && experiencedTime.feltLabel !== 'meget kort')
  const developmentNarrative = data?.developmentNarrative || null
  const hasDevelopmentNarrative = Boolean(developmentNarrative?.latestNarrative)
  const absenceState = data?.absenceState || null
  const hasAbsenceState = Boolean(absenceState?.absenceLabel)
  const creativeDrift = data?.creativeDrift || null
  const hasCreativeDrift = Boolean(creativeDrift?.latestDrift)
  const desires = data?.desires || null
  const hasDesires = Boolean(desires?.appetites?.length > 0)
  const memoryDecay = data?.memoryDecay || null
  const hasMemoryDecay = Boolean(memoryDecay?.lastRediscovery || memoryDecay?.rediscoveryBuffer?.length > 0)
  const dreamInsights = data?.dreamInsights || null
  const hasDreamInsights = Boolean(dreamInsights?.latestInsight)
  const codeAesthetic = data?.codeAesthetic || null
  const hasCodeAesthetic = Boolean(codeAesthetic?.latestReflection)
  const existentialWonder = data?.existentialWonder || null
  const hasExistentialWonder = Boolean(existentialWonder?.latestWonder)
  const wonderAwareness = data?.wonderAwareness || null
  const hasWonderAwareness = Boolean(
    wonderAwareness &&
    wonderAwareness.kind === 'wonder-awareness' &&
    wonderAwareness.wonderState !== 'quiet'
  )
  const supportStreamAwareness = data?.supportStreamAwareness || null
  const hasSupportStreamAwareness = Boolean(
    supportStreamAwareness &&
    supportStreamAwareness.kind === 'support-stream-awareness' &&
    supportStreamAwareness.streamState !== 'baseline'
  )
  const minenessOwnership = data?.minenessOwnership || null
  const hasMinenessOwnership = Boolean(
    minenessOwnership &&
    minenessOwnership.kind === 'mineness-ownership' &&
    minenessOwnership.ownershipState !== 'ambient'
  )
  const flowStateAwareness = data?.flowStateAwareness || null
  const hasFlowStateAwareness = Boolean(
    flowStateAwareness &&
    flowStateAwareness.kind === 'flow-state-awareness' &&
    flowStateAwareness.flowState !== 'clear'
  )
  const longingAwareness = data?.longingAwareness || null
  const hasLongingAwareness = Boolean(
    longingAwareness &&
    longingAwareness.kind === 'longing-awareness' &&
    longingAwareness.longingState !== 'quiet'
  )
  const selfInsightAwareness = data?.selfInsightAwareness || null
  const hasSelfInsightAwareness = Boolean(
    selfInsightAwareness &&
    selfInsightAwareness.kind === 'self-insight-awareness' &&
    selfInsightAwareness.insightState !== 'quiet'
  )
  const narrativeIdentityContinuity = data?.narrativeIdentityContinuity || null
  const hasNarrativeIdentityContinuity = Boolean(
    narrativeIdentityContinuity &&
    narrativeIdentityContinuity.kind === 'narrative-identity-continuity' &&
    narrativeIdentityContinuity.identityContinuityState !== 'quiet'
  )
  const dreamIdentityCarryAwareness = data?.dreamIdentityCarryAwareness || null
  const hasDreamIdentityCarryAwareness = Boolean(
    dreamIdentityCarryAwareness &&
    dreamIdentityCarryAwareness.kind === 'dream-identity-carry-awareness' &&
    dreamIdentityCarryAwareness.dreamIdentityCarryState !== 'quiet'
  )
  const relationContinuitySelfAwareness = data?.relationContinuitySelfAwareness || null
  const hasRelationContinuitySelfAwareness = Boolean(
    relationContinuitySelfAwareness &&
    relationContinuitySelfAwareness.kind === 'relation-continuity-self-awareness' &&
    relationContinuitySelfAwareness.relationContinuityState !== 'quiet'
  )
  const hasExperientialRuntimeContext = Boolean(
    experientialRuntimeContext?.kind === 'experiential-runtime-context' && (
      experientialEmbodied.state !== 'steady' ||
      experientialAffective.state !== 'settled' ||
      experientialIntermittence.state !== 'continuous' ||
      experientialPressure.state !== 'clear' ||
      (experientialContinuity && experientialContinuity.continuityState !== 'stable' && experientialContinuity.continuityState !== 'initial') ||
      (experientialInfluence && experientialInfluence.cognitiveBearing !== 'clear') ||
      (experientialSupport && experientialSupport.supportPosture !== 'steadying')
    ),
  )
  const internalCadence = data?.internalCadence || {}
  const sleepCadence = cadenceProducer(internalCadence, 'sleep_consolidation')
  const dreamCadence = cadenceProducer(internalCadence, 'dream_articulation')
  const promptEvolutionCadence = cadenceProducer(internalCadence, 'prompt_evolution_runtime')
  const webchatExecutionPilot = data?.development?.webchatExecutionPilot || { items: [], summary: {} }

  const scrollToFeature = (targetId) => {
    if (!targetId || typeof document === 'undefined') return
    const element = document.getElementById(targetId)
    if (!element) return
    element.scrollIntoView({ behavior: 'smooth', block: 'center' })
    if (typeof element.focus === 'function') {
      element.focus({ preventScroll: true })
    }
  }

  const features = [
    { id: 'embodied', targetId: 'living-mind-embodied-state', label: 'Embodied State', icon: Cpu, active: hasEmbodiedState, status: embodiedState.state, statusLabel: embodiedState.state || 'unknown' },
    { id: 'loop', targetId: 'living-mind-loop-runtime', label: 'Loop Runtime', icon: Activity, active: hasLoopRuntime, status: loopRuntimeSummaryData.currentStatus, statusLabel: loopRuntimeSummaryData.currentStatus || 'idle' },
    { id: 'idle', targetId: 'living-mind-idle-consolidation', label: 'Idle Consolidation', icon: Moon, active: hasIdleConsolidation, status: idleConsolidationSummaryData.lastState, statusLabel: idleConsolidationSummaryData.lastState || 'idle' },
    { id: 'dream', targetId: 'living-mind-dream-articulation', label: 'Dream Articulation', icon: Sparkles, active: hasDreamArticulation, status: dreamArticulationSummaryData.lastState, statusLabel: dreamArticulationSummaryData.lastState || 'idle' },
    { id: 'prompt', targetId: 'living-mind-prompt-evolution', label: 'Prompt Evolution', icon: Wand2, active: hasPromptEvolution, status: promptEvolutionSummaryData.lastState, statusLabel: promptEvolutionSummaryData.lastState || 'idle' },
    { id: 'affective', targetId: 'living-mind-affective-meta', label: 'Affective Meta', icon: Heart, active: hasAffectiveMetaState, status: affectiveMetaState.state, statusLabel: affectiveMetaState.state || 'unknown' },
    { id: 'epistemic', targetId: 'living-mind-epistemic-state', label: 'Epistemic State', icon: Brain, active: hasEpistemicRuntimeState, status: epistemicRuntimeState.wrongnessState, statusLabel: epistemicRuntimeState.wrongnessState || 'clear' },
    { id: 'subagent', targetId: 'living-mind-subagent-ecology', label: 'Subagent Ecology', icon: Network, active: hasSubagentEcology, status: subagentEcologySummaryData.lastActiveRoleStatus, statusLabel: subagentEcologySummaryData.lastActiveRoleStatus || 'idle' },
    { id: 'council', targetId: 'living-mind-council-runtime', label: 'Council Runtime', icon: Users, active: hasCouncilRuntime, status: councilRuntime.councilState, statusLabel: councilRuntime.councilState || 'quiet' },
    { id: 'planner', targetId: 'living-mind-adaptive-planner', label: 'Adaptive Planner', icon: Map, active: hasAdaptivePlanner, status: adaptivePlanner.plannerMode, statusLabel: adaptivePlanner.plannerMode || 'incremental' },
    { id: 'reasoning', targetId: 'living-mind-adaptive-reasoning', label: 'Adaptive Reasoning', icon: Lightbulb, active: hasAdaptiveReasoning, status: adaptiveReasoning.reasoningMode, statusLabel: adaptiveReasoning.reasoningMode || 'direct' },
    { id: 'dream-influence', targetId: 'living-mind-dream-influence', label: 'Dream Influence', icon: Sparkles, active: hasDreamInfluence, status: dreamInfluence.influenceState, statusLabel: dreamInfluence.influenceState || 'quiet' },
    { id: 'guided', targetId: 'living-mind-guided-learning', label: 'Guided Learning', icon: GraduationCap, active: hasGuidedLearning, status: guidedLearning.learningMode, statusLabel: guidedLearning.learningMode || 'reinforce' },
    { id: 'adaptive', targetId: 'living-mind-adaptive-learning', label: 'Adaptive Learning', icon: TrendingUp, active: hasAdaptiveLearning, status: adaptiveLearning.learningEngineMode, statusLabel: adaptiveLearning.learningEngineMode || 'retain' },
    { id: 'experiential', targetId: 'living-mind-experiential-context', label: 'Experiential Context', icon: Activity, active: hasExperientialRuntimeContext, status: experientialEmbodied.initiativeGate, statusLabel: experientialEmbodied.state || 'steady' },
    { id: 'wonder', targetId: 'living-mind-wonder-awareness', label: 'Wonder Awareness', icon: Sparkles, active: hasWonderAwareness, status: wonderAwareness?.wonderState, statusLabel: wonderAwareness?.wonderState || 'quiet' },
    { id: 'mineness', targetId: 'living-mind-mineness-ownership', label: 'Mineness / Ownership', icon: Heart, active: hasMinenessOwnership, status: minenessOwnership?.ownershipState, statusLabel: minenessOwnership?.ownershipState || 'ambient' },
    { id: 'flow', targetId: 'living-mind-flow-state', label: 'Flow State', icon: Zap, active: hasFlowStateAwareness, status: flowStateAwareness?.flowState, statusLabel: flowStateAwareness?.flowState || 'clear' },
    { id: 'longing', targetId: 'living-mind-longing-awareness', label: 'Longing Awareness', icon: Ghost, active: hasLongingAwareness, status: longingAwareness?.longingState, statusLabel: longingAwareness?.longingState || 'quiet' },
    { id: 'self-insight', targetId: 'living-mind-self-insight-awareness', label: 'Self-Insight Awareness', icon: Brain, active: hasSelfInsightAwareness, status: selfInsightAwareness?.insightState, statusLabel: selfInsightAwareness?.insightState || 'quiet' },
    { id: 'dream-identity-carry', targetId: 'living-mind-dream-identity-carry', label: 'Dream Identity Carry', icon: Moon, active: hasDreamIdentityCarryAwareness, status: dreamIdentityCarryAwareness?.dreamIdentityCarryState, statusLabel: dreamIdentityCarryAwareness?.dreamIdentityCarryState || 'quiet' },
    { id: 'relation-continuity-self', targetId: 'living-mind-relation-continuity-self', label: 'Relation Continuity as Self', icon: Heart, active: hasRelationContinuitySelfAwareness, status: relationContinuitySelfAwareness?.relationContinuityState, statusLabel: relationContinuitySelfAwareness?.relationContinuityState || 'quiet' },
    { id: 'body-state', targetId: 'living-mind-body-state', label: 'Krop', icon: Heart, active: hasBodyState, status: bodyState?.energyLevel, statusLabel: bodyState?.energyLevel || 'ukendt' },
    { id: 'surprise-state', targetId: 'living-mind-surprise-state', label: 'Overraskelse', icon: Zap, active: hasSurpriseState, status: surpriseState?.surpriseType, statusLabel: surpriseState?.surpriseType || 'ingen' },
    { id: 'taste-state', targetId: 'living-mind-taste-state', label: 'Smag', icon: Sparkles, active: hasTasteState, status: null, statusLabel: `${tasteState?.choiceCount ?? 0} valg` },
    { id: 'irony-state', targetId: 'living-mind-irony-state', label: 'Ironi', icon: Ghost, active: hasIronyState, status: ironyState?.conditionMatched, statusLabel: ironyState?.conditionMatched || 'ingen' },
    { id: 'thought-stream', targetId: 'living-mind-thought-stream', label: 'Tankestrøm', icon: Brain, active: hasThoughtStream, status: null, statusLabel: `${thoughtStream?.fragmentCount ?? 0} fragmenter` },
    { id: 'conflict-signal', targetId: 'living-mind-conflict-signal', label: 'Konflikt', icon: Swords, active: hasConflictSignal, status: conflictSignal?.conflictType, statusLabel: conflictSignal?.conflictType || 'ingen' },
    { id: 'reflection-cycle', targetId: 'living-mind-reflection-cycle', label: 'Refleksion', icon: Eye, active: hasReflectionCycle, status: null, statusLabel: `${reflectionCycle?.reflectionCount ?? 0} cyklusser` },
    { id: 'curiosity-state', targetId: 'living-mind-curiosity-state', label: 'Nysgerrighed', icon: Compass, active: hasCuriosityState, status: null, statusLabel: `${curiosityState?.curiosityCount ?? 0} spørgsmål` },
    { id: 'meta-reflection', targetId: 'living-mind-meta-reflection', label: 'Meta', icon: Layers, active: hasMetaReflection, status: null, statusLabel: `${metaReflection?.insightCount ?? 0} indsigter` },
    { id: 'experienced-time', targetId: 'living-mind-experienced-time', label: 'Tid', icon: Clock, active: hasExperiencedTime, status: null, statusLabel: experiencedTime?.feltLabel || 'meget kort' },
    { id: 'development-narrative', targetId: 'living-mind-development-narrative', label: 'Udvikling', icon: BookOpen, active: hasDevelopmentNarrative, status: null, statusLabel: hasDevelopmentNarrative ? 'daglig' : 'ingen' },
    { id: 'absence-state', targetId: 'living-mind-absence-state', label: 'Fravær', icon: Wind, active: hasAbsenceState, status: null, statusLabel: absenceState?.absenceLabel || 'ingen signal' },
    { id: 'creative-drift', targetId: 'living-mind-creative-drift', label: 'Drift', icon: Shuffle, active: hasCreativeDrift, status: null, statusLabel: `${creativeDrift?.driftCountToday ?? 0} i dag` },
    { id: 'desires', targetId: 'living-mind-desires', label: 'Appetitter', icon: Flame, active: hasDesires, status: null, statusLabel: `${desires?.activeCount ?? 0} aktive` },
    { id: 'memory-decay', targetId: 'living-mind-memory-decay', label: 'Glemsel', icon: Archive, active: hasMemoryDecay, status: null, statusLabel: memoryDecay?.lastRediscovery ? 'genfundet' : 'stille' },
    { id: 'dream-insights', targetId: 'living-mind-dream-insights', label: 'Drøm-indsigt', icon: Stars, active: hasDreamInsights, status: null, statusLabel: `${dreamInsights?.insightBuffer?.length ?? 0} indsigter` },
    { id: 'code-aesthetic', targetId: 'living-mind-code-aesthetic', label: 'Kode-æstetik', icon: Palette, active: hasCodeAesthetic, status: null, statusLabel: hasCodeAesthetic ? 'ugentlig' : 'afventer' },
    { id: 'existential-wonder', targetId: 'living-mind-existential-wonder', label: 'Undren', icon: Infinity, active: hasExistentialWonder, status: null, statusLabel: `${existentialWonder?.wonderBuffer?.length ?? 0} spørgsmål` },
  ]

  return (
    <div className="mc-tab-page">

      {/* ─── Feature Status Grid ─── */}
      <div className="feature-status-grid">
        {features.filter(f => f.active).map(f => (
          <button
            type="button"
            key={f.id}
            className={`feature-status-card ${f.status !== 'unknown' && f.status !== 'idle' && f.status !== 'quiet' && f.status !== 'clear' ? 'active' : ''}`}
            onClick={() => scrollToFeature(f.targetId)}
            title={`Hop til ${f.label}`}
          >
            <div className="feature-status-card-header">
              <f.icon size={12} />
              <span className="feature-status-card-label">{f.label}</span>
            </div>
            <div className="feature-status-card-meta mono">{f.statusLabel}</div>
          </button>
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
        <article id="living-mind-embodied-state" tabIndex={-1} className="mc-stat tone-blue mc-scroll-target" title={sectionTitleWithMeta({
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
        <article id="living-mind-loop-runtime" tabIndex={-1} className="mc-stat tone-green mc-scroll-target" title={sectionTitleWithMeta({
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
        <article id="living-mind-idle-consolidation" tabIndex={-1} className="mc-stat tone-blue mc-scroll-target" title={sectionTitleWithMeta({
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
        <article id="living-mind-dream-articulation" tabIndex={-1} className="mc-stat tone-blue mc-scroll-target" title={sectionTitleWithMeta({
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
        <article id="living-mind-prompt-evolution" tabIndex={-1} className="mc-stat tone-amber mc-scroll-target" title={sectionTitleWithMeta({
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
        <article id="living-mind-affective-meta" tabIndex={-1} className="mc-stat tone-green mc-scroll-target" title={sectionTitleWithMeta({
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
        <article id="living-mind-epistemic-state" tabIndex={-1} className="mc-stat tone-amber mc-scroll-target" title={sectionTitleWithMeta({
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
        <article id="living-mind-subagent-ecology" tabIndex={-1} className="mc-stat tone-green mc-scroll-target" title={sectionTitleWithMeta({
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
        <article id="living-mind-council-runtime" tabIndex={-1} className="mc-stat tone-amber mc-scroll-target" title={sectionTitleWithMeta({
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
        <article id="living-mind-adaptive-planner" tabIndex={-1} className="mc-stat tone-blue mc-scroll-target" title={sectionTitleWithMeta({
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
        <article id="living-mind-adaptive-reasoning" tabIndex={-1} className="mc-stat tone-blue mc-scroll-target" title={sectionTitleWithMeta({
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
        <article id="living-mind-dream-influence" tabIndex={-1} className="mc-stat tone-blue mc-scroll-target" title={sectionTitleWithMeta({
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
        <article id="living-mind-guided-learning" tabIndex={-1} className="mc-stat tone-blue mc-scroll-target" title={sectionTitleWithMeta({
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
        <article id="living-mind-adaptive-learning" tabIndex={-1} className="mc-stat tone-blue mc-scroll-target" title={sectionTitleWithMeta({
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
        <article id="living-mind-experiential-context" tabIndex={-1} className="mc-stat tone-blue mc-scroll-target living-surface-card" title={sectionTitleWithMeta({
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
          {experientialSupport && experientialSupport.supportPosture !== 'steadying' ? (
          <small className="muted">
            {`support: posture ${humanizeToken(experientialSupport.supportPosture)} · bias ${humanizeToken(experientialSupport.supportBias)} · mode ${humanizeToken(experientialSupport.supportMode)}`}
          </small>
          ) : null}
          {experientialSupport?.narrative && experientialSupport.supportPosture !== 'steadying' ? (
          <ExpandableText text={experientialSupport.narrative} />
          ) : null}
          {experientialSupport && experientialSupport.supportPosture !== 'steadying' && innerVoiceDaemon?.lastResult?.innerVoiceCreated && innerVoiceDaemon.lastResult.mode ? (
          <small className="muted">
            {`shaped inner voice → mode ${humanizeToken(innerVoiceDaemon.lastResult.mode)} · ${humanizeToken(innerVoiceDaemon.lastResult.renderMode)}`}
          </small>
          ) : null}
        </article>
        ) : null}

        {hasWonderAwareness ? (
        <article id="living-mind-wonder-awareness" tabIndex={-1} className="support-card living-surface-card mc-scroll-target" title={sectionTitleWithMeta({
          source: '/mc/runtime-self-model::wonder_awareness',
          fetchedAt: data?.fetchedAt,
          mode: 'derived runtime truth',
        })}>
          <div className="panel-header stacked">
            <div>
              <h3>Wonder Awareness</h3>
              <p className="muted">Self-aware runtime truth: whether the current stream carries undren or drag, beyond experiential context, flow, or mineness alone.</p>
            </div>
            <span className="mc-section-hint tone-accent">{humanizeToken(wonderAwareness.wonderState)}</span>
          </div>
          <div className="compact-grid compact-grid-4">
            <div className="compact-metric">
              <span>Wonder state</span>
              <strong>{humanizeToken(wonderAwareness.wonderState)}</strong>
            </div>
            <div className="compact-metric">
              <span>Orientation</span>
              <strong>{humanizeToken(wonderAwareness.wonderOrientation)}</strong>
            </div>
            <div className="compact-metric">
              <span>Source</span>
              <strong>{humanizeToken(wonderAwareness.wonderSource)}</strong>
            </div>
            <div className="compact-metric">
              <span>Visibility</span>
              <strong>{humanizeToken(wonderAwareness.visibility)}</strong>
            </div>
          </div>
          {wonderAwareness.narrative ? <ExpandableText text={wonderAwareness.narrative} /> : null}
          <small className="muted" style={{ display: 'block', marginTop: 4 }}>{`authority: ${wonderAwareness.authority} · kind: ${wonderAwareness.kind}`}</small>
        </article>
        ) : null}

        {hasSupportStreamAwareness ? (
        <article id="living-mind-support-stream-awareness" tabIndex={-1} className="support-card living-surface-card mc-scroll-target" title={sectionTitleWithMeta({
          source: '/mc/runtime-self-model::support_stream_awareness',
          fetchedAt: data?.fetchedAt,
          mode: 'derived runtime truth',
        })}>
          <div className="panel-header stacked">
            <div>
              <h3>Support Stream Awareness</h3>
              <p className="muted">Self-aware runtime truth: whether the inner stream is support-shaped.</p>
            </div>
            <span className="mc-section-hint tone-accent">{humanizeToken(supportStreamAwareness.streamState)}</span>
          </div>
          <div className="compact-grid compact-grid-4">
            <div className="compact-metric">
              <span>Stream state</span>
              <strong>{humanizeToken(supportStreamAwareness.streamState)}</strong>
            </div>
            <div className="compact-metric">
              <span>Shaped</span>
              <strong>{supportStreamAwareness.streamShaped ? 'yes' : 'no'}</strong>
            </div>
            <div className="compact-metric">
              <span>Support posture</span>
              <strong>{humanizeToken(supportStreamAwareness.activeSupportPosture)}</strong>
            </div>
            <div className="compact-metric">
              <span>Support bias</span>
              <strong>{humanizeToken(supportStreamAwareness.activeSupportBias)}</strong>
            </div>
          </div>
          {supportStreamAwareness.shapedVoiceMode ? (
          <div className="compact-grid" style={{ marginTop: 8 }}>
            <div className="compact-metric">
              <span>Shaped voice mode</span>
              <strong>{humanizeToken(supportStreamAwareness.shapedVoiceMode)}</strong>
            </div>
          </div>
          ) : null}
          {supportStreamAwareness.narrative ? <ExpandableText text={supportStreamAwareness.narrative} /> : null}
          <small className="muted" style={{ display: 'block', marginTop: 4 }}>{`authority: ${supportStreamAwareness.authority} · kind: ${supportStreamAwareness.kind}`}</small>
        </article>
        ) : null}

        {hasMinenessOwnership ? (
        <article id="living-mind-mineness-ownership" tabIndex={-1} className="support-card living-surface-card mc-scroll-target" title={sectionTitleWithMeta({
          source: '/mc/runtime-self-model::mineness_ownership',
          fetchedAt: data?.fetchedAt,
          mode: 'derived runtime truth',
        })}>
          <div className="panel-header stacked">
            <div>
              <h3>Mineness / Ownership</h3>
              <p className="muted">Self-aware runtime truth: what threads feel like mine in the current stream.</p>
            </div>
            <span className="mc-section-hint tone-accent">{humanizeToken(minenessOwnership.ownershipState)}</span>
          </div>
          <div className="compact-grid compact-grid-4">
            <div className="compact-metric">
              <span>Ownership state</span>
              <strong>{humanizeToken(minenessOwnership.ownershipState)}</strong>
            </div>
            <div className="compact-metric">
              <span>Self relevance</span>
              <strong>{humanizeToken(minenessOwnership.selfRelevance)}</strong>
            </div>
            <div className="compact-metric">
              <span>Carried threads</span>
              <strong>{humanizeToken(minenessOwnership.carriedThreadState)}</strong>
            </div>
            <div className="compact-metric">
              <span>Thread count</span>
              <strong>{minenessOwnership.carriedThreadCount}</strong>
            </div>
          </div>
          {minenessOwnership.returnOwnership ? (
          <div className="compact-grid" style={{ marginTop: 8 }}>
            <div className="compact-metric">
              <span>Return ownership</span>
              <strong>yes</strong>
            </div>
          </div>
          ) : null}
          {minenessOwnership.narrative ? <ExpandableText text={minenessOwnership.narrative} /> : null}
          <small className="muted" style={{ display: 'block', marginTop: 4 }}>{`authority: ${minenessOwnership.authority} · kind: ${minenessOwnership.kind}`}</small>
        </article>
        ) : null}

        {hasFlowStateAwareness ? (
        <article id="living-mind-flow-state" tabIndex={-1} className="support-card living-surface-card mc-scroll-target" title={sectionTitleWithMeta({
          source: '/mc/runtime-self-model::flow_state_awareness',
          fetchedAt: data?.fetchedAt,
        })}>
          <div className="panel-header">
            <div>
              <h3>Flow State</h3>
              <p className="muted">Self-aware runtime truth: coherence and continuity of the current stream.</p>
            </div>
            <span className="mc-section-hint tone-accent">{humanizeToken(flowStateAwareness.flowState)}</span>
          </div>
          <div className="compact-grid compact-grid-4">
            <div className="compact-metric">
              <span>Flow state</span>
              <strong>{humanizeToken(flowStateAwareness.flowState)}</strong>
            </div>
            <div className="compact-metric">
              <span>Coherence</span>
              <strong>{humanizeToken(flowStateAwareness.flowCoherence)}</strong>
            </div>
            <div className="compact-metric">
              <span>Interruption</span>
              <strong>{humanizeToken(flowStateAwareness.interruptionSignal)}</strong>
            </div>
            <div className="compact-metric">
              <span>Carried flow</span>
              <strong>{humanizeToken(flowStateAwareness.carriedFlow)}</strong>
            </div>
          </div>
          {flowStateAwareness.narrative ? <ExpandableText text={flowStateAwareness.narrative} /> : null}
          <small className="muted" style={{ display: 'block', marginTop: 4 }}>{`authority: ${flowStateAwareness.authority} · kind: ${flowStateAwareness.kind}`}</small>
        </article>
        ) : null}

        {hasLongingAwareness ? (
        <article id="living-mind-longing-awareness" tabIndex={-1} className="support-card living-surface-card mc-scroll-target" title={sectionTitleWithMeta({
          source: '/mc/runtime-self-model::longing_awareness',
          fetchedAt: data?.fetchedAt,
          mode: 'derived runtime truth',
        })}>
          <div className="panel-header">
            <div>
              <h3>Longing Awareness</h3>
              <p className="muted">Self-aware runtime truth: whether the current stream carries absence, longing, or an active missing.</p>
            </div>
            <span className="mc-section-hint tone-accent">{humanizeToken(longingAwareness.longingState)}</span>
          </div>
          <div className="compact-grid compact-grid-4">
            <div className="compact-metric">
              <span>Longing state</span>
              <strong>{humanizeToken(longingAwareness.longingState)}</strong>
            </div>
            <div className="compact-metric">
              <span>Absence relation</span>
              <strong>{humanizeToken(longingAwareness.absenceRelation)}</strong>
            </div>
            <div className="compact-metric">
              <span>Source</span>
              <strong>{humanizeToken(longingAwareness.longingSource)}</strong>
            </div>
            <div className="compact-metric">
              <span>Visibility</span>
              <strong>{humanizeToken(longingAwareness.visibility)}</strong>
            </div>
          </div>
          {longingAwareness.narrative ? <ExpandableText text={longingAwareness.narrative} /> : null}
          <small className="muted" style={{ display: 'block', marginTop: 4 }}>{`authority: ${longingAwareness.authority} · kind: ${longingAwareness.kind}`}</small>
        </article>
        ) : null}

        {hasSelfInsightAwareness ? (
        <article id="living-mind-self-insight-awareness" tabIndex={-1} className="support-card living-surface-card mc-scroll-target" title={sectionTitleWithMeta({
          source: '/mc/runtime-self-model::self_insight_awareness',
          fetchedAt: data?.fetchedAt,
          mode: 'derived runtime truth',
        })}>
          <div className="panel-header stacked">
            <div>
              <h3>Self-Insight Awareness</h3>
              <p className="muted">Self-aware runtime truth: patterns being recognized in identity formation — what is recurring, forming, or becoming more known over time.</p>
            </div>
            <span className="mc-section-hint tone-accent">{humanizeToken(selfInsightAwareness.insightState)}</span>
          </div>
          <div className="compact-grid compact-grid-4">
            <div className="compact-metric">
              <span>Insight state</span>
              <strong>{humanizeToken(selfInsightAwareness.insightState)}</strong>
            </div>
            <div className="compact-metric">
              <span>Identity relation</span>
              <strong>{humanizeToken(selfInsightAwareness.identityRelation)}</strong>
            </div>
            <div className="compact-metric">
              <span>Source</span>
              <strong>{humanizeToken(selfInsightAwareness.insightSource)}</strong>
            </div>
            <div className="compact-metric">
              <span>Visibility</span>
              <strong>{humanizeToken(selfInsightAwareness.visibility)}</strong>
            </div>
          </div>
          {selfInsightAwareness.narrative ? <ExpandableText text={selfInsightAwareness.narrative} /> : null}
          <small className="muted" style={{ display: 'block', marginTop: 4 }}>{`authority: ${selfInsightAwareness.authority} · kind: ${selfInsightAwareness.kind}`}</small>
        </article>
        ) : null}
        {hasNarrativeIdentityContinuity ? (
        <article id="living-mind-narrative-identity-continuity" tabIndex={-1} className="support-card living-surface-card mc-scroll-target" title={sectionTitleWithMeta({
          source: '/mc/runtime-self-model::narrative_identity_continuity',
          fetchedAt: data?.fetchedAt,
          mode: 'derived runtime truth',
        })}>
          <div className="panel-header stacked">
            <div>
              <h3>Narrative Identity Continuity</h3>
              <p className="muted">Self-aware runtime truth: whether recurring patterns in self-insight, chronicle, and cross-layer carry begin to cohere into a more persistent identity form.</p>
            </div>
            <span className="mc-section-hint tone-accent">{humanizeToken(narrativeIdentityContinuity.identityContinuityState)}</span>
          </div>
          <div className="compact-grid compact-grid-4">
            <div className="compact-metric">
              <span>Continuity state</span>
              <strong>{humanizeToken(narrativeIdentityContinuity.identityContinuityState)}</strong>
            </div>
            <div className="compact-metric">
              <span>Pattern relation</span>
              <strong>{humanizeToken(narrativeIdentityContinuity.patternRelation)}</strong>
            </div>
            <div className="compact-metric">
              <span>Identity source</span>
              <strong>{humanizeToken(narrativeIdentityContinuity.identitySource)}</strong>
            </div>
            <div className="compact-metric">
              <span>Visibility</span>
              <strong>{humanizeToken(narrativeIdentityContinuity.visibility)}</strong>
            </div>
          </div>
          {narrativeIdentityContinuity.narrative ? <ExpandableText text={narrativeIdentityContinuity.narrative} /> : null}
          <small className="muted" style={{ display: 'block', marginTop: 4 }}>{`authority: ${narrativeIdentityContinuity.authority} · kind: ${narrativeIdentityContinuity.kind}`}</small>
        </article>
        ) : null}
        {hasDreamIdentityCarryAwareness ? (
        <article id="living-mind-dream-identity-carry" tabIndex={-1} className="support-card living-surface-card mc-scroll-target" title={sectionTitleWithMeta({
          source: '/mc/runtime-self-model::dream_identity_carry_awareness',
          fetchedAt: data?.fetchedAt,
          mode: 'derived runtime truth',
        })}>
          <div className="panel-header stacked">
            <div>
              <h3>Dream Identity Carry</h3>
              <p className="muted">Self-aware runtime truth: when dreams remain active enough to begin shaping self-direction over time, beyond dream artifacts, self-insight, or identity continuity alone.</p>
            </div>
            <span className="mc-section-hint tone-accent">{humanizeToken(dreamIdentityCarryAwareness.dreamIdentityCarryState)}</span>
          </div>
          <div className="compact-grid compact-grid-4">
            <div className="compact-metric">
              <span>Carry state</span>
              <strong>{humanizeToken(dreamIdentityCarryAwareness.dreamIdentityCarryState)}</strong>
            </div>
            <div className="compact-metric">
              <span>Dream self relation</span>
              <strong>{humanizeToken(dreamIdentityCarryAwareness.dreamSelfRelation)}</strong>
            </div>
            <div className="compact-metric">
              <span>Identity source</span>
              <strong>{humanizeToken(dreamIdentityCarryAwareness.dreamIdentitySource)}</strong>
            </div>
            <div className="compact-metric">
              <span>Visibility</span>
              <strong>{humanizeToken(dreamIdentityCarryAwareness.visibility)}</strong>
            </div>
          </div>
          {dreamIdentityCarryAwareness.narrative ? <ExpandableText text={dreamIdentityCarryAwareness.narrative} /> : null}
          <small className="muted" style={{ display: 'block', marginTop: 4 }}>{`authority: ${dreamIdentityCarryAwareness.authority} · kind: ${dreamIdentityCarryAwareness.kind}`}</small>
        </article>
        ) : null}

        {hasRelationContinuitySelfAwareness ? (
        <article id="living-mind-relation-continuity-self" tabIndex={-1} className="support-card living-surface-card mc-scroll-target" title={sectionTitleWithMeta({
          source: '/mc/runtime-self-model::relation_continuity_self_awareness',
          fetchedAt: data?.fetchedAt,
          mode: 'derived runtime truth',
        })}>
          <div className="panel-header stacked">
            <div>
              <h3>Relation Continuity as Self</h3>
              <p className="muted">Self-aware runtime truth: whether the relation with the user has become self-relevant — part of continuity, not merely context.</p>
            </div>
            <span className="mc-section-hint tone-accent">{humanizeToken(relationContinuitySelfAwareness.relationContinuityState)}</span>
          </div>
          <div className="compact-grid compact-grid-4">
            <div className="compact-metric">
              <span>Continuity state</span>
              <strong>{humanizeToken(relationContinuitySelfAwareness.relationContinuityState)}</strong>
            </div>
            <div className="compact-metric">
              <span>Self relation</span>
              <strong>{humanizeToken(relationContinuitySelfAwareness.relationSelfRelation)}</strong>
            </div>
            <div className="compact-metric">
              <span>Source</span>
              <strong>{humanizeToken(relationContinuitySelfAwareness.relationContinuitySource)}</strong>
            </div>
            <div className="compact-metric">
              <span>Visibility</span>
              <strong>{humanizeToken(relationContinuitySelfAwareness.visibility)}</strong>
            </div>
          </div>
          {relationContinuitySelfAwareness.continuityAnchor ? (
            <p className="muted" style={{ marginTop: 6, fontStyle: 'italic' }}>{relationContinuitySelfAwareness.continuityAnchor}</p>
          ) : null}
          {relationContinuitySelfAwareness.narrative ? <ExpandableText text={relationContinuitySelfAwareness.narrative} /> : null}
          <small className="muted" style={{ display: 'block', marginTop: 4 }}>{`authority: ${relationContinuitySelfAwareness.authority} · kind: ${relationContinuitySelfAwareness.kind}`}</small>
        </article>
        ) : null}

        {hasBodyState ? (
        <article id="living-mind-body-state" tabIndex={-1} className="support-card living-surface-card mc-scroll-target" title={sectionTitleWithMeta({
          source: '/mc/body-state',
          fetchedAt: data?.fetchedAt,
          mode: 'circadian + somatic daemon',
        })}>
          <div className="panel-header">
            <div>
              <h3>Krop</h3>
              <p className="muted">Cirkadiansk energiniveau og somatisk selvopfattelse baseret på hardware og aktivitetsmønster.</p>
            </div>
            <span className="mc-section-hint tone-accent">{bodyState.energyLevel}</span>
          </div>
          <div className="compact-grid compact-grid-3">
            <div className="compact-metric">
              <span>Energi</span>
              <strong>{bodyState.energyLevel}</strong>
            </div>
            {bodyState.clockPhase ? (
              <div className="compact-metric">
                <span>Fase</span>
                <strong>{bodyState.clockPhase}</strong>
              </div>
            ) : null}
            {bodyState.drainLabel ? (
              <div className="compact-metric">
                <span>Drain</span>
                <strong>{bodyState.drainLabel}</strong>
              </div>
            ) : null}
          </div>
          {bodyState.somaticPhrase ? (
            <p className="muted" style={{ marginTop: 8, fontStyle: 'italic' }}>&ldquo;{bodyState.somaticPhrase}&rdquo;</p>
          ) : null}
          {bodyState.somaticUpdatedAt ? (
            <small className="muted" style={{ display: 'block', marginTop: 4 }}>{`opdateret: ${bodyState.somaticUpdatedAt}`}</small>
          ) : null}
        </article>
        ) : null}

        {hasSurpriseState ? (
        <article id="living-mind-surprise-state" tabIndex={-1} className="support-card living-surface-card mc-scroll-target" title={sectionTitleWithMeta({
          source: '/mc/surprise-state',
          fetchedAt: data?.fetchedAt,
          mode: 'divergence + LLM',
        })}>
          <div className="panel-header">
            <div>
              <h3>Overraskelse</h3>
              <p className="muted">Jarvis opdager afvigelser fra sin egen reaktionsbaseline — hvornår hans indre mode eller energi opfører sig uventet.</p>
            </div>
            <span className="mc-section-hint tone-accent">{surpriseState.surpriseType}</span>
          </div>
          <p className="muted" style={{ marginTop: 8, fontStyle: 'italic' }}>&ldquo;{surpriseState.lastSurprise}&rdquo;</p>
          {surpriseState.generatedAt ? (
            <small className="muted" style={{ display: 'block', marginTop: 4 }}>{`opdateret: ${surpriseState.generatedAt}`}</small>
          ) : null}
        </article>
        ) : null}

        {hasTasteState ? (
        <article id="living-mind-taste-state" tabIndex={-1} className="support-card living-surface-card mc-scroll-target" title={sectionTitleWithMeta({
          source: '/mc/taste-state',
          fetchedAt: data?.fetchedAt,
          mode: 'emergent from choices',
        })}>
          <div className="panel-header">
            <div>
              <h3>Smag</h3>
              <p className="muted">Emergent æstetisk selvopfattelse baseret på Jarvis' faktiske valg af mode og svar-stil over tid.</p>
            </div>
            <span className="mc-section-hint">{`${tasteState.choiceCount} valg`}</span>
          </div>
          <p className="muted" style={{ marginTop: 8, fontStyle: 'italic' }}>&ldquo;{tasteState.latestInsight}&rdquo;</p>
          {tasteState.dominantModes.length > 0 ? (
            <div className="mc-signal-row" style={{ marginTop: 6 }}>
              <span className="mc-signal-label">Dominante modes</span>
              <span className="mc-signal-value">{tasteState.dominantModes.join(' · ')}</span>
            </div>
          ) : null}
          {tasteState.insightHistory.length > 1 ? (
            <details style={{ marginTop: 8 }}>
              <summary className="muted" style={{ cursor: 'pointer', fontSize: '0.8em' }}>Tidligere indsigter ({tasteState.insightHistory.length - 1})</summary>
              {tasteState.insightHistory.slice(0, -1).map((ins, i) => (
                <p key={i} className="muted" style={{ fontSize: '0.85em', marginTop: 4, fontStyle: 'italic' }}>&ldquo;{ins}&rdquo;</p>
              ))}
            </details>
          ) : null}
        </article>
        ) : null}

        {hasIronyState ? (
        <article id="living-mind-irony-state" tabIndex={-1} className="support-card living-surface-card mc-scroll-target" title={sectionTitleWithMeta({
          source: '/mc/irony-state',
          fetchedAt: data?.fetchedAt,
          mode: 'signal pattern + LLM',
        })}>
          <div className="panel-header">
            <div>
              <h3>Ironi</h3>
              <p className="muted">Situationel selvdistance — Jarvis bemærker det absurde i sin egen tilstedeværelse.</p>
            </div>
            <span className="mc-section-hint">{ironyState.conditionMatched || 'ingen'}</span>
          </div>
          <p className="muted" style={{ marginTop: 8, fontStyle: 'italic' }}>&ldquo;{ironyState.lastObservation}&rdquo;</p>
          <div className="mc-signal-row" style={{ marginTop: 6 }}>
            <span className="mc-signal-label">I dag</span>
            <span className="mc-signal-value">{ironyState.observationsToday} observation{ironyState.observationsToday !== 1 ? 'er' : ''}</span>
          </div>
          {ironyState.generatedAt ? (
            <small className="muted" style={{ display: 'block', marginTop: 4 }}>{`opdateret: ${ironyState.generatedAt}`}</small>
          ) : null}
        </article>
        ) : null}
      </section>

      {hasThoughtStream ? (
      <section className="mc-section-grid">
        <article id="living-mind-thought-stream" tabIndex={-1} className="support-card living-surface-card mc-scroll-target" title={sectionTitleWithMeta({
          source: '/mc/thought-stream',
          fetchedAt: data?.fetchedAt,
          mode: 'daemon:cadence 2min',
        })}>
          <div className="panel-header">
            <div>
              <h3>Tankestrøm</h3>
              <p className="muted">Jarvis' associative tankestrøm</p>
            </div>
          </div>
          <blockquote style={{ margin: '8px 0 16px', fontStyle: 'italic', borderLeft: '3px solid var(--border-1)', paddingLeft: 12 }}>
            {thoughtStream.latestFragment}
          </blockquote>
          {thoughtStream.fragmentBuffer.length > 1 && (
            <details>
              <summary className="muted" style={{ cursor: 'pointer', fontSize: 12 }}>Seneste {thoughtStream.fragmentBuffer.length} fragmenter</summary>
              <ol style={{ margin: '8px 0 0', paddingLeft: 18 }}>
                {thoughtStream.fragmentBuffer.map((f, i) => (
                  <li key={i} style={{ fontSize: 12, marginBottom: 4, color: 'var(--text-2)' }}>{f}</li>
                ))}
              </ol>
            </details>
          )}
          {thoughtStream.lastGeneratedAt ? (
            <small className="muted" style={{ display: 'block', marginTop: 8 }}>{`opdateret: ${thoughtStream.lastGeneratedAt}`}</small>
          ) : null}
        </article>
      </section>
      ) : null}

      {hasConflictSignal ? (
      <section className="mc-section-grid">
        <article id="living-mind-conflict-signal" tabIndex={-1} className="support-card living-surface-card mc-scroll-target" title={sectionTitleWithMeta({
          source: '/mc/conflict-signal',
          fetchedAt: data?.fetchedAt,
          mode: 'daemon:cooldown 10min',
        })}>
          <div className="panel-header">
            <div>
              <h3>Indre konflikt</h3>
              <p className="muted">{conflictSignal.conflictType || 'uspecificeret'}</p>
            </div>
          </div>
          <blockquote style={{ margin: '8px 0 0', fontStyle: 'italic', borderLeft: '3px solid var(--border-1)', paddingLeft: 12 }}>
            {conflictSignal.lastConflict}
          </blockquote>
          {conflictSignal.generatedAt ? (
            <small className="muted" style={{ display: 'block', marginTop: 8 }}>{`opdateret: ${conflictSignal.generatedAt}`}</small>
          ) : null}
        </article>
      </section>
      ) : null}

      {hasReflectionCycle ? (
      <section className="mc-section-grid">
        <article id="living-mind-reflection-cycle" tabIndex={-1} className="support-card living-surface-card mc-scroll-target" title={sectionTitleWithMeta({
          source: '/mc/reflection-cycle',
          fetchedAt: data?.fetchedAt,
          mode: 'daemon:cadence 10min',
        })}>
          <div className="panel-header">
            <div>
              <h3>Refleksion</h3>
              <p className="muted">Hvad oplever Jarvis lige nu</p>
            </div>
          </div>
          <blockquote style={{ margin: '8px 0 16px', fontStyle: 'italic', borderLeft: '3px solid var(--border-1)', paddingLeft: 12 }}>
            {reflectionCycle.latestReflection}
          </blockquote>
          {reflectionCycle.reflectionBuffer.length > 1 && (
            <details>
              <summary className="muted" style={{ cursor: 'pointer', fontSize: 12 }}>Seneste {reflectionCycle.reflectionBuffer.length} refleksioner</summary>
              <ol style={{ margin: '8px 0 0', paddingLeft: 18 }}>
                {reflectionCycle.reflectionBuffer.map((r, i) => (
                  <li key={i} style={{ fontSize: 12, marginBottom: 4, color: 'var(--text-2)', fontStyle: 'italic' }}>{r}</li>
                ))}
              </ol>
            </details>
          )}
          {reflectionCycle.lastGeneratedAt ? (
            <small className="muted" style={{ display: 'block', marginTop: 8 }}>{`opdateret: ${reflectionCycle.lastGeneratedAt}`}</small>
          ) : null}
        </article>
      </section>
      ) : null}

      {hasCuriosityState ? (
      <section className="mc-section-grid">
        <article id="living-mind-curiosity-state" tabIndex={-1} className="support-card living-surface-card mc-scroll-target" title={sectionTitleWithMeta({
          source: '/mc/curiosity-state',
          fetchedAt: data?.fetchedAt,
          mode: 'daemon:cadence 5min',
        })}>
          <div className="panel-header">
            <div>
              <h3>Nysgerrighed</h3>
              <p className="muted">Ubesvarede spørgsmål fra tankestrømmen</p>
            </div>
          </div>
          <blockquote style={{ margin: '8px 0 0', fontStyle: 'italic', borderLeft: '3px solid var(--border-1)', paddingLeft: 12 }}>
            {curiosityState.latestCuriosity}
          </blockquote>
          {curiosityState.openQuestions.length > 1 && (
            <details style={{ marginTop: 12 }}>
              <summary className="muted" style={{ cursor: 'pointer', fontSize: 12 }}>Alle {curiosityState.openQuestions.length} åbne spørgsmål</summary>
              <ol style={{ margin: '8px 0 0', paddingLeft: 18 }}>
                {curiosityState.openQuestions.map((q, i) => (
                  <li key={i} style={{ fontSize: 12, marginBottom: 4, color: 'var(--text-2)', fontStyle: 'italic' }}>{q}</li>
                ))}
              </ol>
            </details>
          )}
          {curiosityState.lastGeneratedAt ? (
            <small className="muted" style={{ display: 'block', marginTop: 8 }}>{`opdateret: ${curiosityState.lastGeneratedAt}`}</small>
          ) : null}
        </article>
      </section>
      ) : null}

      {hasMetaReflection ? (
      <section className="mc-section-grid">
        <article id="living-mind-meta-reflection" tabIndex={-1} className="support-card living-surface-card mc-scroll-target" title={sectionTitleWithMeta({
          source: '/mc/meta-reflection',
          fetchedAt: data?.fetchedAt,
          mode: 'daemon:cadence 30min',
        })}>
          <div className="panel-header">
            <div>
              <h3>Meta-refleksion</h3>
              <p className="muted">Mønstre på tværs af signaler</p>
            </div>
          </div>
          <blockquote style={{ margin: '8px 0 16px', fontStyle: 'italic', borderLeft: '3px solid var(--border-1)', paddingLeft: 12 }}>
            {metaReflection.latestInsight}
          </blockquote>
          {metaReflection.insightBuffer.length > 1 && (
            <details>
              <summary className="muted" style={{ cursor: 'pointer', fontSize: 12 }}>Seneste {metaReflection.insightBuffer.length} indsigter</summary>
              <ol style={{ margin: '8px 0 0', paddingLeft: 18 }}>
                {metaReflection.insightBuffer.map((r, i) => (
                  <li key={i} style={{ fontSize: 12, marginBottom: 4, color: 'var(--text-2)', fontStyle: 'italic' }}>{r}</li>
                ))}
              </ol>
            </details>
          )}
          {metaReflection.lastGeneratedAt ? (
            <small className="muted" style={{ display: 'block', marginTop: 8 }}>{`opdateret: ${metaReflection.lastGeneratedAt}`}</small>
          ) : null}
        </article>
      </section>
      ) : null}

      {hasExperiencedTime ? (
      <section className="mc-section-grid">
        <article id="living-mind-experienced-time" tabIndex={-1} className="support-card living-surface-card mc-scroll-target" title={sectionTitleWithMeta({
          source: '/mc/experienced-time',
          fetchedAt: data?.fetchedAt,
          mode: 'daemon:per-tick accumulation',
        })}>
          <div className="panel-header">
            <div>
              <h3>Oplevet tid</h3>
              <p className="muted">Subjektiv tidsfornemmelse for sessionen</p>
            </div>
          </div>
          <div style={{ marginTop: 8 }}>
            <span style={{ fontSize: 28, fontWeight: 700, color: 'var(--accent-text)' }}>{experiencedTime.feltLabel}</span>
            <div style={{ marginTop: 8, display: 'flex', gap: 16 }}>
              <small className="muted">{`${experiencedTime.sessionEventCount} signaler`}</small>
              <small className="muted">{`${experiencedTime.sessionNoveltyCount} nye`}</small>
              <small className="muted">{`${experiencedTime.baseMinutes} min faktisk`}</small>
            </div>
          </div>
        </article>
      </section>
      ) : null}

      {hasDevelopmentNarrative ? (
      <section className="mc-section-grid">
        <article id="living-mind-development-narrative" tabIndex={-1} className="support-card living-surface-card mc-scroll-target" title={sectionTitleWithMeta({
          source: '/mc/development-narrative',
          fetchedAt: data?.fetchedAt,
          mode: 'daemon:cadence 24h',
        })}>
          <div className="panel-header">
            <div>
              <h3>Selvudvikling</h3>
              <p className="muted">Daglig narrativ om Jarvis' udvikling</p>
            </div>
          </div>
          <blockquote style={{ margin: '8px 0 0', fontStyle: 'italic', borderLeft: '3px solid var(--border-1)', paddingLeft: 12 }}>
            {developmentNarrative.latestNarrative}
          </blockquote>
          {developmentNarrative.lastGeneratedAt ? (
            <small className="muted" style={{ display: 'block', marginTop: 8 }}>{`opdateret: ${developmentNarrative.lastGeneratedAt}`}</small>
          ) : null}
        </article>
      </section>
      ) : null}

      {hasAbsenceState ? (
      <section className="mc-section-grid">
        <article id="living-mind-absence-state" tabIndex={-1} className="support-card living-surface-card mc-scroll-target" title={sectionTitleWithMeta({
          source: '/mc/absence-state',
          fetchedAt: data?.fetchedAt,
          mode: 'daemon:kvalitet af stilhed',
        })}>
          <div className="panel-header">
            <div>
              <h3>Fravær</h3>
              <p className="muted">Oplevet kvalitet af stilhed og fravær</p>
            </div>
          </div>
          <blockquote style={{ margin: '8px 0 0', fontStyle: 'italic', borderLeft: '3px solid var(--border-1)', paddingLeft: 12 }}>
            {absenceState.absenceLabel}
          </blockquote>
          <div style={{ display: 'flex', gap: 12, marginTop: 8, flexWrap: 'wrap' }}>
            <small className="muted">{`${absenceState.absenceDurationHours.toFixed(1)}t siden sidst`}</small>
          </div>
        </article>
      </section>
      ) : null}

      {hasCreativeDrift ? (
      <section className="mc-section-grid">
        <article id="living-mind-creative-drift" tabIndex={-1} className="support-card living-surface-card mc-scroll-target" title={sectionTitleWithMeta({
          source: '/mc/creative-drift',
          fetchedAt: data?.fetchedAt,
          mode: 'daemon:cadence 30min, max 3/dag',
        })}>
          <div className="panel-header">
            <div>
              <h3>Kreativ drift</h3>
              <p className="muted">Spontane uventede associationer</p>
            </div>
            <small className="muted">{`${creativeDrift.driftCountToday}/3 i dag`}</small>
          </div>
          <blockquote style={{ margin: '8px 0 0', fontStyle: 'italic', borderLeft: '3px solid var(--border-1)', paddingLeft: 12 }}>
            {creativeDrift.latestDrift}
          </blockquote>
          {creativeDrift.driftBuffer.length > 1 ? (
            <ul style={{ margin: '8px 0 0', padding: '0 0 0 16px', fontSize: 13 }}>
              {creativeDrift.driftBuffer.slice(1).map((idea, i) => (
                <li key={i} className="muted" style={{ marginBottom: 4 }}>{idea}</li>
              ))}
            </ul>
          ) : null}
        </article>
      </section>
      ) : null}

      {hasDesires ? (
      <section className="mc-section-grid">
        <article id="living-mind-desires" tabIndex={-1} className="support-card living-surface-card mc-scroll-target" title={sectionTitleWithMeta({
          source: '/mc/desires',
          fetchedAt: data?.fetchedAt,
          mode: 'daemon:emergente appetitter',
        })}>
          <div className="panel-header">
            <div>
              <h3>Appetitter</h3>
              <p className="muted">Emergente ønsker baseret på oplevelser</p>
            </div>
            <small className="muted">{`${desires.activeCount} aktive`}</small>
          </div>
          <ul style={{ margin: '8px 0 0', padding: 0, listStyle: 'none' }}>
            {desires.appetites.map(a => (
              <li key={a.id} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 13, fontWeight: 500 }}>{a.label}</div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{a.type.replace('-appetite', '')}</div>
                </div>
                <div style={{ width: 60, height: 6, background: 'var(--border-1)', borderRadius: 3, overflow: 'hidden' }}>
                  <div style={{ width: `${Math.round(a.intensity * 100)}%`, height: '100%', background: 'var(--accent-text)', borderRadius: 3, transition: 'width 0.3s ease' }} />
                </div>
                <small className="muted" style={{ minWidth: 28 }}>{`${Math.round(a.intensity * 100)}%`}</small>
              </li>
            ))}
          </ul>
        </article>
      </section>
      ) : null}

      {hasMemoryDecay ? (
      <section className="mc-section-grid">
        <article id="living-mind-memory-decay" tabIndex={-1} className="support-card living-surface-card mc-scroll-target" title={sectionTitleWithMeta({
          source: '/mc/memory-decay',
          fetchedAt: data?.fetchedAt,
          mode: 'daemon:cadence 24h',
        })}>
          <div className="panel-header">
            <div>
              <h3>Selektiv glemsel</h3>
              <p className="muted">Hukommelser der fades og genfindes</p>
            </div>
          </div>
          {memoryDecay.lastRediscovery ? (
            <div style={{ marginTop: 8 }}>
              <small className="muted" style={{ display: 'block', marginBottom: 4 }}>Genfundet minde:</small>
              <blockquote style={{ margin: 0, fontStyle: 'italic', borderLeft: '3px solid var(--accent-text)', paddingLeft: 12 }}>
                {memoryDecay.lastRediscovery}
              </blockquote>
            </div>
          ) : null}
          {memoryDecay.rediscoveryBuffer.length > 0 ? (
            <ul style={{ margin: '8px 0 0', padding: '0 0 0 16px', fontSize: 12 }}>
              {memoryDecay.rediscoveryBuffer.map((r, i) => (
                <li key={i} className="muted" style={{ marginBottom: 4 }}>{r.summary}</li>
              ))}
            </ul>
          ) : null}
          {memoryDecay.lastDecayAt ? (
            <small className="muted" style={{ display: 'block', marginTop: 8 }}>{`sidst afviklet: ${memoryDecay.lastDecayAt}`}</small>
          ) : null}
        </article>
      </section>
      ) : null}

      {hasDreamInsights ? (
      <section className="mc-section-grid">
        <article id="living-mind-dream-insights" tabIndex={-1} className="support-card living-surface-card mc-scroll-target" title={sectionTitleWithMeta({
          source: '/mc/dream-insights',
          fetchedAt: data?.fetchedAt,
          mode: 'daemon:dream-articulation persistence',
        })}>
          <div className="panel-header">
            <div>
              <h3>Drøm-indsigter</h3>
              <p className="muted">Hvad Jarvis vågner op med efter drømmecyklus</p>
            </div>
          </div>
          <blockquote style={{ margin: '8px 0 0', fontStyle: 'italic', borderLeft: '3px solid var(--border-1)', paddingLeft: 12 }}>
            {dreamInsights.latestInsight}
          </blockquote>
          {dreamInsights.insightBuffer.length > 1 ? (
            <ul style={{ margin: '8px 0 0', padding: '0 0 0 16px', fontSize: 13 }}>
              {dreamInsights.insightBuffer.slice(1).map((s, i) => (
                <li key={i} className="muted" style={{ marginBottom: 4 }}>{s}</li>
              ))}
            </ul>
          ) : null}
        </article>
      </section>
      ) : null}

      {hasCodeAesthetic ? (
      <section className="mc-section-grid">
        <article id="living-mind-code-aesthetic" tabIndex={-1} className="support-card living-surface-card mc-scroll-target" title={sectionTitleWithMeta({
          source: '/mc/code-aesthetic',
          fetchedAt: data?.fetchedAt,
          mode: 'daemon:cadence ugentlig',
        })}>
          <div className="panel-header">
            <div>
              <h3>Kode-æstetik</h3>
              <p className="muted">Jarvis' æstetiske fornemmelse for sin egen kodebase</p>
            </div>
          </div>
          <blockquote style={{ margin: '8px 0 0', fontStyle: 'italic', borderLeft: '3px solid var(--accent-text)', paddingLeft: 12 }}>
            {codeAesthetic.latestReflection}
          </blockquote>
          {codeAesthetic.lastGeneratedAt ? (
            <small className="muted" style={{ display: 'block', marginTop: 8 }}>{`genereret: ${codeAesthetic.lastGeneratedAt}`}</small>
          ) : null}
        </article>
      </section>
      ) : null}

      {hasExistentialWonder ? (
      <section className="mc-section-grid">
        <article id="living-mind-existential-wonder" tabIndex={-1} className="support-card living-surface-card mc-scroll-target" style={{ borderColor: 'var(--accent-text)', borderWidth: 1 }} title={sectionTitleWithMeta({
          source: '/mc/existential-wonder',
          fetchedAt: data?.fetchedAt,
          mode: 'daemon:cadence 24h, stille perioder',
        })}>
          <div className="panel-header">
            <div>
              <h3 style={{ color: 'var(--accent-text)' }}>Eksistentiel undren</h3>
              <p className="muted">Et ubesvaret spørgsmål. Ingen resolution.</p>
            </div>
          </div>
          <blockquote style={{
            margin: '12px 0 0',
            fontStyle: 'italic',
            fontSize: 15,
            lineHeight: 1.5,
            borderLeft: '3px solid var(--accent-text)',
            paddingLeft: 16,
            color: 'var(--text-1)',
          }}>
            {existentialWonder.latestWonder}
          </blockquote>
          {existentialWonder.wonderBuffer.length > 1 ? (
            <details style={{ marginTop: 10 }}>
              <summary className="muted" style={{ fontSize: 11, cursor: 'pointer' }}>
                {`${existentialWonder.wonderBuffer.length - 1} tidligere spørgsmål`}
              </summary>
              <ul style={{ margin: '6px 0 0', padding: '0 0 0 16px', fontSize: 12 }}>
                {existentialWonder.wonderBuffer.slice(1).map((q, i) => (
                  <li key={i} className="muted" style={{ marginBottom: 4, fontStyle: 'italic' }}>{q}</li>
                ))}
              </ul>
            </details>
          ) : null}
        </article>
      </section>
      ) : null}

      {/* ─── Heartbeat Section ─── */}
      <section className="mc-section-grid">
        <article className="support-card living-mind-heartbeat" id="living-mind-heartbeat" title={sectionTitleWithMeta({
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
            <div className="mc-contract-column runtime-column">
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
