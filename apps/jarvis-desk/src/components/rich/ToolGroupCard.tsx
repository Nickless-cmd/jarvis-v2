import { useState } from 'react'
import { ChevronRight, ChevronDown, Code2 } from 'lucide-react'
import type { ToolGroupBlock } from '../../lib/toolRounds'
import { summarizeRound, summerDiff } from '../../lib/toolRound'
import { useLoebendeTid } from '../../lib/useLoebendeTid'
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
  etiket,
}: {
  block: ToolGroupBlock
  density: 'compact' | 'full'
  /**
   * Overskriften over runden — «Rettede fejl i login».
   *
   * Skrevet af en lille lokal model på serveren og slået op på kaldets id.
   * Udeladt = ingen overskrift; kortet skal kunne stå uden, for den kommer
   * først når runden er talt op. 1:1 med mobilen.
   */
  etiket?: string
}) {
  const [open, setOpen] = useState(false)
  const Chevron = open ? ChevronDown : ChevronRight
  const resume = summarizeRound(block.tools)
  const sum = summerDiff(block.tools)
  const koerer = block.tools.some((t) => (t.status ?? 'running') === 'running')
  // Live tid for runden, fra det første kald der stadig kører (Bjørn 17/9-2026:
  // live metadata i stedet for en linje der står stille til kaldet er færdigt).
  const startet = block.tools
    .filter((t) => (t.status ?? 'running') === 'running' && t.startet != null)
    .reduce<number | undefined>((min, t) => (min == null || t.startet! < min ? t.startet : min), undefined)
  const sek = useLoebendeTid(koerer && startet != null, startet)
  if (!resume) return null

  return (
    <div className={`toolgroup${koerer ? ' er-koerende' : ''}`}>
      {/* Bjoerns raekkefoelge: etiketten FOERST, det mekaniske efter.
          Overskriften siger hvad runden UDRETTEDE; linjen under hvad der
          SKETE. */}
      {etiket ? <div className="toolgroup-etiket">{etiket}</div> : null}
      <button
        type="button"
        className="toolgroup-head"
        aria-expanded={open}
        aria-label={etiket ? `${etiket}. ${resume}` : resume}
        onClick={() => setOpen((o) => !o)}
      >
        <Code2 size={15} className="toolgroup-icon" strokeWidth={1.8} />
        <span className="toolgroup-label">
          <span className="linje-titel">{resume}</span>
          {koerer && sek != null && sek >= 1
            ? <span className="linje-meta" data-testid="runde-tid"> · {Math.floor(sek)} s</span>
            : null}
        </span>
        {/* Summen i selve linjen, 1:1 med mobilen: foldet som standard ville
            tallene ellers kun ses af den der folder ud. Et nul vises ikke. */}
        {sum ? (
          <span className="toolgroup-diffstat" data-testid="toolgroup-diffstat">
            {sum.add ? <span className="git-add">+{sum.add}</span> : null}
            {sum.add && sum.del ? ' ' : null}
            {sum.del ? <span className="git-del">−{sum.del}</span> : null}
          </span>
        ) : null}
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
