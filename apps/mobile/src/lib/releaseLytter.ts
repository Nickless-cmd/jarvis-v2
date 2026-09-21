/**
 * Release-lytteren på mobilen — push i stedet for at vente på forgrunden.
 *
 * ## Hvorfor den findes (Bjørn 21/9-2026)
 *
 * «både i mobil og desk skal jeg gå ud og ind igen før den viser nye
 * opdateringer.»
 *
 * På desk var det en fejl i det sidste led. På mobilen er det ikke en fejl —
 * vejen blev aldrig bygget. `App.tsx` tjekker ved opstart og når appen vender
 * tilbage til forgrunden (`AppState` → `active`), og det er ALT. Går man ikke
 * ud og ind, sker der intet. Målt 21/9-2026: der fandtes ingen `app.release`-
 * lytter i mobil-appen overhovedet.
 *
 * Serveren har opdaget releasen hele tiden — `app_release.py` lægger
 * `app.release.available` på event-bussen, og `/ws` streamer bussen til enhver
 * klient med et token. Desk lytter med siden 20/9. Denne fil er mobilens
 * tvilling til `apps/jarvis-desk/electron/appRelease.ts`.
 *
 * ## Hvad der kommer ind ad forbindelsen
 *
 * `/ws` bærer HELE bussen: indre stemme, ræsonnements-konklusioner,
 * private_brain. Vi kaster alt andet væk med det samme — vi læser kun `kind`,
 * og kun for at sammenligne én streng. Der gemmes intet.
 *
 * ## Hvorfor den ikke bare kan hægtes på bro-forbindelsen
 *
 * `broKlient` taler med `api/jarvisx-bridge/ws`, som er en ANDEN kanal med et
 * andet formål (værktøjskald ud til telefonen). Event-bussen ligger på `/ws` i
 * roden. To kanaler, to forbindelser.
 */
import type { WebSocketLignende } from './broKlient'

const KIND = 'app.release.available'

/** Samme opbremsning som desk: rolig, og holder op med at vokse. En telefon
 *  der har ligget i lommen skal være tilbage inden for et minut. */
export const GENFORBIND_MS = [5_000, 15_000, 30_000, 60_000]
/** Den pause der gaelder naar listen er opbrugt. Samme som dens sidste. */
const LOFT_MS = 60_000

export function releaseUrl(apiBaseUrl: string): string {
  return `${apiBaseUrl.replace(/\/+$/, '').replace(/^http/, 'ws')}/ws`
}

export interface ReleaseLytterOpsaetning {
  apiBaseUrl: string
  authToken: string | null
  /** Kaldes når serveren melder en ny release. Kalderen bestemmer hvad der sker. */
  onRelease: () => void
  /** Injicerbar til test, så der ikke skal en rigtig socket til. */
  lavSocket?: (
    url: string,
    muligheder?: { headers: Record<string, string> },
  ) => WebSocketLignende
  /** Injicerbar til test, så genforbindelse kan køres uden rigtig ventetid. */
  planlaeg?: (fn: () => void, ms: number) => unknown
  ryd?: (haandtag: unknown) => void
  log?: (besked: string) => void
}

export interface ReleaseLytter {
  stop(): void
  erForbundet(): boolean
}

export function startReleaseLytter(opsaetning: ReleaseLytterOpsaetning): ReleaseLytter {
  const { apiBaseUrl, authToken, onRelease } = opsaetning
  // React Natives WebSocket tager (url, protokoller, muligheder); TypeScript
  // ser DOM-varianten, som kun kender to. Typen skrives derfor eksplicit her
  // frem for et blindt cast — samme greb som i broKlient.
  type RNWebSocket = new (
    url: string,
    protokoller?: string | string[],
    muligheder?: { headers?: Record<string, string> },
  ) => WebSocketLignende
  const lavSocket = opsaetning.lavSocket
    ?? ((url: string, muligheder?: { headers: Record<string, string> }) =>
      new (WebSocket as unknown as RNWebSocket)(url, undefined, muligheder))
  const planlaeg = opsaetning.planlaeg ?? ((fn, ms) => setTimeout(fn, ms))
  const ryd = opsaetning.ryd
    ?? ((h: unknown) => clearTimeout(h as ReturnType<typeof setTimeout>))
  const log = opsaetning.log ?? (() => {})

  let ws: WebSocketLignende | null = null
  let stoppet = false
  let forbundet = false
  let forsoeg = 0
  let ventende: unknown = null

  const genforbind = (): void => {
    if (stoppet) return
    // `?? LOFT`: med noUncheckedIndexedAccess er et opslag i en liste
    // `number | undefined`, ogsaa naar indekset er klemt fast. Loftet er den
    // samme vaerdi som listens sidste — det er ikke en gaetning, det er at
    // sige hoejt hvad der sker hvis listen en dag bliver tom.
    const vent = GENFORBIND_MS[Math.min(forsoeg, GENFORBIND_MS.length - 1)] ?? LOFT_MS
    forsoeg += 1
    log(`release-lytter: genforbinder om ${vent / 1000}s`)
    ventende = planlaeg(forbind, vent)
  }

  function forbind(): void {
    if (stoppet) return
    // Token'et skal i HEADEREN. Serveren laeser Authorization ved handshaket;
    // uden den er der ingen claims og forbindelsen lukkes.
    const muligheder = authToken
      ? { headers: { Authorization: `Bearer ${authToken}` } }
      : undefined
    try {
      ws = lavSocket(releaseUrl(apiBaseUrl), muligheder)
    } catch (fejl) {
      log(`release-lytter: forbindelse kunne ikke oprettes: ${String(fejl)}`)
      genforbind()
      return
    }

    ws.onopen = () => {
      forbundet = true
      forsoeg = 0
      log('release-lytter: forbundet')
    }

    ws.onmessage = (e) => {
      let besked: { kind?: string }
      try {
        besked = JSON.parse(String(e.data)) as { kind?: string }
      } catch {
        return // serverens ping er JSON, men alt uforstaaeligt ignoreres
      }
      if (besked?.kind !== KIND) return
      log('release-lytter: ny release paa bussen')
      try {
        onRelease()
      } catch {
        // En fejl i kalderen maa ikke draebe forbindelsen — saa ville EN
        // daarlig opdateringscheck koste alle de foelgende.
      }
    }

    ws.onclose = () => {
      forbundet = false
      ws = null
      genforbind()
    }

    ws.onerror = () => {
      // 'close' foelger efter og tager genforbindelsen — her logges kun.
      log('release-lytter: fejl paa forbindelsen')
    }
  }

  forbind()

  return {
    stop: (): void => {
      stoppet = true
      forbundet = false
      if (ventende !== null) {
        ryd(ventende)
        ventende = null
      }
      const s = ws
      ws = null
      if (s) {
        s.onopen = null
        s.onclose = null
        s.onerror = null
        s.onmessage = null
        try {
          s.close()
        } catch {
          // allerede lukket
        }
      }
    },
    erForbundet: (): boolean => forbundet,
  }
}
