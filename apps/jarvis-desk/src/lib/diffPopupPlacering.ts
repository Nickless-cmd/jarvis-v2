/**
 * Hvor hover-diffen skal staa.
 *
 * Bjoern 29/9-2026: «den ska til den anden side altsaa over chatview.. og
 * opad eller nedad afhaengig af skaermen».
 *
 * Foerste udgave spejlede til VENSTRE naar der ikke var plads til hoejre, og
 * maalte plads mod hele vinduet. Fil-raekken staar langt ude til hoejre i en
 * bred besked, saa der var praktisk talt aldrig plads — og spejlingen lagde
 * diffen hen over SIDEPANELET, den ene flade i vinduet der ikke har noget med
 * den at goere.
 *
 * Derfor er rammen her chat-fladen og ikke vinduet: popup'en maa flytte sig
 * hvorhen den vil INDEN FOR den, og aldrig udenfor. Lodret er det omvendt —
 * den maa gerne bruge hele skaermen, for det er skaermen der begraenser den.
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
/** Afstand fra fil-raekken til popup'ens naermeste kant. */
const AFSTAND = 10
const MIN_BREDDE = 320
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

  // ── Vandret: hoejre for raekken, ellers venstre — men altid inde i rammen.
  const plads = Math.max(0, ramme.right - ramme.left - LUFT * 2)
  const bredde = Math.max(Math.min(MAX_BREDDE, plads), Math.min(MIN_BREDDE, plads))

  let left = raekke.right + AFSTAND
  if (left + bredde > ramme.right - LUFT) left = raekke.left - bredde - AFSTAND
  // Klemmes ind i rammen. Er rammen smallere end popup'en, vinder venstre
  // kant — en popup der stikker ud til hoejre er stadig laesbar forfra.
  const venstreGraense = ramme.left + LUFT
  const hoejreGraense = ramme.right - bredde - LUFT
  left = Math.max(venstreGraense, Math.min(left, Math.max(venstreGraense, hoejreGraense)))

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
