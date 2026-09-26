import { useEffect, useRef } from 'react'
import { Animated, Easing, Pressable, StyleSheet, Text, View } from 'react-native'
import { ChevronDown, ChevronRight } from 'lucide-react-native'
import { useReducedMotion } from '../lib/useReducedMotion'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'
import { GlidendeTekst } from './GlidendeTekst'

/** Turens arbejdsdør. Svaret ligger udenfor og bliver altid synligt. */
export function TurnHeader({
  label, live, open, onToggle,
}: {
  label: string
  live: boolean
  open: boolean
  onToggle: () => void
}) {
  const tokens = useTheme()
  const styles = useStyles(makestyles)
  const reduced = useReducedMotion()
  const caretLight = useRef(new Animated.Value(1)).current
  const tekst = live ? 'Working…' : label
  useEffect(() => {
    if (!live || reduced) {
      caretLight.stopAnimation()
      caretLight.setValue(1)
      return
    }
    const loop = Animated.loop(Animated.sequence([
      Animated.timing(caretLight, { toValue: 0.6, duration: 1125, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
      Animated.timing(caretLight, { toValue: 1, duration: 1125, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
    ]))
    loop.start()
    return () => loop.stop()
  }, [caretLight, live, reduced])
  return (
    <Pressable
      testID="turn-header"
      accessibilityRole="button"
      accessibilityLabel={`${tekst}, ${open ? 'skjul' : 'vis'} arbejdet`}
      accessibilityState={{ expanded: open }}
      onPress={onToggle}
      style={styles.row}
    >
      <View style={styles.tekst}>
        {live
          ? <GlidendeTekst text={tekst} aktiv style={styles.label} numberOfLines={1} />
          : <Text style={styles.label} numberOfLines={1}>{tekst}</Text>}
      </View>
      <Animated.View style={{ opacity: caretLight }}>
        {open
          ? <ChevronDown size={18} color={tokens.color.fg3} strokeWidth={1.8} />
          : <ChevronRight size={18} color={tokens.color.fg3} strokeWidth={1.8} />}
      </Animated.View>
    </Pressable>
  )
}

const makestyles = (tokens: Theme) => StyleSheet.create({
  row: {
    marginHorizontal: tokens.spacing.lg,
    paddingVertical: 9,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: tokens.color.line,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  tekst: { flexShrink: 1, minWidth: 0 },
  label: { color: tokens.color.fg2, fontSize: 14, fontWeight: '400' },
})
