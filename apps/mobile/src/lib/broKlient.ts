/**
 * Bro-klient — appen som en enhed Jarvis kan udføre ting på.
 *
 * Samme protokol som desk-broen: serveren annoncerer værktøjet, klienten
 * udfører det og sender resultatet tilbage. Det nye er, at broen siden
 * 7/9-2026 kan holde flere klienter pr. bruger og vælger dem på
 * `capabilities` — så computeren ikke bliver sparket af når telefonen
 * forbinder, og et `phone_*`-kald finder telefonen af sig selv.
 *
 * To ting gør telefonen anderledes end en desktop, og de former koden her:
 *
 * 1. **Android kapper socket'en når appen går i baggrunden.** Derfor
 *    genforbindelse med voksende pause — ikke som pynt, men fordi det er
 *    normaltilstanden. En bro der ikke kommer tilbage af sig selv er en bro
 *    der virker indtil man låser telefonen.
 * 2. **Vi må aldrig efterlade et kald ubesvaret.** Serveren venter på et
 *    `tool_result` med samme correlation_id og timer ellers ud. Kaster en
 *    handler, sender vi fejlen tilbage i stedet for at tie — ellers venter
 *    Jarvis 45 sekunder på ingenting.
 */

export type Udfoerer = (vaerktoej: string, args: Record<string, unknown>) => Promise<unknown>

export interface BroOpsaetning {
  /** Fx https://api.srvlab.dk/ — http(s) laves om til ws(s) her. */
  apiBaseUrl: string
  authToken: string
  /** Værktøjer denne enhed kan udføre. Serveren router på dem. */
  capabilities: string[]
  /** Stabil id pr. app-installation, så to enheder ikke er samme klient. */
  clientId: string
  version?: string
  udfoer: Udfoerer
  /** Injicerbar til test. Default: global WebSocket MED Authorization-header. */
  lavSocket?: (url: string, muligheder?: { headers: Record<string, string> }) => WebSocketLignende
  /** Injicerbar til test, så genforbindelse kan køres uden rigtig ventetid. */
  planlaeg?: (fn: () => void, ms: number) => unknown
  /** Gentagende vagt. Egen injektion fordi `planlaeg` er engangs — og fordi
   *  testene kalder den synkront, hvilket ville få en gentagende vagt til at
   *  rekursere i stedet for at vente. */
  planlaegVagt?: (fn: () => void, ms: number) => unknown
  rydVagt?: (haandtag: unknown) => void
  /** Injicerbart ur, så trafik-vagten kan testes uden at vente 75 sekunder. */
  nu?: () => number
  log?: (besked: string, ...rest: unknown[]) => void
}

/** Den del af WebSocket vi faktisk bruger — så en fake i test er lille. */
export interface WebSocketLignende {
  send(data: string): void
  close(): void
  onopen: (() => void) | null
  onclose: (() => void) | null
  onerror: ((e: unknown) => void) | null
  onmessage: ((e: { data: string }) => void) | null
}

/** Pauser mellem genforbindelsesforsøg. Vokser, men holder op med at vokse:
 *  en telefon der har ligget i lommen en time skal være tilbage inden for et
 *  halvt minut, ikke inden for en time. */
export const GENFORBIND_MS = [1000, 2000, 5000, 10000, 20000, 30000]

/** Hvor længe der må gå uden ÉN indgående frame før forbindelsen er død.
 *
 *  Klienten svarede på `ping`, men INTET opdagede en halvåben socket. Suspenderer
 *  Android den i baggrunden, kommer `onclose` aldrig — og klienten sidder og tror
 *  den er forbundet, mens serveren for længst har lukket efter tre ubesvarede
 *  ping (uvicorn: 20 s interval, 20 s timeout).
 *
 *  Målt 11/9-2026 over 48 timer på `mobil-2j1dxlnh`: 98 huller, median-LEVETID
 *  for en forbindelse 99 sekunder, 74 af 99 under fem minutter. Desk-klienten
 *  har haft præcis denne vagt hele tiden (75 s / 10 s); mobilen havde ingen.
 *
 *  75 s = tre ubesvarede ping plus lidt luft. */
