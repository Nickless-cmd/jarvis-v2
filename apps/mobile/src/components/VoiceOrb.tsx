import { useEffect, useRef } from 'react'
import { Animated, Easing, StyleSheet, View } from 'react-native'
import Svg, { Circle, Defs, Ellipse, RadialGradient, Stop } from 'react-native-svg'
import { useTheme } from '../theme/ThemeContext'
import { useReducedMotion } from '../lib/useReducedMotion'

/**
 * Kuglen i samtale-tilstand.
 *
 * En mikrofon-emoji i en ring så ud som en KNAP — noget man betjener. En kugle
 * ser ud som noget der er TIL STEDE og lytter, og det er den rigtige fornemmelse
 * for et rum hvor man taler frit.
 *
 * Bevægelsen ligger INDE i kuglen, ikke i dens omrids. To bløde lag driver
 * forbi hinanden med hver sin hastighed; det er dét der får den til at ligne
 * væske frem for en pulserende cirkel. Omridset bevæger sig kun svagt, og kun
 * med din stemme — så en ændring i størrelse BETYDER noget i stedet for at være
 * pynt der kører hele tiden.
 */

export type OrbState = 'idle' | 'listening' | 'transcribing' | 'thinking' | 'speaking'

export interface VoiceOrbProps {
  state: OrbState
  /** 0..1 — hvor kraftigt der tales lige nu, som Animated.Value så kuglen kan
   *  følge stemmen uden at skærmen rendres om ved hver måling. */
  level?: Animated.Value
  size?: number
}

/** Hvor hurtigt det indre driver. Tavshed ånder; tale rører på sig. */
const DRIFT_MS: Record<OrbState, number> = {
  idle: 9000,
  listening: 5200,
  transcribing: 4200,
  thinking: 3200,
  speaking: 2600,
}

export function VoiceOrb({ state, level, size = 232 }: VoiceOrbProps) {
  const tokens = useTheme()
  const reduced = useReducedMotion()
  const drift = useRef(new Animated.Value(0)).current
  const own = useRef(new Animated.Value(0)).current
  const swell = level ?? own

  useEffect(() => {
    if (reduced) { drift.stopAnimation(); drift.setValue(0); return }
    drift.setValue(0)
    const loop = Animated.loop(
      Animated.timing(drift, {
        toValue: 1,
        duration: DRIFT_MS[state],
        easing: Easing.linear,
        useNativeDriver: true,
      }),
    )
    loop.start()
    return () => loop.stop()
  }, [state, drift, reduced])

  // Kuglen svulmer KUN mens der lyttes. Hook'en nulstiller niveauet når
  // optagelsen stopper, men her holdes den også fast, så et efterslæb fra
  // sidste måling ikke får den til at ånde videre mens han tænker.
  const responsive = state === 'listening'

  const accent = tokens.color.accent
  const dark = tokens.scheme === 'dark'
  // Sløret skal ALTID gå mod lys. Første forsøg malede med fladens egen farve —
  // det virker i lyst tema, men i mørkt bliver et sort slør til et HUL midt i
  // kuglen frem for til dybde. Lys over farve læses som en genskin uanset tema.
  const veil = dark ? '#ffffff' : tokens.color.bg0
  const veilTop = dark ? 0.3 : 0.9
  const veilMid = dark ? 0.14 : 0.45
  // Bunden må ikke forsvinde helt: i mørkt tema falder en gennemsigtig kant i
  // ét med baggrunden, og kuglen ser afskåret ud i stedet for rund.
  const bodyFloor = dark ? 0.34 : 0.1
  const scale = responsive
    ? swell.interpolate({ inputRange: [0, 1], outputRange: [1, 1.11] })
    : 1
  // De to lag deler samme ur men går hver sin vej, så mønsteret aldrig gentager
  // sig helt. Vandringen holdes inden for kuglen — den er klippet af.
  const up = drift.interpolate({ inputRange: [0, 1], outputRange: [size * 0.42, -size * 0.52] })
  const down = drift.interpolate({ inputRange: [0, 1], outputRange: [-size * 0.46, size * 0.38] })
  const sway = drift.interpolate({ inputRange: [0, 0.5, 1], outputRange: [-size * 0.07, size * 0.07, -size * 0.07] })

  return (
    <Animated.View style={[styles.wrap, { width: size, height: size, transform: [{ scale }] }]}>
      <View style={[styles.clip, { width: size, height: size, borderRadius: size / 2 }]}>
        {/* Kuglens krop: mættet foroven, næsten væk forneden — som belyst
            ovenfra. Uden det bliver den en flad skive. */}
        <Svg width={size} height={size} style={StyleSheet.absoluteFill}>
          <Defs>
            <RadialGradient id="orbBody" cx="50%" cy="18%" r="88%">
              <Stop offset="0" stopColor={accent} stopOpacity="0.98" />
              <Stop offset="0.52" stopColor={accent} stopOpacity="0.62" />
              <Stop offset="1" stopColor={accent} stopOpacity={String(bodyFloor)} />
            </RadialGradient>
          </Defs>
          <Circle cx={size / 2} cy={size / 2} r={size / 2} fill="url(#orbBody)" />
        </Svg>

        <Animated.View
          style={[StyleSheet.absoluteFill, { transform: [{ translateY: up }, { translateX: sway }] }]}
          pointerEvents="none"
        >
          <Svg width={size} height={size}>
            {/* Gradienten SKAL stå i det samme <Svg> som den bruges i. Hvert
                <Svg> er sit eget dokument, så en id fra et andet peger på
                ingenting — og så tegnes figuren sort. */}
            <Defs>
              <RadialGradient id="veilA" cx="50%" cy="50%" r="50%">
                <Stop offset="0" stopColor={veil} stopOpacity={String(veilTop)} />
                <Stop offset="0.6" stopColor={veil} stopOpacity={String(veilMid)} />
                <Stop offset="1" stopColor={veil} stopOpacity="0" />
              </RadialGradient>
            </Defs>
            <Ellipse cx={size * 0.42} cy={size * 0.5} rx={size * 0.52} ry={size * 0.26} fill="url(#veilA)" />
          </Svg>
        </Animated.View>

        <Animated.View
          style={[StyleSheet.absoluteFill, { transform: [{ translateY: down }] }]}
          pointerEvents="none"
        >
          <Svg width={size} height={size}>
            <Defs>
              <RadialGradient id="veilB" cx="50%" cy="50%" r="50%">
                <Stop offset="0" stopColor={veil} stopOpacity={String(veilTop * 0.82)} />
                <Stop offset="0.62" stopColor={veil} stopOpacity={String(veilMid * 0.78)} />
                <Stop offset="1" stopColor={veil} stopOpacity="0" />
              </RadialGradient>
            </Defs>
            <Ellipse cx={size * 0.6} cy={size * 0.5} rx={size * 0.46} ry={size * 0.2} fill="url(#veilB)" />
          </Svg>
        </Animated.View>
      </View>
    </Animated.View>
  )
}

const styles = StyleSheet.create({
  wrap: { alignItems: 'center', justifyContent: 'center' },
  // Klipningen er dét der holder de drivende lag inde i kuglen. Uden den
  // stikker de ud som firkanter.
  clip: { overflow: 'hidden' },
})
