import { useState } from 'react'
import { ChevronRight, ChevronDown, Code2 } from 'lucide-react'
import type { ToolGroupBlock } from '../../lib/toolRounds'
import { summarizeRound } from '../../lib/toolRound'
import { ToolCard } from './ToolCard'

/**
 * Én sammenfoldet linje for en HEL runde værktøjsarbejde — 1:1 med mobilens
 * `InlineToolGroup` (Bjørn 8/9-2026: «det skal lige 1:1»).
 *
 *     fortælling
 *     </> Kørte agent.ts
 *     fortælling
 *     </> Kørte 2 ting  ›
 *
 * Linjen ændrer sig mens runden kører («Læser 3 filer…») og lander på sin datid
 * når den er færdig. Trykker man, folder den ud.
 *
 * Én forskel fra mobilen, og den er bevidst: mobilen skjuler chevronen ved ét
 * kald, fordi den intet har at folde ud. Desk HAR noget — diff, output,
 * argumenter — så chevronen står der. Reglen er den samme (chevron hvis der er
 * noget bag den); det er kun svaret der er forskelligt, fordi funktionen er.
 */
export function ToolGroupCard({
  block,
  density,
}: {
  block: ToolGroupBlock
  density: 'compact' | 'full'
}) {
  const [open, setOpen] = useState(false)
  const Chevron = open ? ChevronDown : ChevronRight
  const resume = summarizeRound(block.tools)
  if (!resume) return null

  const koerer = block.tools.some((t) => (t.status ?? 'running') === 'running')

  return (
    <div className={`toolgroup${koerer ? ' er-koerende' : ''}`}>
      <button
        type="button"
        className="toolgroup-head"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
      >
        <Code2 size={15} className="toolgroup-icon" strokeWidth={1.8} />
        <span className="toolgroup-label">{resume}</span>
        <Chevron size={15} className="toolgroup-chevron" strokeWidth={1.8} />
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
