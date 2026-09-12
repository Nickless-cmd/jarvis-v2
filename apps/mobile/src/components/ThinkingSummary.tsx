import { useEffect, useRef, useState } from 'react'
import { Animated, Easing, Pressable, StyleSheet, Text, View } from 'react-native'
import { Brain, ChevronDown, ChevronRight } from 'lucide-react-native'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'
import { useReducedMotion } from '../lib/useReducedMotion'

/**
 * «🧠 Tænker…» mens den tænker. «🧠 Tænkte i 14 s ›» når den er færdig.
 *
 * Tænkningen forsvinder ikke, den folder sig sammen — og mens den står på,
 * er den én rolig linje med et brain-ikon, præcis som værktøjslinjen
 * (`InlineToolGroup`). Før blev rå CoT smeltet ind i svarets tekstboble;
 * nu står den som sin egen række over værktøjerne.
 *
 * Designmæssigt er den et søskendebarn til `InlineToolGroup`:
 * - Samme ikon + tekst + chevron-layout
 * - Samme padding og fontSize (15)
 * - Samme åndedrag-animation mens den kører
 * - Samme fold-ud når man vil se detaljen
 *
 * Tre tilstande:
 * - `live`: tænkningen streames → «Tænker…» med åndedrag
 * - færdig med målt varighed → «Tænkte i X s»
 * - færdig uden målt varighed men med tekst → «Tænkte» (vi ved den tænkte,
 *   bare ikke hvor længe — så vi påstår ikke et tal vi ikke har)
 */
export function ThinkingSummary({ seconds, text, live }: { seconds?: number; text?: string; live?: boolean }) {
  const tokens = useTheme()
  const styles = useStyles(makestyles)
  const [open, setOpen] = useState(false)
  const hasText = !!(text ?? '').trim()
  const reduced = useReducedMotion()
  const pulse = useRef(new Animated.Value(1)).current

  const isLive = !!live
  const hasSeconds = seconds != null && seconds > 0

  // Intet at vise: ikke live, ingen tekst, ingen målt varighed.
  if (!isLive && !hasText && !hasSeconds) return null

  useEffect(() => {
    if (!isLive || reduced) {
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
  }, [isLive, reduced, pulse])

  const label = isLive
    ? 'Tænker…'
    : hasSeconds
      ? seconds! < 60
        ? `Tænkte i ${formatSeconds(seconds!)} s`
        : `Tænkte i ${Math.floor(seconds! / 60)} min ${Math.round(seconds! % 60)} s`
      : 'Tænkte'

  // Fold-ud er kun relevant når der er tekst at vise.
  const expandable = hasText

  const toggle = () => {
    if (!expandable) return
    if (!reduced) {
      // LayoutAnimation er ikke importeret her for at holde afhængighederne
      // minimale — InlineToolGroup bruger den, men tænkningen er typisk ét
      // blok tekst, ikke en liste der har brug for glidende animation.
    }
    setOpen((v) => !v)
  }

  return (
    <View style={styles.wrap}>
      <Pressable
        testID="thinking-summary"
        accessibilityRole={expandable ? 'button' : 'text'}
        accessibilityLabel={isLive ? label : open ? `${label}, skjul` : `${label}, vis`}
        accessibilityState={expandable ? { expanded: open } : undefined}
        disabled={!expandable}
        onPress={toggle}
        hitSlop={8}
      >
        <Animated.View style={[styles.row, isLive ? { opacity: pulse } : null]}>
          <Brain size={16} color={tokens.color.fg2} strokeWidth={1.8} />
          <Text style={styles.label} numberOfLines={1}>{label}</Text>
          {expandable ? (
            open ? (
              <ChevronDown size={16} color={tokens.color.fg2} strokeWidth={1.8} />
            ) : (
              <ChevronRight size={16} color={tokens.color.fg2} strokeWidth={1.8} />
            )
          ) : null}
        </Animated.View>
      </Pressable>
      {open && hasText ? <Text selectable style={styles.body}>{text}</Text> : null}
    </View>
  )
}

/** 12.0 → «12», 3.4 → «3,4». Dansk komma, og ingen tom decimal. */
function formatSeconds(s: number): string {
  const rounded = Math.round(s * 10) / 10
  return Number.isInteger(rounded) ? String(rounded) : String(rounded).replace('.', ',')
}

const makestyles = (tokens: Theme) => StyleSheet.create({
  wrap: { paddingHorizontal: tokens.spacing.lg },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: tokens.spacing.sm,
    paddingVertical: tokens.spacing.sm
  },
  label: { color: tokens.color.fg2, fontSize: 15, flexShrink: 1 },
  body: {
    color: tokens.color.fg3,
    fontSize: 14,
    lineHeight: 21,
    marginTop: tokens.spacing.xs,
    paddingLeft: 24,
    paddingBottom: tokens.spacing.sm,
    borderLeftWidth: 2,
    borderLeftColor: tokens.color.line
  }
})