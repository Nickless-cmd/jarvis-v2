import { StyleSheet, View } from 'react-native'
import Svg, { Defs, LinearGradient, Rect, Stop } from 'react-native-svg'
import { useTheme } from '../theme/ThemeContext'

/**
 * Blød overgang mellem en svævende bjælke og tråden bagved.
 *
 * ## Hvorfor den findes
 *
 * Headeren og komponisten ligger begge som halvgennemsigtige flader over
 * tråden — `scrim`, 72 % sort i mørkt tema. Fladen er der med vilje: uden den
 * ville tråden blive klippet hårdt af en massiv bjælke, og det er dét der giver
 * følelsen af ét sammenhængende rum frem for tre etager.
 *
 * Men den var en FLADE, ikke en fade. Den begyndte og sluttede brat — og
 * baggrunden er selv sort (`bg0` = #000000), så 72 % sort oven på sort er
 * stadig sort. Der var altså intet at tone ud imod: bare en skarp vandret
 * streg tværs over skærmen, samme sted hele vejen hen.
 *
 * Bjørn 28/9-2026: «nu det eneste der irritere mig er fade både ved composer
 * og header.. det er så tidligt man se kanten». Han havde ret, og det er derfor
 * han havde svært ved at sætte ord på det: der BURDE være en fade, og der var
 * en kant.
 *
 * `KantFade` maler præcis den samme farve som en gradient i stedet. Boksens
 * egen `backgroundColor` fjernes, og denne lægges i dens sted — så bjælken
 * dækker lige så meget som før, men overgangen til tråden er glidende.
 *
 * ## Retningen
 *
 * - `ned` — headerens boks: fuld foroven, transparent forneden. Tråden toner
 *   IND under bjælken i stedet for at begynde ved en streg.
 * - `op` — komponistens boks: transparent foroven, fuld forneden. Tråden toner
 *   UD ned mod komponisten, og bunden er stadig dækket — så teksten ikke
 *   lækker ud i enhedens gestus-zone nedenfor.
 *
 * ## Farven
 *
 * `scrim` er en `rgba()`-streng, og SVG's `stop-opacity` GANGER med farvens
 * egen alpha — så den kan ikke sættes direkte oveni. `delAlpha` skiller de to
 * ad, og gradienten rammer dermed nøjagtig samme dækning som fladen havde i
 * sin fulde ende.
 *
 * ## Navnet
 *
 * Gradient-id'er er GLOBALE i SVG-dokumentet. To `KantFade` med samme id ville
 * arve hinandens farve, og den ene ville stiltiende forsvinde. `navn` gør dem
 * unikke — og giver samtidig et testID at måle på.
 */
export function KantFade({ retning, navn, over = 0 }: {
  retning: 'op' | 'ned'
  navn: string
  /**
   * Hvor mange dp over forælderens overkant gradienten skal begynde.
   *
   * Kun for `op`, og den findes fordi den er nødvendig: uden den starter
   * gradienten ved forælderens top med opacity 0 — og for komponisten ER
   * forælderens top komponistens overkant. Faden var derfor transparent
   * netop dér hvor tråden møder komposeren, og fuld (sort på sort) bag det
   * uigennemsigtige kort. Den var altså usynlig, ikke fraværende.
   *
   * Bjørn 28/9-2026: «mangler fade helt bag composer». Målt: gradienten nåede
   * aldrig op over kortets overkant. Med `over` forlænges laget opad, og
   * gradienten måles i dp derfra — transparent ved -over, fuld ved
   * forælderens top, og fuld hele vejen ned.
   */
  over?: number
}) {
  const { color } = useTheme()
  const { farve, alpha } = delAlpha(color.scrim)
  const id = `kantfade-${navn}`
  const ned = retning === 'ned'
  // Forlængelsen kraever at gradienten måles i faste dp (userSpaceOnUse) frem
  // for i procenter af boksen: procent-koordinater ville følge den NYE, højere
  // boks og sprede faden ud over hele laget i stedet for at samle den ved
  // kanten. y2 = over betyder «fuld dér hvor forælderen begynder» — alt
  // nedenunder arver den fulde stop-farve.
  const straek = over > 0 && !ned
  return (
    <View
      testID={`kantfade-ramme-${navn}`}
      pointerEvents="none"
      style={straek ? [styles.lag, { top: -over }] : styles.lag}
    >
      <Svg
        testID={`kantfade-${navn}`}
        pointerEvents="none"
        width="100%"
        height="100%"
      >
        <Defs>
          <LinearGradient
            id={id}
            x1="0" y1={straek ? 0 : '0%'}
            x2="0" y2={straek ? over : '100%'}
            gradientUnits={straek ? 'userSpaceOnUse' : 'objectBoundingBox'}
          >
            <Stop offset="0" stopColor={farve} stopOpacity={ned ? alpha : 0} />
            <Stop offset="1" stopColor={farve} stopOpacity={ned ? 0 : alpha} />
          </LinearGradient>
        </Defs>
        <Rect x="0" y="0" width="100%" height="100%" fill={`url(#${id})`} />
      </Svg>
    </View>
  )
}

/**
 * Deler en `rgb()`/`rgba()`-streng i farve og alpha.
 *
 * Nødvendig fordi SVG's `stop-opacity` er en MULTIPLIKATOR oven på farvens
 * egen alpha: en `rgba(0, 0, 0, 0.72)` med `stopOpacity={1}` giver 0,72 — men
 * sætter man alpha direkte som stop-opacity, får man 0,72 × 0,72 = 0,52 og en
 * kant der er for svag.
 *
 * Ukendte formater (hex, farvenavne) gives videre uændret med alpha 1 — hellere
 * en kant i den forkerte farve end ingen kant, for det er kanten der bærer
 * adskillelsen.
 */
export function delAlpha(rgba: string): { farve: string; alpha: number } {
  const m = /^rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*(?:,\s*([\d.]+)\s*)?\)$/.exec(
    rgba.trim()
  )
  if (!m) return { farve: rgba, alpha: 1 }
  return {
    farve: `rgb(${m[1]}, ${m[2]}, ${m[3]})`,
    alpha: m[4] === undefined ? 1 : Number(m[4])
  }
}

const styles = StyleSheet.create({
  // Fylder den boks den lægges i — hverken mere eller mindre. At strække den
  // ned under headeren ville ramme søgefeltet, der ligger ved `insets.top + 52`.
  lag: { position: 'absolute', left: 0, right: 0, top: 0, bottom: 0 }
})
