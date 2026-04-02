import { ChevronRight } from 'lucide-react'
import { MainAgentPanel } from '../shared/MainAgentPanel'
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

function toolIntentRow(item, onOpen) {
  if (!item || (!item.intentState && !item.intentType)) return null

  const detailText = [
    [
      item.executionState ? `execution ${humanizeToken(item.executionState)}` : '',
      item.executionMode ? `mode ${humanizeToken(item.executionMode)}` : '',
      item.approvalState ? `approval ${humanizeToken(item.approvalState)}` : '',
      item.approvalSource && item.approvalSource !== 'none' ? `source ${humanizeToken(item.approvalSource)}` : '',
      item.intentType ? `type ${humanizeToken(item.intentType)}` : '',
      item.executionTarget || item.intentTarget ? `target ${item.executionTarget || item.intentTarget}` : '',
      item.approvalScope ? `scope ${humanizeToken(item.approvalScope)}` : '',
    ].filter(Boolean).join(' · '),
    item.executionSummary,
    item.intentReason,
    item.approvalResolutionMessage,
  ].filter(Boolean)[0] || 'Inspect bounded operational tool intent'

  const timingLabel = executionTimingLabel(item) || approvalTimingLabel(item)

  return (
    <button
      className="mc-list-row"
      onClick={() => onOpen('Tool Intent', item)}
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
        {item.intentType ? <small>{humanizeToken(item.intentType)}</small> : null}
        {item.executionMode ? <small>{humanizeToken(item.executionMode)}</small> : null}
        {item.urgency ? <small>{humanizeToken(item.urgency)}</small> : null}
        <small>{item.mutationPermitted ? 'mutation allowed' : 'mutation blocked'}</small>
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

  return (
    <div className="mc-tab-page">
      <section className="mc-section-grid mc-operations-grid">
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
              <p className="muted">Bounded operational intent with read-only execution truth and boundary state.</p>
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
              <p className="muted">{humanizeToken(toolIntent.approvalSource || 'none')} · {toolIntent.approvalRequired ? 'required' : 'not required'}</p>
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
              <strong>{toolIntent.mutationPermitted ? 'mutable' : 'read-only'}</strong>
              <p className="muted">{toolIntent.approvalScope || 'repo-read'} · {toolIntent.approvalLifecycle || 'bounded-approval-surface-light'}</p>
            </div>
            <div className="compact-metric" title="Execution or approval freshness">
              <span>Freshness</span>
              <strong>{executionTimingLabel(toolIntent) || approvalTimingLabel(toolIntent) || 'awaiting signal'}</strong>
              <p className="muted">{toolIntent.executionSummary || toolIntent.approvalResolutionReason || toolIntent.approvalResolutionMessage || 'No execution summary recorded'}</p>
            </div>
          </div>
          {toolIntent.executionSummary ? (
            <article className="mc-code-card mc-tool-intent-summary">
              <strong>Read-only result</strong>
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

      <section className="support-card" id="runs" title={sectionTitleWithMeta({
        source: '/mc/runs',
        fetchedAt: data?.fetchedAt,
        mode: 'event-assisted + 20s',
      })}>
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
      </section>

      <section className="mc-section-grid">
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
      </section>
    </div>
  )
}
