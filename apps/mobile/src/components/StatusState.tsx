import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'

export function StatusState({
  title,
  detail,
  loading = false,
  actionLabel,
  onAction
}: {
  title: string
  detail?: string
  loading?: boolean
  actionLabel?: string
  onAction?: () => void
}) {
  const tokens = useTheme()
  const styles = useStyles(makes)
  return (
    <View style={styles.wrap}>
      {loading ? <ActivityIndicator color={tokens.color.accent} /> : null}
      <Text style={styles.title}>{title}</Text>
      {detail ? <Text style={styles.detail}>{detail}</Text> : null}
      {actionLabel && onAction ? (
        <Pressable accessibilityRole="button" onPress={onAction} style={styles.button}>
          <Text style={styles.buttonText}>{actionLabel}</Text>
        </Pressable>
      ) : null}
    </View>
  )
}

const makes = (tokens: Theme) => StyleSheet.create({
  wrap: { flex: 1, minHeight: 180, alignItems: 'center', justifyContent: 'center', gap: tokens.spacing.sm, padding: tokens.spacing.xl },
  title: { color: tokens.color.fg1, fontSize: 16, fontWeight: '700', textAlign: 'center' },
  detail: { color: tokens.color.fg3, fontSize: 13, lineHeight: 19, textAlign: 'center' },
  button: {
    marginTop: tokens.spacing.sm,
    minHeight: 40,
    paddingHorizontal: tokens.spacing.lg,
    borderRadius: tokens.radius.md,
    borderWidth: 1,
    borderColor: tokens.color.line,
    alignItems: 'center',
    justifyContent: 'center'
  },
  buttonText: { color: tokens.color.fg1, fontWeight: '700' }
})
