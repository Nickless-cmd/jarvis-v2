import { X } from 'lucide-react'
import { formatFreshness } from './meta'

function humanizeKey(value) {
  return String(value || '')
    .replace(/([a-z0-9])([A-Z])/g, '$1 $2')
    .replace(/[_-]+/g, ' ')
    .trim()
}

function isScalar(value) {
  return value == null || ['string', 'number', 'boolean'].includes(typeof value)
}

function formatScalar(value) {
  if (value == null || value === '') return '—'
  if (typeof value === 'boolean') return value ? 'yes' : 'no'
  if (Array.isArray(value)) return value.join(', ')
  return String(value)
}

function splitEntries(value) {
  return Object.entries(value || {}).reduce((acc, [key, entry]) => {
    if (isScalar(entry) || (Array.isArray(entry) && entry.every(isScalar))) {
      acc.scalars.push([key, entry])
      return acc
    }
    acc.groups.push([key, entry])
    return acc
  }, { scalars: [], groups: [] })
}

function StructuredDetailValue({ value, depth = 0 }) {
  if (isScalar(value)) {
    return <p>{formatScalar(value)}</p>
  }

  if (Array.isArray(value)) {
    if (!value.length) return <p className="muted">No entries.</p>

    if (value.every(isScalar)) {
      return (
        <div className="mc-drawer-list">
          {value.map((entry, index) => (
            <p key={`${String(entry)}-${index}`}>{formatScalar(entry)}</p>
          ))}
        </div>
      )
    }

    return (
      <div className="mc-detail-array">
        {value.slice(0, 8).map((entry, index) => (
          <article className="mc-detail-group" key={index}>
            <strong>{`Entry ${index + 1}`}</strong>
            <StructuredDetailValue value={entry} depth={depth + 1} />
          </article>
        ))}
        {value.length > 8 ? <p className="muted">{`Showing first 8 of ${value.length} entries.`}</p> : null}
      </div>
    )
  }

  const { scalars, groups } = splitEntries(value)

  return (
    <div className="mc-detail-sections">
      {scalars.length ? (
        <div className="mc-keyval-grid">
          {scalars.map(([key, entry]) => (
            <div key={key}>
              <span>{humanizeKey(key)}</span>
              <strong>{formatScalar(entry)}</strong>
            </div>
          ))}
        </div>
      ) : null}
      {groups.map(([key, entry]) => (
        <article className="mc-detail-group" key={key}>
          <strong>{humanizeKey(key)}</strong>
          <StructuredDetailValue value={entry} depth={depth + 1} />
        </article>
      ))}
    </div>
  )
}

function StructuredDetailCard({ title, value }) {
  return (
    <article className="mc-code-card mc-structured-card">
      <strong>{title}</strong>
      <StructuredDetailValue value={value} />
    </article>
  )
}

