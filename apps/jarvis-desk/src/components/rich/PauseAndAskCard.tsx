import { HelpCircle } from 'lucide-react'
import { emitPauseSvar, type PauseAsk } from '../../lib/pauseAsk'

/** Jarvis standsede og spurgte. Spørgsmålet vises INERT (som ApprovalCard),
 *  så fjendtligt tool-indhold ikke kan udgive sig for at være en knap. Kun
 *  option-strengene bliver knapper, og et klik gør præcis én ting: sender
 *  teksten som næste bruger-besked. Ingen knap udfører noget i sig selv.
 */
export function PauseAndAskCard({ ask }: { ask: PauseAsk }) {
  return (
    <div className={`pauseask haste-${ask.urgency}`}>
      <div className="pauseask-head">
        <HelpCircle size={14} />
        <span>Jarvis venter på dig</span>
      </div>
      <p className="pauseask-q">{ask.question}</p>
      {ask.context && <pre className="pauseask-ctx">{ask.context}</pre>}
      {ask.options.length > 0 ? (
        <div className="pauseask-valg">
          {ask.options.map((o) => (
            <button
              key={o}
              type="button"
              className="pauseask-btn"
              onClick={() => emitPauseSvar(o)}
            >
              {o}
            </button>
          ))}
        </div>
      ) : (
        <div className="pauseask-fri">Svar i feltet nedenfor.</div>
      )}
    </div>
  )
}
