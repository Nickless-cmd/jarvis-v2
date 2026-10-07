/**
 * Hvor hover-diffen skal staa.
 *
 * Hover-diffen ligger centreret over beskedkolonnen. Lodret bliver den ved
 * filraekken og vender opad, naar der ikke er plads nedenfor.
 */
export interface Kant {
  top: number
  bottom: number
  left: number
  right: number
}

export interface Placering {
  top: number
  left: number
  bredde: number
  /** Den hoejde der faktisk er plads til. Er skaermen lavere end popup'ens
   *  oenskede hoejde, KRYMPER den — den stikker ikke ud foroven og forneden. */
  hoejde: number
  /** Sand naar popup'en aabner OPAD. Kun til test og aria — CSS bruger `top`. */
  opad: boolean
}

/** Luft til rammens og skaermens kanter. */
const LUFT = 8
const MAX_BREDDE = 560

export function beregnDiffPlacering(arg: {
  /** Fil-raekken der hoveres. */
  raekke: Kant
  /** Chat-fladen. Popup'en forlader den aldrig vandret. */
  ramme: Kant
  /** Skaermen. Popup'en forlader den aldrig lodret. */
  vindue: { bredde: number; hoejde: number }
  /** Popup'ens faste hoejde. */
  hoejde: number
}): Placering {
  const { raekke, ramme, vindue, hoejde } = arg

  // ── Vandret: midt over beskedkolonnen, ogsaa naar raekken staar i kanten.
  const plads = Math.max(0, ramme.right - ramme.left - LUFT * 2)
  const bredde = Math.min(MAX_BREDDE, plads)
  const left = ramme.left + (ramme.right - ramme.left - bredde) / 2

  // ── Lodret: nedad fra raekkens top, medmindre skaermen slipper op. Saa
  // vendes den, saa dens BUND staar ved raekkens bund — den bliver hos sin
  // raekke i stedet for at glide op og daekke den.
  //
  // Paa en lav skaerm er der ingen vending der hjaelper: er der 414 px og
  // popup'en vil vaere 420, stikker den ud uanset hvor den staar. Saa
  // krymper den i stedet. Kroppen scroller allerede.
  const brugbar = Math.max(0, vindue.hoejde - LUFT * 2)
  const h = Math.min(hoejde, brugbar)

  let opad = false
  let top = raekke.top
  if (top + h > vindue.hoejde - LUFT) {
    opad = true
    top = raekke.bottom - h
  }
  top = Math.max(LUFT, Math.min(top, vindue.hoejde - h - LUFT))
  return { top, left, bredde, hoejde: h, opad }
}
