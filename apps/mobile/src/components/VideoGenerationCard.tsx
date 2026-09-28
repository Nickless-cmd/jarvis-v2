import { useEffect, useRef, useState } from 'react'
import { Animated, Easing, StyleSheet, Text, View } from 'react-native'
import { useStyles, type Theme } from '../theme/ThemeContext'
import { useReducedMotion } from '../lib/useReducedMotion'

/**
 * Video bliver til: et spor der løber, og et ur.
 *
 * ## Hvorfor den ikke er prik-gitteret
 *
 * `ImageGenerationCard` viser et 16×16 gitter mens et billede laves. Det
 * arbejde er målt til ~8 s. `pollinations_video` bruger 39 s på pipelinen og
 * har op til **600 s** timeout.
 *
 * Et gitter der pulser i ti minutter siger ikke noget andet efter otte
 * minutter end efter ét — og det er præcis dér man tror turen er hængt og
 * lukker appen. Uret er derfor ikke pynt: det er den eneste oplysning der
 * ændrer sig, og den eneste måde at skelne «arbejder stadig» fra «gået i stå».
 *
 * Ingen procent. Backend har ingen, og et falsk fremskridt er værre end
 * ingen — derfor løber sporet i ring frem for at fyldes op.
 *
 * «Reducer bevægelse» respekteres: sporet står stille, men uret tæller videre.
 * Det er hele pointen med uret — det er information, ikke bevægelse.
 */
export function VideoGenerationCard() {
  const styles = useStyles(makeStyles)
  const reducedMotion = useReducedMotion()
  const loeb = useRef(new Animated.Value(0)).current
  const [sekunder, setSekunder] = useState(0)
  const [bredde, setBredde] = useState(0)

  useEffect(() => {
    const id = setInterval(() => setSekunder((n) => n + 1), 1000)
    return () => clearInterval(id)
  }, [])

  useEffect(() => {
    if (reducedMotion || bredde <= 0) {
      loeb.stopAnimation()
      loeb.setValue(0)
      return
    }
    loeb.setValue(0)
    const animation = Animated.loop(Animated.timing(loeb, {
      toValue: 1, duration: 1800, easing: Easing.inOut(Easing.ease), useNativeDriver: true,
    }))
    animation.start()
    return () => animation.stop()
  }, [loeb, bredde, reducedMotion])

  // -bredde → +bredde: hovedet er helt ude af sporet i begge yderpunkter, så
  // loop-resettet ikke ses som et hak. Samme greb som `BilledePlads`.
  const translateX = bredde > 0
    ? loeb.interpolate({ inputRange: [0, 1], outputRange: [-bredde, bredde] })
    : 0

  const ur = sekunder < 60
    ? `${sekunder} s`
    : `${Math.floor(sekunder / 60)}:${String(sekunder % 60).padStart(2, '0')}`

  return (
    <View testID="video-generation-progress" accessibilityRole="progressbar"
      accessibilityLabel="Genererer video" style={styles.wrap}>
      <Text style={styles.label}>
        Genererer video… <Text testID="video-generation-ur" style={styles.ur}>{ur}</Text>
      </Text>
      <View
        style={styles.spor}
        onLayout={(e) => {
          const b = Math.round(e.nativeEvent.layout.width)
          if (b > 0 && b !== bredde) setBredde(b)
        }}
      >
        <Animated.View style={[styles.hoved, { width: Math.max(1, bredde * 0.38), transform: [{ translateX }] }]} />
      </View>
    </View>
  )
}

const makeStyles = (tokens: Theme) => StyleSheet.create({
  wrap: {
    width: 280, alignSelf: 'flex-start',
    marginHorizontal: tokens.spacing.lg, marginVertical: tokens.spacing.md,
    gap: tokens.spacing.md,
  },
  label: { color: tokens.color.fg2, fontSize: 14 },
  ur: { color: tokens.color.fg3, fontVariant: ['tabular-nums'] },
  spor: { height: 4, borderRadius: 2, backgroundColor: tokens.color.bg3, overflow: 'hidden' },
  hoved: { height: 4, borderRadius: 2, backgroundColor: tokens.color.accent },
})
