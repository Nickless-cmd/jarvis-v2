/**
 * Område-beregningen for markør-laget — ren, uden electron-import, så den kan
 * testes uden en skærm.
 *
 * Målt på Bjørns maskine 21/9-2026:
 *
 *   number of screens: 1        dimensions: 5760x1080
 *   Monitors: 3                 XINERAMA heads: 3
 *     head #2: 1920x1080 @    0,0
 *     head #0: 1920x1080 @ 1920,0
 *     head #1: 1920x1080 @ 3840,0
 *
 * Altså: tre fysiske skærme, men ÉT X-screen — Xinerama lægger dem side om
 * side i samme virtuelle rum, og musen flyttes i de virtuelle koordinater
 * (nut.js læste (3037, 551), hvilket kun giver mening i det rum). Electron
 * rapporterer dem som tre displays, og unionen af deres bounds er hele
 * skrivebordet. Det er den beregning der ligger her.
 */

export interface Skærm {
  x: number
  y: number
  width: number
  height: number
}

/** Unionen af alle skærme — det rektangel der rummer dem alle.
 *
 *  Negativ x/y er gyldigt og almindeligt: en skærm sat til venstre for den
 *  primære har negative koordinater i X11. Løsningen er ikke at klippe til
 *  nul — det ville sætte laget skævt på præcis de opsætninger der har en
 *  skærm til venstre. */
export function unionAf(skaerme: Skærm[]): Skærm {
  if (skaerme.length === 0) return { x: 0, y: 0, width: 0, height: 0 }
  const venstre = Math.min(...skaerme.map((s) => s.x))
  const top = Math.min(...skaerme.map((s) => s.y))
  const hoejre = Math.max(...skaerme.map((s) => s.x + s.width))
  const bund = Math.max(...skaerme.map((s) => s.y + s.height))
  return { x: venstre, y: top, width: hoejre - venstre, height: bund - top }
}

/** Oversæt skærm-bounds til vinduets LOKALE rum.
 *
 *  Vinduet ligger i unionens øverste venstre hjørne (main sætter dets bounds
 *  til `unionAf`). Renderer'en kender derfor kun sit eget rum og skal ikke
 *  vide hvor på skrivebordet laget ligger — den tegner bare de rektangler den
 *  får. Det er den samme oversættelse `pegMarkoer` gør for markøren.
 *
 *  Halo'en bruger den til at lægge én kant pr. SKÆRM: på et tre-skærms
 *  skrivebord skal hver skærm lyse op, ikke bare den ydre ramme af unionen. */
export function lokaleSkærme(skaerme: Skærm[], vindue: Skærm): Skærm[] {
  return skaerme.map((s) => ({
    x: s.x - vindue.x,
    y: s.y - vindue.y,
    width: s.width,
    height: s.height,
  }))
}