export function DetailDrawer({ drawer, onClose, onApprovalAction, onContractCandidateAction, onDevelopmentFocusAction }) {
  if (!drawer) return null

  return (
    <aside className="mc-drawer-backdrop" onClick={onClose}>
      <div className="mc-drawer" onClick={(event) => event.stopPropagation()}>
        <div className="mc-drawer-header">
          <div>
            <p className="eyebrow">Detail</p>
            <h3>{drawer.title}</h3>
            <p className="mc-drawer-subtitle">
              {drawer.kind === 'run' ? 'Run drilldown' : null}
              {drawer.kind === 'event' ? 'Event payload and context' : null}
              {drawer.kind === 'approval' ? 'Approval queue item and actions' : null}
              {drawer.kind === 'session' ? 'Session transcript preview' : null}
              {drawer.kind === 'tool-intent' ? 'Bounded tool intent and read-only execution detail' : null}
              {drawer.kind === 'jarvis' ? 'Jarvis state and continuity detail' : null}
              {drawer.kind === 'contract-candidate' ? 'Governed USER/MEMORY workflow item' : null}
              {drawer.kind === 'development-focus' ? 'Development focus detail and actions' : null}
            </p>
          </div>
          <button className="icon-btn" onClick={onClose}><X size={16} /></button>
        </div>

        {drawer.kind === 'run' ? (
          <div className="mc-drawer-body">
            <div className="mc-keyval-grid">
              <div><span>Run ID</span><strong>{drawer.item.runId}</strong></div>
              <div><span>Status</span><strong>{drawer.item.status}</strong></div>
              <div><span>Provider</span><strong>{drawer.item.provider} / {drawer.item.model}</strong></div>
              <div><span>Lane</span><strong>{drawer.item.lane}</strong></div>
            </div>
            <div className="mc-inline-meta">
              <span className="mc-meta-pill">Started {formatFreshness(drawer.item.startedAt)}</span>
              {drawer.item.finishedAt ? <span className="mc-meta-pill">Finished {formatFreshness(drawer.item.finishedAt)}</span> : null}
              {drawer.item.capabilityId ? <span className="mc-meta-pill">Capability {drawer.item.capabilityId}</span> : null}
            </div>
            <article className="mc-code-card">
              <strong>Preview</strong>
              <p>{drawer.item.textPreview || 'No preview recorded.'}</p>
            </article>
            {drawer.item.error ? (
              <article className="mc-code-card tone-danger">
                <strong>Error</strong>
                <p>{drawer.item.error}</p>
              </article>
            ) : null}
          </div>
        ) : null}

        {drawer.kind === 'event' ? (
          <div className="mc-drawer-body">
            <div className="mc-keyval-grid">
              <div><span>Kind</span><strong>{drawer.item.kind}</strong></div>
              <div><span>Family</span><strong>{drawer.item.family}</strong></div>
              <div><span>When</span><strong>{drawer.item.relativeTime}</strong></div>
              <div><span>ID</span><strong>{drawer.item.id}</strong></div>
            </div>
            <div className="mc-inline-meta">
              <span className="mc-meta-pill">Event feed detail</span>
              <span className="mc-meta-pill">Source /ws + /mc/events</span>
            </div>
            <article className="mc-code-card">
              <strong>Payload</strong>
              <StructuredDetailValue value={drawer.item.payload} />
            </article>
          </div>
        ) : null}

        {drawer.kind === 'tool-intent' ? (
          <div className="mc-drawer-body">
            <div className="mc-keyval-grid">
              <div><span>Intent</span><strong>{drawer.item.intentType || 'inspect-repo-status'}</strong></div>
              <div><span>State</span><strong>{drawer.item.intentState || 'idle'}</strong></div>
              <div><span>Approval</span><strong>{drawer.item.approvalState || 'none'}</strong></div>
              <div><span>Execution</span><strong>{drawer.item.executionState || 'not-executed'}</strong></div>
              <div><span>Mode</span><strong>{drawer.item.executionMode || 'read-only'}</strong></div>
              <div><span>Target</span><strong>{drawer.item.executionTarget || drawer.item.intentTarget || 'workspace'}</strong></div>
              <div><span>Mutation</span><strong>{drawer.item.mutationPermitted ? 'permitted' : 'blocked'}</strong></div>
              <div><span>Urgency</span><strong>{drawer.item.urgency || 'low'}</strong></div>
            </div>
            {drawer.item.hasMutationIntentSurface ? (
              <div className="mc-keyval-grid">
                <div><span>Mutation State</span><strong>{drawer.item.mutationIntentState || 'idle'}</strong></div>
                <div><span>Classification</span><strong>{drawer.item.mutationIntentClassification || 'none'}</strong></div>
                <div><span>Action Near</span><strong>{drawer.item.mutationNear ? 'yes' : 'no'}</strong></div>
                <div><span>Can Execute</span><strong>{drawer.item.mutationExecutionPermitted ? 'yes' : 'no'}</strong></div>
                <div><span>Repo Scope</span><strong>{drawer.item.mutationRepoScope || 'none'}</strong></div>
                <div><span>System Scope</span><strong>{drawer.item.mutationSystemScope || 'none'}</strong></div>
                <div><span>Sudo</span><strong>{drawer.item.mutationSudoRequired ? 'required' : 'not needed'}</strong></div>
                <div><span>Criticality</span><strong>{drawer.item.mutationCritical ? 'critical' : 'normal'}</strong></div>
              </div>
            ) : null}
            <div className="mc-inline-meta">
              {drawer.item.approvalSource ? <span className="mc-meta-pill">approval source {drawer.item.approvalSource}</span> : null}
              {drawer.item.approvalScope ? <span className="mc-meta-pill">scope {drawer.item.approvalScope}</span> : null}
              {drawer.item.executionConfidence ? <span className="mc-meta-pill">confidence {drawer.item.executionConfidence}</span> : null}
              {drawer.item.executionFinishedAt ? <span className="mc-meta-pill">finished {formatFreshness(drawer.item.executionFinishedAt)}</span> : null}
              {!drawer.item.executionFinishedAt && drawer.item.approvalResolvedAt ? <span className="mc-meta-pill">resolved {formatFreshness(drawer.item.approvalResolvedAt)}</span> : null}
            </div>
            {drawer.item.hasMutationIntentSurface ? (
              <article className="mc-code-card">
                <strong>Mutation targets</strong>
                <div className="mc-drawer-list">
                  {drawer.item.mutationTargetFiles?.length ? (
                    <p>Files: {drawer.item.mutationTargetFiles.join(', ')}</p>
                  ) : null}
                  {drawer.item.mutationTargetPaths?.length ? (
                    <p>Paths: {drawer.item.mutationTargetPaths.join(', ')}</p>
                  ) : null}
                  {!drawer.item.mutationTargetFiles?.length && !drawer.item.mutationTargetPaths?.length ? (
                    <p>No mutation targets recorded.</p>
                  ) : null}
                </div>
              </article>
            ) : null}
            {drawer.item.hasGitRepoStewardshipProposalSurface ? (
              <article className="mc-code-card">
                <strong>Git repo stewardship</strong>
                <div className="mc-keyval-grid">
                  <div><span>Domain</span><strong>{drawer.item.mutatingExecRepoStewardshipDomain || 'git'}</strong></div>
                  <div><span>Class</span><strong>{drawer.item.mutatingExecGitMutationClass || 'none'}</strong></div>
                  <div><span>Command</span><strong>{drawer.item.mutatingExecProposalCommand || 'none'}</strong></div>
                  <div><span>Boundary</span><strong>{drawer.item.executionState === 'not-executed' ? 'proposal only' : 'executed'}</strong></div>
                </div>
                <p>{drawer.item.mutatingExecProposalReason || drawer.item.mutatingExecProposalSummary || 'Git repo stewardship intent is present.'}</p>
                <div className="mc-inline-meta">
                  <span className="mc-meta-pill">approval gated</span>
                  <span className="mc-meta-pill">{drawer.item.mutatingExecRequiresSudo ? 'sudo required' : 'non-sudo path'}</span>
                  <span className="mc-meta-pill">{drawer.item.executionState === 'not-executed' ? 'not executed' : 'execution recorded'}</span>
                </div>
              </article>
            ) : null}
            <article className="mc-code-card">
              <strong>Read-only result</strong>
              <p>{drawer.item.executionSummary || 'No bounded repo inspection has been executed.'}</p>
            </article>
            {drawer.item.hasMutationIntentSurface && drawer.item.mutationSummary ? (
              <article className="mc-code-card">
                <strong>Mutation summary</strong>
                <p>{drawer.item.mutationSummary}</p>
              </article>
            ) : null}
            {drawer.item.hasMutationIntentSurface && drawer.item.mutationBoundary ? (
              <article className="mc-code-card">
                <strong>Mutation boundary</strong>
                <p>{drawer.item.mutationBoundary}</p>
              </article>
            ) : null}
            {drawer.item.boundary ? (
              <article className="mc-code-card">
                <strong>Approval and execution boundary</strong>
                <p>{drawer.item.boundary}</p>
              </article>
            ) : null}
            {drawer.item.intentReason ? (
              <article className="mc-code-card">
                <strong>Why this intent exists</strong>
                <p>{drawer.item.intentReason}</p>
              </article>
            ) : null}
            {drawer.item.executionExcerpt?.length ? (
              <article className="mc-code-card">
                <strong>Observed excerpt</strong>
                <div className="mc-drawer-list">
                  {drawer.item.executionExcerpt.map((line) => (
                    <p key={line}>{line}</p>
                  ))}
                </div>
              </article>
            ) : null}
          </div>
        ) : null}

        {drawer.kind === 'approval' ? (
          <div className="mc-drawer-body">
            <div className="mc-keyval-grid">
              <div><span>Capability</span><strong>{drawer.item.capabilityName}</strong></div>
              <div><span>Status</span><strong>{drawer.item.status}</strong></div>
              <div><span>Mode</span><strong>{drawer.item.executionMode || 'unknown'}</strong></div>
              <div><span>Requested</span><strong>{drawer.item.requestedAt || 'unknown'}</strong></div>
            </div>
            <div className="mc-inline-meta">
              <span className="mc-meta-pill">Queue source /mc/approvals</span>
              {drawer.item.approvalPolicy ? <span className="mc-meta-pill">Policy {drawer.item.approvalPolicy}</span> : null}
            </div>
            {drawer.error ? <div className="inline-error">{drawer.error}</div> : null}
            <div className="mc-inline-actions">
              <button
                className="primary-btn"
                disabled={drawer.busy || drawer.item.status !== 'pending'}
                onClick={() => onApprovalAction(drawer.item.requestId, 'approve')}
              >
                {drawer.busy ? 'Working…' : 'Approve'}
              </button>
              <button
                className="secondary-btn"
                disabled={drawer.busy || drawer.item.status !== 'approved'}
                onClick={() => onApprovalAction(drawer.item.requestId, 'execute')}
              >
                Execute
              </button>
            </div>
            <article className="mc-code-card">
              <strong>Approval record</strong>
              <StructuredDetailValue value={drawer.item} />
            </article>
          </div>
        ) : null}

        {drawer.kind === 'session' ? (
          <div className="mc-drawer-body">
            <div className="mc-keyval-grid">
              <div><span>Session</span><strong>{drawer.item.id}</strong></div>
              <div><span>Title</span><strong>{drawer.item.title}</strong></div>
              <div><span>Messages</span><strong>{drawer.item.message_count || drawer.item.messages?.length || 0}</strong></div>
              <div><span>Updated</span><strong>{drawer.item.updated_at || 'unknown'}</strong></div>
            </div>
            <div className="mc-inline-meta">
              <span className="mc-meta-pill">Read-only transcript preview</span>
              <span className="mc-meta-pill">Source /chat/sessions/{'{id}'}</span>
            </div>
            <div className="mc-transcript-preview">
              {(drawer.item.messages || []).map((message) => (
                <article className={`mc-transcript-line ${message.role}`} key={message.id}>
                  <strong>{message.role}</strong>
                  <p>{message.content}</p>
                </article>
              ))}
            </div>
          </div>
        ) : null}

        {drawer.kind === 'contract-candidate' ? (
          <div className="mc-drawer-body">
            <div className="mc-keyval-grid">
              <div><span>Candidate</span><strong>{drawer.item.candidateId || 'unknown'}</strong></div>
              <div><span>Status</span><strong>{drawer.item.status || 'unknown'}</strong></div>
              <div><span>Target</span><strong>{drawer.item.targetFile || 'unknown'}</strong></div>
              <div><span>Type</span><strong>{drawer.item.candidateType || 'unknown'}</strong></div>
            </div>
            <div className="mc-inline-meta">
              {drawer.item.sourceKind ? <span className="mc-meta-pill">Source {drawer.item.sourceKind}</span> : null}
              {drawer.item.evidenceClass ? <span className="mc-meta-pill">Evidence {drawer.item.evidenceClass.replace(/_/g, ' ')}</span> : null}
              {drawer.item.confidence ? <span className="mc-meta-pill">Confidence {drawer.item.confidence}</span> : null}
              {drawer.item.supportCount ? <span className="mc-meta-pill">{drawer.item.supportCount} supporting signals</span> : null}
              {drawer.item.sessionCount ? <span className="mc-meta-pill">{drawer.item.sessionCount} sessions</span> : null}
              {drawer.item.mergeCount ? <span className="mc-meta-pill">{drawer.item.mergeCount} merges</span> : null}
              {drawer.item.updatedAt ? <span className="mc-meta-pill">Updated {formatFreshness(drawer.item.updatedAt)}</span> : null}
            </div>
            {drawer.error ? <div className="inline-error">{drawer.error}</div> : null}
            <div className="mc-inline-actions">
              <button
                className="primary-btn"
                disabled={drawer.busy || drawer.item.status !== 'proposed'}
                onClick={() => onContractCandidateAction?.(drawer.item.candidateId, 'approve')}
              >
                {drawer.busy ? 'Working…' : 'Approve'}
              </button>
              <button
                className="secondary-btn"
                disabled={drawer.busy || !['proposed', 'approved'].includes(drawer.item.status)}
                onClick={() => onContractCandidateAction?.(drawer.item.candidateId, 'reject')}
              >
                Reject
              </button>
              <button
                className="secondary-btn"
                disabled={drawer.busy || drawer.item.status !== 'approved'}
                onClick={() => onContractCandidateAction?.(drawer.item.candidateId, 'apply')}
              >
                Apply
              </button>
            </div>
            <article className="mc-code-card">
              <strong>Evidence</strong>
              <p>{drawer.item.evidenceSummary || 'No evidence summary recorded.'}</p>
            </article>
            {drawer.item.supportSummary ? (
              <article className="mc-code-card">
                <strong>Why this is pending</strong>
                <p>{drawer.item.supportSummary}</p>
              </article>
            ) : null}
            {drawer.item.proposedValue ? (
              <article className="mc-code-card">
                <strong>Proposed write</strong>
                <p>{drawer.item.proposedValue}</p>
              </article>
            ) : null}
            {drawer.item.statusReason ? (
              <article className="mc-code-card">
                <strong>Status note</strong>
                <p>{drawer.item.statusReason}</p>
              </article>
            ) : null}
            {drawer.item.write ? (
              <article className="mc-code-card">
                <strong>Applied write</strong>
                <p>{drawer.item.write.write_status || 'unknown'} · {drawer.item.write.target_file || drawer.item.targetFile}</p>
              </article>
            ) : null}
            <article className="mc-code-card">
              <strong>Candidate detail</strong>
              <StructuredDetailValue value={drawer.item} />
            </article>
          </div>
        ) : null}

        {drawer.kind === 'jarvis' ? (
          <div className="mc-drawer-body">
            <div className="mc-keyval-grid">
              {drawer.item.source ? <div><span>Source</span><strong>{drawer.item.source}</strong></div> : null}
              {drawer.item.createdAt ? <div><span>Updated</span><strong>{formatFreshness(drawer.item.createdAt)}</strong></div> : null}
              {drawer.item.status ? <div><span>Status</span><strong>{drawer.item.status}</strong></div> : null}
              {drawer.item.confidence ? <div><span>Confidence</span><strong>{drawer.item.confidence}</strong></div> : null}
              {drawer.item.summary ? (
                <article className="mc-code-card">
                  <strong>Summary</strong>
                  <p>{drawer.item.summary}</p>
                </article>
              ) : null}
              {drawer.item.rationale ? (
                <article className="mc-code-card">
                  <strong>Rationale</strong>
                  <p>{drawer.item.rationale}</p>
                </article>
              ) : null}
              {drawer.item.supportSummary ? (
                <article className="mc-code-card">
                  <strong>Why this exists</strong>
                  <p>{drawer.item.supportSummary}</p>
                </article>
              ) : null}
            </div>
            <StructuredDetailCard title="Detail" value={drawer.item} />
          </div>
        ) : null}

        {drawer.kind === 'development-focus' ? (
          <div className="mc-drawer-body">
            <div className="mc-keyval-grid">
              <div><span>Focus</span><strong>{drawer.item.title || 'Development Focus'}</strong></div>
              <div><span>Status</span><strong>{drawer.item.status || 'unknown'}</strong></div>
              <div><span>Type</span><strong>{drawer.item.focusType || drawer.item.focus_type || 'unknown'}</strong></div>
              <div><span>Confidence</span><strong>{drawer.item.confidence || 'unknown'}</strong></div>
            </div>
            <div className="mc-inline-meta">
              {drawer.item.sourceKind ? <span className="mc-meta-pill">Source {drawer.item.sourceKind.replace(/-/g, ' ')}</span> : null}
              {drawer.item.supportCount ? <span className="mc-meta-pill">{drawer.item.supportCount} supporting signals</span> : null}
              {drawer.item.sessionCount ? <span className="mc-meta-pill">{drawer.item.sessionCount} sessions</span> : null}
              {drawer.item.updatedAt ? <span className="mc-meta-pill">Updated {formatFreshness(drawer.item.updatedAt)}</span> : null}
            </div>
            {drawer.error ? <div className="inline-error">{drawer.error}</div> : null}
            {drawer.item.status !== 'completed' ? (
              <div className="mc-inline-actions">
                <button
                  className="primary-btn"
                  disabled={drawer.busy}
                  onClick={() => onDevelopmentFocusAction?.(drawer.item.focusId, 'complete')}
                >
                  {drawer.busy ? 'Working…' : 'Mark Completed'}
                </button>
              </div>
            ) : (
              <div className="mc-inline-meta">
                <span className="mc-meta-pill tone-success">Already completed</span>
              </div>
            )}
            {drawer.item.summary ? (
              <article className="mc-code-card">
                <strong>Summary</strong>
                <p>{drawer.item.summary}</p>
              </article>
            ) : null}
            {drawer.item.rationale ? (
              <article className="mc-code-card">
                <strong>Rationale</strong>
                <p>{drawer.item.rationale}</p>
              </article>
            ) : null}
            {drawer.item.statusReason ? (
              <article className="mc-code-card">
                <strong>Status Note</strong>
                <p>{drawer.item.statusReason}</p>
              </article>
            ) : null}
            {drawer.item.supportSummary ? (
              <article className="mc-code-card">
                <strong>Support Summary</strong>
                <p>{drawer.item.supportSummary}</p>
              </article>
            ) : null}
            <StructuredDetailCard title="Focus Detail" value={drawer.item} />
          </div>
        ) : null}
      </div>
    </aside>
  )
}
