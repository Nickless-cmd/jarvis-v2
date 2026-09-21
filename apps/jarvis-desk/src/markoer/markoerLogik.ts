/**
 * Logikken bag markør-laget — ren, så den kan testes uden en browser.
 *
 * Laget er ikke en virtuel markør: Jarvis flytter Bjørns rigtige mus gennem
 * nut.js, så cursoren står der allerede. Vi tegner et mærke omkring den, i det
 * øjeblik den flytter sig, og lader mærket falme — så det er til at se HVORNÅR
 * det er Jarvis der styrer og ikke Bjørn.
 */

/** Så længe halo'en bliver stående efter sidste handlende kald.
 *
 *  Uden en rummelig frist ville den blinke af og på midt i en sekvens af klik.
 *  Ti sekunder dækker en typisk arbejdsgang — klik, skriv, klik — som ÉN
 *  synlig overtagelse, og slukker alligevel af sig selv, så skærmen ikke står
 *  tændt og lyser om natten. */
export const OVERTAG_MS = 10000

/** Så længe lever et spor-punkt, fra det sættes til det er væk. */
export const FADE_MS = 1500

/** Flere punkter end dette giver ingen synlig forskel — kun arbejde. */
export const TRAIL_MAKS = 10

/** Bevægelser under dette antal pixels er støj fra en teleport der ikke
 *  flyttede sig; de ville stable bunker af prikker oven på hinanden. */
export const MIN_AFSTAND = 3

export interface Peg {
  id: number
  x: number
  y: number
  /** Tidsstempel i ms (performance.now()). */
  t: number
}

/**
 * Tilføj et peg til sporet. Springer næsten-identiske punkter over, og holder
 * listen nede på `maks` — de ældste falder ud først.
 */
export function tilfoejPeg(liste: Peg[], peg: Peg, maks: number = TRAIL_MAKS): Peg[] {
  const sidste = liste[liste.length - 1]
  if (sidste) {
    const dx = peg.x - sidste.x
    const dy = peg.y - sidste.y
    if (dx * dx + dy * dy < MIN_AFSTAND * MIN_AFSTAND) return liste
  }
  const ny = [...liste, peg]
  return ny.length > maks ? ny.slice(ny.length - maks) : ny
}

/** Fjern punkter der er ældre end levetiden. */
export function fjernAeldre(liste: Peg[], nu: number, levetid: number = FADE_MS): Peg[] {
  return liste.filter((p) => nu - p.t < levetid)
}

/** 0..1 — hvor synligt et punkt skal være lige nu. */
export function opacitet(alder: number, levetid: number = FADE_MS): number {
  if (alder <= 0) return 1
  if (alder >= levetid) return 0
  return 1 - alder / levetid
}

/** Spor-prikkens størrelse: den nyeste er størst, de ældste svinder ind. */
export function sporStoerrelse(placering: number, antal: number): number {
  if (antal <= 1) return 7
  const andel = placering / (antal - 1) // 0 = ældste, 1 = nyeste
  return 3 + andel * 4
}

/** Et rektangel i vinduets lokale koordinater — én skærm. */
export interface Rektangel {
  x: number
  y: number
  width: number
  height: number
}

/**
 * Hvilken skærm et punkt ligger på — eller -1 hvis det ligger uden for dem alle.
 *
 * Bjørn 21/9-2026: «halo og markør følges ikke lige nu». Halo'en tegnede en kant
 * pr. skærm, ALLE på én gang: den viste AT Jarvis havde overtaget, men ikke
 * HVOR. Med dette kan den lyse på den skærm han faktisk står på.
 *
 * -1 frem for et gæt: hellere ingen kant end en kant på den forkerte skærm. Et
 * punkt i et mellemrum mellem to skærme hører ikke til nogen af dem, og en
 * halo der peger på den forkerte skærm er værre end ingen halo — den lyver om
 * hvor Jarvis er.
 *
 * Intervallerne er halvåbne ([x, x+width[), så et punkt på den præcise grænse
 * mellem to skærme hører til den højre og ikke til begge.
 */
export function aktivSkærm(skaerme: Rektangel[], x: number, y: number): number {
  for (let i = 0; i < skaerme.length; i++) {
    const s = skaerme[i]
    if (!s) continue
    if (x >= s.x && x < s.x + s.width && y >= s.y && y < s.y + s.height) return i
  }
  return -1
}
