/** Ro-tilstand: skru polningen ned når ingen kigger.
 *
 * ## Hvorfor (målt 20/9-2026 på CT105)
 *
 * Mellem kl. 03 og 04 om natten — Bjørn sov, ingen vinduer blev rørt — fik
 * jarvis-api **31.146 kald i den ene time**. 23.070 af dem kom fra ÉN desk
 * (10.0.0.20), resten fra en telefon. Flere endpoints blev hentet hvert 1,5
 * sekund hele natten: `/ui/view-requests/pending`, `/chat/sessions`,
 * `/central/costs-daily`. Det er grunden til at API-processen brugte 23 % CPU
 * på ingenting.
 *
 * `sharedRead` løste allerede DUBLETTERNE (fire komponenter der spørger om det
 * samme deler ét svar). Det her løser det andet: at vi spørger lige så tit når
 * ingen ser svaret.
 *
 * ## Hvordan
 *
 * Én faktor, der ganges på intervallerne:
 *
 *  - **1× mens noget streamer.** Live-arbejde bremses aldrig — det er hele
 *    grunden til at polle.
 *  - **1× når nogen lige har rørt maskinen.** Musen, tastaturet, et hjul eller
 *    fokus tæller.
 *  - **8× efter tre minutter uden et eneste tegn på liv.**
 *  - **20× når vinduet er skjult** (minimeret, dækket, anden fane).
 *
 * Med et loft på ét minut: en 1,5-sekunders poll bliver til 30 s i ro, ikke
 * til uendelig. Og ved første tegn på liv nulstilles alt, så det der står på
 * skærmen er friskt igen indenfor ét tick — ikke om et minut.
 */

export const ROLIG_EFTER_MS = 3 * 60_000
export const FAKTOR_RO = 8
export const FAKTOR_SKJULT = 20
export const LOFT_MS = 60_000

let sidsteLivstegn = Date.now()
const sidstePoll = new Map<string, number>()

/** Kunstigt ur i test. */
let naa: () => number = () => Date.now()

export function _saetUr(ur: () => number): void {
  naa = ur
}

/** Nogen rørte maskinen: væk alt, og lad næste tick hente med det samme. */
export function vaagn(): void {
  sidsteLivstegn = naa()
  sidstePoll.clear()
}

function erSkjult(): boolean {
  return typeof document !== 'undefined' && document.visibilityState === 'hidden'
}

/** Hvor gammelt et «ingen kørende runs» må være i et SYNLIGT vindue, også i ro.
 *  Målt 12/11-2026: 12 s poll + 16 s cache lod et 20 s wake-run blive opdaget 3 s før
 *  det sluttede (se `RoValg.loftSynligMs`). Pollen og cachen deler loftet. Bor HER og ikke
 *  i `api.ts`, fordi view-testene mocker `api` med en fast eksportliste. */
export const AKTIVE_RUNS_LOFT_SYNLIG_MS = 2_000

/** Loftet for et SYNLIGT vindue, ellers «intet loft». Se `RoValg.loftSynligMs`. */
export function synligtLoft(valg: RoValg): number {
  return !erSkjult() && valg.loftSynligMs ? Math.max(valg.loftSynligMs, 1) : Infinity
}

export interface RoValg {
  /** Live-arbejde: bremses aldrig. */
  fuldFart?: boolean
  /** Et skjult vindue tæller som roligt, ikke som væk. Bruges af det der skal
   *  frem UANSET om vinduet er oppe — en desktop-notifikation betyder mest
   *  netop når vinduet er minimeret. */
  ignorerSkjult?: boolean
  /** Eget loft, hvis det forlængede interval ikke må blive så langt. */
  loftMs?: number
  /** Loft der KUN gælder mens vinduet er SYNLIGT (12/11-2026).
   *
   *  Hvile («tre minutter uden input») skal spare en sovende eller skjult skærm, ikke
   *  en der bliver kigget på. Den som venter på en vækning rører ikke musen, og hvile-
   *  faktoren 8 gjorde pollen af `/chat/active-runs` til 12 s og dens delte cache til
   *  16 s: wake-runnet autonomous-7d13b933 (20 s) blev opdaget 17 s inde, 3 s før det
   *  sluttede, og kom ind som 305 frames på én gang. Et skjult vindue beholder sin
   *  langsomme takt, og `vaagn()` nulstiller alt når det bliver synligt igen. */
  loftSynligMs?: number
}

/** Hvor meget intervallerne skal ganges lige nu. `fuldFart` vinder over alt. */
export function roFaktor(valg: RoValg | boolean = false): number {
  const v: RoValg = typeof valg === 'boolean' ? { fuldFart: valg } : valg
  if (v.fuldFart) return 1
  if (erSkjult() && !v.ignorerSkjult) return FAKTOR_SKJULT
  if (naa() - sidsteLivstegn > ROLIG_EFTER_MS) return FAKTOR_RO
  return 1
}

/**
 * Må denne poll køre nu? Kaldes først i en poll-funktion:
 *
 *     if (!maaPolle('view-requests', POLL_MS)) return
 *
 * Komponenten beholder sit eget interval; i ro springes tick'ene over indtil
 * det forlængede interval er gået. Under normal drift er svaret altid ja, så
 * intet skifter adfærd mens nogen arbejder.
 */
export function maaPolle(noegle: string, intervalMs: number, valg: RoValg | boolean = false): boolean {
  const v: RoValg = typeof valg === 'boolean' ? { fuldFart: valg } : valg
  const faktor = roFaktor(v)
  if (faktor === 1) return true
  const nu = naa()
  const forlaenget = Math.min(intervalMs * faktor, v.loftMs ?? LOFT_MS, synligtLoft(v))
  const sidste = sidstePoll.get(noegle)
  if (sidste !== undefined && nu - sidste < forlaenget) return false
  sidstePoll.set(noegle, nu)
  return true
}

/** Kun til test. */
export function _nulstil(): void {
  sidsteLivstegn = naa()
  sidstePoll.clear()
}

const LIVSTEGN = ['pointerdown', 'keydown', 'wheel', 'focus', 'touchstart'] as const

if (typeof window !== 'undefined') {
  for (const h of LIVSTEGN) window.addEventListener(h, vaagn, { passive: true, capture: true })
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') vaagn()
  })
}
