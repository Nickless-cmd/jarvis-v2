import { useEffect, useRef, useState } from 'react'
import { AccessibilityInfo, Animated, Easing, StyleSheet, View } from 'react-native'
import { useTheme } from '../theme/ThemeContext'

/**
 * Puls-mærket i bevægelse — tre bjælker der løfter sig i bølge (Bjørn 21/9-2026).
 *
 * ## Hvorfor tre Views og ikke ét SVG
 *
 * Formen er mærkets egen (samme tal som `PulsIkon.tsx`: 19 enheder brede i en
 * 100-boks, 7 fra hinanden, højderne 36/61/39). Men her skal bjælkerne
 * SKALERE. En `Rect` i SVG skalerer om sit eget hjørne, og desk løser det med
 * `transform-origin: 50px 50px` i CSS — der findes ingen direkte pendant i
 * `react-native-svg`. En View skalerer om sit eget midtpunkt, og det er
 * præcis den bevægelse der skal til: alle tre bjælker i mærket har lodret
 * centrum på 50 i den 100-boks store ramme, så «om eget midtpunkt» og «om
 * mærkets midtpunkt» er den samme bevægelse.
 *
 * ## Rytmen er desk's, uændret
 *
 * 1,6 s gennem omløbet, `scaleY` 0,72 → 1,28, og 0,22 s / 0,43 s forskydning
 * mellem bjælkerne (13,5 % og 27 % af omløbet). Mærket skal bevæge sig ens i
 * begge klienter — se `JarvisPulse.css` i desk.
 */

// Mærkets geometri som andele af `size` — samme forhold som PulsIkon.tsx.
const BREDDE = 0.19
const GAP = 0.07
// Højde og forskydning hører sammen pr. bjælke, så de står som ét. To arrays
// der indekseres med samme `i` kan drive fra hinanden uden at nogen opdager
// det — og TypeScript kan ikke se at indekset findes.
const BJAELKER = [
  { hoejde: 0.36, forsinkelse: 0 },     // venstre: kort
  { hoejde: 0.61, forsinkelse: 220 },   // midten: højest
  { hoejde: 0.39, forsinkelse: 430 },   // højre: mellem
] as const
// Rytmen fra desk.
const RY = 1600
const LAV = 0.72
const HOEJ = 1.28
const FADE_MS = 220

/** Desk slukker for bevægelsen når systemet beder om det. Det skal vi også. */
function useRoerIKkePaaSig(): boolean {
  const [ro, setRo] = useState(false)
  useEffect(() => {
    let aktiv = true
    Promise.resolve(AccessibilityInfo.isReduceMotionEnabled?.())
      .then((v) => { if (aktiv) setRo(Boolean(v)) })
      .catch(() => { /* ældre RN uden kalder — så bevæger den sig bare */ })
    const sub = AccessibilityInfo.addEventListener?.('reduceMotionChanged', (v) => setRo(Boolean(v)))
    return () => { aktiv = false; sub?.remove?.() }
  }, [])
  return ro
}

function Bjaelke({ bredde, hoejde, farve, forsinkelse, ro }: {
  bredde: number; hoejde: number; farve: string; forsinkelse: number; ro: boolean
}) {
  const skala = useRef(new Animated.Value(LAV)).current
  useEffect(() => {
    if (ro) { skala.setValue(1); return }
    skala.setValue(LAV)
    const boelge = Animated.loop(Animated.sequence([
      Animated.timing(skala, { toValue: HOEJ, duration: RY / 2, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
      Animated.timing(skala, { toValue: LAV, duration: RY / 2, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
    ]))
    // Forskydningen lægges på STARTEN af loopet — ikke som en `delay` inde i
    // det. En delay pr. omløb ville give et hak hver 1,6 s, hvor bølgen holdt
    // vejret og begyndte forfra; nu løber den bare senere af sted og glider.
    const t = setTimeout(() => boelge.start(), forsinkelse)
    return () => { clearTimeout(t); boelge.stop() }
  }, [ro, forsinkelse, skala])
  return (
    <Animated.View
      style={{
        width: bredde,
        height: hoejde,
        borderRadius: bredde / 2,
        backgroundColor: farve,
        transform: [{ scaleY: skala }],
      }}
    />
  )
}

/** Selve mærket. Statisk i sin form, levende i sin bevægelse. */
export function AnimeretPuls({ size = 16, farve, testID }: { size?: number; farve: string; testID?: string }) {
  const ro = useRoerIKkePaaSig()
  return (
    <View testID={testID} style={[stil.raekke, { height: size * BJAELKER[1].hoejde, gap: size * GAP }]}>
      {BJAELKER.map((b, i) => (
        <Bjaelke
          key={i}
          bredde={size * BREDDE}
          hoejde={size * b.hoejde}
          farve={farve}
          forsinkelse={b.forsinkelse}
          ro={ro}
        />
      ))}
    </View>
  )
}

/**
 * Pulsen ved tilbage-pilen: dukker op når noget kræver dig, forsvinder når
 * intet gør. Den ERSTATTER den statiske prik — to tegn for samme tilstand
 * ville være støj.
 *
 * Fade-ud kræver at mærket bliver monteret mens det toner væk, ellers ville
 * det blinke af. Derfor `monteret` ved siden af `synlig`.
 */
export function PulsVedPil({ synlig, farve }: { synlig: boolean; farve: string }) {
  const tokens = useTheme()
  const [monteret, setMonteret] = useState(synlig)
  const op = useRef(new Animated.Value(synlig ? 1 : 0)).current

  useEffect(() => {
    if (synlig) {
      setMonteret(true)
      Animated.timing(op, { toValue: 1, duration: FADE_MS, easing: Easing.out(Easing.ease), useNativeDriver: true }).start()
      return
    }
    Animated.timing(op, { toValue: 0, duration: FADE_MS, easing: Easing.in(Easing.ease), useNativeDriver: true })
      .start(({ finished }) => { if (finished) setMonteret(false) })
  }, [synlig, op])

  if (!monteret) return null
  return (
    <Animated.View
      testID="opm-puls"
      // Pulsen sidder oven på pilens trykflade. Uden dette ville det lille
      // mærke spise trykket, og pilen ville føles død i netop det hjørne.
      pointerEvents="none"
      style={[stil.pilPuls, { backgroundColor: tokens.color.bgFloat, opacity: op }]}
    >
      <AnimeretPuls size={16} farve={farve} />
    </Animated.View>
  )
}

const stil = StyleSheet.create({
  raekke: { flexDirection: 'row', alignItems: 'center' },
  // Pladen bag mærket er knappens egen farve, så mærket læses som om det
  // ligger PÅ knappen frem for at skære gennem pilen bagved.
  pilPuls: {
    position: 'absolute',
    top: 0,
    right: 0,
    paddingHorizontal: 2,
    paddingVertical: 2,
    borderRadius: 99,
    alignItems: 'center',
    justifyContent: 'center',
  },
})
