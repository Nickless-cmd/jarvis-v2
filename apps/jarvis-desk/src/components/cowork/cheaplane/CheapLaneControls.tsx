/**
 * Handlingerne — og det der skiller dem ad.
 *
 * Tre knapper rammer hver sit lag og har hver sin varighed. Forskellen står
 * på knappen selv, ikke i en hjælpetekst nogen skal finde:
 *
 *   Pause      balancerens egen tilstand — væk ved næste opbygning
 *   Deaktivér  registret — overlever en genstart
 *   Fjern      registret, uigenkaldeligt
 *
 * De to sidste kræver en grund. Det er ikke en formalitet: serveren afviser
 * dem uden (`ControlScopeError`), og en handling der bliver afvist EFTER at
 * brugeren troede den var udført, er værre end en der spørger først.
 *
 * Ingen gentagelse: en kontrol-handling er ikke idempotent, og et dobbeltklik
 * må ikke kunne pause den samme udbyder to gange med to revisioner i sporet.
 */
import { useState } from 'react'
import { AlertTriangle } from 'lucide-react'

export interface Kommando {
  action: string
  target: string
  reason?: string
  expected_revision?: string
  parameters?: Record<string, unknown>
}

export type Udfoer = (k: Kommando) => Promise<unknown>

/** Handlinger der ændrer noget varigt eller fjerner noget. */
const KRAEVER_GRUND = /\.(deactivate|delete|activate)$/
const DESTRUKTIV = /\.delete$/

export function Handling({
  etiket, kommando, udfoer, variant = 'normal', beskrivelse,
}: {
  etiket: string
  kommando: Kommando
  udfoer: Udfoer
  variant?: 'normal' | 'advarsel' | 'destruktiv'
  /** Vises i bekræftelsen — hvad handlingen faktisk gør. */
  beskrivelse?: string
}) {
  const [åben, setÅben] = useState(false)
  const [grund, setGrund] = useState('')
  const [kører, setKører] = useState(false)
  const [fejl, setFejl] = useState('')

  const spørgFørst = KRAEVER_GRUND.test(kommando.action) || DESTRUKTIV.test(kommando.action)

  async function send(medGrund: string) {
    setKører(true)
    setFejl('')
    try {
      await udfoer({ ...kommando, reason: medGrund })
      setÅben(false)
      setGrund('')
    } catch (e) {
      // Fejlen bliver STÅENDE. En besked der forsvinder af sig selv, er en
      // besked brugeren ikke nåede at læse — og her betyder den at systemet
      // ikke gjorde det han bad om.
      setFejl(e instanceof Error ? e.message : 'handlingen fejlede')
    } finally {
      setKører(false)
    }
  }

  return (
    <>
      <button
        type="button"
        className={`cl-handling cl-handling-${variant}`}
        disabled={kører}
        onClick={() => { if (spørgFørst) setÅben(true); else void send('') }}
      >
        {etiket}
      </button>

      {fejl ? <span className="cl-handling-fejl" role="alert">{fejl}</span> : null}

      {åben && (
        <div className="cl-dialog-baggrund" role="presentation" onClick={() => setÅben(false)}>
          <div className="cl-dialog" role="dialog" aria-modal="true"
               aria-label={etiket} onClick={(e) => e.stopPropagation()}>
            <h4>{etiket}</h4>
            {beskrivelse ? <p className="cl-dialog-tekst">{beskrivelse}</p> : null}
            {DESTRUKTIV.test(kommando.action) && (
              <p className="cl-dialog-advarsel">
                <AlertTriangle size={14} aria-hidden="true" />
                Dette kan ikke fortrydes. Legitimationen bevares i auth-profilen,
                så udbyderen kan tilføjes igen uden en ny nøgle.
              </p>
            )}
            <label>
              Grund
              <input value={grund} onChange={(e) => setGrund(e.target.value)}
                     placeholder="hvorfor — står i revisionssporet" autoFocus />
            </label>
            {fejl ? <p className="cl-handling-fejl" role="alert">{fejl}</p> : null}
            <div className="cl-dialog-knapper">
              <button type="button" onClick={() => setÅben(false)}>Annullér</button>
              <button type="button" className="cl-primaer" disabled={!grund.trim() || kører}
                      onClick={() => void send(grund.trim())}>
                {kører ? 'Sender…' : 'Bekræft'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
