import { Pressable, StyleSheet, Text, View } from 'react-native'
import { ChevronDown, ChevronRight } from 'lucide-react-native'
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
  const tekst = live ? 'Working…' : label
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
      {open
        ? <ChevronDown size={18} color={tokens.color.fg3} strokeWidth={1.8} />
        : <ChevronRight size={18} color={tokens.color.fg3} strokeWidth={1.8} />}
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
  tekst: { flex: 0, flexShrink: 1, minWidth: 0 },
  label: { color: tokens.color.fg2, fontSize: 14, fontWeight: '400' },
})
