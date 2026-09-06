import { useCallback, useEffect, useState } from 'react'
import { GraduationCap, Check, X } from 'lucide-react'
import { getLektier, saetLektionStatus, type Lektion } from '../../lib/coworkApi'
import type { ApiConfig } from '../../lib/api'

/** Lærings-løkken: forslag → dom → prompt.
 *
 *  Løkken var halv. Forslag blev skrevet, og aktive lektier går ind i
 *  prompten — men intet kunne flytte en lektion fra det ene til det andet.
 *  Fire forslag stod fra 4.-5. september uden at nogen kunne se dem.
 *
 *  Bevis-tallene står synligt: set én gang er en anelse, set tre gange er et
 *  mønster. Den vurdering er Bjørns, ikke appens.
 */
export function Lektier({ config }: { config?: ApiConfig }) {
  const [forslag, setForslag] = useState<Lektion[]>([])
  const [aktive, setAktive] = useState<Lektion[]>([])
  const [travl, setTravl] = useState<number | null>(null)
  const [fejl, setFejl] = useState('')

  const hent = useCallback(() => {
    if (!config) return
    getLektier(config)
      .then((d) => { setForslag(d.proposed); setAktive(d.active) })
      .catch(() => setFejl('Kunne ikke hente lektierne.'))
  }, [config?.apiBaseUrl, config?.authToken])

  useEffect(hent, [hent])

  const døm = async (id: number, status: 'active' | 'rejected') => {
    if (!config) return
    setTravl(id)
    try {
      const r = await saetLektionStatus(config, id, status)
      if (r.status !== 'ok') setFejl(r.error ?? 'Kunne ikke gemme dommen.')
      else hent()
    } catch {
      setFejl('Kunne ikke gemme dommen.')
    } finally {
      setTravl(null)
    }
  }

  if (fejl) return <p className="lk-tom">{fejl}</p>
  if (forslag.length === 0 && aktive.length === 0) return null

  return (
    <section className="lk">
      <h3 className="lk-head">
        <GraduationCap size={14} />
        <span>Lektier</span>
        {aktive.length > 0 && <span className="lk-aktive">{aktive.length} i brug</span>}
      </h3>

      {forslag.length === 0 ? (
        <p className="lk-tom">Ingen nye forslag.</p>
      ) : (
        <ul className="lk-liste">
          {forslag.map((l) => (
            <li key={l.id} className="lk-kort">
              <p className="lk-tekst">{l.lesson}</p>
              <div className="lk-fod">
                <span className="lk-kilde">{l.source}</span>
                <span className="lk-bevis">
                  set {l.evidence_count}×
                  {l.repeated_count > 0 ? ` · gentaget ${l.repeated_count}×` : ''}
                </span>
                <button
                  type="button" className="lk-ja" disabled={travl === l.id}
                  onClick={() => void døm(l.id, 'active')}
                  title="Aktive lektier går ind i hans prompt"
                >
                  <Check size={12} /> Gem som regel
                </button>
                <button
                  type="button" className="lk-nej" disabled={travl === l.id}
                  onClick={() => void døm(l.id, 'rejected')}
                >
                  <X size={12} /> Afvis
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
