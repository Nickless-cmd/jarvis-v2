import { useEffect, useRef } from 'react'
import { Animated, Easing, Pressable, StyleSheet, Text, View } from 'react-native'
import { Code2, ChevronRight } from 'lucide-react-native'
import { tokens } from '../theme/tokens'
import { useReducedMotion } from '../lib/useReducedMotion'

interface Props {
  /** Hvad der blev gjort, i datid: «Læste db.py», «Ændrede 16 filer». */
  summary: string
  onPress?: () => void
  /** Sandt mens værktøjet stadig kører. */
  running?: boolean
}

/**
 * Et værktøjs-resultat som ÉN kompakt linje inde i samtalen.
 *
 * Målt i ChatGPT/Codex-appen 2026-09-02:
 *
 *     </> Redigerede test_push_dispatcher.py  ›
 *     </> Ændrede 16 filer  ›
 *
 * Ingen kort, ingen ramme, intet udfoldet output — bare en grå linje mellem
 * afsnittene. Det er hele grunden til at deres tråd virker rolig.
 *
 * ANIMATION: mens værktøjet KØRER, ånder linjen — samme sweep som
 * «Tænker»-labelen, så de to ventetegn taler samme sprog. Når det er færdigt,
 * står linjen helt stille. Bevægelse betyder «i gang»; ro betyder «færdig».
 * En linje der bliver ved med at pulse efter den er færdig, lyver.
 */
export function InlineToolLine({ summary, onPress, running }: Props) {
  const pulse = useRef(new Animated.Value(1)).current
  const reduced = useReducedMotion()

  useEffect(() => {
    if (!running || reduced) {
      pulse.stopAnimation()
      pulse.setValue(1)
      return
    }
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(pulse, {
          toValue: 0.4,
          duration: 800,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: true
        }),
        Animated.timing(pulse, {
          toValue: 1,
          duration: 800,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: true
        })
      ])
    )
    loop.start()
    return () => loop.stop()
  }, [running, reduced, pulse])

  const body = (
    <Animated.View style={[styles.row, running ? { opacity: pulse } : null]}>
      <Code2 size={16} color={tokens.color.fg2} strokeWidth={1.8} />
      <Text style={styles.summary} numberOfLines={1}>
        {summary}
      </Text>
      {onPress ? (
        <ChevronRight size={16} color={tokens.color.fg2} strokeWidth={1.8} />
      ) : null}
    </Animated.View>
  )

  if (!onPress) return <View testID="inline-tool-static">{body}</View>
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={summary}
      onPress={onPress}
      testID="inline-tool-line"
    >
      {body}
    </Pressable>
  )
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: tokens.spacing.sm,
    paddingVertical: tokens.spacing.sm,
    paddingHorizontal: tokens.spacing.lg
  },
  summary: {
    color: tokens.color.fg2,
    fontSize: 15,
    flexShrink: 1
  }
})
