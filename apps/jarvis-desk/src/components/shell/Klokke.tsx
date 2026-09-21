import { useCallback, useEffect, useRef, useState } from 'react'
import { Bell } from 'lucide-react'
import type { ApiConfig } from '../../lib/api'
import { hentNotifikationer } from '../../lib/notifikationerApi'
import { maaPolle } from '../../lib/ro'

/**
 * Notifikations-klokken med sin taeller.
 *
 * Taelleren er antal AABNE — alle slags, ikke kun dem der kraever et svar.
 * Det foelger af at feeden er en to-do-liste: staar noget der, er det ikke
 * klaret. En taeller der kun talte godkendelser ville lade et fejlet run staa
 * usynligt bag et tomt tal.
 *
 * Kan listen ikke hentes, skjules taelleren ikke bare — knappen siger det.
 * En tom klokke og en brudt klokke maa ikke ligne hinanden.
 */
export function Klokke({ config, onAaben }: {
  config: ApiConfig | null
  onAaben: () => void
}) {
  const [antal, setAntal] = useState(0)
  const [fejl, setFejl] = useState(false)

  // `alive` vaerner mod at saette state efter unmount — samme moenster som
  // usePollWhenVisible. Uden det kan et sent svar fra en ALLEREDE lukket
  // klokke (fx skift af flade midt i et kald) skrive ind i en fjernet
  // komponent.
  const alive = useRef(true)

  const hent = useCallback(() => {
    if (!config) return
    if (!maaPolle('notifikationer', 8000)) return
    hentNotifikationer(config)
      .then((f) => {
        if (!alive.current) return
        setAntal(f.antal)
        setFejl(false)
      })
      .catch(() => {
        if (!alive.current) return
        setFejl(true)
      })
  }, [config])

  useEffect(() => {
    alive.current = true
    hent()
    const id = window.setInterval(hent, 8000)
    return () => { alive.current = false; window.clearInterval(id) }
  }, [hent])

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
      {fejl && <span className="klokke-fejl" aria-hidden="true" />}
    </button>
  )
}
