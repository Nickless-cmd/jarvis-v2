import { useEffect, useRef } from 'react'
import { Animated, Easing, StyleSheet, View } from 'react-native'
import { useReducedMotion } from '../lib/useReducedMotion'

/**
 * Tre prikker der ruller — Claude Desktops `timeline-quiet-dots`, portet til
 * React Native (19/9-2026). Samme tal som desk og som deres CSS:
 *
 *   3 dp, 3,5 dp mellemrum, 1,9 s pr. bølge på cubic-bezier(.4,0,.2,1),
 *   150 ms forskudt pr. prik.
 *   0-8 %   usynlig, 2 dp nede
 *   22 %    fuld, 2,5 dp oppe
 *   36-70 % fuld, i hvile
 *   90-100 % usynlig
 *
 * Reduceret bevægelse: prikkerne står stille og fulde (kildens regel).
 */
const BOELGE_MS = 1900
const FORSKYDNING_MS = 150
const TRIN = [0, 0.08, 0.22, 0.36, 0.7, 0.9, 1]

function Prik({ nr, farve }: { nr: number; farve: string }) {
  const reduced = useReducedMotion()
  const t = useRef(new Animated.Value(0)).current

  useEffect(() => {
    if (reduced) return
    let loop: Animated.CompositeAnimation | null = null
    const start = setTimeout(() => {
      loop = Animated.loop(
        Animated.timing(t, {
          toValue: 1,
          duration: BOELGE_MS,
          easing: Easing.bezier(0.4, 0, 0.2, 1),
          useNativeDriver: true,
        }),
      )
      loop.start()
    }, nr * FORSKYDNING_MS)
    return () => { clearTimeout(start); loop?.stop() }
  }, [reduced, nr, t])

  const stil = reduced
    ? { opacity: 1 }
    : {
        opacity: t.interpolate({ inputRange: TRIN, outputRange: [0, 0, 1, 1, 1, 0, 0] }),
        transform: [{ translateY: t.interpolate({ inputRange: TRIN, outputRange: [2, 2, -2.5, 0, 0, 0, 0] }) }],
      }
  return <Animated.View style={[styles.prik, { backgroundColor: farve }, stil]} />
}

export function Prikker({ farve }: { farve: string }) {
  return (
    <View style={styles.raekke} testID="prikker" accessibilityElementsHidden importantForAccessibility="no-hide-descendants">
      <Prik nr={0} farve={farve} />
      <Prik nr={1} farve={farve} />
      <Prik nr={2} farve={farve} />
    </View>
  )
}

const styles = StyleSheet.create({
  // top: .26em i kilden — prikkerne sidder på grundlinjen, ikke midt i linjen.
  raekke: { flexDirection: 'row', gap: 3.5, alignItems: 'center', top: 4 },
  prik: { width: 3, height: 3, borderRadius: 1.5 },
})
