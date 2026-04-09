import { useState } from 'react'
import { ShieldCheck, ShieldX } from 'lucide-react'

export function ApprovalCard({ approval }) {
  const [state, setState] = useState('pending')
  const [resultText, setResultText] = useState('')

  const handleApprove = async () => {
    setState('approving')
    try {
      const res = await fetch(`/chat/approvals/${approval.approval_id}/approve`, { method: 'POST' })
      const data = await res.json()
      if (data.status === 'ok') {
        setState('approved')
        setResultText(data.result_text || 'Done')
      } else {
        setState('error')
        setResultText(data.error || data.detail || 'Failed')
      }
    } catch (err) {
      setState('error')
      setResultText(String(err))
    }
  }

  const handleDeny = async () => {
    try {
      await fetch(`/chat/approvals/${approval.approval_id}/deny`, { method: 'POST' })
    } catch { /* ignore */ }
    setState('denied')
  }

  return (
    <div className={`approval-card ${state}`}>
      <div className="approval-header">
        {state === 'denied' ? <ShieldX size={14} /> : <ShieldCheck size={14} />}
        <span className="approval-tool mono">{approval.tool}</span>
      </div>
      <div className="approval-detail mono">{approval.detail || approval.message}</div>
      {state === 'pending' && (
        <div className="approval-actions">
          <button className="approval-btn approve" onClick={handleApprove}>Approve</button>
          <button className="approval-btn deny" onClick={handleDeny}>Deny</button>
        </div>
      )}
      {state === 'approving' && <div className="approval-status">Executing...</div>}
      {state === 'approved' && <div className="approval-status ok">{resultText}</div>}
      {state === 'denied' && <div className="approval-status denied">Denied</div>}
      {state === 'error' && <div className="approval-status error">{resultText}</div>}
    </div>
  )
}
