import { X } from 'lucide-react'
import { formatFreshness } from './meta'

function renderJson(value) {
  return JSON.stringify(value, null, 2)
}

export function DetailDrawer({ drawer, onClose, onApprovalAction }) {
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
              {drawer.kind === 'jarvis' ? 'Jarvis state and continuity detail' : null}
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
              <pre>{renderJson(drawer.item.payload)}</pre>
            </article>
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
              <pre>{renderJson(drawer.item)}</pre>
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

        {drawer.kind === 'jarvis' ? (
          <div className="mc-drawer-body">
            <div className="mc-inline-meta">
              {drawer.item.source ? <span className="mc-meta-pill">Source {drawer.item.source}</span> : null}
              {drawer.item.createdAt ? <span className="mc-meta-pill">Updated {formatFreshness(drawer.item.createdAt)}</span> : null}
            </div>
            {drawer.item.summary ? (
              <article className="mc-code-card">
                <strong>Summary</strong>
                <p>{drawer.item.summary}</p>
              </article>
            ) : null}
            <article className="mc-code-card">
              <strong>Detail</strong>
              <pre>{renderJson(drawer.item)}</pre>
            </article>
          </div>
        ) : null}
      </div>
    </aside>
  )
}
