import type { ApiConfig, CentralFeedItem } from './api'
import { streamCentral } from './api'

/** ÉN delt /central/stream-forbindelse på tværs af hele appen (Bjørn 2026-06-23).
 *
 *  Før åbnede Central-feltet (code mode) OG Jarvis Mind (cowork) hver sin SSE-stream + poll.
 *  På single-worker-API'et sultede de hinanden (hver stream holder en thread-pool-tråd), så
 *  Jarvis Mind hang/timeout'ede. Denne singleton holder MAX ÉN forbindelse, fan-out'er hver
 *  nerve-fyring til alle abonnenter, og ref-tæller: åbner ved første subscriber, lukker ved den
 *  sidste. Resultatet: uanset hvor mange paneler der vil have pulsen, er der kun ét abonnement.
 */
type ItemCb = (item: CentralFeedItem) => void
type ErrCb = () => void

let conn: { abort: () => void } | null = null
let cfg: ApiConfig | null = null
let reconnectTimer: ReturnType<typeof setTimeout> | null = null
const itemSubs = new Set<ItemCb>()
const errSubs = new Set<ErrCb>()

function open() {
  if (conn || !cfg) return
  conn = streamCentral(
    cfg,
    (it) => { for (const f of itemSubs) { try { f(it) } catch { /* en lytter må ikke vælte de andre */ } } },
    () => {
      // Drop: ÉN blid reconnect (3s) hvis der stadig er abonnenter — ikke 1.5s-storm pr. panel.
      conn = null
      for (const f of errSubs) { try { f() } catch { /* noop */ } }
      if (itemSubs.size > 0 && !reconnectTimer) {
        reconnectTimer = setTimeout(() => { reconnectTimer = null; open() }, 3000)
      }
    },
  )
}

function close() {
  if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = null }
  conn?.abort()
  conn = null
}

/** Abonnér på den delte Central-stream. Returnér en unsubscribe der lukker forbindelsen
 *  når den SIDSTE abonnent forsvinder. */
export function subscribeCentralStream(config: ApiConfig, onItem: ItemCb, onError?: ErrCb): () => void {
  cfg = config
  itemSubs.add(onItem)
  if (onError) errSubs.add(onError)
  open()
  return () => {
    itemSubs.delete(onItem)
    if (onError) errSubs.delete(onError)
    if (itemSubs.size === 0) close()
  }
}
