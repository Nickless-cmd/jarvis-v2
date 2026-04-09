import { ChevronRight, ChevronDown, ChevronUp } from 'lucide-react'
import { useState } from 'react'
import { MainAgentPanel } from '../shared/MainAgentPanel'
import { AutonomyProposalsPanel } from './AutonomyProposalsPanel'
import { formatFreshness, sectionTitleWithMeta } from './meta'
import { s, T } from '../../shared/theme/tokens'

function CollapsibleSection({ title, subtitle, defaultOpen = false, children }) {
  const [isOpen, setIsOpen] = useState(defaultOpen)
  
  return (
    <div style={s({ border: `1px solid ${T.border0}`, borderRadius: 10, overflow: 'hidden', marginTop: 8 })}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        style={s({
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '10px 12px',
          background: T.bgSurface,
          border: 'none',
          color: T.text1,
          cursor: 'pointer',
          textAlign: 'left',
        })}
      >
        <div>
          <div style={s({ fontSize: 11, fontWeight: 500 })}>{title}</div>
          {subtitle && <div style={s({ fontSize: 10, color: T.text3, marginTop: 2 })}>{subtitle}</div>}
        </div>
        {isOpen ? <ChevronUp size={14} color={T.text3} /> : <ChevronDown size={14} color={T.text3} />}
      </button>
      {isOpen && (
        <div style={s({ padding: 12, background: T.bgRaised })}>
          {children}
        </div>
      )}
    </div>
  )
}

