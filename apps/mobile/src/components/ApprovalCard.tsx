import { Pressable, StyleSheet, Text, View } from 'react-native'
import { tokens } from '../theme/tokens'

export interface ApprovalViewModel {
  approvalId: string
  tool: string
  message: string
  detail?: string
}

export function ApprovalCard({
  approval,
  onApprove,
  onDeny
}: {
  approval: ApprovalViewModel
  onApprove: () => void
  onDeny: () => void
}) {
  return (
    <View style={styles.root}>
      <Text style={styles.title}>{approval.tool || 'Approval required'}</Text>
      <Text style={styles.message}>{approval.message}</Text>
      {approval.detail ? <Text style={styles.detail}>{approval.detail}</Text> : null}
      <View style={styles.actions}>
        <Pressable accessibilityRole="button" onPress={onDeny} style={[styles.button, styles.deny]}>
          <Text style={styles.buttonText}>Afvis</Text>
        </Pressable>
        <Pressable
          accessibilityRole="button"
          onPress={onApprove}
          style={[styles.button, styles.allow]}
        >
          <Text style={styles.allowText}>Tillad</Text>
        </Pressable>
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  root: {
    margin: tokens.spacing.md,
    padding: tokens.spacing.md,
    borderRadius: tokens.radius.md,
    borderWidth: 1,
    borderColor: tokens.color.warn,
    backgroundColor: tokens.color.bg1
  },
  title: {
    color: tokens.color.fg1,
    fontWeight: '700',
    marginBottom: tokens.spacing.xs
  },
  message: {
    color: tokens.color.fg2
  },
  detail: {
    color: tokens.color.fg3,
    marginTop: tokens.spacing.sm
  },
  actions: {
    flexDirection: 'row',
    gap: tokens.spacing.sm,
    marginTop: tokens.spacing.md
  },
  button: {
    flex: 1,
    alignItems: 'center',
    padding: tokens.spacing.md,
    borderRadius: tokens.radius.md
  },
  deny: {
    backgroundColor: tokens.color.bg3
  },
  allow: {
    backgroundColor: tokens.color.accent
  },
  buttonText: {
    color: tokens.color.fg1,
    fontWeight: '700'
  },
  allowText: {
    color: tokens.color.bg0,
    fontWeight: '700'
  }
})
