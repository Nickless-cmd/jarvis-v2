import { useCallback, useEffect, useRef, useState, type RefObject } from 'react'

/** Hvor ofte ruden pinnes til bund mens der arbejdes. */
export const PIN_INTERVAL_MS = 250

/**
 * Hvor langt fra gulvet der stadig tæller som «på gulvet», i px.
 *
 * 25 er DSH's eget tal, læst i kilden — `useScrollFollow(state.followingTail, 25)`
 * (`@deepseek-ai/dsh-client-ui-chat/lib/client.js:4509`). Her stod 120 indtil
 * 29/9-2026. Det var et gæt, og det var for stort: ved 120 px holdt ruden fast i
 * bunden også når man bevidst havde scrollet op for at læse. Det er den slags
 * Bjørn mærker som «ruden stjæler scrollen tilbage».
 */
export const FOELG_TAERSKEL_PX = 25

/**
 * Hvor længe et læser-input må være uafregnet før beslutningen falder.
 *
 * DSH: `SCROLL_SAMPLE_INTERVAL_MS = 500` (`client.js:4291`). Kommer der et
 * `scrollend` før, afregnes der straks — intervallet er kun loftet, ikke ventetiden.
 */
export const SCROLL_SAMPLE_INTERVAL_MS = 500

/** Bevægelser under dette tæller ikke som en ny position (sub-pixel). */
const BEVAEGELSE_EPS = 0.5

