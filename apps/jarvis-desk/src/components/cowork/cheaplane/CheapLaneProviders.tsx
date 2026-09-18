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
import { CheapLaneTabel, Status } from './CheapLaneTabel'

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

      <CheapLaneTabel
        raekker={rækker}
        noegle={(m) => `${m.provider}/${m.model}`}
        tom="Ingen modeller i cheap lane matcher."
        kolonner={[
          { id: 'udbyder', navn: 'Udbyder', vaerdi: (m) => m.provider,
            celle: (m) => (
              <button type="button" className="cl-linkknap"
                      onClick={() => onInspicer?.(String(m.provider), String(m.model))}>
                {m.provider}
              </button>) },
          { id: 'model', navn: 'Model', vaerdi: (m) => m.model, celle: (m) => m.model },
          { id: 'status', navn: 'Status', vaerdi: (m) => (m.enabled ? 'aktiv' : 'slået fra'),
            celle: (m) => <Status status={m.enabled ? 'aktiv' : 'slået fra'} /> },
          { id: 'handlinger', navn: 'Handlinger', fast: true, celle: (m) => {
            const mål = `${m.provider}/${m.model}`
            return (
              <span className="cl-handlinger">
                <Handling etiket={`Pause ${m.model}`} udfoer={udfoer}
                          kommando={{ action: 'model.pause', target: mål }} />
                <Handling etiket={`Deaktivér ${m.model}`} udfoer={udfoer} variant="advarsel"
                          beskrivelse="Modellen bliver væk af puljen — også efter en genstart."
                          kommando={{ action: 'model.deactivate', target: mål }} />
                <Handling etiket={`Fjern ${m.model}`} udfoer={udfoer} variant="destruktiv"
                          beskrivelse="Modellen fjernes fra registret."
                          kommando={{ action: 'model.delete', target: mål }} />
              </span>)
          } },
        ]}
      />
    </div>
  )
}
