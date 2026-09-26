import { useCallback, useEffect, useRef, useState } from 'react'
import { Bell } from 'lucide-react'
import type { ApiConfig } from '../../lib/api'
import { openEventSocket } from '../../lib/api'
import { hentNotifikationer } from '../../lib/notifikationerApi'
import { maaPolle } from '../../lib/ro'

/**
 * Notifikations-klokken med sin taeller.
 *
 * Taelleren er antal der VENTER — alt undtagen Jarvis' egne svar.
 *
 * Den var foer antal AABNE i alt, med den begrundelse at feeden var en
 * to-do-liste: staar noget der, er det ikke klaret. Det holdt indtil
 * `run_done` viste sig at vaere den stoerste post i tabellen (maalt
 * 26/9-2026: 100 aabne paa én gang). Et svar venter ikke paa noget — det er
 * laesning — og et tal der taeller dem gjorde klokken til en konstant «9+»
 * hvor intet faktisk manglede hans svar. Serveren sender derfor to tal:
 * `antal` (alt aabent) og `venter` (dem der ikke er svar). Klokken viser det
 * sidste; feedet viser begge, i hver sin fane.
 *
 * Kan listen ikke hentes, skjules taelleren ikke bare — knappen siger det.
 * En tom klokke og en brudt klokke maa ikke ligne hinanden.
 */
export function Klokke({ config, onAaben, aktivSession }: {
  config: ApiConfig | null
  onAaben: () => void
  /** Samtalen brugeren sidder i nu. Svar fra den springes over paa serveren. */
  aktivSession?: string | null
}) {
  const [antal, setAntal] = useState(0)
  const [fejl, setFejl] = useState(false)

  // `alive` vaerner mod at saette state efter unmount — samme moenster som
  // usePollWhenVisible. Uden det kan et sent svar fra en ALLEREDE lukket
  // klokke (fx skift af flade midt i et kald) skrive ind i en fjernet
  // komponent.
  const alive = useRef(true)

  // `hentNu` gaar UDEN OM ro-loftet (`maaPolle`) — den bruges baade af pollet
  // selv (efter loftet har sagt ja) og af WS-lytteren nedenfor, hvor en
  // haendelse ER signalet og derfor aldrig maa sluges af ro-mekanismen.
  const hentNu = useCallback(() => {
    if (!config) return
    hentNotifikationer(config, aktivSession)
      .then((f) => {
        if (!alive.current) return
        // Faldet til `antal` er ikke kosmetik: en klient der rammer en
        // aeldre server (rullende udgivelse) faar ingen `venter`, og uden
        // det ville taelleren vise NaN.
        setAntal(typeof f.venter === 'number' ? f.venter : f.antal)
        setFejl(false)
      })
      .catch(() => {
        if (!alive.current) return
        setFejl(true)
      })
  }, [config, aktivSession])

  const hent = useCallback(() => {
    if (!config) return
    if (!maaPolle('notifikationer', 8000)) return
    hentNu()
  }, [config, hentNu])

  useEffect(() => {
    alive.current = true
    hent()
    const id = window.setInterval(hent, 8000)
    return () => { alive.current = false; window.clearInterval(id) }
  }, [hent])

  // Live-vejen. Pollet er sikkerhedsnettet; DETTE er grunden til at man ikke
  // skal ud og ind af appen for at se en ny godkendelse. `hentNu` gaar uden om
  // `maaPolle`: en haendelse ER signalet, og et ro-loft ville sluge den.
  useEffect(() => {
    if (!config) return
    let ws: WebSocket | null = null
    try {
      ws = openEventSocket(config)
      ws.onmessage = (e) => {
        try {
          const kind = String(JSON.parse(String(e.data))?.kind || '')
          if (kind.startsWith('notifikation.')) hentNu()
        } catch { /* ikke-JSON paa bussen er ikke vores */ }
      }
      ws.onerror = () => { /* pollet daekker */ }
    } catch { /* pollet daekker */ }
    return () => { try { ws?.close() } catch { /* noop */ } }
  }, [config, hentNu])

  const titel = fejl
    ? 'Notifikationer — listen kunne ikke hentes'
    : antal > 0 ? `Notifikationer — ${antal} åbne` : 'Notifikationer'

  return (
    <button type="button" className="icon-btn klokke" title={titel}
            aria-label={titel} onClick={onAaben}>
      <Bell size={15} />
      {antal > 0 && (
        <span className="klokke-taeller" data-testid="klokke-taeller">
          {antal > 9 ? '9+' : antal}
        </span>
      )}
      {/* data-testid ved siden af className: samme moenster som
          klokke-taeller ovenfor. className alene er en stil-krog der kan
          flyttes/omdoebes uden at det er en adfaerdsaendring — en test der
          hang paa den ville braekke paa den forkerte begivenhed. testid'et
          er kontrakten testen laaser fast; className er fri til at aendre sig. */}
      {fejl && <span className="klokke-fejl" data-testid="klokke-fejl" aria-hidden="true" />}
    </button>
  )
}
