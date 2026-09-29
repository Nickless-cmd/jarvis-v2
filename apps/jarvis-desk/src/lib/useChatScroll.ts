import { useCallback, useEffect, useRef, useState, type RefObject } from 'react'

/** Hvor ofte ruden pinnes til bund mens der arbejdes. */
export const PIN_INTERVAL_MS = 250

/** Afstand til bunden der stadig tæller som «i bund». */
export const NEAR_BOTTOM_PX = 120

/**
 * Hvem der bad om at der blev skrevet til bunden.
 *
 * Kun til sporing og test: viewport'en skriver ens uanset hvem der meldte.
 * Det er intent'en — ikke kalderen — der afgør OM der må skrives. Det er hele
 * pointen: før skrev otte steder i follow-stien til `scrollTop`, hver med sin
 * egen opfattelse af hvem der bestemte (målt 29/9-2026: ChatView ×4,
 * CodeView ×2, useFastholdBund, usePinVedStart).
 */
export type ScrollIntent =
  | 'pin-start'   // dit eget svar begynder
  | 'ny-session'  // sessionen blev skiftet
  | 'ny-besked'   // besked-antallet ændrede sig
  | 'indhold'     // indholdet voksede uden at nogen React-tilstand ændrede sig
  | 'resize'      // containeren skiftede højde
  | 'til-bund'    // brugeren trykkede på til-bund-pilen

export interface ChatScroll {
  /** Læserens sandhed: står brugeren i bunden? */
  atBottom: boolean
  /** Beskeder der er kommet til mens brugeren ikke stod i bunden. */
  unread: number
  /** Sæt på scroll-containeren. Den ENESTE der flytter follow-ejerskabet. */
  onScroll: () => void
  /** Callback-ref til scroll-containeren — se noten i kroppen. */
  containerRef: (node: HTMLElement | null) => void
  /** Meld intent. Skriver kun når intent'en må følge bunden. */
  melder: (kind: ScrollIntent) => void
}

/**
 * Én scroll-koordinator for chat- og code-viewet.
 *
 * Bjørn 29/9-2026: «Du bestemmer hvordan du vil gribe den … gør det rigtigt.»
 * Kontrakten står i `docs/superpowers/specs/2026-09-29-desk-chatview-komplethed-design.md`
 * (punkt 1a) og er DSH's: **præcis én controller skriver til DOM'en. De øvrige
 * melder intent.** Læseren ejer `atBottom`; viewport'en udfører den clamped
 * skrivning. Alt andet — interval, resize, ny besked, stream-start — kalder
 * `melder` i stedet for at skrive selv.
 *
 * Hooken bærer de tre ting der før var spredt og hver for sig ufuldstændige:
 *
 * - **Interval-nettet** (17/9-2026, før `useFastholdBund`): et svar kan lande ad
 *   en vej hvor hverken `stream.blocks`, `followState.blocks` eller antallet af
 *   beskeder ændrer sig — fx serverens gemte besked der ERSTATTER en linje, så
 *   antallet står stille. ResizeObserveren ser det heller ikke: den kigger på
 *   containeren, og DEN ændrer ikke højde når dens indhold vokser. Derfor et
 *   lille interval, og kun mens der arbejdes.
 * - **ResizeObserveren**: takeover-banneret og liveness-indikatoren sidder
 *   UDENFOR scroll-containeren, så når de dukker op krymper `.transcript` og
 *   nederste besked falder under folden.
 * - **Pin ved start** (Claude Desktops pin, §10): dit eget svar begynder → til
 *   bund og bliv der. Før `usePinVedStart`, der blev kaldt fra BEGGE views med
 *   samme callback — ét hook-instans der meldte til to forskellige ejere.
 *
 * `arbejder` er dit EGET svar (pin-ved-start); `aktiv` er alt arbejde, også et
 * cross-device run (nettet). De to var før forskellige parametre til to hooks,
 * og forskellen er reel: pin-ved-start må kun fyre på dit eget svar, mens
 * nettet skal holde uanset hvor indholdet kommer fra.
 */
