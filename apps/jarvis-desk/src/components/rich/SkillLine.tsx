import { useState } from 'react'
import { ChevronDown, ChevronRight, Sparkles } from 'lucide-react'
import type { ContentBlock } from '../../lib/sseProtocol'
import { scoreTekst, skillOversigt } from '../../lib/skillLinje'
import { useLoebendeTid } from '../../lib/useLoebendeTid'
import { ToolCard } from './ToolCard'

/**
 * Én linje når skill-gaten fyrer eller en skill indlæses — søskende til
 * runde-linjen og tanke-linjen. Se `lib/skillLinje.ts` for hvorfor.
 *
 *     ✦ Tjekker skills for «lav et regneark» · 2 s
 *     ✦ Skill-gate: xlsx · 0,82 · indlæst · 4,2k tegn  ›
 *     ✦ Indlæste skill git-advanced · 6,1k tegn  ›
 */
export function SkillLine({
  block,
  density,
}: {
  block: Extract<ContentBlock, { type: 'tool_use' }>
  density: 'compact' | 'full'
}) {
  const [open, setOpen] = useState(false)
  const o = skillOversigt(block)
  const sek = useLoebendeTid(o.koerer)
  const Chevron = open ? ChevronDown : ChevronRight
  const meta = o.koerer && sek != null && sek >= 1 ? [...o.meta, `${Math.floor(sek)} s`] : o.meta

  return (
    <div className={`toolgroup skill-linje${o.koerer ? ' er-koerende' : ''}${o.fejl ? ' har-fejl' : ''}`}>
      <button
        type="button"
        className="toolgroup-head"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        <Sparkles size={15} className="toolgroup-icon" strokeWidth={1.8} />
        <span className="toolgroup-label">
          {o.titel}
          {meta.length ? <span className="skill-meta">{meta.map((m) => ` · ${m}`).join('')}</span> : null}
        </span>
        <Chevron size={15} className="toolgroup-chevron" strokeWidth={1.8} />
      </button>
      {open && (
        <div className="toolgroup-body skill-body">
          {o.beskrivelse ? <p className="skill-beskrivelse">{o.beskrivelse}</p> : null}
          {o.matches.length > 1 ? (
            <ul className="skill-matches">
              {o.matches.map((m) => (
                <li key={m.name}><span>{m.name}</span><span className="skill-score">{scoreTekst(m.score)}</span></li>
              ))}
            </ul>
          ) : null}
          {/* Det rå kald står stadig til rådighed — linjen er et resumé, ikke et filter. */}
          <ToolCard block={block} density={density} />
        </div>
      )}
    </div>
  )
}
