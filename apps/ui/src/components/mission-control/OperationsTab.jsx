import { ChevronRight } from 'lucide-react'
import { MainAgentPanel } from '../shared/MainAgentPanel'
import { AutonomyProposalsPanel } from './AutonomyProposalsPanel'
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

function gitStewardshipLabel(item) {
  if (item?.mutatingExecRepoStewardshipDomain !== 'git') return ''
  if (!item?.mutatingExecGitMutationClass || item?.mutatingExecGitMutationClass === 'none') return ''
  return `git stewardship · ${humanizeToken(item.mutatingExecGitMutationClass)}`
}

function approvalTimingLabel(item) {
  if (item?.approvalState === 'pending' && item?.approvalExpiresAt) {
    return `expires ${formatFreshness(item.approvalExpiresAt)}`
  }
  if (item?.approvalResolvedAt) {
    return `resolved ${formatFreshness(item.approvalResolvedAt)}`
  }
  if (item?.approvalRequestedAt) {
    return `requested ${formatFreshness(item.approvalRequestedAt)}`
  }
  return ''
}

function executionTimingLabel(item) {
  if (item?.executionFinishedAt) {
    return `finished ${formatFreshness(item.executionFinishedAt)}`
  }
  if (item?.executionStartedAt) {
    return `started ${formatFreshness(item.executionStartedAt)}`
  }
  return ''
}

function summarizeMutationTargets(item) {
  const files = Array.isArray(item?.mutationTargetFiles) ? item.mutationTargetFiles : []
  const paths = Array.isArray(item?.mutationTargetPaths) ? item.mutationTargetPaths : []

  if (files.length > 0) {
    const preview = files.slice(0, 2).join(', ')
    const remainder = files.length > 2 ? ` +${files.length - 2} more` : ''
    return `${preview}${remainder}`
  }

  if (paths.length > 0) {
    const preview = paths.slice(0, 2).join(', ')
    const remainder = paths.length > 2 ? ` +${paths.length - 2} more` : ''
    return `${preview}${remainder}`
  }

  return 'No mutation targets recorded'
}

function mutationScopeSummary(item) {
  return [item?.mutationRepoScope, item?.mutationSystemScope].filter(Boolean).join(' · ')
}

function mutationGuardLabel(item) {
  return item?.mutationExecutionPermitted ? 'execution permitted' : 'proposal only'
}

function mutatingExecGuardLabel(item) {
  if (!item?.hasMutatingExecProposalSurface) return 'no proposal'
  return item?.mutatingExecRequiresApproval ? 'approval required' : 'review only'
}

function mutatingExecExecutionGuardLabel(item) {
  if (!item?.hasMutatingExecExecutionSurface) return 'not executed'
  return item?.mutatingExecApprovalMatched ? 'approved binding matched' : 'review binding'
}

function sudoExecGuardLabel(item) {
  if (!item?.hasSudoExecProposalSurface) return 'no sudo proposal'
  return item?.sudoExecRequiresApproval ? 'approval required' : 'review only'
}

function sudoApprovalWindowGuardLabel(item) {
  if (!item?.hasSudoApprovalWindowSurface) return 'no window'
  return item?.sudoApprovalWindowReusable ? 'reusable' : 'not reusable'
}

