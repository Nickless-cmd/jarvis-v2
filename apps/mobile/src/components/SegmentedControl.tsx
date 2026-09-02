import { useMemo } from 'react'
import { Pressable, StyleSheet, Text, View } from 'react-native'
import { tokens } from '../theme/tokens'

export interface SegmentOption<T extends string> {
  value: T
  label: string
  /** Vises som en lille prik på segmentet — fx ventende godkendelser. */
  badge?: boolean
}

interface Props<T extends string> {
  options: SegmentOption<T>[]
  value: T
  onChange: (next: T) => void
  /** Lille variant til under-niveauet (Tasks|Approve). */
  compact?: boolean
}

/**
 * Pilleformet segmented control — ChatGPT-appens navigations-mønster.
 *
 * Bruges to steder: top-niveau (Snak|Arbejde) og inde i Arbejde
 * (Tasks|Approve). Derfor generisk over værdi-typen frem for to komponenter
 * der driver fra hinanden.
 */
export function SegmentedControl<T extends string>({ options, value, onChange, compact }: Props<T>) {
  const styles = useMemo(() => makeStyles(Boolean(compact)), [compact])
  return (
    <View style={styles.container} accessibilityRole="tablist">
      {options.map((opt) => {
        const active = opt.value === value
        return (
          <Pressable
            key={opt.value}
            accessibilityRole="tab"
            accessibilityState={{ selected: active }}
            accessibilityLabel={opt.label}
            onPress={() => onChange(opt.value)}
            style={[styles.segment, active && styles.segmentActive]}
          >
            <View style={styles.labelRow}>
              <Text style={[styles.label, active && styles.labelActive]} numberOfLines={1}>
                {opt.label}
              </Text>
              {opt.badge ? <View style={styles.badge} testID={`segment-badge-${opt.value}`} /> : null}
            </View>
          </Pressable>
        )
      })}
    </View>
  )
}

const makeStyles = (compact: boolean) =>
  StyleSheet.create({
    container: {
      flexDirection: 'row',
      // Beholderen er LYSERE end den aktive pille — målt på R2.
      backgroundColor: tokens.color.segmentTrack,
      borderRadius: tokens.radius.pill,
      padding: 3
    },
    segment: {
      flex: 1,
      paddingVertical: compact ? 5 : 7,
      paddingHorizontal: compact ? 10 : 16,
      borderRadius: tokens.radius.pill,
      alignItems: 'center',
      justifyContent: 'center'
    },
    segmentActive: {
      backgroundColor: tokens.color.segmentActive
    },
    labelRow: {
      flexDirection: 'row',
      alignItems: 'center',
      gap: 6
    },
    label: {
      color: tokens.color.fg2,
      fontSize: compact ? 13 : 14,
      fontWeight: '600'
    },
    labelActive: {
      color: tokens.color.fg1
    },
    badge: {
      width: 6,
      height: 6,
      borderRadius: 3,
      backgroundColor: tokens.color.accent
    }
  })
