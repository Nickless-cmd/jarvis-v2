/**
 * Klientlog ved renderbeslutningen — fire målepunkter, ingen guard.
 *
 * ## Hvorfor den findes (25/10-2026)
 *
 * `MarkdownRenderer` falder lydløst tilbage til `ChatCodeBlock` når en
 * `jarvis-ui`-blok ikke kan blive en flade. Intet blev logget. Fire diagnoser
 * i træk pegede derfor forkert: fejlen var usynlig præcis dér hvor
 * beslutningen blev truffet.
 *
 * Dette er en MÅLING, ikke et fix. Den retter intet, blokerer intet og
 * afviser intet — den fortæller hvad browseren faktisk så.
 *
 * ## Hvorfor en sender og ikke `apiFetch` direkte
 *
 * `MarkdownRenderer` ligger dybt i træet og kender hverken API-base eller
 * token. At trække `config` hele vejen ned ville røre hver komponent mellem
 * `ChatView` og rendereren for at løse et observabilitets-behov. Senderen
 * sættes ét sted hvor `config` findes (`ChatView`), og rendereren kalder en
 * funktion der ikke kender transporten.
 *
 * ## Rate-limiter
 *
 * Streaming kalder rendereren mange gange i sekundet. Nøglen er
 * `udfald + lang + blok-længde + blokkens første 200 tegn`, så den SAMME fejl
 * kun rapporteres én gang — også når blokken re-rendres. Derudover et loft pr.
 * session, så en ukendt fejlform ikke kan oversvømme serveren.
 */

export type FladeUdfald = 'native' | 'parse-null' | 'wrong-lang' | 'no-pre-node'

export interface FladeSnapshot {
  udfald: FladeUdfald
  /** Teksten FØR `stabilizeStreamingMarkdown`. */
  foer: string
  /** Teksten EFTER `stabilizeStreamingMarkdown`. */
  efter: string
  /** Den konkrete markdown-blok ReactMarkdown modtog. */
  blok: string
  /** `className` i `pre`-grenen. */
  className: string
  /** Udledt sprog fra `className`. */
  lang: string
  /** Kodeindholdet i `pre`-grenen. */
  kode: string
}

type Sender = (snapshot: FladeSnapshot) => void

/** Sættes af `ChatView`, hvor API-base og token er kendt. */
let sender: Sender | null = null

const sendt = new Set<string>()

/** Et loft pr. sidevisning. En ukendt fejlform må ikke kunne oversvømme. */
export const MAKS_PR_SESSION = 50

export function saetFladeLogSender(fn: Sender | null): void {
  sender = fn
}

/** Én nøgle pr. unik fejlform — ikke pr. render. */
export function fladeLogNoegle(s: FladeSnapshot): string {
  return `${s.udfald}|${s.lang}|${s.blok.length}|${s.blok.slice(0, 200)}`
}

export function logFlade(s: FladeSnapshot): void {
  if (!sender) return
  if (sendt.size >= MAKS_PR_SESSION) return
  const noegle = fladeLogNoegle(s)
  if (sendt.has(noegle)) return
  sendt.add(noegle)
  try {
    sender(s)
  } catch {
    // fail-open: en log der kaster må aldrig koste en rendering
  }
}

/** Kun til test: glem hvad der er sendt, så en test kan køre fra nul. */
export function nulstilFladeLog(): void {
  sendt.clear()
  sender = null
}