function StatusBadge({ status }) {
  const getColor = (s) => {
    const lower = String(s || '').toLowerCase()
    if (lower === 'approved' || lower === 'ok' || lower === 'completed') return T.green
    if (lower === 'pending' || lower === 'review') return T.amber
    if (lower === 'rejected' || lower === 'failed' || lower === 'error') return T.red
    return T.text3
  }
  const color = getColor(status)
  return (
    <span style={s({
      fontSize: 9,
      padding: '2px 6px',
      borderRadius: 6,
      background: `${color}15`,
      color: color,
      fontFamily: T.mono,
      letterSpacing: '0.04em',
    })}>
      {status}
    </span>
  )
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
              <p className="muted">Main-agent selection.</p>
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
              <p className="muted">Visible, cheap, coding, local.</p>
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
        <section className="support-card" id="tool-intent" style={{ marginTop: 12 }}>
          <div className="panel-header">
            <div>
              <h3>Tool Intent</h3>
              <p className="muted">Bounded operational intent.</p>
            </div>
            <div style={s({ display: 'flex', gap: 6 })}>
              <StatusBadge status={toolIntent.intentState || 'idle'} />
              <StatusBadge status={toolIntent.approvalState || 'none'} />
            </div>
          </div>
          
          <div className="compact-grid" style={{ marginBottom: 8 }}>
            <div className="compact-metric">
              <span>Target</span>
              <strong>{toolIntent.executionTarget || toolIntent.intentTarget || 'workspace'}</strong>
              <p className="muted">{toolIntent.intentType || 'inspect'}</p>
            </div>
            <div className="compact-metric">
              <span>Mode</span>
              <strong>{humanizeToken(toolIntent.executionMode || 'read-only')}</strong>
              <p className="muted">{toolIntent.executionState || 'not-executed'}</p>
            </div>
          </div>

          {showMutationIntent && (
            <CollapsibleSection 
              title="Mutation Intent" 
              subtitle={`${toolIntent.mutationTargetFiles?.length || 0} files · ${mutationGuardLabel(toolIntent)}`}
            >
              <div className="compact-grid compact-grid-4" style={{ marginBottom: 8 }}>
                <div className="compact-metric">
                  <span>Classification</span>
                  <strong>{humanizeToken(toolIntent.mutationIntentClassification || 'none')}</strong>
                </div>
                <div className="compact-metric">
                  <span>Targets</span>
                  <strong>{toolIntent.mutationTargetFiles?.length || 0}</strong>
                  <p className="muted">{mutationTargets}</p>
                </div>
                <div className="compact-metric">
                  <span>Scope</span>
                  <strong>{mutationScope || 'none'}</strong>
                </div>
                <div className="compact-metric">
                  <span>Guard</span>
                  <strong>{mutationGuardLabel(toolIntent)}</strong>
                </div>
              </div>
            </CollapsibleSection>
          )}

          {showMutatingExecProposal && (
            <CollapsibleSection 
              title="Mutating Exec Proposal" 
              subtitle={humanizeToken(toolIntent.mutatingExecProposalState || 'none')}
            >
              <div className="compact-grid compact-grid-4" style={{ marginBottom: 8 }}>
                <div className="compact-metric">
                  <span>State</span>
                  <strong>{humanizeToken(toolIntent.mutatingExecProposalState || 'none')}</strong>
                </div>
                <div className="compact-metric">
                  <span>Scope</span>
                  <strong>{humanizeToken(toolIntent.mutatingExecProposalScope || 'none')}</strong>
                </div>
                <div className="compact-metric">
                  <span>Guard</span>
                  <strong>{mutatingExecGuardLabel(toolIntent)}</strong>
                </div>
                <div className="compact-metric">
                  <span>Confidence</span>
                  <strong>{humanizeToken(toolIntent.mutatingExecConfidence || 'low')}</strong>
                </div>
              </div>
              {toolIntent.mutatingExecProposalSummary && (
                <p style={s({ fontSize: 11, color: T.text2, marginTop: 8 })}>{toolIntent.mutatingExecProposalSummary}</p>
              )}
            </CollapsibleSection>
          )}

          {showSudoExecProposal && (
            <CollapsibleSection 
              title="Sudo Exec Proposal" 
              subtitle={humanizeToken(toolIntent.sudoExecProposalState || 'none')}
            >
              <div className="compact-grid compact-grid-4" style={{ marginBottom: 8 }}>
                <div className="compact-metric">
                  <span>State</span>
                  <strong>{humanizeToken(toolIntent.sudoExecProposalState || 'none')}</strong>
                </div>
                <div className="compact-metric">
                  <span>Scope</span>
                  <strong>{humanizeToken(toolIntent.sudoExecProposalScope || 'none')}</strong>
                </div>
                <div className="compact-metric">
                  <span>Guard</span>
                  <strong>{sudoExecGuardLabel(toolIntent)}</strong>
                </div>
              </div>
            </CollapsibleSection>
          )}

          {showSudoApprovalWindow && (
            <CollapsibleSection 
              title="Sudo Approval Window" 
              subtitle={`${toolIntent.sudoApprovalWindowRemainingSeconds || 0}s remaining`}
            >
              <div className="compact-grid compact-grid-4" style={{ marginBottom: 8 }}>
                <div className="compact-metric">
                  <span>State</span>
                  <strong>{humanizeToken(toolIntent.sudoApprovalWindowState || 'none')}</strong>
                </div>
                <div className="compact-metric">
                  <span>Scope</span>
                  <strong>{humanizeToken(toolIntent.sudoApprovalWindowScope || 'none')}</strong>
                </div>
                <div className="compact-metric">
                  <span>Remaining</span>
                  <strong>{toolIntent.sudoApprovalWindowRemainingSeconds || 0}s</strong>
                </div>
                <div className="compact-metric">
                  <span>Expires</span>
                  <strong>{toolIntent.sudoApprovalWindowExpiresAt ? formatFreshness(toolIntent.sudoApprovalWindowExpiresAt) : 'unknown'}</strong>
                </div>
              </div>
            </CollapsibleSection>
          )}

          {showMutatingExecExecution && (
            <CollapsibleSection 
              title="Mutating Exec Execution" 
              subtitle={toolIntent.executionSummary ? 'Completed' : 'Running'}
            >
              <div className="compact-grid compact-grid-4" style={{ marginBottom: 8 }}>
                <div className="compact-metric">
                  <span>Result</span>
                  <strong>{humanizeToken(toolIntent.mutatingExecExecutionState || 'mutating-exec')}</strong>
                </div>
                <div className="compact-metric">
                  <span>Scope</span>
                  <strong>{humanizeToken(toolIntent.mutatingExecExecutionScope || 'none')}</strong>
                </div>
                <div className="compact-metric">
                  <span>Binding</span>
                  <strong>{mutatingExecExecutionGuardLabel(toolIntent)}</strong>
                </div>
              </div>
              {toolIntent.executionSummary && (
                <p style={s({ fontSize: 11, color: T.text2, marginTop: 8 })}>{toolIntent.executionSummary}</p>
              )}
            </CollapsibleSection>
          )}

          {toolIntent.executionSummary && (
            <div style={s({ marginTop: 8, padding: 10, background: T.bgSurface, borderRadius: 8 })}>
              <strong style={s({ fontSize: 11, color: T.text1 })}>Result</strong>
              <p style={s({ fontSize: 11, color: T.text2, marginTop: 4 })}>{toolIntent.executionSummary}</p>
            </div>
          )}

          {toolIntent.approvalState === 'pending' ? (
            <div style={s({ marginTop: 12, display: 'flex', gap: 8, alignItems: 'center' })}>
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
              {toolIntentActionError && (
                <span style={s({ fontSize: 11, color: T.red })}>{toolIntentActionError}</span>
              )}
            </div>
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
