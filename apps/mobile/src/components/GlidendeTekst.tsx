import { useEffect, useRef, useState } from 'react'
import { Animated, Easing, StyleSheet, Text, View, type TextStyle, type StyleProp } from 'react-native'
import { useReducedMotion } from '../lib/useReducedMotion'

/** Hvor længe lyset er om at rejse hen over linjen. */
const VARIGHED_MS = 1600
/** Båndets bredde i dp. Bredere = blødere stryg. */
const BAAND = 90

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
 * gjorde med det samme.
 *
 * Nu ligger teksten urørt, og båndet glider HEN OVER den i et lag der ikke
 * kan trykkes på og ikke bliver læst op. Der findes ingen gradient-pakke i
 * projektet, så blødheden laves af tre lag med aftagende gennemsigtighed —
 * billigere end at trække en afhængighed ind for én animation.
 */
export function GlidendeTekst({
  text, aktiv, style, numberOfLines, fuldBredde,
}: {
  text: string
  aktiv: boolean
  /** Maal hele linjens bredde i stedet for tekstens. */
  fuldBredde?: boolean
  style?: StyleProp<TextStyle>
  numberOfLines?: number
}) {
  const reduced = useReducedMotion()
  const x = useRef(new Animated.Value(0)).current
  const [bredde, setBredde] = useState(0)
  const animer = aktiv && !reduced && bredde > 0

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
      // `fuldBredde`: Bjoern 12/9-2026 — «den lyse boelge skal koere den fulde
      // skaerm bredde selv om teksten ikke er saa lang». Uden den maaler
      // onLayout kun tekstens egen bredde, og lyset naar aldrig ud i linjen.
      style={[styles.wrap, fuldBredde ? styles.fuld : null]}
      // Bredden måles FØR lyset kan rejse. Uden den ville båndet enten stå
      // stille eller skyde forbi kanten på en linje af ukendt længde.
      onLayout={(e) => {
        const b = Math.round(e.nativeEvent.layout.width)
        setBredde((p) => (Math.abs(p - b) > 1 ? b : p))
      }}
    >
      <Text style={style} numberOfLines={numberOfLines}>{text}</Text>
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
          <View style={[styles.lag, styles.ydre]} />
          <View style={[styles.lag, styles.midt]} />
          <View style={[styles.lag, styles.ydre]} />
        </Animated.View>
      ) : null}
    </View>
  )
}

const styles = StyleSheet.create({
  // `flexShrink`: en lang etiket skal stadig kunne klippes af sin forælder,
  // ellers skubber den chevronen ud over kanten.
  wrap: { flexShrink: 1, overflow: 'hidden', justifyContent: 'center' },
  baand: {
    position: 'absolute',
    top: 0, bottom: 0, left: 0,
    width: BAAND,
    flexDirection: 'row',
  },
  fuld: { alignSelf: 'stretch', flexShrink: 0 },
  lag: { flex: 1 },
  ydre: { backgroundColor: 'rgba(255,255,255,0.05)' },
  midt: { backgroundColor: 'rgba(255,255,255,0.13)' },
})
