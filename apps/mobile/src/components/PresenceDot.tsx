import { useEffect, useRef } from 'react'
import { Animated, Easing, Pressable, StyleSheet, Text, View } from 'react-native'
import { describePresence, type Presence } from '../lib/companionClient'
import { useReducedMotion } from '../lib/useReducedMotion'
import { tokens } from '../theme/tokens'

/**
 * Livstegn — «han er her», også mellem svar.
 *
 * Jarvis' eget ønske, og hans egen betingelse: IKKE en statisk online-prik der
 * lyver. Derfor har prikken fire udseender, ét pr. sandhed serveren kan levere:
 *
 *   arbejder — grøn og ÅNDENDE. Der sker noget lige nu.
 *   vågen    — grøn og stille. Hjertet slår, men han laver ikke noget.
 *   stille   — dæmpet. Hjertet slår ikke for tiden.
 *   ved ikke — hul ring. Vi kunne ikke se ham, og så siger vi DET.
 *
 * Den hule ring er den vigtigste. En netværksfejl er præcis det øjeblik hvor
 * fristelsen til at vise noget levende er størst — og hvor det ville være en
 * løgn.
 *
 * Åndedrættet kører KUN i «arbejder». En prik der pulser når han sover, ville
 * sige det samme som den gamle grønne: at der altid sker noget.
 */
export function PresenceDot({ presence, onPress }: {
  presence: Presence
  onPress?: () => void
}) {
  const pulse = useRef(new Animated.Value(0)).current
  const reduced = useReducedMotion()
  const working = presence.state === 'working'

  useEffect(() => {
    if (!working || reduced) {
      pulse.setValue(0)
      return
    }
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(pulse, { toValue: 1, duration: 1100, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
        Animated.timing(pulse, { toValue: 0, duration: 1100, easing: Easing.inOut(Easing.ease), useNativeDriver: true })
      ])
    )
    loop.start()
    return () => loop.stop()
  }, [working, reduced, pulse])

  const scale = pulse.interpolate({ inputRange: [0, 1], outputRange: [1, 1.35] })
  const opacity = pulse.interpolate({ inputRange: [0, 1], outputRange: [1, 0.55] })

  return (
    <Pressable
      testID="presence-dot"
      accessibilityRole={onPress ? 'button' : 'text'}
      accessibilityLabel={`Jarvis er ${describePresence(presence)}`}
      onPress={onPress}
      hitSlop={10}
      style={styles.row}
    >
      <Animated.View
        style={[
          styles.dot,
          STATE_STYLE[presence.state] ?? STATE_STYLE.unknown,
          working ? { transform: [{ scale }], opacity } : null
        ]}
      />
      <Text style={styles.label} numberOfLines={1}>{describePresence(presence)}</Text>
    </Pressable>
  )
}

const STATE_STYLE = StyleSheet.create({
  working: { backgroundColor: tokens.color.accent, borderColor: tokens.color.accent },
  awake: { backgroundColor: tokens.color.accent, borderColor: tokens.color.accent },
  quiet: { backgroundColor: tokens.color.fg3, borderColor: tokens.color.fg3 },
  // Hul ring: vi ved det ikke, og prikken skal ikke ligne at vi gør.
  unknown: { backgroundColor: 'transparent', borderColor: tokens.color.fg3 }
})

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', gap: 7 },
  dot: { width: 8, height: 8, borderRadius: 4, borderWidth: 1.5 },
  label: { color: tokens.color.fg3, fontSize: 12.5, flexShrink: 1 }
})
