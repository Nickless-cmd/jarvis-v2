/**
 * Zoom-regning til fuldskærms-visningen.
 *
 * Pinch-zoom findes ikke i React Native selv. De biblioteker der giver det
 * (`react-native-gesture-handler` + `reanimated`) er NATIVE moduler: de skal
 * ind i build'et og i babel-konfigurationen, og et nyt native modul betyder en
 * ny APK-version — for en funktion der kan regnes ud i hånden.
 *
 * Her ligger derfor KUN matematikken. Komponenten rører `Animated` og
 * fingerbevægelserne; det her rører tal og kan prøves af uden en telefon.
 */

/** Mindste skala. 1 = billedet fylder som da det åbnede. */
export const MIN_SKALA = 1
/** Største skala. Længere ind end det, og billedet er bare pixels. */
export const MAKS_SKALA = 5

export interface Prik {
  x: number
  y: number
}

/** Den ramme billedet bor i. Kommer fra `onLayout`, altså i punkt, ikke pixels. */
export interface Ramme {
  bredde: number
  hoejde: number
}

/**
 * Afstanden mellem to fingre — grundlaget for hele skalaen.
 *
 * 0 når der ikke ER to fingre. Det er ikke en fejl men svaret: uden to
 * kontaktpunkter findes der ingen afstand at måle, og et knib der begynder
 * eller slutter midt i en bevægelse giver en liste der skrumper undervejs.
 */
export function fingerAfstand(touches: { pageX: number; pageY: number }[]): number {
  if (!touches || touches.length < 2) return 0
  // Eksplicitte indekser frem for destructuring: `noUncheckedIndexedAccess`
  // gør hvert element `| undefined`, og laengden er allerede efterproevet.
  const a = touches[0]!
  const b = touches[1]!
  return Math.hypot(b.pageX - a.pageX, b.pageY - a.pageY)
}

/**
 * Hold skalaen inden for det der giver mening.
 *
 * Uden loftet kunne et hurtigt knib løbe løbsk. Uden gulvet ville billedet
 * kunne blive MINDRE end den ramme det bor i, og så står det og flagrer i
 * midten af et tomt felt — det ser ud som en fejl, ikke som en funktion.
 *
 * `NaN` (en touche-liste der tømmes midt i et knib, så forholdet bliver 0/0)
 * falder tilbage til 1 frem for at forgifte hele transformen. Uendelighed gør
 * IKKE: et knib der løber løbsk skal klemme til loftet, ikke springe tilbage
 * til uzoomet.
 */
export function begraensSkala(skala: number, min = MIN_SKALA, maks = MAKS_SKALA): number {
  if (Number.isNaN(skala)) return min
  return Math.min(maks, Math.max(min, skala))
}

/**
 * Hvor langt må billedet skubbes?
 *
 * Ved skala `s` rager billedet `(s-1)/2` af rammen ud til hver side — det er
 * den afstand der faktisk ER noget at panorere i. Tillod man mere, kunne man
 * trække billedet væk fra skærmen og stå med et tomt felt og ingen vej tilbage.
 *
 * Ved skala 1 er begge grænser 0, altså: ikke noget at panorere i. Det er
 * præcis meningen — et uzoomet billede skal ikke kunne flyttes.
 */
export function begraensForskydning(f: Prik, skala: number, ramme: Ramme): Prik {
  const s = begraensSkala(skala)
  const maksX = Math.max(0, ((ramme?.bredde ?? 0) * (s - 1)) / 2)
  const maksY = Math.max(0, ((ramme?.hoejde ?? 0) * (s - 1)) / 2)
  const klem = (v: number, maks: number) => {
    if (!Number.isFinite(v)) return 0
    return Math.min(maks, Math.max(-maks, v))
  }
  return { x: klem(f?.x ?? 0, maksX), y: klem(f?.y ?? 0, maksY) }
}