export const TRAFIK_TIMEOUT_MS = 75_000
/** Finere end timeouten, så vi opdager tavsheden inden for et vindue og ikke
 *  først ved næste hele periode. */
export const VAGT_INTERVAL_MS = 10_000

export function broUrl(apiBaseUrl: string): string {
  const base = apiBaseUrl.endsWith('/') ? apiBaseUrl : `${apiBaseUrl}/`
  return `${base.replace(/^http/, 'ws')}api/jarvisx-bridge/ws`
}

export interface Bro {
  start(): void
  stop(): void
  erForbundet(): boolean
  /** Antal genforbindelsesforsøg siden sidste vellykkede registrering. */
  forsoeg(): number
}

export function opretBro(opsaetning: BroOpsaetning): Bro {
  const {
    apiBaseUrl, authToken, capabilities, clientId,
    version = '', udfoer,
  } = opsaetning
  // Token'et skal i HEADEREN, ikke i register-beskeden. Serveren laeser kun
  // Authorization ved handshaket og tager user_id fra token'ets `sub`; uden
  // headeren er der ingen claims, og forbindelsen lukkes med
  // «user_id_missing» foer register-beskeden overhovedet betyder noget.
  // Samme form som desk-broen: new WebSocket(url, { headers }).
  // React Natives WebSocket tager (url, protokoller, muligheder); TypeScript
  // ser DOM-varianten, som kun kender to. Typen skrives derfor eksplicit her
  // frem for et blindt cast, saa det staar hvad der faktisk kaldes.
  type RNWebSocket = new (
    url: string,
    protokoller?: string | string[],
    muligheder?: { headers?: Record<string, string> },
  ) => WebSocketLignende
  const lavSocket = opsaetning.lavSocket
    ?? ((url: string, muligheder?: { headers: Record<string, string> }) =>
      new (WebSocket as unknown as RNWebSocket)(url, undefined, muligheder))
  const planlaeg = opsaetning.planlaeg ?? ((fn, ms) => setTimeout(fn, ms))
  const log = opsaetning.log ?? (() => {})

  const planlaegVagt = opsaetning.planlaegVagt
    ?? ((fn: () => void, ms: number) => setInterval(fn, ms))
  const rydVagt = opsaetning.rydVagt
    ?? ((h: unknown) => clearInterval(h as ReturnType<typeof setInterval>))
  const nu = opsaetning.nu ?? (() => Date.now())

  let ws: WebSocketLignende | null = null
  let forbundet = false
  let stoppet = false
  let antalForsoeg = 0
  let sidsteTrafik = 0
  let vagt: unknown = null
  let genforbindPlanlagt = false

  function stopVagt() {
    if (vagt !== null) {
      try { rydVagt(vagt) } catch { /* allerede ryddet */ }
      vagt = null
    }
  }

  /** ÉN genforbindelse pr. socket. Både `onclose` og vagten kan nå hertil, og
   *  uden denne spærre ville en halvåben socket der ENDELIG lukker give to
   *  parallelle genforbindelser — og dermed to brorepræsentationer af samme
   *  telefon. */
  function planlaegGenforbind() {
    if (stoppet || genforbindPlanlagt) return
    genforbindPlanlagt = true
    // ?? for at holde typetjekket ærligt: en indeksering KAN give undefined,
    // og den længste pause er det rigtige fallback hvis listen nogensinde
    // bliver tom.
    const pause = GENFORBIND_MS[Math.min(antalForsoeg, GENFORBIND_MS.length - 1)] ?? 30000
    antalForsoeg += 1
    log(`bro: lukket, prøver igen om ${pause} ms`)
    planlaeg(() => { genforbindPlanlagt = false; forbind() }, pause)
  }

  function startVagt() {
    stopVagt()
    sidsteTrafik = nu()
    vagt = planlaegVagt(() => {
      if (stoppet || !ws) return
      const tavs = nu() - sidsteTrafik
      if (tavs <= TRAFIK_TIMEOUT_MS) return
      log(`bro: ingen trafik i ${Math.round(tavs / 1000)}s — tvinger genforbindelse`)
      const doed = ws
      stopVagt()
      ws = null
      forbundet = false
      // Luk FØRST, genforbind bagefter. På en halvåben socket kommer `onclose`
      // måske aldrig, så vi må selv planlægge — spærren ovenfor sikrer at et
      // sent `onclose` ikke gør det én gang til.
      try { doed.close() } catch { /* allerede væk */ }
      planlaegGenforbind()
    }, VAGT_INTERVAL_MS)
  }

  function sendResultat(correlationId: string, status: string, data: unknown, fejl?: string) {
    if (!ws) return
    try {
      ws.send(JSON.stringify({
        type: 'tool_result',
        correlation_id: correlationId,
        status,
        result: status === 'ok' ? data : null,
        error: fejl ?? null
      }))
    } catch (e) {
      log('bro: kunne ikke sende resultat', e)
    }
  }

  async function haandterInvoke(besked: Record<string, unknown>) {
    const correlationId = String(besked.correlation_id ?? '')
    const vaerktoej = String(besked.tool ?? '')
    const args = (besked.args ?? {}) as Record<string, unknown>
    if (!correlationId) return
    try {
      const svar = await udfoer(vaerktoej, args)
      sendResultat(correlationId, 'ok', svar)
    } catch (e) {
      // Aldrig tavshed: serveren venter på correlation_id og ville ellers
      // stå og time ud på et kald vi allerede VED er fejlet.
      sendResultat(correlationId, 'error', null, String((e as Error)?.message ?? e).slice(0, 300))
    }
  }

  function forbind() {
    if (stoppet) return
    const s = lavSocket(broUrl(apiBaseUrl), {
      headers: { Authorization: `Bearer ${authToken}` }
    })
    ws = s

    s.onopen = () => {
      startVagt()
      try {
        s.send(JSON.stringify({
          type: 'register',
          // user_id udelades med vilje: serveren tager den fra token'ets
          // `sub`, så der ikke opstår to kilder til hvem enheden tilhører.
          client: 'jarvis-mobile',
          client_id: clientId,
          version,
          platform: 'android',
          capabilities
        }))
      } catch (e) {
        log('bro: register fejlede', e)
      }
    }

    s.onmessage = (e) => {
      // ENHVER indgående frame tæller som livstegn — også `ping`. Det er
      // netop serverens ping der beviser at socket'en stadig lever, så en
      // vagt der kun så `tool_invoke` ville fyre midt i en stille periode.
      sidsteTrafik = nu()
      let besked: Record<string, unknown>
      try {
        besked = JSON.parse(e.data)
      } catch {
        return
      }
      const type = String(besked.type ?? '')
      if (type === 'registered') {
        forbundet = true
        antalForsoeg = 0
        log('bro: registreret')
        return
      }
      if (type === 'tool_invoke') {
        void haandterInvoke(besked)
        return
      }
      if (type === 'ping') {
        try {
          s.send(JSON.stringify({ type: 'pong' }))
        } catch { /* socket lukkede lige */ }
      }
    }

    s.onerror = () => { /* onclose kommer bagefter og håndterer genforbindelse */ }

    s.onclose = () => {
      forbundet = false
      ws = null
      stopVagt()
      planlaegGenforbind()
    }
  }

  return {
    start() {
      stoppet = false
      antalForsoeg = 0
      forbind()
    },
    stop() {
      stoppet = true
      stopVagt()
      forbundet = false
      try { ws?.close() } catch { /* allerede lukket */ }
      ws = null
    },
    erForbundet: () => forbundet,
    forsoeg: () => antalForsoeg
  }
}
