import { useCallback, useEffect, useRef, useState } from 'react'
import { Bell } from 'lucide-react'
import type { ApiConfig } from '../../lib/api'
import { openEventSocket } from '../../lib/api'
import { hentNotifikationer, type Notifikation } from '../../lib/notifikationerApi'
import { maaPolle } from '../../lib/ro'
import { acknowledgeNotifications, NOTIFICATION_READ_EVENT, notificationAttention } from '../../lib/notificationAttention'

/** Aabne poster sammenholdes med klientens laest/kvitteret-id'er.
 * Nye poster giver vedvarende ring; klik kvitterer for ringningen, mens
 * den lille prik bliver indtil posten er laest eller fjernet. */
export function Klokke({ config, onAaben, aktivSession }: {
  config: ApiConfig | null
  onAaben: () => void
  /** Samtalen brugeren sidder i nu. Svar fra den springes over paa serveren. */
  aktivSession?: string | null
}) {
  const [poster, setPoster] = useState<Notifikation[]>([])
  const [, setSeenVersion] = useState(0)
  const [fejl, setFejl] = useState(false)

  // Klokken reagerer KUN paa poster der kraever et svar.
  //
  // `run_done` («Svar klar i «X»») er baggrundsstof: der kommer en ny hver gang
  // et run slutter. Maalt 4/10-2026 laa der 1152 aabne, og hvert klik kvitterer
  // kun dem der er der NU — to minutter senere er der en ny. Klokken ringede og
  // prikkede derfor permanent, og en klokke der altid ringer, ringer aldrig.
  //
  // Det er ikke et nyt begreb: serveren melder praecis denne maengde som
  // `venter` (`slags != "run_done"`), og feeden har den som fanen «Venter paa
  // dig». Klokken var det eneste sted der ikke brugte den.
  const venterIds = poster.filter((p) => p.slags !== 'run_done').map((p) => p.id)
  const { unread, attention } = notificationAttention(venterIds)

  useEffect(() => {
    const changed = () => setSeenVersion((n) => n + 1)
    window.addEventListener(NOTIFICATION_READ_EVENT, changed)
    return () => window.removeEventListener(NOTIFICATION_READ_EVENT, changed)
  }, [])

  // `alive` vaerner mod at saette state efter unmount — samme moenster som
  // usePollWhenVisible. Uden det kan et sent svar fra en ALLEREDE lukket
  // klokke (fx skift af flade midt i et kald) skrive ind i en fjernet
  // komponent.
  const alive = useRef(true)
  const requestVersion = useRef(0)

  // `hentNu` gaar UDEN OM ro-loftet (`maaPolle`) — den bruges baade af pollet
  // selv (efter loftet har sagt ja) og af WS-lytteren nedenfor, hvor en
  // haendelse ER signalet og derfor aldrig maa sluges af ro-mekanismen.
  const hentNu = useCallback(() => {
    if (!config) return
    const version = ++requestVersion.current
    hentNotifikationer(config, aktivSession)
      .then((f) => {
        if (!alive.current || version !== requestVersion.current) return
        setPoster(f.poster)
        setFejl(false)
      })
      .catch(() => {
        if (!alive.current || version !== requestVersion.current) return
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
    const versions = requestVersion
    hent()
    const id = window.setInterval(hent, 8000)
    return () => { alive.current = false; versions.current++; window.clearInterval(id) }
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
    : unread ? 'Notifikationer — ulæste poster' : 'Notifikationer'

  return (
    <button type="button" className={`icon-btn klokke${attention ? ' klokke-attention' : ''}`} title={titel}
            aria-label={titel} onClick={() => { acknowledgeNotifications(venterIds); onAaben() }}>
      <Bell size={15} />
      {unread && <span className="klokke-ulast" data-testid="klokke-ulast" aria-hidden="true" />}
      {/* En fejlet hentning maa stadig se anderledes ud end en tom liste. */}
      {fejl && <span className="klokke-fejl" data-testid="klokke-fejl" aria-hidden="true" />}
    </button>
  )
}