export function useChatScroll(
  ref: RefObject<HTMLElement | null>,
  { arbejder, aktiv }: { arbejder: boolean; aktiv: boolean },
): ChatScroll {
  const [atBottom, setAtBottom] = useState(true)
  const [unread, setUnread] = useState(0)
  const [container, setContainer] = useState<HTMLElement | null>(null)

  // Sandheden om bunden holdes i en ref ved siden af staten. `melder` kaldes fra
  // effekter og intervaller, hvor staten fra denne render allerede kan være
  // forældet — en ref læses frisk. Staten er til tegningen, ref'en til beslutningen.
  const atBottomRef = useRef(true)

  // Transcripten er BETINGET monteret: tom-samtale-grenen i begge views
  // returnerer før den findes. En RefObject kan ikke fortælle os hvornår den
  // fyldes, så `ResizeObserver`-effekten ville skulle gætte på en tilfældig
  // anden afhængighed (som ChatView gjorde med `[atBottom]` — observeren blev
  // aldrig oprettet hvis atBottom ikke tilfældigt skiftede efter mount).
  // Callback-ref'en sætter den DELTE RefObject — `MessageRail` og `StickyPrompt`
  // læser den — og giver samtidig effekterne et ægte signal.
  const containerRef = useCallback((node: HTMLElement | null) => {
    ref.current = node
    setContainer(node)
  }, [ref])

  // ── Den ENESTE skriver ────────────────────────────────────────────────────
  // Alt andet i denne fil — og begge views — melder intent. Skrivningen sker her
  // og ingen andre steder, så «hvem bestemmer over rullen» har ét svar.
  const skrivTilBund = useCallback(() => {
    const el = ref.current
    if (!el) return
    // Kun hvis den faktisk er rykket. En tildeling der ikke ændrer noget udløser
    // stadig et scroll-event, og det ville nulstille brugerens «jeg har scrollet
    // op» hvert kvarte sekund — ruden ville «stjæle» scrollen tilbage.
    if (el.scrollTop !== el.scrollHeight - el.clientHeight) {
      el.scrollTop = el.scrollHeight
    }
  }, [ref])

  const melder = useCallback((kind: ScrollIntent) => {
    switch (kind) {
      case 'pin-start':
      case 'ny-session':
      case 'til-bund':
        // Bunden er ønsket: følg den — og bliv der. Gælder dit eget svar der
        // begynder, et sessionsskift, og brugerens eget tryk på til-bund-pilen.
        atBottomRef.current = true
        setAtBottom(true)
        setUnread(0)
        skrivTilBund()
        break
      case 'ny-besked':
        // Nyt indhold: følg kun hvis vi ALLEREDE stod i bunden. Ellers er det
        // brugerens læseposition der gælder, og ulæst-tælleren tager over.
        if (atBottomRef.current) {
          setUnread(0)
          skrivTilBund()
        } else {
          setUnread((u) => u + 1)
        }
        break
      case 'indhold':
      case 'resize':
        if (atBottomRef.current) skrivTilBund()
        break
    }
  }, [skrivTilBund])

  // ── Læseren ───────────────────────────────────────────────────────────────
  // Den ENESTE der flytter follow-ejerskabet. Vores egne skrivninger udløser
  // også scroll-events, men de sker kun når vi allerede ER i bund, så de
  // bekræfter bare tilstanden frem for at ændre den.
  const onScroll = useCallback(() => {
    const el = ref.current
    if (!el) return
    const near = el.scrollHeight - el.scrollTop - el.clientHeight < NEAR_BOTTOM_PX
    atBottomRef.current = near
    setAtBottom(near)
    if (near) setUnread(0)
  }, [ref])

  // ── Pin ved overgangen til «arbejder» ─────────────────────────────────────
  // Kun ved OVERGANGEN — ikke hver gang der kommer indhold. Har man scrollet op
  // mens svaret kører, respekteres det (nettet nedenfor holder kun når man ER i bund).
  const foerArbejdede = useRef(arbejder)
  useEffect(() => {
    const startede = arbejder && !foerArbejdede.current
    foerArbejdede.current = arbejder
    if (startede) melder('pin-start')
  }, [arbejder, melder])

  // ── Interval-nettet ───────────────────────────────────────────────────────
  // Målt i Chromium 29/9-2026 med 20 indholdsvækster på ~1 sekund: med
  // `.bund-anker` gav nettet 0 scrollTop-skrivninger og browseren 20 native
  // scroll-events; uden anker gav fallbacken 4 skrivninger/4 events på 1,4 s.
  // At fjerne intervallet sparer altså ingen skrivninger når CSS virker, men
  // mister dækningen for erstattede beskeder og autonome refreshes ovenfor.
  useEffect(() => {
    if (!aktiv) return
    // Beslutningen om der MÅ følges ligger i `melder` — ikke her. Intervallet
    // melder bare; kører det mens man er scrollet op, sker der ingenting. To
    // værn om samme sag ville gøre det umuligt at mutationsprøve hvilket af dem
    // der bærer beskyttelsen.
    melder('indhold')
    const id = setInterval(() => melder('indhold'), PIN_INTERVAL_MS)
    return () => clearInterval(id)
  }, [aktiv, melder])

  // ── Containerens højde ────────────────────────────────────────────────────
  // Nettet ovenfor fanger højdeændringer først ved næste tick; ResizeObserveren
  // fanger ALLE layout-ændringer generisk og straks, uanset årsag.
  useEffect(() => {
    if (!container || typeof ResizeObserver === 'undefined') return
    const ro = new ResizeObserver(() => melder('resize'))
    ro.observe(container)
    return () => ro.disconnect()
  }, [container, melder])

  return { atBottom, unread, onScroll, containerRef, melder }
}
