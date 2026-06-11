import { useState } from 'react'
import type { ContentBlock } from '../../lib/sseProtocol'

/** Density-aware tool-kald visning. compact = kompakt linje, udfold på klik
 *  (Chat-mode); full = altid udfoldet timeline-kort (Code-mode). Argumenter og
 *  resultat rendres som INERT tekst via <pre> — aldrig som markdown/HTML — så
 *  fjendtligt tool-output ikke kan injicere klikbare elementer. */
export function ToolCard({
  block,
  density,
}: {
  block: Extract<ContentBlock, { type: 'tool_use' }>
  density: 'compact' | 'full'
}) {
  const [open, setOpen] = useState(density === 'full')
  const expanded = density === 'full' || open
  return (
    <div className="toolcard">
      <button
        type="button"
        className="toolcard-head"
        onClick={() => density === 'compact' && setOpen((o) => !o)}
      >
        <span className="toolcard-name">{block.name}</span>
        <span className="toolcard-status">{block.status ?? 'running'}</span>
      </button>
      {expanded && (
        <div className="toolcard-body">
          {block.partialJson && <pre className="toolcard-args">{block.partialJson}</pre>}
          {block.result && <pre className="toolcard-result">{block.result}</pre>}
        </div>
      )}
    </div>
  )
}
