import { useState } from 'react'
import { ChevronRight, ChevronDown, CheckCircle2, XCircle, Loader2, ListChecks } from 'lucide-react'
import type { ContentBlock } from '../../lib/sseProtocol'

type ProgressBlock = Extract<ContentBlock, { type: 'progress' }>

/** Foldbart "Forløb"-spor: den narration Jarvis viste undervejs ("Analyserede
 *  billede…") persisteret pr. tool i kald-rækkefølge, så forløbet overlever
 *  reload (spec 2026-07-09, FLAT v1). Default foldet når sporet er langt, så det
 *  ikke støjer oven på tool-kortene. parent_tool_use_id ignoreres i v1 (fladt). */
export function ProgressTrail({ items }: { items: ProgressBlock[] }) {
  const FOLD_THRESHOLD = 3
  const [open, setOpen] = useState(items.length <= FOLD_THRESHOLD)
  if (items.length === 0) return null
  const Chevron = open ? ChevronDown : ChevronRight

  return (
    <div className="progress-trail">
      <button
        type="button"
        className="progress-trail-head"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
      >
        <ListChecks size={13} className="progress-trail-icon" />
        <span className="progress-trail-label">Forløb ({items.length})</span>
        <Chevron size={14} className="progress-trail-chevron" />
      </button>
      {open && (
        <ol className="progress-trail-body">
          {items.map((p, i) => (
            <li key={`${p.tool_use_id}-${i}`} className={`progress-step status-${p.status}`}>
              <StatusIcon status={p.status} />
              <span className="progress-step-msg">{p.message}</span>
            </li>
          ))}
        </ol>
      )}
    </div>
  )
}

function StatusIcon({ status }: { status: ProgressBlock['status'] }) {
  if (status === 'error') return <XCircle size={13} className="progress-step-ico err" />
  if (status === 'running') return <Loader2 size={13} className="progress-step-ico run" />
  return <CheckCircle2 size={13} className="progress-step-ico ok" />
}
