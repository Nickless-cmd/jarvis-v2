import { useState } from 'react'
import { ArrowDown, ArrowUp, Check, Pencil, Send, X } from 'lucide-react'

export function QueuedFollowups({ items, error, isStreaming, steerReady, onEdit, onRemove, onMove, onSendNow }) {
  const [editingId, setEditingId] = useState(null)
  const [draft, setDraft] = useState('')
  if (!items.length && !error) return null
  return (
    <div className="composer-followups" aria-label="Queued follow-ups">
      <div className="composer-followups-heading mono">queued · {items.length}</div>
      <div className="composer-followups-list">
        {items.map((item, index) => (
          <div className="composer-followup-row" key={item.id}>
            {editingId === item.id ? (
              <textarea className="composer-followup-edit" aria-label="Edit follow-up"
                value={draft} onChange={(event) => setDraft(event.target.value)} autoFocus rows={2} />
            ) : (
              <span className="composer-followup-text" title={item.msg}>
                {item.msg || 'Attachment'}
                {item.opts?.attachmentIds?.length ? ` · ${item.opts.attachmentIds.length} file(s)` : ''}
              </span>
            )}
            <div className="composer-followup-actions">
              {editingId === item.id ? (
                <>
                  <button type="button" title="Save edit" aria-label="Save edit"
                    disabled={!draft.trim() && !item.opts?.attachmentIds?.length}
                    onClick={() => { onEdit(item.id, draft); setEditingId(null) }}><Check size={14} /></button>
                  <button type="button" title="Cancel edit" aria-label="Cancel edit"
                    onClick={() => setEditingId(null)}><X size={14} /></button>
                </>
              ) : (
                <>
                  <button type="button" title="Edit follow-up" aria-label="Edit follow-up"
                    onClick={() => { setEditingId(item.id); setDraft(item.msg) }}><Pencil size={14} /></button>
                  <button type="button" title="Move up" aria-label="Move up" disabled={index === 0}
                    onClick={() => onMove(item.id, -1)}><ArrowUp size={14} /></button>
                  <button type="button" title="Move down" aria-label="Move down" disabled={index === items.length - 1}
                    onClick={() => onMove(item.id, 1)}><ArrowDown size={14} /></button>
                  <button type="button" title={isStreaming ? item.opts?.attachmentIds?.length ? 'Attachments wait until the run finishes' : 'Send now to active run' : 'Send now'}
                    aria-label={isStreaming ? 'Send now to active run' : 'Send now'} disabled={isStreaming && (!steerReady || !!item.opts?.attachmentIds?.length)}
                    onClick={() => void onSendNow(item.id)}><Send size={14} /></button>
                  <button type="button" title="Remove from queue" aria-label="Remove from queue"
                    onClick={() => onRemove(item.id)}><X size={14} /></button>
                </>
              )}
            </div>
          </div>
        ))}
      </div>
      {error ? <div className="composer-followup-error" role="alert">{error}</div> : null}
    </div>
  )
}
