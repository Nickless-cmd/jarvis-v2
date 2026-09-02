import { Pressable, StyleSheet, Text, View } from 'react-native'
import { tokens } from '../theme/tokens'

export function ErrorBanner({
  title,
  detail,
  actionLabel,
  onAction,
  onDismiss
}: {
  title: string
  detail?: string
  actionLabel?: string
  onAction?: () => void
  /** Luk-knap (×). Når sat, vises en virkende dismiss. */
  onDismiss?: () => void
}) {
  return (
    <View style={styles.root}>
      <View style={styles.copy}>
        <Text style={styles.title}>{title}</Text>
        {detail ? <Text style={styles.detail}>{detail}</Text> : null}
      </View>
      {actionLabel && onAction ? (
        <Pressable accessibilityRole="button" onPress={onAction} style={styles.action}>
          <Text style={styles.actionText}>{actionLabel}</Text>
        </Pressable>
      ) : null}
      {onDismiss ? (
        <Pressable accessibilityRole="button" accessibilityLabel="luk" onPress={onDismiss} style={styles.dismiss}>
          <Text style={styles.dismissText}>×</Text>
        </Pressable>
      ) : null}
    </View>
  )
}

const styles = StyleSheet.create({
  root: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: tokens.spacing.md,
    paddingHorizontal: tokens.spacing.md,
    paddingVertical: tokens.spacing.sm,
    borderTopColor: tokens.color.line,
    borderTopWidth: 1,
    backgroundColor: tokens.color.bg1
  },
  copy: {
    flex: 1
  },
  title: {
    color: tokens.color.fg1,
    fontWeight: '700'
  },
  detail: {
    color: tokens.color.fg3,
    marginTop: 2
  },
  action: {
    minHeight: 38,
    minWidth: 72,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: tokens.radius.md,
    borderColor: tokens.color.accent,
    borderWidth: 1
  },
  actionText: {
    color: tokens.color.accent,
    fontWeight: '700'
  },
  dismiss: {
    minHeight: 38,
    minWidth: 38,
    alignItems: 'center',
    justifyContent: 'center'
  },
  dismissText: {
    color: tokens.color.fg3,
    fontSize: 22,
    lineHeight: 24
  }
})
