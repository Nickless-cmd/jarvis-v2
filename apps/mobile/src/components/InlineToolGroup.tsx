import { useEffect, useRef, useState } from 'react'
import { Animated, Easing, LayoutAnimation, Pressable, StyleSheet, Text, View } from 'react-native'
import { ChevronDown, ChevronRight, Code2 } from 'lucide-react-native'
import { tokens } from '../theme/tokens'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'
import { useReducedMotion } from '../lib/useReducedMotion'
import { summarizeRound, type ToolItem } from '../lib/toolGroup'

interface Props {
  items: ToolItem[]
}

/**
 * Én sammenfoldet linje for en HEL runde værktøjsarbejde.
 *
 * Codex-appen viser fortælling → én linje → fortælling. Ikke ti linjer i træk.
 * Linjen ændrer sig mens runden kører («Læser 3 filer…») og lander på sin
 * datid når den er færdig («Læste 3 filer»). Trykker man, folder den ud og
 * viser hvert enkelt kald — detaljen er der, den fylder bare ikke tråden.
 *
 * Mens runden kører, ånder linjen; når den er færdig, står den stille.
 * Bevægelse betyder «i gang». En linje der pulser efter den er færdig, lyver.
 */
export function InlineToolGroup({ items }: Props) {
  const tokens = useTheme()
  const styles = useStyles(makestyles)
  const [open, setOpen] = useState(false)
  const pulse = useRef(new Animated.Value(1)).current
  const reduced = useReducedMotion()
  const running = items.some((i) => i.running)
  const summary = summarizeRound(items)

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

  if (!summary) return null

  // Ét kald har ingen detalje at folde ud — så er chevronen et tomt løfte.
  const expandable = items.length > 1

  const toggle = () => {
    if (!expandable) return
    if (!reduced) LayoutAnimation.configureNext(LayoutAnimation.Presets.easeInEaseOut)
    setOpen((v) => !v)
  }

  return (
    <View style={styles.wrap}>
      <Pressable
        accessibilityRole={expandable ? 'button' : 'text'}
        accessibilityLabel={summary}
        accessibilityState={expandable ? { expanded: open } : undefined}
        onPress={toggle}
        testID="tool-group"
      >
        <Animated.View style={[styles.row, running ? { opacity: pulse } : null]}>
          <Code2 size={16} color={tokens.color.fg2} strokeWidth={1.8} />
          <Text style={styles.summary} numberOfLines={1}>
            {summary}
          </Text>
          {expandable ? (
            open ? (
              <ChevronDown size={16} color={tokens.color.fg2} strokeWidth={1.8} />
            ) : (
              <ChevronRight size={16} color={tokens.color.fg2} strokeWidth={1.8} />
            )
          ) : null}
        </Animated.View>
      </Pressable>

      {open ? (
        <View style={styles.details} testID="tool-group-details">
          {items.map((item, i) => (
            <Text key={`${item.label}-${i}`} style={styles.detail} numberOfLines={1}>
              {item.label}
            </Text>
          ))}
        </View>
      ) : null}
    </View>
  )
}

const makestyles = (tokens: Theme) => StyleSheet.create({
  wrap: { paddingHorizontal: tokens.spacing.lg },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: tokens.spacing.sm,
    paddingVertical: tokens.spacing.sm
  },
  summary: { color: tokens.color.fg2, fontSize: 15, flexShrink: 1 },
  details: {
    paddingLeft: 24,
    paddingBottom: tokens.spacing.sm,
    gap: 6
  },
  detail: { color: tokens.color.fg3, fontSize: 14 }
})
