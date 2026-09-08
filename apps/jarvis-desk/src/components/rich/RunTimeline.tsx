import { useState } from 'react'
import {
  Brain, BookOpen, Search, FilePen, Terminal, FlaskConical,
  MessageSquare, ChevronRight, Check, X, Loader,
} from 'lucide-react'
import { byggeTidslinje, type Fase, type FaseSlags } from '../../lib/agentTimeline'
import type { ContentBlock } from '../../lib/sseProtocol'

const IKON: Record<FaseSlags, typeof Brain> = {
  taenkte: Brain, laeste: BookOpen, soegte: Search, aendrede: FilePen,
  koerte: Terminal, testede: FlaskConical, svarede: MessageSquare,
}

/** «Hvad skete der egentlig?» — turens forløb som én lodret linje.
 *
 *  Foldet sammen som standard: den skal kunne besvare spørgsmålet på ét blik
 *  uden at fylde over selve svaret. Åbner man den, står faserne i rækkefølge.
 */
export function RunTimeline({ blocks }: { blocks: ContentBlock[] }) {
  const [aaben, setAaben] = useState(false)
  const faser = byggeTidslinje(blocks)

  // En tur uden værktøjsarbejde har intet forløb at fortælle om.
  const harArbejde = faser.some((f) => f.slags !== 'svarede' && f.slags !== 'taenkte')
  if (!harArbejde) return null

  const fejlede = faser.some((f) => f.status === 'fejl')
  const arbejde = faser.filter((f) => f.slags !== 'svarede')
  // Resuméet bærer nu den FØRSTE detalje: «Kørte en kommando» sagde ikke hvad
  // der blev kørt, og så var linjen ikke værd at læse (Bjørn 8/9-2026).
  const resume = arbejde
    .map((f) => (f.detaljer[0] ? `${f.label}: ${f.detaljer[0]}` : f.label))
    .join(' · ')

  return (
    <div className={`runtl${fejlede ? ' har-fejl' : ''}`}>
      <button
        type="button"
        className="runtl-head"
        onClick={() => setAaben((o) => !o)}
        aria-expanded={aaben}
      >
        <ChevronRight size={13} className={`runtl-pil${aaben ? ' aaben' : ''}`} />
        <span className="runtl-titel">Forløb ({arbejde.length})</span>
        <span className="runtl-resume">{resume}</span>
      </button>
      {aaben && (
        <ol className="runtl-liste">
          {faser.map((f, i) => (
            <li key={i} className={`runtl-fase st-${f.status}`}>
              <Prik fase={f} />
              <span className="runtl-label">{f.label}</span>
              {f.detaljer.length > 0 && (
                <span className="runtl-detaljer">
                  {f.detaljer.map((d, j) => <code key={j} className="runtl-detalje">{d}</code>)}
                </span>
              )}
            </li>
          ))}
        </ol>
      )}
    </div>
  )
}

function Prik({ fase }: { fase: Fase }) {
  const Ikon = IKON[fase.slags]
  return (
    <span className="runtl-prik">
      <Ikon size={12} />
      {fase.status === 'fejl' && <X size={9} className="runtl-mrk mrk-fejl" />}
      {fase.status === 'koerer' && <Loader size={9} className="runtl-mrk mrk-koerer" />}
      {fase.status === 'ok' && fase.slags === 'testede' && <Check size={9} className="runtl-mrk mrk-ok" />}
    </span>
  )
}
