import { useState } from 'react'
import { ChevronDown, Sparkles } from 'lucide-react'
import type { ContentBlock } from '../../lib/sseProtocol'
import { scoreTekst, skillOversigt } from '../../lib/skillLinje'
import { useLoebendeTid } from '../../lib/useLoebendeTid'
import { Prikker, udenEllipse } from './Prikker'
import { Fold } from './Fold'
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
  const sek = useLoebendeTid(o.koerer, block.startet)
  const meta = o.koerer && sek != null && sek >= 1 ? [...o.meta, `${Math.floor(sek)} s`] : o.meta

  return (
    <div className={`toolgroup skill-linje${o.koerer ? ' er-koerende' : ''}${o.fejl ? ' har-fejl' : ''}${open ? ' er-aaben' : ''}`}>
      <button
        type="button"
        className="toolgroup-head"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        {/* Samme opbygning som runde-linjen — se ThinkingLine. */}
        <span className="toolgroup-spark" aria-hidden="true">
          <Sparkles size={15} className="toolgroup-icon" strokeWidth={1.8} />
        </span>
        <span className="toolgroup-label">
          <span className={`linje-titel${o.koerer ? ' shimmer' : ''}`}>{o.koerer ? udenEllipse(o.titel) : o.titel}</span>
          {meta.length ? <span className="linje-meta skill-meta">{meta.map((m) => ` · ${m}`).join('')}</span> : null}
        </span>
        <span className="toolgroup-celle">
          <Prikker live={o.koerer} />
          <ChevronDown size={15} className="toolgroup-chevron" strokeWidth={1.8} />
        </span>
      </button>
      <Fold aaben={open}>
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
      </Fold>
    </div>
  )
}

/**
 * Skills runtimen selv lagde i prompten — den automatiske gate, uden et kald.
 *
 *     ✦ Skill-match: xlsx · 0,78 · stærkt match  ›
 *     ✦ Skills foreslået: pdf, csv · bedst 0,72  ›
 *
 * Et stærkt match er en instruks i prompten («læs skillet før du svarer»), et
 * svagt et tilbud. Linjen skal skelne dem, ellers ser «han ignorerede et
 * tilbud» og «han ignorerede en instruks» ens ud.
 */
export function SkillSurfaceLine({ block }: { block: Extract<ContentBlock, { type: 'skill_surface' }> }) {
  const [open, setOpen] = useState(false)
  const sorteret = [...block.matches].sort((a, b) => b.score - a.score)
  const bedst = sorteret[0]
  if (!bedst) return null
  const staerke = sorteret.filter((m) => m.primary)
  const titel = staerke.length
    ? `Skill-match: ${staerke.map((m) => m.name).join(', ')}`
    : `Skills foreslået: ${sorteret.map((m) => m.name).join(', ')}`
  const meta = staerke.length
    ? [scoreTekst(staerke[0]!.score), 'stærkt match', ...(sorteret.length > staerke.length ? [`+${sorteret.length - staerke.length} svagere`] : [])]
    : [`bedst ${scoreTekst(bedst.score)}`]
  return (
    <div className={`toolgroup skill-linje skill-flade${open ? ' er-aaben' : ''}`}>
      <button type="button" className="toolgroup-head" aria-expanded={open} onClick={() => setOpen((v) => !v)}>
        <span className="toolgroup-spark" aria-hidden="true">
          <Sparkles size={15} className="toolgroup-icon" strokeWidth={1.8} />
        </span>
        <span className="toolgroup-label">
          <span className="linje-titel">{titel}</span>
          <span className="linje-meta skill-meta">{meta.map((m) => ` · ${m}`).join('')}</span>
        </span>
        <span className="toolgroup-celle">
          <ChevronDown size={15} className="toolgroup-chevron" strokeWidth={1.8} />
        </span>
      </button>
      <Fold aaben={open}>
        <div className="toolgroup-body skill-body">
          <p className="skill-beskrivelse">
            {staerke.length
              ? 'Runtimen lagde skillet i prompten som instruks: læs det før svaret.'
              : 'Runtimen lagde skills i prompten som tilbud — ikke et krav.'}
          </p>
          <ul className="skill-matches">
            {sorteret.map((m) => (
              <li key={m.name}><span>{m.name}{m.primary ? ' · stærkt' : ''}</span><span className="skill-score">{scoreTekst(m.score)}</span></li>
            ))}
          </ul>
        </div>
      </Fold>
    </div>
  )
}
