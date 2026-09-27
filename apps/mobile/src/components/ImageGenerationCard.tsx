import { useEffect, useRef } from 'react'
import { Animated, Easing, StyleSheet, Text, View } from 'react-native'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'
import { useReducedMotion } from '../lib/useReducedMotion'

/** Værktøjet leverer ingen procent, så animationen viser aktivitet uden et estimat. */
export function ImageGenerationCard() {
  const tokens = useTheme()
  const styles = useStyles(makeStyles)
  const reducedMotion = useReducedMotion()
  const puls = useRef(new Animated.Value(0.4)).current

  useEffect(() => {
    if (reducedMotion) {
      puls.setValue(0.7)
      return
    }
    const animation = Animated.loop(Animated.sequence([
      Animated.timing(puls, { toValue: 1, duration: 1500, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
      Animated.timing(puls, { toValue: 0.4, duration: 1500, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
    ]))
    animation.start()
    return () => animation.stop()
  }, [puls, reducedMotion])

  return (
    <View testID="image-generation-progress" accessibilityRole="progressbar"
      accessibilityLabel="Genererer billede" style={styles.wrap}>
      <Text style={styles.label}>Genererer billede…</Text>
      <Animated.View style={[styles.grid, { opacity: puls }]}>
        {Array.from({ length: 16 * 16 }, (_, index) => {
          const x = index % 16
          const y = Math.floor(index / 16)
          const distance = Math.hypot(x - 7.5, y - 7.5)
          return <View key={index} style={[styles.dot, {
            backgroundColor: tokens.color.accent,
            opacity: Math.max(0.12, 0.8 - distance * 0.08),
          }]} />
        })}
      </Animated.View>
    </View>
  )
}

const makeStyles = (tokens: Theme) => StyleSheet.create({
  wrap: { width: 280, alignSelf: 'flex-start', marginHorizontal: tokens.spacing.lg,
    marginVertical: tokens.spacing.md, gap: tokens.spacing.lg },
  label: { color: tokens.color.fg2, fontSize: 14 },
  grid: { width: 256, height: 256, flexDirection: 'row', flexWrap: 'wrap',
    alignItems: 'center', justifyContent: 'space-around' },
  dot: { width: 4, height: 4, borderRadius: 2 },
})
