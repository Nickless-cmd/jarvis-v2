import { useState } from 'react'
import { ChevronRight, ChevronDown, Search } from 'lucide-react'
import type { ToolGroupBlock } from '../../lib/groupReadSearch'
import { ToolCard } from './ToolCard'

/** Sammenfoldet visning af en run af read/søge-tool-kald. Default foldet: én
 *  kompakt linje ("🔍 Læste/søgte N gange") med en chevron. Klik folder ud til
 *  de individuelle ToolCard-kort (genbrugt), med status/resultat bevaret. */
export function ToolGroupCard({
  block,
  density,
}: {
  block: ToolGroupBlock
  density: 'compact' | 'full'
}) {
  const [open, setOpen] = useState(false)
  const Chevron = open ? ChevronDown : ChevronRight

  return (
    <div className="toolgroup">
      <button
        type="button"
        className="toolgroup-head"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
      >
        <Search size={13} className="toolgroup-icon" />
        <span className="toolgroup-label">Læste/søgte {block.count} gange</span>
        <Chevron size={14} className="toolgroup-chevron" />
      </button>
      {open && (
        <div className="toolgroup-body">
          {block.tools.map((t) => (
            <ToolCard key={t.id} block={t} density={density} />
          ))}
        </div>
      )}
    </div>
  )
}
