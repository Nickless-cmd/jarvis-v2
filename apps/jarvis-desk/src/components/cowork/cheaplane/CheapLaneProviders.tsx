/**
 * Cheap lanes udbydere og modeller — og KUN dem.
 *
 * Den almindelige udbyder-side findes stadig og viser hele registret. Blandes
 * de to, kan man komme til at slukke for den synlige lane fra et panel der
 * hedder «cheap». Derfor filtreres der på `lane === 'cheap'` her, og en
 * tilføjelse sender altid `lane: 'cheap'` — der er med vilje ingen lane-vælger.
 */
import { useMemo, useState } from 'react'
import type { Registret } from '../../../lib/cheapLaneApi'
import { Handling, type Udfoer } from './CheapLaneControls'

export function CheapLaneProviders({
  registret, udfoer, onInspicer,
}: {
  registret: Registret | null
  udfoer: Udfoer
  /** Åbner rækken i den delte inspektør til højre. */
  onInspicer?: (provider: string, model: string) => void
}) {
  const [søg, setSøg] = useState('')

  const rækker = useMemo(() => {
    const alle = (registret?.modeller ?? []).filter((m) => (m.lane ?? '') === 'cheap')
    const q = søg.trim().toLowerCase()
    if (!q) return alle
    return alle.filter((m) =>
      `${m.provider ?? ''} ${m.model ?? ''} ${m.lane ?? ''}`.toLowerCase().includes(q))
  }, [registret, søg])

  return (
    <div className="cl-udbydere">
      <div className="cl-soeg-raekke">
        <label>
          Søg
          <input value={søg} onChange={(e) => setSøg(e.target.value)}
                 placeholder="udbyder, model eller profil" />
        </label>
        <span className="cl-dæmpet">{rækker.length} modeller i cheap lane</span>
      </div>

      {rækker.length === 0 ? (
        <p className="cl-tom">Ingen modeller i cheap lane matcher.</p>
      ) : (
        <div className="cl-tabel-holder">
          <table className="cl-tabel">
            <thead>
              <tr>
                <th scope="col">Udbyder</th>
                <th scope="col">Model</th>
                <th scope="col">Status</th>
                <th scope="col">Handlinger</th>
              </tr>
            </thead>
            <tbody>
              {rækker.map((m) => {
                const mål = `${m.provider}/${m.model}`
                return (
                  <tr key={mål}>
                    <th scope="row">
                      <button type="button" className="cl-linkknap"
                              onClick={() => onInspicer?.(String(m.provider), String(m.model))}>
                        {m.provider}
                      </button>
                    </th>
                    <td>{m.model}</td>
                    <td>
                      <span className={m.enabled ? 'cl-status-aktiv' : 'cl-status-fra'}>
                        {m.enabled ? 'aktiv' : 'slået fra'}
                      </span>
                    </td>
                    <td className="cl-handlinger">
                      {/* Midlertidig: væk ved næste opbygning af puljen. */}
                      <Handling etiket={`Pause ${m.model}`} udfoer={udfoer}
                                kommando={{ action: 'model.pause', target: mål }} />
                      {/* Varig: overlever en genstart, og kræver derfor en grund. */}
                      <Handling etiket={`Deaktivér ${m.model}`} udfoer={udfoer} variant="advarsel"
                                beskrivelse="Modellen bliver væk af puljen — også efter en genstart."
                                kommando={{ action: 'model.deactivate', target: mål }} />
                      <Handling etiket={`Fjern ${m.model}`} udfoer={udfoer} variant="destruktiv"
                                beskrivelse="Modellen fjernes fra registret."
                                kommando={{ action: 'model.delete', target: mål }} />
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
