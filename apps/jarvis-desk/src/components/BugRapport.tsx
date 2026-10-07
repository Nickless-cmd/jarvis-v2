import { useEffect, useRef, useState } from 'react'
import { X } from 'lucide-react'
import type { ApiConfig } from '../lib/api'
import { rapporterBug } from '../lib/bugApi'
import '../styles/bug-rapport.css'

/** Fejl-rapporten — et felt MIDT PÅ SKÆRMEN, ikke et popover i sidebaren.
 *
 *  Bjørn 4/10-2026: «bug icon laves om til et felt midt på skærmen hvor man
 *  kan melde faktisk bug til dit bug endpoint».
 *
 *  Forskellen fra før er ikke kun placeringen. Det gamle popover lagde sin
 *  tekst i skrivefeltet via `jarvis-bug`, hvor den blev en besked i samtalen.
 *  Denne sender til `/chat/inbox/flag` — rapporten bliver en post i indbakken,
 *  med id og terminale tilstande, altså noget der kan ses og lukkes.
 *
 *  TITEL ER KRÆVET, og det er serverens kontrakt: en tom titel afvises med 400,
 *  fordi «en post der ikke kan navngives i visningen ikke må gate». Derfor er
 *  Send-knappen disabled indtil der står noget i titel-feltet — hellere det end
 *  at lade et klik gå af sted mod et svar vi ved bliver en fejl.
 *
 *  Beskrivelsen er valgfri. Serveren tager imod en tom streng.
 */
export function BugRapport({ config, onClose }: { config?: ApiConfig; onClose: () => void }) {
  const ref = useRef<HTMLDialogElement>(null)
  const [titel, setTitel] = useState('')
  const [beskrivelse, setBeskrivelse] = useState('')
  const [sender, setSender] = useState(false)
  const [sendt, setSendt] = useState(false)
  const [fejl, setFejl] = useState<string | null>(null)

  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null
    const dialog = ref.current
    if (dialog?.showModal) dialog.showModal()
    else dialog?.setAttribute('open', '')
    return () => { dialog?.close?.(); previous?.focus() }
  }, [])

  const send = async () => {
    const t = titel.trim()
    if (!t || sender) return
    if (!config) {
      // Uden config er der ingen server at sende til. Sig det, frem for at
      // lade knappen gøre ingenting — det er samme tavshed som hele dagen er
      // gået med at fjerne.
      setFejl('Ingen forbindelse til serveren — prøv igen om lidt.')
      return
    }
    setSender(true)
    setFejl(null)
    try {
      await rapporterBug(config, t, beskrivelse.trim())
      setSendt(true)
    } catch (e) {
      // Serverens EGEN forklaring frem for et statustal. `apiFetch` pakker
      // `{"detail": …}` ud via `serverForklaring` og lægger den i `message`,
      // så «titel kraeves» når frem i stedet for «HTTP 400».
      setFejl((e as Error)?.message || 'Kunne ikke sende rapporten.')
    } finally {
      setSender(false)
    }
  }

  return <dialog ref={ref} className="bug-rapport" aria-label="Rapportér en fejl"
    onCancel={(event) => { event.preventDefault(); onClose() }}
    onClick={(event) => { if (event.target === event.currentTarget) onClose() }}>
    <div className="bug-rapport-content">
      <button type="button" className="bug-rapport-close" aria-label="Luk fejl-rapport" onClick={onClose}>
        <X size={18} />
      </button>

      {sendt ? (
        <>
          <h3 className="bug-rapport-titel">Sendt til Jarvis</h3>
          <p className="bug-rapport-note" role="status">
            Rapporten ligger i indbakken — den kan ses og lukkes der.
          </p>
          <div className="bug-rapport-handlinger">
            <button type="button" className="primaer" onClick={onClose}>Luk</button>
          </div>
        </>
      ) : (
        <>
          <h3 className="bug-rapport-titel">Rapportér en fejl</h3>

          <label className="bug-rapport-label" htmlFor="bug-titel">Hvad gik galt?</label>
          <input id="bug-titel" className="bug-rapport-felt" value={titel}
                 onChange={(e) => setTitel(e.target.value)}
                 placeholder="Kort — fx «streamen stopper ved genstart»" />

          <label className="bug-rapport-label" htmlFor="bug-beskrivelse">Beskrivelse (valgfri)</label>
          <textarea id="bug-beskrivelse" className="bug-rapport-tekst" rows={5}
                    value={beskrivelse} onChange={(e) => setBeskrivelse(e.target.value)}
                    placeholder="Hvad gjorde du, hvad skete der, hvad forventede du?" />

          {fejl && <p className="bug-rapport-fejl" role="alert">{fejl}</p>}

          <div className="bug-rapport-handlinger">
            <button type="button" onClick={onClose}>Annuller</button>
            <button type="button" className="primaer" disabled={!titel.trim() || sender}
                    onClick={() => { void send() }}>
              {sender ? 'Sender …' : 'Send til Jarvis'}
            </button>
          </div>
        </>
      )}
    </div>
  </dialog>
}
