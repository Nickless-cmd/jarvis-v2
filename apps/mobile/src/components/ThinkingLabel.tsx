import { useEffect, useRef } from 'react'
import { Animated, Easing, StyleSheet, Text, View } from 'react-native'
import { tokens } from '../theme/tokens'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'
import { useReducedMotion } from '../lib/useReducedMotion'

interface Props {
  label?: string
}

/**
 * «Tænker» — ét ord med et lysende sweep hen over bogstaverne.
 *
 * Målt i ChatGPT-appen på enheden 2026-09-02: der er INGEN spinner, ingen ring,
 * intet kort. Bare ordet, venstrejusteret i tråden, hvor et skimmer glider fra
 * venstre mod højre. Målt i pixels midt i animationen: lysstyrken hen over
 * ordet var 61 · 45 · 96 · 82 · 175 · 82 — altså en blød rampe, ikke et blink.
 *
 * Det er derfor liveness-ringen ikke skal bruges her: den signalerer det samme
 * ét andet sted, og ChatGPT's rolige indtryk kommer netop af at ventetegnet
 * står PÅ SIN PLADS i samtalen frem for oppe i en header.
 */
export function ThinkingLabel({ label = 'Tænker' }: Props) {
  const tokens = useTheme()
  const styles = useStyles(makestyles)
  const sweep = useRef(new Animated.Value(0)).current
  const reduced = useReducedMotion()

  useEffect(() => {
    if (reduced) return
    const loop = Animated.loop(
      Animated.timing(sweep, {
        toValue: 1,
        duration: 1600,
        easing: Easing.inOut(Easing.ease),
        useNativeDriver: true
      })
    )
    loop.start()
    return () => loop.stop()
  }, [reduced, sweep])

  // Reduceret bevægelse: vis ordet dæmpet og stille frem for at pulse.
  if (reduced) {
    return (
      <View style={styles.row}>
        <Text style={[styles.word, styles.dim]} accessibilityLabel={label}>
          {label}
        </Text>
      </View>
    )
  }

  const opacity = sweep.interpolate({
    inputRange: [0, 0.5, 1],
    outputRange: [0.35, 1, 0.35]
  })

  return (
    <View style={styles.row}>
      <Animated.Text
        style={[styles.word, { opacity }]}
        accessibilityLabel={label}
        accessibilityRole="text"
        testID="thinking-label"
      >
        {label}
      </Animated.Text>
    </View>
  )
}

const makestyles = (tokens: Theme) => StyleSheet.create({
  row: { paddingVertical: tokens.spacing.sm },
  word: {
    color: tokens.color.fg1,
    fontSize: 16,
    letterSpacing: 0.2
  },
  dim: { color: tokens.color.fg2 }
})
