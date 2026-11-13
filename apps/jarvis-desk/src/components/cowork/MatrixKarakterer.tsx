import type { ApiConfig } from '../../lib/api'
import { getMatrixKarakterer } from '../../lib/api'
import { usePollWhenVisible } from '../../hooks/usePollWhenVisible'
import {
  formatCooldown, formatSidste, karakterListe, splitFunktion, udfaldVisning,
} from '../../lib/matrixKarakterer'

const POLL_MS = 30_000

/** Matrix-karaktererne i Systemstatus — navn + funktion, sidste kørsel, effektiv
 *  cooldown og SENESTE UDFALD. Listen kommer fra serveren (udledt af registret);
 *  der er ingen karakter-liste i denne fil. */
export function MatrixKarakterer({ config }: { config?: ApiConfig }) {
  const { data, loading, error } = usePollWhenVisible(
    () => getMatrixKarakterer(config!), POLL_MS, !!config,
  )
  if (error) return <div className="jm-error">Kunne ikke hente karaktererne: {error}</div>
  if (!data) return <div className="jm-dim">{loading ? 'Henter…' : 'Ingen data.'}</div>
  const liste = karakterListe(data)
  if (!data.active || liste.length === 0) {
    return <div className="jm-dim">Ingen Matrix-karakterer i cadence-registret.</div>
  }
  return (
    <>
      <div className="jm-section-sub">
        {liste.length} karakterer · tempo ×{data.tempo.toFixed(2)}
      </div>
      <div className="jm-feed mk-liste">
        {liste.map((k) => {
          const { navn, beskrivelse } = splitFunktion(k.funktion, k.name)
          const u = udfaldVisning(k)
          return (
            <div key={k.name} className="jm-feed-row mk-raekke">
              <span className={`jm-dot ${k.last_run_at ? 'on' : 'off'}`} />
              <span className="mk-navn">
                <b>{navn}</b>
                {beskrivelse && <span className="jm-dim"> — {beskrivelse}</span>}
              </span>
              <span className="jm-dim mk-sidste">{formatSidste(k.last_run_at)}</span>
              <span className="jm-dim mk-cooldown">{formatCooldown(k, data.tempo)}</span>
              <span className={`mk-udfald mk-tone-${u.tone}`} title={u.title}>{u.tekst}</span>
            </div>
          )
        })}
      </div>
    </>
  )
}