function toolIntentRow(item, onOpen) {
  if (!item || (!item.intentState && !item.intentType)) return null

  const detailText = [
    [
      item.executionState ? `execution ${humanizeToken(item.executionState)}` : '',
      item.executionMode ? `mode ${humanizeToken(item.executionMode)}` : '',
      item.approvalState ? `approval ${humanizeToken(item.approvalState)}` : '',
      item.approvalSource && item.approvalSource !== 'none' ? `source ${humanizeToken(item.approvalSource)}` : '',
      item.intentType ? `type ${humanizeToken(item.intentType)}` : '',
      item.hasGitRepoStewardshipProposalSurface ? gitStewardshipLabel(item) : '',
      item.hasMutationIntentSurface ? `mutation ${humanizeToken(item.mutationIntentClassification || 'none')}` : '',
      item.hasMutationIntentSurface ? `${item.mutationNear ? 'action-near' : 'not action-near'}` : '',
      item.executionTarget || item.intentTarget ? `target ${item.executionTarget || item.intentTarget}` : '',
      item.approvalScope ? `scope ${humanizeToken(item.approvalScope)}` : '',
    ].filter(Boolean).join(' · '),
    item.hasMutationIntentSurface ? summarizeMutationTargets(item) : '',
    item.executionSummary,
    item.intentReason,
    item.approvalResolutionMessage,
  ].filter(Boolean)[0] || 'Inspect bounded operational tool intent'

  const timingLabel = executionTimingLabel(item) || approvalTimingLabel(item)

  return (
    <button
      className="mc-list-row"
      onClick={() => onOpen('Tool Intent', { ...item, kind: 'approval-gated-tool-intent-light' })}
      title={sectionTitleWithMeta({
        source: item.source,
        fetchedAt: item.createdAt,
        mode: 'operations intent detail',
      })}
    >
      <div>
        <strong>Tool Intent</strong>
        <span>{detailText}</span>
      </div>
      <div className="mc-row-meta">
        <StatusPill status={item.intentState || 'idle'} />
        <StatusPill status={item.approvalState || 'none'} />
        <StatusPill status={item.executionState || 'not-executed'} />
        {item.hasMutationIntentSurface ? <StatusPill status={item.mutationIntentState || 'idle'} /> : null}
        {item.intentType ? <small>{humanizeToken(item.intentType)}</small> : null}
        {item.hasMutationIntentSurface ? <small>{humanizeToken(item.mutationIntentClassification || 'none')}</small> : null}
        {item.hasGitRepoStewardshipProposalSurface ? <small>{gitStewardshipLabel(item)}</small> : null}
        {item.executionMode ? <small>{humanizeToken(item.executionMode)}</small> : null}
        {item.urgency ? <small>{humanizeToken(item.urgency)}</small> : null}
        <small>{mutationGuardLabel(item)}</small>
        {timingLabel ? <small>{timingLabel}</small> : null}
        <ChevronRight size={14} />
      </div>
    </button>
  )
}

