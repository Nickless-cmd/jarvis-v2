import { useEffect, useRef, useState } from 'react'
import { Animated, Easing, PixelRatio, StyleSheet, Text, View, type TextStyle, type StyleProp } from 'react-native'
import Svg, { Defs, G, LinearGradient, Mask, Rect, Stop, Text as SvgText } from 'react-native-svg'
import { useReducedMotion } from '../lib/useReducedMotion'
import { useTheme } from '../theme/ThemeContext'

/* DSH-rytmen, som desk fik 30/9-2026 (Bjoern: «vil du soerge for mobilen for
   samme dsh shimmer som du lige lavet i desk? Runde linjerne? Det er stadig
   den sloeve»): 300 ms opstart, 1 s sweep, 500 ms hvile.

   Vores egen var ét kontinuert sweep paa 2.250 ms. Forskellen er ikke farten:
   DSH's HAR en pause, saa hvert sweep laeses som en begivenhed frem for som en
   tilstand der bare koerer.

   Hvilen ligger i INTERPOLATIONEN og ikke i en sekvens: ét `timing` over hele
   omloebet, hvor de sidste 33 % holder baandet i ro. Saa bliver der kun ét
   animeret vaerdi-forloeb at stoppe og rydde op i, og `useNativeDriver`
   beholdes.

   Desk havde samtidig en anden fejl — dens gradient var BROLAGT
   (`background-repeat: repeat`), saa der altid var et naeste lysbaand paa vej
   ind. Den findes ikke her: masken har ÉT baand, og det starter paa `-BAAND`
   og ender paa `bredde + BAAND`, altsaa uden for teksten i begge ender. Den
   del var rigtig i forvejen. */
const SWEEP_MS = 1000
const HVILE_MS = 500
const OPSTART_MS = 300
const OMLOEB_MS = SWEEP_MS + HVILE_MS
/** Hvor stor en del af omloebet der er bevaegelse. Resten holder baandet i ro. */
export const SWEEP_ANDEL = SWEEP_MS / OMLOEB_MS
const BAAND = 90

/**
 * Baandets vej gennem omloebet.
 *
 * Udskilt som en ren funktion, fordi den ellers ikke kan MAALES: Animated med
 * `useNativeDriver` opdaterer ikke JS-vaerdien i en test, og fake timers
 * driver den ikke. En test kunne saa kun laese konstanterne — og en
 * mutationskoersel viste praecis det hul: at fjerne plateauet fra
 * interpolationen lod alle elleve tests bestaa.
 *
 * Tre punkter, ikke to: sweepet fylder de foerste 66,67 %, og resten holder
 * baandet ude til hoejre. Ombrydningen fra 1 til 0 sker mens baandet er uden
 * for teksten, saa den ikke kan ses.
 */
export function banen(bredde: number): { inputRange: number[]; outputRange: number[] } {
  return {
    inputRange: [0, SWEEP_ANDEL, 1],
    outputRange: [-BAAND, bredde + BAAND, bredde + BAAND],
  }
}
const DAEMPET = 0.5
const LYS_MOERK = '#eafff3'
const AnimatedG = Animated.createAnimatedComponent(G)

/** Én synlig SVG-tekstmaske: lyset kan kun ramme bogstaverne, og der er
 * ingen ekstra native tekstlag, som Android kan placere forskudt. */
