import { useState } from 'react'
import { Check, X, FileText } from 'lucide-react'
import type { QueueItem } from '../../lib/coworkApi'

export function ApprovalQueue({ items, onResolve }: { items: QueueItem[]; onResolve: (id: string, d: 'approve' | 'reject') => void }) {
  if (items.length === 0) return <div className="cowork-empty">Ingen afventende godkendelser</div>
  return (
    <div className="cowork-queue">
      {items.map((it) => <QueueRow key={it.id} item={it} onResolve={onResolve} />)}
    </div>
  )
}

function QueueRow({ item, onResolve }: { item: QueueItem; onResolve: (id: string, d: 'approve' | 'reject') => void }) {
  const [showDiff, setShowDiff] = useState(false)
  return (
    <div className="cowork-item">
      <div className="cowork-item-title"><FileText size={13} /> {item.title}</div>
      {item.detail && <div className="cowork-item-detail">{item.detail}</div>}
      <div className="cowork-item-actions">
        <button type="button" onClick={() => onResolve(item.id, 'approve')}><Check size={12} /> Godkend</button>
        <button type="button" onClick={() => onResolve(item.id, 'reject')}><X size={12} /> Afvis</button>
        {item.diff && <button type="button" onClick={() => setShowDiff((s) => !s)}>Diff</button>}
      </div>
      {showDiff && item.diff && <pre className="cowork-diff">{item.diff}</pre>}
    </div>
  )
}
