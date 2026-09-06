import { useEffect, useState } from 'react'
import { Users, Check, X, Loader2 } from 'lucide-react'
import { getAgentArbejde, type AgentArbejde } from '../../lib/coworkApi'
import type { ApiConfig } from '../../lib/api'

/** Hans subagenter som synlige arbejdere.
 *
 *  Ikke skjult intern magi: rolle, udfald, model, tokens og pris pr. kørsel.
 *  Rollen kommer fra registret; er agenten ikke registreret, står feltet tomt
 *  frem for at få en opdigtet titel.
 */
const IKON: Record<string, typeof Check> = { completed: Check, failed: X, running: Loader2 }

export function AgentWork({ config }: { config?: ApiConfig }) {
  const [runs, setRuns] = useState<AgentArbejde[] | null>(null)
  const [fejl, setFejl] = useState('')

  useEffect(() => {
    if (!config) return
    let levende = true
    getAgentArbejde(config, 20)
      .then((d) => { if (levende) setRuns(d.runs) })
      .catch(() => { if (levende) setFejl('Kunne ikke hente agent-arbejdet.') })
    return () => { levende = false }
  }, [config?.apiBaseUrl, config?.authToken])

  if (fejl) return <p className="aw-tom">{fejl}</p>
  if (!runs) return null
  if (runs.length === 0) return <p className="aw-tom">Ingen subagenter har kørt endnu.</p>

  return (
    <section className="aw">
      <h3 className="aw-head"><Users size={14} /> Hans arbejdere</h3>
      <ul className="aw-liste">
        {runs.map((r) => {
          const Ikon = IKON[r.status] ?? Check
          return (
            <li key={r.run_id} className={`aw-kort st-${r.status}`}>
              <div className="aw-top">
                <Ikon size={12} className={r.status === 'running' ? 'wq-spin' : undefined} />
                <span className="aw-rolle">{r.role || 'uden rolle'}</span>
                {r.execution_mode && <span className="aw-mode">{r.execution_mode}</span>}
                <span className="aw-pris">
                  {r.tokens > 0 ? `${Math.round(r.tokens / 100) / 10}k tokens` : ''}
                  {r.cost_usd > 0 ? ` · $${r.cost_usd.toFixed(3)}` : ''}
                </span>
              </div>
              {r.goal && <p className="aw-maal">{r.goal}</p>}
              {r.output_summary && <p className="aw-ud">{r.output_summary}</p>}
            </li>
          )
        })}
      </ul>
    </section>
  )
}