export function OperationsTab({
  data,
  selection,
  onSelectionChange,
  onOpenRun,
  onOpenSession,
  onOpenApproval,
  onOpenItem,
  onToolIntentAction,
  toolIntentActionBusy,
  toolIntentActionError,
}) {
  const activeRunId = data?.runs?.activeRun?.runId || ''
  const recentRuns = (data?.runs?.recentRuns || []).filter((run) => run.runId !== activeRunId)
  const toolIntent = data?.toolIntent || null
  const showMutationIntent = Boolean(toolIntent?.hasMutationIntentSurface)
  const showMutatingExecProposal = Boolean(
    toolIntent?.hasMutatingExecProposalSurface
    && (
      toolIntent?.mutatingExecProposalState
      || toolIntent?.mutatingExecProposalCommand
      || toolIntent?.mutatingExecProposalSummary
    )
    && toolIntent?.mutatingExecProposalState !== 'none'
  )
  const showMutatingExecExecution = Boolean(
    toolIntent?.hasMutatingExecExecutionSurface
    && toolIntent?.executionMode === 'mutating-exec'
  )
  const showSudoExecProposal = Boolean(
    toolIntent?.hasSudoExecProposalSurface
    && (
      toolIntent?.sudoExecProposalState
      || toolIntent?.sudoExecProposalCommand
      || toolIntent?.sudoExecProposalSummary
    )
    && toolIntent?.sudoExecProposalState !== 'none'
  )
  const showSudoApprovalWindow = Boolean(
    toolIntent?.hasSudoApprovalWindowSurface
    && (
      toolIntent?.sudoApprovalWindowState
      || toolIntent?.sudoApprovalWindowScope
      || toolIntent?.sudoApprovalWindowExpiresAt
    )
    && toolIntent?.sudoApprovalWindowState !== 'none'
  )
  const mutationScope = mutationScopeSummary(toolIntent)
  const mutationTargets = summarizeMutationTargets(toolIntent)

  return (
    <div className="mc-tab-page">
      <section className="mc-section-grid mc-operations-grid">
        <article className="support-card" id="autonomy-proposals" style={{ gridColumn: '1 / -1' }}>
          <AutonomyProposalsPanel />
        </article>

        <article className="support-card" id="execution-authority" title={sectionTitleWithMeta({
          source: '/mc/main-agent-selection',
          fetchedAt: data?.fetchedAt,
          mode: 'editable authority',
        })}>
          <div className="panel-header stacked">
            <div>
              <h3>Execution Authority</h3>
              <p className="muted">Canonical home for main-agent selection.</p>
            </div>
            <span className="mc-section-hint">Editable</span>
          </div>
          <MainAgentPanel selection={selection} onSave={onSelectionChange} embedded />
        </article>

        <article className="support-card" id="runtime-lanes" title={sectionTitleWithMeta({
          source: '/mc/runtime',
          fetchedAt: data?.fetchedAt,
          mode: 'periodic status',
        })}>
          <div className="panel-header">
            <div>
              <h3>Runtime Lanes</h3>
              <p className="muted">Visible, cheap, coding, and local readiness.</p>
            </div>
            <span className="mc-section-hint">Read-only</span>
          </div>
          <div className="compact-grid">
            {Object.values(data?.lanes || {}).map((lane) => (
              <div className="compact-metric" key={lane.label} title={`Source: /mc/runtime · ${lane.label} · readiness/auth status`}>
                <span>{lane.label}</span>
                <strong>{lane.provider || 'unknown'} / {lane.model || 'unconfigured'}</strong>
                <p className="muted">{lane.status} · {lane.providerStatus || 'unknown'}</p>
              </div>
            ))}
          </div>
        </article>
      </section>

      {toolIntent ? (
        <section className="support-card" id="tool-intent" title={sectionTitleWithMeta({
          source: toolIntent.source || '/mc/tool-intent',
          fetchedAt: toolIntent.createdAt || data?.fetchedAt,
          mode: 'operational intent detail',
        })}>
          <div className="panel-header">
            <div>
              <h3>Tool Intent</h3>
              <p className="muted">Bounded operational intent with mutation visibility and a proposal-only execution boundary.</p>
            </div>
            <span className="mc-section-hint">Read-only</span>
          </div>
          <div className="compact-grid">
            <div className="compact-metric" title="Current intent state">
              <span>State</span>
              <strong>{toolIntent.intentState || 'idle'}</strong>
              <p className="muted">{toolIntent.intentType || 'inspect-repo-status'}</p>
            </div>
            <div className="compact-metric" title="Approval lifecycle state and source">
              <span>Approval</span>
              <strong>{humanizeToken(toolIntent.approvalState || 'none')}</strong>
              <p className="muted">via {humanizeToken(toolIntent.approvalSource || 'none')} · {toolIntent.approvalRequired ? 'required' : 'not required'}</p>
            </div>
            <div className="compact-metric" title="Intent target and urgency">
              <span>Target</span>
              <strong>{toolIntent.executionTarget || toolIntent.intentTarget || 'workspace'}</strong>
              <p className="muted">{toolIntent.urgency || 'low'} urgency</p>
            </div>
            <div className="compact-metric" title="Read-only execution state and mode">
              <span>Execution</span>
              <strong>{toolIntent.executionState || 'not-executed'}</strong>
              <p className="muted">{humanizeToken(toolIntent.executionMode || 'read-only')} · {toolIntent.executionOperation ? humanizeToken(toolIntent.executionOperation) : humanizeToken(toolIntent.intentType || 'inspect-repo-status')}</p>
            </div>
            <div className="compact-metric" title="Boundary and mutation permission">
              <span>Boundary</span>
              <strong>{toolIntent.mutationPermitted ? 'mutable' : 'proposal-only'}</strong>
              <p className="muted">{toolIntent.approvalScope || 'repo-read'} · {toolIntent.approvalLifecycle || 'bounded-approval-surface-light'}</p>
            </div>
            <div className="compact-metric" title="Execution or approval freshness">
              <span>Freshness</span>
              <strong>{executionTimingLabel(toolIntent) || approvalTimingLabel(toolIntent) || 'awaiting signal'}</strong>
              <p className="muted">{toolIntent.executionSummary || toolIntent.approvalResolutionReason || toolIntent.approvalResolutionMessage || 'No execution summary recorded'}</p>
            </div>
          </div>
          {showMutationIntent ? (
            <>
              <div className="compact-grid compact-grid-4 mc-tool-intent-mutation-grid">
                <div className="compact-metric" title="Mutation intent state and classification">
                  <span>Mutation</span>
                  <strong>{humanizeToken(toolIntent.mutationIntentClassification || 'none')}</strong>
                  <p className="muted">{humanizeToken(toolIntent.mutationIntentState || 'idle')} · {toolIntent.mutationNear ? 'action-near' : 'not action-near'}</p>
                </div>
                <div className="compact-metric" title="Bounded mutation targets">
                  <span>Targets</span>
                  <strong>{toolIntent.mutationTargetFiles?.length || toolIntent.mutationTargetPaths?.length || 0}</strong>
                  <p className="muted">{mutationTargets}</p>
                </div>
                <div className="compact-metric" title="Repo or system mutation scope">
                  <span>Scope</span>
                  <strong>{mutationScope || 'none'}</strong>
                  <p className="muted">repo {toolIntent.mutationRepoScope || 'none'} · system {toolIntent.mutationSystemScope || 'none'}</p>
                </div>
                <div className="compact-metric" title="Mutation boundary and execution permission">
                  <span>Guard</span>
                  <strong>{mutationGuardLabel(toolIntent)}</strong>
                  <p className="muted">sudo {toolIntent.mutationSudoRequired ? 'required' : 'not needed'} · {toolIntent.mutationCritical ? 'critical' : 'normal risk'}</p>
                </div>
              </div>
              <article className="mc-code-card mc-tool-intent-summary mc-tool-intent-mutation-summary">
                <strong>Mutation intent</strong>
                <p>{toolIntent.mutationSummary || 'No bounded mutation intent is active.'}</p>
                <div className="mc-inline-meta">
                  <span className="mc-meta-pill">classification {humanizeToken(toolIntent.mutationIntentClassification || 'none')}</span>
                  <span className="mc-meta-pill">{toolIntent.mutationNear ? 'action-near' : 'not action-near'}</span>
                  <span className="mc-meta-pill">{mutationGuardLabel(toolIntent)}</span>
                  <span className="mc-meta-pill">{toolIntent.mutationSudoRequired ? 'sudo required' : 'sudo not needed'}</span>
                  <span className="mc-meta-pill">{toolIntent.mutationCritical ? 'critical change' : 'normal risk'}</span>
                  {toolIntent.createdAt ? <span className="mc-meta-pill">updated {formatFreshness(toolIntent.createdAt)}</span> : null}
                </div>
              </article>
            </>
          ) : null}
          {showMutatingExecProposal ? (
            <>
              <div className="compact-grid compact-grid-4 mc-tool-intent-mutation-grid">
                <div className="compact-metric" title="Mutating exec proposal state and review boundary">
                  <span>Exec Proposal</span>
                  <strong>{humanizeToken(toolIntent.mutatingExecProposalState || 'none')}</strong>
                  <p className="muted">proposal-only · not executed</p>
                </div>
                {toolIntent.hasGitRepoStewardshipProposalSurface ? (
                  <div className="compact-metric" title="Repo stewardship domain and git mutation class">
                    <span>Stewardship</span>
                    <strong>{humanizeToken(toolIntent.mutatingExecGitMutationClass || 'none')}</strong>
                    <p className="muted">{humanizeToken(toolIntent.mutatingExecRepoStewardshipDomain || 'none')} repo stewardship</p>
                  </div>
                ) : null}
                <div className="compact-metric" title="Mutating exec scope and criticality">
                  <span>Scope</span>
                  <strong>{humanizeToken(toolIntent.mutatingExecProposalScope || 'none')}</strong>
                  <p className="muted">{humanizeToken(toolIntent.mutatingExecCriticality || 'none')} criticality</p>
                </div>
                <div className="compact-metric" title="Approval and sudo requirements">
                  <span>Guard</span>
                  <strong>{mutatingExecGuardLabel(toolIntent)}</strong>
                  <p className="muted">sudo {toolIntent.mutatingExecRequiresSudo ? 'required' : 'not needed'}</p>
                </div>
                <div className="compact-metric" title="Proposal confidence and fingerprint">
                  <span>Confidence</span>
                  <strong>{humanizeToken(toolIntent.mutatingExecConfidence || 'low')}</strong>
                  <p className="muted">{toolIntent.mutatingExecCommandFingerprint || 'no fingerprint'}</p>
                </div>
              </div>
              <article className="mc-code-card mc-tool-intent-summary mc-tool-intent-mutation-summary">
                <strong>Mutating exec proposal</strong>
                <p>{toolIntent.mutatingExecProposalSummary || toolIntent.mutatingExecProposalReason || 'A mutating exec proposal is present and remains review-only.'}</p>
                <div className="mc-inline-meta">
                  {toolIntent.hasGitRepoStewardshipProposalSurface ? (
                    <>
                      <span className="mc-meta-pill">domain {humanizeToken(toolIntent.mutatingExecRepoStewardshipDomain || 'none')}</span>
                      <span className="mc-meta-pill">class {humanizeToken(toolIntent.mutatingExecGitMutationClass || 'none')}</span>
                    </>
                  ) : null}
                  <span className="mc-meta-pill">command {toolIntent.mutatingExecProposalCommand || 'none'}</span>
                  <span className="mc-meta-pill">scope {humanizeToken(toolIntent.mutatingExecProposalScope || 'none')}</span>
                  <span className="mc-meta-pill">{toolIntent.mutatingExecRequiresApproval ? 'approval required' : 'approval not required'}</span>
                  <span className="mc-meta-pill">{toolIntent.mutatingExecRequiresSudo ? 'sudo required' : 'sudo not needed'}</span>
                  <span className="mc-meta-pill">not executed</span>
                </div>
              </article>
              {toolIntent.hasGitRepoStewardshipProposalSurface ? (
                <article className="mc-code-card mc-tool-intent-summary mc-tool-intent-mutation-summary">
                  <strong>Git repo stewardship</strong>
                  <p>This proposal is repo stewardship truth, not generic shell mutation. It stays approval-gated and not executed until an explicit approval path acts on it.</p>
                  <div className="mc-inline-meta">
                    <span className="mc-meta-pill">git {humanizeToken(toolIntent.mutatingExecGitMutationClass || 'none')}</span>
                    <span className="mc-meta-pill">approval gated</span>
                    <span className="mc-meta-pill">proposal only</span>
                    <span className="mc-meta-pill">not executed</span>
                  </div>
                </article>
              ) : null}
            </>
          ) : null}
          {showSudoExecProposal ? (
            <>
              <div className="compact-grid compact-grid-4 mc-tool-intent-mutation-grid">
                <div className="compact-metric" title="Sudo exec proposal state and review boundary">
                  <span>Sudo Proposal</span>
                  <strong>{humanizeToken(toolIntent.sudoExecProposalState || 'none')}</strong>
                  <p className="muted">proposal-only · not executed</p>
                </div>
                <div className="compact-metric" title="Sudo exec scope and criticality">
                  <span>Scope</span>
                  <strong>{humanizeToken(toolIntent.sudoExecProposalScope || 'none')}</strong>
                  <p className="muted">{humanizeToken(toolIntent.sudoExecCriticality || 'none')} criticality</p>
                </div>
                <div className="compact-metric" title="Approval and sudo requirements">
                  <span>Guard</span>
                  <strong>{sudoExecGuardLabel(toolIntent)}</strong>
                  <p className="muted">{toolIntent.sudoExecRequiresSudo ? 'requires sudo' : 'sudo not needed'}</p>
                </div>
                <div className="compact-metric" title="Proposal confidence and fingerprint">
                  <span>Fingerprint</span>
                  <strong>{toolIntent.sudoExecCommandFingerprint || 'none'}</strong>
                  <p className="muted">{humanizeToken(toolIntent.sudoExecConfidence || 'low')} confidence</p>
                </div>
              </div>
              <article className="mc-code-card mc-tool-intent-summary mc-tool-intent-mutation-summary">
                <strong>Sudo exec proposal</strong>
                <p>{toolIntent.sudoExecProposalSummary || toolIntent.sudoExecProposalReason || 'A sudo exec proposal is present and remains review-only.'}</p>
                <div className="mc-inline-meta">
                  <span className="mc-meta-pill">command {toolIntent.sudoExecProposalCommand || 'none'}</span>
                  <span className="mc-meta-pill">scope {humanizeToken(toolIntent.sudoExecProposalScope || 'none')}</span>
                  <span className="mc-meta-pill">{toolIntent.sudoExecRequiresApproval ? 'approval required' : 'approval not required'}</span>
                  <span className="mc-meta-pill">{toolIntent.sudoExecRequiresSudo ? 'requires sudo' : 'sudo not needed'}</span>
                  <span className="mc-meta-pill">not executed</span>
                </div>
              </article>
            </>
          ) : null}
          {showSudoApprovalWindow ? (
            <>
              <div className="compact-grid compact-grid-4 mc-tool-intent-mutation-grid">
                <div className="compact-metric" title="Short bounded sudo approval window state">
                  <span>Sudo Window</span>
                  <strong>{humanizeToken(toolIntent.sudoApprovalWindowState || 'none')}</strong>
                  <p className="muted">{sudoApprovalWindowGuardLabel(toolIntent)} · short TTL</p>
                </div>
                <div className="compact-metric" title="Bounded sudo approval scope and source">
                  <span>Scope</span>
                  <strong>{humanizeToken(toolIntent.sudoApprovalWindowScope || 'none')}</strong>
                  <p className="muted">via {humanizeToken(toolIntent.sudoApprovalWindowSource || 'none')}</p>
                </div>
                <div className="compact-metric" title="Remaining sudo approval window time">
                  <span>Remaining</span>
                  <strong>{toolIntent.sudoApprovalWindowRemainingSeconds || 0}s</strong>
                  <p className="muted">{toolIntent.sudoApprovalWindowReusable ? 'approval reusable' : 'reuse blocked'}</p>
                </div>
                <div className="compact-metric" title="Window lifecycle timestamps">
                  <span>Expires</span>
                  <strong>{toolIntent.sudoApprovalWindowExpiresAt ? formatFreshness(toolIntent.sudoApprovalWindowExpiresAt) : 'unknown'}</strong>
                  <p className="muted">{toolIntent.sudoApprovalWindowStartedAt ? `started ${formatFreshness(toolIntent.sudoApprovalWindowStartedAt)}` : 'start time unavailable'}</p>
                </div>
              </div>
              <article className="mc-code-card mc-tool-intent-summary mc-tool-intent-mutation-summary">
                <strong>Sudo approval window</strong>
                <p>A short, scoped sudo approval window may reuse a recent approval only within the same bounded sudo scope. It is not global root access.</p>
                <div className="mc-inline-meta">
                  <span className="mc-meta-pill">state {humanizeToken(toolIntent.sudoApprovalWindowState || 'none')}</span>
                  <span className="mc-meta-pill">scope {humanizeToken(toolIntent.sudoApprovalWindowScope || 'none')}</span>
                  <span className="mc-meta-pill">{toolIntent.sudoApprovalWindowReusable ? 'reusable' : 'not reusable'}</span>
                  <span className="mc-meta-pill">{toolIntent.sudoApprovalWindowRemainingSeconds || 0}s remaining</span>
                  <span className="mc-meta-pill">source {humanizeToken(toolIntent.sudoApprovalWindowSource || 'none')}</span>
                </div>
              </article>
            </>
          ) : null}
          {showMutatingExecExecution ? (
            <>
              <div className="compact-grid compact-grid-4 mc-tool-intent-mutation-grid">
                <div className="compact-metric" title="Mutating exec execution state and outcome">
                  <span>Exec Result</span>
                  <strong>{humanizeToken(toolIntent.mutatingExecExecutionState || 'mutating-exec')}</strong>
                  <p className="muted">{toolIntent.mutatingExecExecutionSucceeded ? 'completed' : 'failed'} · {toolIntent.mutationPermitted ? 'mutation permitted' : 'mutation blocked'}</p>
                </div>
                <div className="compact-metric" title="Mutating exec scope and non-sudo boundary">
                  <span>Scope</span>
                  <strong>{humanizeToken(toolIntent.mutatingExecExecutionScope || 'none')}</strong>
                  <p className="muted">{toolIntent.mutatingExecRequiresSudo ? 'sudo required' : 'sudo not permitted'}</p>
                </div>
                <div className="compact-metric" title="Approval binding and execution mode">
                  <span>Binding</span>
                  <strong>{mutatingExecExecutionGuardLabel(toolIntent)}</strong>
                  <p className="muted">{humanizeToken(toolIntent.executionMode || 'mutating-exec')} · approval {humanizeToken(toolIntent.approvalState || 'none')}</p>
                </div>
                <div className="compact-metric" title="Command fingerprint and continuity outcome">
                  <span>Fingerprint</span>
                  <strong>{toolIntent.mutatingExecCommandFingerprint || 'none'}</strong>
                  <p className="muted">{humanizeToken(toolIntent.lastActionOutcome || 'none')} · {humanizeToken(toolIntent.followupState || 'none')}</p>
                </div>
              </div>
              <article className="mc-code-card mc-tool-intent-summary mc-tool-intent-mutation-summary">
                <strong>Mutating exec execution</strong>
                <p>{toolIntent.executionSummary || 'No bounded mutating exec execution summary is recorded.'}</p>
                <div className="mc-inline-meta">
                  <span className="mc-meta-pill">command {toolIntent.mutatingExecExecutionCommand || 'none'}</span>
                  <span className="mc-meta-pill">scope {humanizeToken(toolIntent.mutatingExecExecutionScope || 'none')}</span>
                  <span className="mc-meta-pill">{toolIntent.mutatingExecApprovalMatched ? 'approval matched' : 'review binding'}</span>
                  <span className="mc-meta-pill">{toolIntent.mutatingExecRequiresSudo ? 'sudo required' : 'sudo_permitted=false'}</span>
                  <span className="mc-meta-pill">{toolIntent.mutationPermitted ? 'mutation permitted' : 'mutation_permitted=false'}</span>
                  {toolIntent.executionFinishedAt ? <span className="mc-meta-pill">finished {formatFreshness(toolIntent.executionFinishedAt)}</span> : null}
                </div>
              </article>
            </>
          ) : null}
          {toolIntent.executionSummary ? (
            <article className="mc-code-card mc-tool-intent-summary">
              <strong>{showMutatingExecExecution ? 'Execution result' : 'Read-only result'}</strong>
              <p>{toolIntent.executionSummary}</p>
              <div className="mc-inline-meta">
                <span className="mc-meta-pill">mode {humanizeToken(toolIntent.executionMode || 'read-only')}</span>
                <span className="mc-meta-pill">{toolIntent.mutationPermitted ? 'mutation permitted' : 'mutation_permitted=false'}</span>
                {toolIntent.executionConfidence ? <span className="mc-meta-pill">confidence {humanizeToken(toolIntent.executionConfidence)}</span> : null}
              </div>
            </article>
          ) : null}
          <div className="mc-list">
            {toolIntentRow(toolIntent, onOpenItem)}
          </div>
          {toolIntent.approvalState === 'pending' ? (
            <>
              {toolIntentActionError ? <div className="inline-error">{toolIntentActionError}</div> : null}
              <div className="mc-inline-actions mc-tool-intent-actions">
                <button
                  className="primary-btn"
                  disabled={toolIntentActionBusy}
                  onClick={() => onToolIntentAction?.('approve')}
                >
                  {toolIntentActionBusy ? 'Working…' : 'Approve'}
                </button>
                <button
                  className="secondary-btn"
                  disabled={toolIntentActionBusy}
                  onClick={() => onToolIntentAction?.('deny')}
                >
                  Deny
                </button>
              </div>
              <p className="mc-tool-intent-help muted">Resolve only bounded approval state here. Any execution stays read-only and mutation_permitted=false.</p>
            </>
          ) : null}
        </section>
      ) : null}

      <article
        className="support-card"
        id="runs"
        style={{ gridColumn: '1 / -1' }}
        title={sectionTitleWithMeta({
          source: '/mc/runs',
          fetchedAt: data?.fetchedAt,
          mode: 'event-assisted + 20s',
        })}
      >
        <div className="panel-header">
          <div>
            <h3>Runs</h3>
            <p className="muted">Active plus recent persisted runs.</p>
          </div>
          <span className="mc-section-hint">Clickable rows</span>
        </div>
        <div className="mc-list">
          {data?.runs?.activeRun ? (
            <button className="mc-list-row active" onClick={() => onOpenRun(data.runs.activeRun)}>
              <div>
                <strong>{data.runs.activeRun.provider} / {data.runs.activeRun.model}</strong>
                <span>{data.runs.activeRun.status} · active run</span>
              </div>
              <div className="mc-row-meta">
                <small>Live</small>
                <ChevronRight size={14} />
              </div>
            </button>
          ) : null}
          {!data?.runs?.activeRun && recentRuns.length === 0 ? (
            <div className="mc-empty-state">
              <strong>No runs yet</strong>
              <p className="muted">Visible execution history will appear here after the next run.</p>
            </div>
          ) : null}
          {recentRuns.map((run) => (
            <button className="mc-list-row" key={run.runId} onClick={() => onOpenRun(run)}>
              <div>
                <strong>{run.provider} / {run.model}</strong>
                <span>{run.status} · {run.finishedAt || run.startedAt || 'unknown'}</span>
              </div>
              <div className="mc-row-meta">
                <small>{run.lane}</small>
                <ChevronRight size={14} />
              </div>
            </button>
          ))}
        </div>
      </article>

        <article className="support-card" id="sessions" title={sectionTitleWithMeta({
          source: '/chat/sessions',
          fetchedAt: data?.fetchedAt,
          mode: 'periodic list',
        })}>
          <div className="panel-header">
            <div>
              <h3>Sessions</h3>
              <p className="muted">Persisted sessions with transcript preview on click.</p>
            </div>
            <span className="mc-section-hint">Transcript drawer</span>
          </div>
          <div className="mc-list">
            {(data?.sessions?.items || []).length === 0 ? (
              <div className="mc-empty-state">
                <strong>No sessions yet</strong>
                <p className="muted">Chat-created sessions will appear here automatically.</p>
              </div>
            ) : null}
            {(data?.sessions?.items || []).map((session) => (
              <button className="mc-list-row" key={session.id} onClick={() => onOpenSession(session)}>
                <div>
                  <strong>{session.title}</strong>
                  <span>{session.last_message || 'Ready'}</span>
                </div>
                <div className="mc-row-meta">
                  <small>{session.message_count || 0} msgs</small>
                  <ChevronRight size={14} />
                </div>
              </button>
            ))}
          </div>
        </article>

        <article className="support-card" id="approvals" title={sectionTitleWithMeta({
          source: '/mc/approvals',
          fetchedAt: data?.fetchedAt,
          mode: 'event-assisted + 20s',
        })}>
          <div className="panel-header">
            <div>
              <h3>Approvals</h3>
              <p className="muted">Canonical approval queue and actions.</p>
            </div>
            <span className="mc-section-hint">Action drawer</span>
          </div>
          <div className="mc-list">
            {(data?.approvals?.requests || []).length === 0 ? (
              <div className="mc-empty-state">
                <strong>No approval requests</strong>
                <p className="muted">Requests that need operator approval will queue here.</p>
              </div>
            ) : null}
            {(data?.approvals?.requests || []).map((approval) => (
              <button className="mc-list-row" key={approval.requestId} onClick={() => onOpenApproval(approval)}>
                <div>
                  <strong>{approval.capabilityName}</strong>
                  <span>{approval.status} · {approval.executionMode || 'unknown'}</span>
                </div>
                <div className="mc-row-meta">
                  <small>{approval.requestedAt || 'unknown'}</small>
                  <ChevronRight size={14} />
                </div>
              </button>
            ))}
          </div>
        </article>
    </div>
  )
}
