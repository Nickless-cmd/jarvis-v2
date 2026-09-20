import Svg, { Rect } from 'react-native-svg'

/**
 * Puls-mærket — tre afrundede lodrette bjælker (Bjørn 20/9-2026).
 *
 * ## Hvorfor det findes
 *
 * Composerens hvileknap bar `AudioLines` fra lucide: SEKS tynde streger med
 * skarpe ender. Det er et pænt ikon, men det er et *generisk* ikon — samme
 * streg-familie som enhver anden lyd/video-app bruger. Bjørn: «Jeg kunne godt
 * tænke mig dit ikon i stedet for stregerne i composer i mobil appen.»
 *
 * Mærket er TRE bjælker med fuldt afrundede ender — kort, høj, mellem. Samme
 * idé som stregerne, men strammere: færre elementer, mere vægt pr. element.
 * Det er formen fra app-ikonet (`favicon.svg` i desk), så knappen og ikonet på
 * telefonens hjemmeskærm nu er samme tegn.
 *
 * ## Hvorfor SVG og ikke et billede
 *
 * Et PNG ville skulle leveres i tre tætheder og se blødt ud i den ene der
 * manglede. `react-native-svg` er allerede i brug fem steder (UploadRing,
 * VoiceOrb, ContextRing, LivenessRing, StreamIndicator), så geometrien skalerer
 * skarpt, og formen ligger som tal man kan rette — ikke som pixels.
 *
 * ## Farven er IKKE mærkets egen
 *
 * Mærkets farve er turkis `#49c9b8`, men composerens knap er mint `#6EE7A8`.
 * Turkise bjælker på en mint knap ville være to næsten ens grønne oven på
 * hinanden. `color` gives derfor udefra — på knappen er den mørk (`bg0`),
 * præcis som stregerne var. Det er FORMEN der skifter, ikke farven.
 *
 * Geometrien er mærkets egen, uændret: bjælkerne er 19 enheder brede i en
 * 100-boks med `rx` på halvdelen af bredden, så enderne er halvcirkler.
 */
export function PulsIkon({ size = 21, color }: { size?: number; color: string }) {
  return (
    <Svg testID="puls-ikon" width={size} height={size} viewBox="0 0 100 100" fill={color}>
      {/* Venstre: kort. Højre: mellem. Midten: højest — og det er midten der
          gør mærket læsbart som «puls» og ikke som en tilfældig stolpe. */}
      <Rect x="15" y="32" width="19" height="36" rx="9.5" />
      <Rect x="41" y="19.5" width="19" height="61" rx="9.5" />
      <Rect x="67" y="30.5" width="19" height="39" rx="9.5" />
    </Svg>
  )
}
