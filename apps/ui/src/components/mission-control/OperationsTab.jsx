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

function toolIntentRow(item, onOpen) {
  if (!item || (!item.intentState && !item.intentType)) return null

  const detailText = [
    [
      item.approvalState ? `approval ${humanizeToken(item.approvalState)}` : '',
      item.approvalSource && item.approvalSource !== 'none' ? `source ${humanizeToken(item.approvalSource)}` : '',
      item.intentType ? `type ${humanizeToken(item.intentType)}` : '',
      item.intentTarget ? `target ${item.intentTarget}` : '',
      item.approvalScope ? `scope ${humanizeToken(item.approvalScope)}` : '',
    ].filter(Boolean).join(' · '),
    item.intentReason,
    item.approvalResolutionMessage,
  ].filter(Boolean)[0] || 'Inspect bounded operational tool intent'

  const timingLabel = approvalTimingLabel(item)

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
        {item.intentType ? <small>{humanizeToken(item.intentType)}</small> : null}
        {item.urgency ? <small>{humanizeToken(item.urgency)}</small> : null}
        {item.approvalSource && item.approvalSource !== 'none' ? <small>{humanizeToken(item.approvalSource)}</small> : null}
        {item.approvalRequired ? <small>approval required</small> : <small>no approval</small>}
        {item.executionState ? <small>{humanizeToken(item.executionState)}</small> : null}
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
              <p className="muted">Bounded operational intent, still proposal-only and not executed.</p>
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
              <strong>{toolIntent.intentTarget || 'workspace'}</strong>
              <p className="muted">{toolIntent.urgency || 'low'} urgency</p>
            </div>
            <div className="compact-metric" title="Approval boundary and execution state">
              <span>Boundary</span>
              <strong>{toolIntent.executionState || 'not-executed'}</strong>
              <p className="muted">{toolIntent.approvalScope || 'repo-read'} · {toolIntent.approvalLifecycle || 'bounded-approval-surface-light'}</p>
            </div>
            <div className="compact-metric" title="Approval timing and resolution state">
              <span>Timing</span>
              <strong>{approvalTimingLabel(toolIntent) || 'awaiting signal'}</strong>
              <p className="muted">{toolIntent.approvalResolutionReason || toolIntent.approvalResolutionMessage || 'No resolution recorded'}</p>
            </div>
          </div>
          <div className="mc-list">
            {toolIntentRow(toolIntent, onOpenItem)}
          </div>
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
