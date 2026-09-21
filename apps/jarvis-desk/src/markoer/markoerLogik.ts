/**
 * Logikken bag markør-laget — ren, så den kan testes uden en browser.
 *
 * Laget er ikke en virtuel markør: Jarvis flytter Bjørns rigtige mus gennem
 * nut.js, så cursoren står der allerede. Vi tegner et mærke omkring den, i det
 * øjeblik den flytter sig, og lader mærket falme — så det er til at se HVORNÅR
 * det er Jarvis der styrer og ikke Bjørn.
 */

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
