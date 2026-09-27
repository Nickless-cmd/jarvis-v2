import { useEffect, useRef } from 'react'
import { Animated, Easing, StyleSheet, Text, View } from 'react-native'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'
import { useReducedMotion } from '../lib/useReducedMotion'

/** Antal prikker pr. side. 16×16 = 256 prikker i et 256 px kvadrat. */
const SIDER = 16

/**
 * Værktøjet leverer ingen procent, så animationen viser aktivitet uden et estimat.
 *
 * Prikkerne bygges som SIDER eksplicitte RÆKKER — ikke som én flad liste med
 * `flexWrap: 'wrap'`.
 *
 * Målt 27/9-2026: den flade liste blev en tynd vandret stribe på mobilen.
 * Flexbox wrapper ved CONTAINERBREDDEN, ikke ved det tilsigtede kolonnetal:
 * 16 prikker à 4 px fylder 64 px, så alle 16 kunne ligge i én række, og wrap
 * skete først ved 256/4 = 64 prikker. Resultatet var 4 rækker à 16 px høj i en
 * 256 px høj boks — og opacity-gradienten (regnet ud fra 16×16-koordinater) pegede
 * på prikker der lå helt andre steder. Desk slap for det, fordi CSS grid med
 * `repeat(16, 1fr)` TILLADER 16 kolonner. Her er rækkerne eksplicitte, så formen
 * ikke længere afhænger af containerbredden.
 */
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
        {Array.from({ length: SIDER }, (_, y) => (
          <View key={y} testID="image-generation-raekke" style={styles.raekke}>
            {Array.from({ length: SIDER }, (_, x) => (
              <View key={x} style={[styles.dot, {
                backgroundColor: tokens.color.accent,
                opacity: Math.max(0.12, 0.8 - Math.hypot(x - 7.5, y - 7.5) * 0.08),
              }]} />
            ))}
          </View>
        ))}
      </Animated.View>
    </View>
  )
}

const makeStyles = (tokens: Theme) => StyleSheet.create({
  wrap: { width: 280, alignSelf: 'flex-start', marginHorizontal: tokens.spacing.lg,
    marginVertical: tokens.spacing.md, gap: tokens.spacing.lg },
  label: { color: tokens.color.fg2, fontSize: 14 },
  // 16 lige høje bånd deler de 256 px; `space-around` giver 12 px mellem
  // prikkerne og 6 px i kanten — samme rum som desk's `repeat(16, 1fr)`.
  grid: { width: 256, height: 256 },
  raekke: { flex: 1, flexDirection: 'row', justifyContent: 'space-around', alignItems: 'center' },
  dot: { width: 4, height: 4, borderRadius: 2 },
})
