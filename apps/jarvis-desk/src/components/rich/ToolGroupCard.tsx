import { useState } from 'react'
import { ChevronDown, Code2 } from 'lucide-react'
import type { ToolGroupBlock } from '../../lib/toolRounds'
import { summarizeRound, summerDiff } from '../../lib/toolRound'
import { KLOKKE_EFTER_S, useLoebendeTid } from '../../lib/useLoebendeTid'
import { Prikker, udenEllipse } from './Prikker'
import { Fold } from './Fold'
import { LabelSkift, formatTid } from './LabelSkift'
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
 * Linjen ændrer sig mens runden kører («Læser 3 filer») og lander på sin datid
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
   * Rundens sætning — «Rettede fejl i login».
   *
   * Skrevet af en lille lokal model på serveren og slået op på kaldets id.
   * Den ERSTATTER den mekaniske tekst (Claude Desktop 1:1, 19/9-2026); før
   * stod den som overskrift over linjen. Udeladt = den mekaniske tekst.
   * Kommer live fra streamen og gemt fra beskedens tool_use_summary-blokke.
   */
  etiket?: string
}) {
  const [open, setOpen] = useState(false)
  const resume = summarizeRound(block.tools)
  const sum = summerDiff(block.tools)
  const koerer = block.tools.some((t) => (t.status ?? 'running') === 'running')
  // Live tid for runden, fra det første kald der stadig kører (Bjørn 17/9-2026:
  // live metadata i stedet for en linje der står stille til kaldet er færdigt).
  const startet = block.tools
    .filter((t) => (t.status ?? 'running') === 'running' && t.startet != null)
    .reduce<number | undefined>((min, t) => (min == null || t.startet! < min ? t.startet : min), undefined)
  const sek = useLoebendeTid(koerer && startet != null, startet)
  // Klokken venter mens linjen KØRER (se KLOKKE_EFTER_S): et kald på to
  // sekunder skal ikke nå at vise «0 s» og skifte. Er runden færdig, vises det
  // målte tal med det samme — der er ingen flimren at undgå, og tallet er
  // information man vil have.
  const visSek = sek == null || (koerer && sek < KLOKKE_EFTER_S) ? null : Math.floor(sek)
  if (!resume) return null
  // Claude Desktop 1:1 (19/9-2026, læst i `Tf`: `summary || … || mekanisk`):
  // modellens sætning ERSTATTER den mekaniske tekst, når den findes. Før stod
  // den som overskrift OVER linjen. Den kommer først når runden er talt op,
  // så skiftet går gennem label-skiftet som et almindeligt tekstskift.
  const tekst = etiket ? etiket : koerer ? udenEllipse(resume) : resume

  return (
    <div className={`toolgroup${koerer ? ' er-koerende' : ''}${open ? ' er-aaben' : ''}`}>
      <button
        type="button"
        className="toolgroup-head"
        aria-expanded={open}
        aria-label={tekst}
        onClick={() => setOpen((o) => !o)}
      >
        {/* Spark-cellen (Claude Desktop, 19/9-2026): 20 px bred mens runden
            arbejder, ingenting bagefter. Når arbejdet slutter, overtager
            label-skiftets spark-lag glyfen og lader den tone ud. */}
        <span className="toolgroup-spark" aria-hidden="true">
          <Code2 size={15} className="toolgroup-icon" strokeWidth={1.8} />
        </span>
        <span className="toolgroup-label">
          <LabelSkift
            tekst={tekst}
            arbejder={koerer}
            className={koerer ? 'shimmer' : ''}
          />
        </span>
        {/* Klokken i kildens format («12s», «1m 5s») og med dens 65 % —
            tallet må ikke konkurrere med labelen. */}
        {visSek != null
          ? <span className="linje-tid" data-testid="runde-tid">{formatTid(visSek)}</span>
          : null}
        {/* Summen i selve linjen, 1:1 med mobilen: foldet som standard ville
            tallene ellers kun ses af den der folder ud. Et nul vises ikke. */}
        {sum ? (
          <span className="toolgroup-diffstat" data-testid="toolgroup-diffstat">
            {sum.add ? <span className="git-add">+{sum.add}</span> : null}
            {sum.add && sum.del ? ' ' : null}
            {sum.del ? <span className="git-del">−{sum.del}</span> : null}
          </span>
        ) : null}
        {/* Prikker og caret i SAMME celle. Mens runden kører står prikkerne
            fremme; ved hover eller tastaturfokus krydsfader de til careten
            (200 ms). Careten er én glyf der drejes -90° når runden er foldet,
            så åbn/luk er en drejning og ikke et ikon-bytte. */}
        <span className="toolgroup-celle" data-testid="tool-status-caret">
          <Prikker live={koerer} />
          <ChevronDown size={15} className="toolgroup-chevron" strokeWidth={1.8} />
        </span>
      </button>
      <Fold aaben={open}>
        <div className="toolgroup-body">
          {block.tools.map((t) => (
            <ToolCard key={t.id} block={t} density={density} />
          ))}
        </div>
      </Fold>
    </div>
  )
}
