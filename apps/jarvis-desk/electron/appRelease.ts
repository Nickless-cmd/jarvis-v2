/**
 * Release-lytteren — push i stedet for poll (Bjørn 20/9-2026).
 *
 * ## Hvorfor den findes
 *
 * «hvorfor skal jeg vente en evighed på appen fanger nye opdateringer?»
 *
 * Fordi kilden ikke kan skubbe. electron-updater poller GitHub hvert 15. minut,
 * og GitHub har ingen kanal ned i en klient — så efter en release gik der op til
 * et kvarter, før appen overhovedet vidste der var noget nyt.
 *
 * ## Hvad den gør i stedet
 *
 * Serveren opdager releasen selv (`apps/api/jarvis_api/routes/app_release.py`)
 * og lægger den på event-bussen. `/ws` streamer bussen til enhver klient med et
 * token (se `core/runtime/ws_auth.py`). Vi lytter med — og når
 * `app.release.available` kommer forbi, beder vi updateren tjekke med det samme
 * frem for at vente på næste 15-minutters-tik.
 *
 * ## Om hvad der kommer ind ad forbindelsen
 *
 * `/ws` bærer HELE bussen: indre stemme, ræsonnements-konklusioner,
 * private_brain. Vi kaster alt andet væk med det samme — vi læser kun `kind`,
 * og kun for at sammenligne én streng. Der gemmes intet.
 *
 * ## Hvorfor `ws` og ikke fetch
 *
 * Pakken ligger allerede i dependencies (bridge.ts bruger den), og WebSocket er
 * den kanal serveren allerede taler. Samme mønster som `electron/bridge.ts`.
 */
import WebSocket from 'ws'

const STI = '/ws'
const KIND = 'app.release.available'
/** Rolig opbremsning: 5s, 15s, 30s og derefter 60s. Aldrig hårdt kørende. */
const BACKOFF_MS = [5_000, 15_000, 30_000, 60_000]
const PING_MS = 25_000

export interface ReleaseLytter {
  luk: () => void
}

export interface ReleaseLytterOptions {
  apiBaseUrl: string
  authToken: string | null
  /** Kaldes når serveren melder en ny release. Kalderen bestemmer hvad der sker. */
  onRelease: (info: Record<string, unknown>) => void
  log?: (besked: string) => void
}

export function startReleaseLytter(opts: ReleaseLytterOptions): ReleaseLytter {
  const log = opts.log ?? ((): void => {})
  const url = opts.apiBaseUrl.replace(/^http/, 'ws').replace(/\/$/, '') + STI

  let ws: WebSocket | null = null
  let ping: ReturnType<typeof setInterval> | null = null
  let reconnect: ReturnType<typeof setTimeout> | null = null
  let forsøg = 0
  let stoppet = false

  const rydPing = (): void => {
    if (ping) {
      clearInterval(ping)
      ping = null
    }
  }

  const genforbind = (): void => {
    if (stoppet) return
    const vent = BACKOFF_MS[Math.min(forsøg, BACKOFF_MS.length - 1)]
    forsøg += 1
    log(`release-lytter: genforbinder om ${vent / 1000}s`)
    reconnect = setTimeout(connect, vent)
  }

  const connect = (): void => {
    if (stoppet) return
    const headers: Record<string, string> = {}
    // Serveren tager tokenet i headeren for klienter der ikke er en browser
    // (browseren kan ikke sætte headers og bruger subprotokollen i stedet).
    if (opts.authToken) headers['Authorization'] = `Bearer ${opts.authToken}`

    try {
      ws = new WebSocket(url, { headers })
    } catch (e) {
      log(`release-lytter: forbindelse kunne ikke oprettes: ${String(e)}`)
      genforbind()
      return
    }

    ws.on('open', () => {
      forsøg = 0
      log('release-lytter: forbundet')
      // Serveren sender selv {"type":"ping"} hvert 25. sekund; dette er ws' egen
      // ping-frame, så en død TCP-forbindelse opdages før brugeren venter i det tomme.
      ping = setInterval(() => {
        try {
          ws?.ping()
        } catch {
          /* close-handleren tager den */
        }
      }, PING_MS)
    })

    ws.on('message', (raw) => {
      let besked: { kind?: string; payload?: unknown }
      try {
        besked = JSON.parse(String(raw)) as { kind?: string; payload?: unknown }
      } catch {
        return // serverens ping er JSON, men alt andet uforståeligt ignoreres
      }
      if (besked?.kind !== KIND) return
      log('release-lytter: ny release på bussen')
      try {
        opts.onRelease((besked.payload ?? {}) as Record<string, unknown>)
      } catch {
        /* en fejl her må ikke dræbe forbindelsen */
      }
    })

    ws.on('close', () => {
      rydPing()
      ws = null
      genforbind()
    })

    ws.on('error', (err) => {
      // 'close' følger efter og tager genforbindelsen — her logges kun.
      log(`release-lytter: fejl: ${err.message}`)
    })
  }

  connect()

  return {
    luk: (): void => {
      stoppet = true
      if (reconnect) {
        clearTimeout(reconnect)
        reconnect = null
      }
      rydPing()
      const s = ws
      ws = null
      if (s) {
        try {
          s.removeAllListeners()
          s.terminate()
        } catch {
          /* allerede lukket */
        }
      }
    },
  }
}
