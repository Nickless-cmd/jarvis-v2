import { useEffect, useRef, useState } from 'react'
import { Animated, Easing, StyleSheet, Text, View, type TextStyle, type StyleProp } from 'react-native'
import { useReducedMotion } from '../lib/useReducedMotion'
import { useTheme } from '../theme/ThemeContext'

/** Hvor længe lyset er om at rejse hen over linjen. */
const VARIGHED_MS = 2250 // Claude Desktops SHIMMER: 2,25 s (desk bruger samme)
/** Båndets bredde i dp. Bredere = blødere stryg. */
const BAAND = 90
/**
 * Lysets vægt pr. vindue — en klokke, ikke en firkant.
 *
 * Vinduet er delt i fem bidder med aftagende vægt ud mod kanterne, så stryget
 * får bløde ender. Ét enkelt vindue ville klippe hårdt og læses som en
 * »afsløring« der glider hen over linjen, ikke som lys der rejser igennem den.
 */
const KLIN = [0.14, 0.42, 1, 0.42, 0.14]
/** Hvor meget grundteksten dæmpes mens lyset løber. */
const DAEMPET = 0.5
/**
 * Lysets farve i mørkt tema — desk's egen `#eafff3` fra `.shimmer`-gradienten.
 * I lyst tema ville den være usynlig på hvid, så dér bruges `accentText`.
 */
const LYS_MOERK = '#eafff3'

/**
 * Tekst med et lys der glider hen over den, mens noget kører.
 *
 * ## Hvorfor et lys og ikke et åndedrag
 *
 * Bjørn 12/9-2026: «i stedet for at pulsere burde det der pulserende være et
 * lys der glider gennem teksten». En hel linje der toner op og ned siger
 * «noget er i gang» — men gør teksten svær at læse i halvdelen af tiden. Et
 * lys der vandrer siger det samme, og man kan læse med imens.
 *
 * ## Hvorfor teksten forbliver ÉT stykke
 *
 * Første forsøg delte linjen i ét `<Text>` pr. bogstav og animerede hver for
 * sig. Effekten var flot og prisen var for høj: en skærmlæser ville læse
 * linjen bogstav for bogstav, tekstmarkering ville gå i stykker, og enhver
 * test der slår teksten op på sit indhold ville fejle — hvilket tre af dem
 * gjorde med det samme. Teksten ligger derfor urørt i bunden, og lyset er en
 * SKJULT kopi af den samme tekst.
 *
 * ## Hvorfor lyset er lavet af TEKSTEN og ikke af et bånd oven på den
 *
 * Første udgave lagde tre halvgennemsigtige hvide flader oven på teksten.
 * Det er ikke det desk gør, og det er ikke det Bjørn ser (21/9-2026: «samme
 * glidende lys wave når de kører som de desk — der kører sådan en lysbølge
 * igennem»). Desk maler gradienten INDE i bogstaverne (`background-clip:
 * text` i `.shimmer`), så lyset kun findes hvor der er bogstaver — og
 * grundteksten er dæmpet uden for båndet.
 *
 * React Native har ingen `background-clip: text`. Men det kan bygges: en
 * lys kopi af teksten lægges oven på den dæmpede grundtekst, og klippes af et
 * vindue der glider. Så lyser bogstaverne — og KUN bogstaverne — hvor vinduet
 * er, præcis som gradienten i desk. Mellemrummene mellem ordene forbliver
 * mørke, hvilket er hele forskellen på en lysbølge og en grå streg.
 *
 * De skjulte kopier er `accessibilityElementsHidden`, så en skærmlæser ikke
 * læser linjen fem gange, og så et tekstoplysning stadig kun finder ét træf.
 */
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
  const [bredde, setBredde] = useState(0)
  const animer = aktiv && !reduced && bredde > 0
  const lys = theme.scheme === 'light' ? theme.color.accentText : LYS_MOERK
  /** Hvor bred hver bid af vinduet er. */
  const bid = BAAND / KLIN.length

  useEffect(() => {
    if (!animer) {
      x.stopAnimation()
      x.setValue(0)
      return
    }
    const loop = Animated.loop(
      Animated.timing(x, {
        toValue: 1,
        duration: VARIGHED_MS,
        easing: Easing.linear,
        useNativeDriver: true,
      }),
    )
    loop.start()
    return () => loop.stop()
  }, [animer, x])

  return (
    <View
      testID="glidende-tekst"
      style={styles.wrap}
      // Bredden måles FØR lyset kan rejse. Uden den ville vinduet enten stå
      // stille eller skyde forbi kanten på en linje af ukendt længde.
      onLayout={(e) => {
        const b = Math.round(e.nativeEvent.layout.width)
        setBredde((p) => (Math.abs(p - b) > 1 ? b : p))
      }}
    >
      <Text style={[style, animer ? styles.daempet : null]} numberOfLines={numberOfLines}>{text}</Text>
      {animer ? (
        <Animated.View
          testID="glidende-lys"
          pointerEvents="none"
          accessibilityElementsHidden
          importantForAccessibility="no-hide-descendants"
          style={[
            styles.baand,
            {
              transform: [{
                translateX: x.interpolate({
                  inputRange: [0, 1],
                  // HELT ind fra venstre og HELT ud til højre, ellers blinker
                  // enderne i stedet for at blive strøget.
                  outputRange: [-BAAND, bredde + BAAND],
                }),
              }],
            },
          ]}
        >
          {KLIN.map((vaegt, i) => (
            <View key={i} style={[styles.vindue, { width: bid, opacity: vaegt }]}>
              {/* Vinduet klipper sin egen bid. Kopien skubbes lige så langt
                  den anden vej, så alle fem bidder viser SAMME sted af ordet —
                  ellers ville hver bid vise begyndelsen af teksten. */}
              <View style={[styles.lag, { left: -i * bid, width: bredde }]}>
                <Text style={[style, { color: lys }]} numberOfLines={numberOfLines}>{text}</Text>
              </View>
            </View>
          ))}
        </Animated.View>
      ) : null}
    </View>
  )
}

const styles = StyleSheet.create({
  // `flexShrink`: en lang etiket skal stadig kunne klippes af sin forælder,
  // ellers skubber den chevronen ud over kanten.
  wrap: { flexShrink: 1, overflow: 'hidden', justifyContent: 'center' },
  // Grundteksten dæmpes mens lyset løber — som desks `fg3` uden for båndet.
  // Uden dæmpningen ville det lyse stryg kun være et par nuancer over teksten.
  daempet: { opacity: DAEMPET },
  baand: {
    position: 'absolute',
    top: 0, bottom: 0, left: 0,
    width: BAAND,
    flexDirection: 'row',
  },
  vindue: { overflow: 'hidden' },
  lag: { position: 'absolute', top: 0, bottom: 0, justifyContent: 'center' },
})