export function GlidendeTekst({
  text, aktiv, style, numberOfLines,
}: {
  text: string
  aktiv: boolean
  style?: StyleProp<TextStyle>
  numberOfLines?: number
}) {
  const reduced = useReducedMotion()
  const theme = useTheme()
  const x = useRef(new Animated.Value(0)).current
  const [maal, setMaal] = useState({ width: 0, height: 0 })
  const animer = aktiv && !reduced && maal.width > 0 && maal.height > 0
  const lys = theme.scheme === 'light' ? theme.color.accentText : LYS_MOERK
  const tekstStyle = StyleSheet.flatten(style) || {}
  const grund = tekstStyle.fontSize || 14
  // Systemets skrift-skala gaelder den NATIVE teksten — RN's `allowFontScaling`
  // er slaaet til som standard — men ikke for SVG'en. Uden den her tegnes de to
  // tilstande i hver sin stoerrelse: den KOERENDE linje (SVG) i 15 dp, den
  // FAERDIGE (native) i 15 x skalaen.
  //
  // Det er ikke teoretisk. Indtil 26/9-2026 var lyset bygget af NATIVE tekstlag
  // og skalerade derfor med grundteksten; `763bb23a0` afloeste dem med én
  // SVG-maske for at fjerne spoegelses-lagene — og tog skaleringen med i koebet.
  // (Bjørn 30/9-2026: «tekst stoerrelsen er for stor mens runden koere … men
  // naar runden er forbi aendrer teksten til normal stoerrelse».)
  const skala = PixelRatio.getFontScale()
  const skrift = grund * skala
  const linje = (tekstStyle.lineHeight || Math.round(grund * 1.2)) * skala
  // SVG bruger en baseline; den usynlige native tekst bestemmer stadig
  // rækkehøjden og oplæsningsindholdet.
  const baseline = (maal.height - linje) / 2 + (linje + skrift) / 2 - 2

  useEffect(() => {
    if (!animer) {
      x.stopAnimation()
      x.setValue(0)
      return
    }
    x.setValue(0)
    const loop = Animated.loop(Animated.timing(x, {
      toValue: 1, duration: OMLOEB_MS,
      easing: Easing.linear, useNativeDriver: true,
    }))
    // Opstarts-forsinkelsen er DSH's: linjen naar at staa stille et oejeblik
    // foer lyset kommer, saa det foerste sweep ogsaa laeses som en begivenhed.
    const hele = Animated.sequence([Animated.delay(OPSTART_MS), loop])
    hele.start()
    return () => { hele.stop(); loop.stop() }
  }, [animer, x])

  return (
    <View
      testID="glidende-tekst"
      style={styles.wrap}
      onLayout={(e) => {
        const { width, height } = e.nativeEvent.layout
        const w = Math.round(width)
        const h = Math.round(height)
        setMaal((old) => old.width === w && old.height === h ? old : { width: w, height: h })
      }}
    >
      <Text style={[style, animer && styles.skjult]} numberOfLines={numberOfLines}>{text}</Text>
      {animer ? (
        <Svg
          testID="glidende-lys"
          pointerEvents="none"
          accessibilityElementsHidden
          importantForAccessibility="no-hide-descendants"
          accessible={false}
          width={maal.width}
          height={maal.height}
          style={styles.svg}
        >
          <Defs>
            <Mask id="bogstaver" x={0} y={0} width={maal.width} height={maal.height} maskUnits="userSpaceOnUse" maskType="alpha">
              <SvgText
                x={0} y={baseline} fill="#fff"
                fontSize={skrift}
                fontFamily={tekstStyle.fontFamily}
                fontWeight={tekstStyle.fontWeight}
              >{text}</SvgText>
            </Mask>
            <LinearGradient id="lysboelge" x1="0" y1="0" x2="1" y2="0">
              <Stop offset="0" stopColor={lys} stopOpacity="0" />
              <Stop offset="0.5" stopColor={lys} stopOpacity="1" />
              <Stop offset="1" stopColor={lys} stopOpacity="0" />
            </LinearGradient>
          </Defs>
          <G mask="url(#bogstaver)">
            <Rect x={0} y={0} width={maal.width} height={maal.height} fill={tekstStyle.color || theme.color.fg2} opacity={DAEMPET} />
            <AnimatedG transform={[{
              translateX: x.interpolate(banen(maal.width)),
            }]}>
              <Rect x={0} y={0} width={BAAND} height={maal.height} fill="url(#lysboelge)" />
            </AnimatedG>
          </G>
        </Svg>
      ) : null}
    </View>
  )
}

const styles = StyleSheet.create({
  // `minWidth: 0` lader leddet krympe under tekstens egen bredde, saa en lang
  // etiket kan afsluttes med «…» i stedet for at skubbe linjen ud over kanten.
  wrap: { flexShrink: 1, minWidth: 0, overflow: 'hidden', justifyContent: 'center' },
  skjult: { opacity: 0 },
  svg: { position: 'absolute', top: 0, left: 0 },
})
