import { useCallback, useEffect, useRef, useState } from 'react'
import { Bell } from 'lucide-react'
import type { ApiConfig } from '../../lib/api'
import { openEventSocket } from '../../lib/api'
import { hentNotifikationer } from '../../lib/notifikationerApi'
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
  const [ids, setIds] = useState<string[]>([])
  const [, setSeenVersion] = useState(0)
  const [fejl, setFejl] = useState(false)
  const { unread, attention } = notificationAttention(ids)

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

  // `hentNu` gaar UDEN OM ro-loftet (`maaPolle`) — den bruges baade af pollet
  // selv (efter loftet har sagt ja) og af WS-lytteren nedenfor, hvor en
  // haendelse ER signalet og derfor aldrig maa sluges af ro-mekanismen.
  const hentNu = useCallback(() => {
    if (!config) return
    hentNotifikationer(config, aktivSession)
      .then((f) => {
        if (!alive.current) return
        setIds(f.poster.map((p) => p.id))
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
    : unread ? 'Notifikationer — ulæste poster' : 'Notifikationer'

  return (
    <button type="button" className={`icon-btn klokke${attention ? ' klokke-attention' : ''}`} title={titel}
            aria-label={titel} onClick={() => { acknowledgeNotifications(ids); onAaben() }}>
      <Bell size={15} />
      {unread && <span className="klokke-ulast" data-testid="klokke-ulast" aria-hidden="true" />}
      {/* En fejlet hentning maa stadig se anderledes ud end en tom liste. */}
      {fejl && <span className="klokke-fejl" data-testid="klokke-fejl" aria-hidden="true" />}
    </button>
  )
}
