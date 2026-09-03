import { useState } from 'react'
import { Pressable, StyleSheet, Text, View } from 'react-native'
import { ChevronDown, ChevronRight } from 'lucide-react-native'
import { tokens } from '../theme/tokens'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'

/**
 * «Tænkte i 14 s ›» — tænkningen forsvinder ikke, den folder sig sammen.
 *
 * Det var den detalje i ChatGPT-appen der overraskede mest: når tænkningen er
 * FÆRDIG, bliver den ikke slettet. Den bliver til én rolig linje med en chevron,
 * som man kan åbne hvis man vil vide hvad der foregik. Vi viste «Tænker» live og
 * derefter ingenting — og dermed forsvandt det eneste spor af, at han faktisk
 * havde overvejet noget.
 *
 * Linjen vises kun når serveren MÅLTE en varighed. Uden tal skriver vi ikke
 * «Tænkte» — så ville vi påstå noget vi ikke har målt.
 */
export function ThinkingSummary({ seconds, text }: { seconds?: number; text?: string }) {
  const tokens = useTheme()
  const styles = useStyles(makestyles)
  const [open, setOpen] = useState(false)
  const hasText = !!(text ?? '').trim()

  if (seconds == null || seconds <= 0) return null

  const label = seconds < 60
    ? `Tænkte i ${formatSeconds(seconds)} s`
    : `Tænkte i ${Math.floor(seconds / 60)} min ${Math.round(seconds % 60)} s`

  return (
    <View style={styles.wrap}>
      <Pressable
        testID="thinking-summary"
        accessibilityRole="button"
        accessibilityLabel={open ? `${label}, skjul` : `${label}, vis`}
        disabled={!hasText}
        onPress={() => setOpen((v) => !v)}
        hitSlop={8}
        style={({ pressed }) => [styles.row, pressed && styles.pressed]}
      >
        <Text style={styles.label}>{label}</Text>
        {hasText ? (
          open ? (
            <ChevronDown size={14} color={tokens.color.fg3} strokeWidth={2} />
          ) : (
            <ChevronRight size={14} color={tokens.color.fg3} strokeWidth={2} />
          )
        ) : null}
      </Pressable>
      {open && hasText ? <Text style={styles.body}>{text}</Text> : null}
    </View>
  )
}

/** 12.0 → «12», 3.4 → «3,4». Dansk komma, og ingen tom decimal. */
function formatSeconds(s: number): string {
  const rounded = Math.round(s * 10) / 10
  return Number.isInteger(rounded) ? String(rounded) : String(rounded).replace('.', ',')
}

const makestyles = (tokens: Theme) => StyleSheet.create({
  wrap: { marginBottom: tokens.spacing.sm },
  row: { flexDirection: 'row', alignItems: 'center', gap: 5 },
  label: { color: tokens.color.fg3, fontSize: 13.5 },
  body: {
    color: tokens.color.fg2,
    fontSize: 14,
    lineHeight: 21,
    marginTop: tokens.spacing.sm,
    paddingLeft: tokens.spacing.sm,
    borderLeftWidth: 2,
    borderLeftColor: tokens.color.line
  },
  pressed: { opacity: 0.6 }
})