/**
 * Hvem der bad om at der blev skrevet til bunden.
 *
 * Kun til sporing og test: viewport'en skriver ens uanset hvem der meldte.
 * Det er intent'en — ikke kalderen — der afgør OM der må skrives. Det er hele
 * pointen: før skrev otte steder i follow-stien til `scrollTop`, hver med sin
 * egen opfattelse af hvem der bestemte (målt 29/9-2026: ChatView ×4,
 * CodeView ×2, useFastholdBund, usePinVedStart).
 *
 * `indhold`, `resize` og `ny-besked` er VÆKST-meldinger: de holdes tilbage mens
 * et læser-input er uafregnet (se `afventendeRef`). `pin-start`, `ny-session` og
 * `til-bund` er eksplicitte ønsker om bunden og rydder den afventende afregning.
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
 * (punkt 1a og 1b(a)) og er DSH's: **præcis én controller skriver til DOM'en. De
 * øvrige melder intent.** Læseren ejer `atBottom`; viewport'en udfører den
 * clamped skrivning. Alt andet — interval, resize, ny besked, stream-start —
 * kalder `melder` i stedet for at skrive selv.
 *
 * ## Afregningen (1b(a), målt mod DSH 29/9-2026)
 *
 * Den vigtigste del er ikke HVOR tærsklen ligger, men HVORNÅR den bruges. DSH's
 * regel, ordret fra deres README og bekræftet i `ChatReading.onScroll`:
 *
 * > *«reader input that reaches the exact floor, update follow ownership
 * > immediately … Other reader movement remains pending until the sampling
 * > interval or `scrollend`, even inside the follow threshold, so layout growth
 * > cannot erase small scroll gestures.»*
 *
 * Oversat til kode: rører læseren hjulet og lander IKKE på gulvet, ændres
 * ejerskabet ikke med det samme. Der armes en timer på
 * `SCROLL_SAMPLE_INTERVAL_MS`, og i mellemtiden rører hverken vækst eller resize
 * ved ruden — ellers ville netop det layout-vækst, der kommer mens man ruller,
 * kunne spise bevægelsen og trække én tilbage til bunden. Beslutningen falder
 * bagefter, på den FRISKE geometri: `gulv - top <= FOELG_TAERSKEL_PX`.
 *
 * Før 29/9-2026 blev beslutningen taget straks, i `onScroll`, med 120 px
 * tærskel. Det er den fejl Bjørn har mærket: en lille scroll-bevægelse blev
 * afvist som «ikke i bunden» eller accepteret som «i bunden» på et tidspunkt hvor
 * layoutet endnu ikke havde sat sig.
 *
 * ## De tre net der stadig er hers
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
  const foelgerRef = useRef(true)

  // Positionen ved sidste levering. DSH's standard-tilskrivning er netop denne
  // sammenligning (`sample(metrics, movedByReader = |top - sampledTop| > .5)`):
  // flyttede positionen sig ikke, var det ikke læseren.
  const sampletTopRef = useRef<number | undefined>(undefined)

  // Læserens input der endnu ikke er afregnet. Sand mens der ventes på
  // `scrollend` eller på sample-intervallet — og imens rører intet andet ruden.
  const afventendeRef = useRef(false)
  const sampleTimerRef = useRef<number | null>(null)

  /** Én geometrilæsning. Gulvet er den største scrollTop browseren tillader. */
  const maal = useCallback(() => {
    const el = ref.current
    if (!el) return null
    return { el, top: el.scrollTop, gulv: el.scrollHeight - el.clientHeight }
  }, [ref])

  // ── Den ENESTE skriver ────────────────────────────────────────────────────
  // Alt andet i denne fil — og begge views — melder intent. Skrivningen sker her
  // og ingen andre steder, så «hvem bestemmer over rullen» har ét svar.
  const skrivTilBund = useCallback(() => {
    const m = maal()
    if (!m) return
    // Kun hvis den faktisk er rykket. En tildeling der ikke ændrer noget udløser
    // stadig et scroll-event, og det ville nulstille brugerens «jeg har scrollet
    // op» hvert kvarte sekund — ruden ville «stjæle» scrollen tilbage.
    if (m.top !== m.gulv) {
      m.el.scrollTop = m.el.scrollHeight
      // Browseren clamper skrivningen til gulvet. Vi noterer den VIRKELIGE
      // position, så den levering vores egen skrivning udløser ikke bagefter
      // læses som en læserbevægelse.
      sampletTopRef.current = m.el.scrollTop
    }
  }, [maal])

  /** Drop en afventende afregning uden at lade den falde. */
  const afbrydAfventende = useCallback(() => {
    afventendeRef.current = false
    if (sampleTimerRef.current !== null) {
      clearTimeout(sampleTimerRef.current)
      sampleTimerRef.current = null
    }
  }, [])

  /**
   * NU falder beslutningen — DSH's `ScrollFollow.sample`.
   *
   * Den måler på ny, for det er hele pointen: den geometri der gjaldt da
   * læseren rørte hjulet, kan være invalidéret af layout-vækst i mellemtiden.
   */
  const afregn = useCallback(() => {
    if (!afventendeRef.current) return
    afbrydAfventende()
    const m = maal()
    if (!m) return
    sampletTopRef.current = m.top
    const foelger = m.gulv - m.top <= FOELG_TAERSKEL_PX
    foelgerRef.current = foelger
    setAtBottom(foelger)
    if (foelger) setUnread(0)
  }, [afbrydAfventende, maal])

  /** Bunden er ønsket: følg den, bliv der, og ryd en ældre afventende afregning. */
  const foelgNu = useCallback(() => {
    afbrydAfventende()
    foelgerRef.current = true
    setAtBottom(true)
    setUnread(0)
    skrivTilBund()
  }, [afbrydAfventende, skrivTilBund])

  const melder = useCallback((kind: ScrollIntent) => {
    switch (kind) {
      case 'pin-start':
      case 'ny-session':
      case 'til-bund':
        // Eksplicitte ønsker om bunden. DSH: «Submitting transcript input or
        // steering immediately restores tail following and clears an older
        // pending reader sample.»
        foelgNu()
        break
      case 'ny-besked':
        // Er der et uafregnet læser-input, ved vi endnu ikke om vi følger. Vi
        // lader ruden stå og tæller beskeden som ulæst; afregningen retter det
        // inden for 500 ms hvis læseren viste sig at være i bunden.
        if (afventendeRef.current) {
          setUnread((u) => u + 1)
          return
        }
        if (foelgerRef.current) {
          setUnread(0)
          skrivTilBund()
        } else {
          setUnread((u) => u + 1)
        }
        break
      case 'indhold':
      case 'resize':
        // Vækst. Mens et læser-input er uafregnet rører vi INTET — det er dét
        // der gør at layout-vækst ikke kan spise en lille scroll-bevægelse.
        if (afventendeRef.current) return
        if (foelgerRef.current) skrivTilBund()
        break
    }
  }, [foelgNu, skrivTilBund])

  // ── Læseren ───────────────────────────────────────────────────────────────
  // Den ENESTE der flytter follow-ejerskabet — og den flytter det ikke straks.
  const onScroll = useCallback(() => {
    const m = maal()
    if (!m) return
    const foer = sampletTopRef.current
    // Første levering efter mount sætter kun grundlinjen. `containerRef` sætter
    // den allerede ved attach; kommer der en alligevel, er den ikke til at
    // tilskrive, og så er det sikre svar ikke at afgøre noget.
    const flyttet = foer === undefined ? false : Math.abs(m.top - foer) > BEVAEGELSE_EPS
    sampletTopRef.current = m.top

    if (!flyttet) {
      // Levering uden læserbevægelse: vores egen skrivning, eller browseren der
      // flyttede os. Følger vi, holdes gulvet — der er intet at afgøre.
      if (foelgerRef.current) skrivTilBund()
      return
    }

    if (m.top >= m.gulv) {
      // Læseren ramte PRÆCIS gulvet. Ingen tvivl at vente på.
      foelgNu()
      return
    }

    // Al anden læserbevægelse er afventende — også inden for tærsklen.
    if (!afventendeRef.current) {
      afventendeRef.current = true
      sampleTimerRef.current = window.setTimeout(afregn, SCROLL_SAMPLE_INTERVAL_MS)
    }
  }, [afregn, foelgNu, maal, skrivTilBund])

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

  // ── Afregning ved browserens scrollend ────────────────────────────────────
  // Uden den ville et lille hjul-trin først blive afregnet efter op til 500 ms.
  // `scrollend` er i Chromium, og desk-klienten ER Chromium (Electron).
  useEffect(() => {
    if (!container) return
    const slut = () => afregn()
    container.addEventListener('scrollend', slut)
    return () => container.removeEventListener('scrollend', slut)
  }, [container, afregn])

  // ── Containerens højde ────────────────────────────────────────────────────
  // Nettet ovenfor fanger højdeændringer først ved næste tick; ResizeObserveren
  // fanger ALLE layout-ændringer generisk og straks, uanset årsag.
  useEffect(() => {
    if (!container || typeof ResizeObserver === 'undefined') return
    const ro = new ResizeObserver(() => melder('resize'))
    ro.observe(container)
    return () => ro.disconnect()
  }, [container, melder])

  // Transcripten er BETINGET monteret: tom-samtale-grenen i begge views
  // returnerer før den findes. En RefObject kan ikke fortælle os hvornår den
  // fyldes, så `ResizeObserver`-effekten ville skulle gætte på en tilfældig
  // anden afhængighed (som ChatView gjorde med `[atBottom]` — observeren blev
  // aldrig oprettet hvis atBottom ikke tilfældigt skiftede efter mount).
  // Callback-ref'en sætter den DELTE RefObject — `MessageRail` og `StickyPrompt`
  // læser den — giver effekterne et ægte signal, og lægger grundlinjen for
  // læser-tilskrivningen.
  const containerRef = useCallback((node: HTMLElement | null) => {
    ref.current = node
    sampletTopRef.current = node ? node.scrollTop : undefined
    setContainer(node)
  }, [ref])

  return { atBottom, unread, onScroll, containerRef, melder }
}
