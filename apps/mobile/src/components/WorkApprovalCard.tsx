import { Pressable, StyleSheet, Text, View } from 'react-native'
import { formatRelativeTime } from '../lib/relativeDate'
import { tokens } from '../theme/tokens'
import { approvalDetail, approvalReason, approvalTag, approvalTitle, isActionable, isToolIntent } from '../lib/mcTypes'
import type { Approval } from '../lib/mcTypes'

interface Props {
  approval: Approval
  busy?: boolean
  onApprove: (a: Approval) => void
  onSkip: (a: Approval) => void
  now?: Date
}

/**
 * Godkendelseskortet (R8-mønsteret): anledningstekst → tag + kodeblok →
 * verber i lodret stak.
 *
 * To ting adskiller det fra V1's ApprovalCard:
 *
 * 1. Det renderer BEGGE godkendelsessystemer. Felterne hedder noget
 *    forskelligt, men udtrækkes gennem mcTypes' hjælpere, så kortet ikke
 *    behøver kende forskellen.
 * 2. Et kort der ikke længere kan handles på siger det HØJT frem for at
 *    tilbyde en knap der giver 409. Det døde kort er hele grunden til at
 *    dette rum findes.
 */
export function WorkApprovalCard({ approval, busy, onApprove, onSkip, now }: Props) {
  const actionable = isActionable(approval)
  const reason = approvalReason(approval)
  const detail = approvalDetail(approval)
  const expired = approval.status === 'expired' || approval.stale

  return (
    <View style={styles.wrap}>
      {reason ? <Text style={styles.reason}>{reason}</Text> : null}

      <View style={styles.card}>
        <View style={styles.tagRow}>
          <Text style={styles.tag} numberOfLines={1}>
            {approvalTag(approval)}
          </Text>
          <View style={styles.spacer} />
          <Text style={styles.age}>{formatRelativeTime(approval.requested_at, now ?? new Date())}</Text>
        </View>

        <Text style={styles.title} numberOfLines={2}>
          {approvalTitle(approval)}
        </Text>

        {detail ? (
          <View style={styles.code}>
            <Text style={styles.codeText} numberOfLines={6}>
              {detail}
            </Text>
          </View>
        ) : null}

        {isToolIntent(approval) && approval.expires_at ? (
          <Text style={styles.meta} testID="expiry-note">
            Vindue udløber {formatRelativeTime(approval.expires_at, now ?? new Date())}
          </Text>
        ) : null}

        {actionable ? (
          <View style={styles.actions}>
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Godkend"
              accessibilityState={{ disabled: Boolean(busy) }}
              disabled={busy}
              onPress={() => onApprove(approval)}
              style={[styles.btn, styles.primary, busy && styles.btnBusy]}
            >
              <Text style={styles.primaryText}>{busy ? 'Godkender…' : 'Godkend'}</Text>
            </Pressable>
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Spring over"
              disabled={busy}
              onPress={() => onSkip(approval)}
              style={[styles.btn, styles.tertiary]}
            >
              <Text style={styles.tertiaryText}>Spring over</Text>
            </Pressable>
          </View>
        ) : (
          <Text style={styles.dead} testID="dead-note">
            {expired
              ? 'Vinduet er udløbet — den kan ikke godkendes længere.'
              : `Afsluttet (${approval.status}).`}
          </Text>
        )}
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  wrap: { gap: 6 },
  reason: { color: tokens.color.fg2, fontSize: 13, lineHeight: 18 },
  card: {
    backgroundColor: tokens.color.bg2,
    borderRadius: tokens.radius.lg,
    padding: tokens.spacing.md,
    gap: tokens.spacing.sm
  },
  tagRow: { flexDirection: 'row', alignItems: 'center' },
  tag: {
    color: tokens.color.fg2,
    fontSize: 11,
    fontWeight: '600',
    backgroundColor: tokens.color.bg3,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: tokens.radius.sm,
    overflow: 'hidden'
  },
  spacer: { flex: 1 },
  age: { color: tokens.color.fg3, fontSize: 11 },
  title: { color: tokens.color.fg1, fontSize: 14, fontWeight: '600' },
  code: {
    backgroundColor: tokens.color.codeBg,
    borderRadius: tokens.radius.md,
    padding: tokens.spacing.sm
  },
  codeText: { color: tokens.color.fg1, fontSize: 12, fontFamily: 'monospace' },
  meta: { color: tokens.color.fg3, fontSize: 11 },
  actions: { gap: tokens.spacing.sm },
  btn: { paddingVertical: 11, borderRadius: tokens.radius.md, alignItems: 'center' },
  primary: { backgroundColor: tokens.color.fg1 },
  btnBusy: { opacity: 0.6 },
  primaryText: { color: tokens.color.bg0, fontSize: 14, fontWeight: '700' },
  tertiary: { backgroundColor: tokens.color.bg3 },
  tertiaryText: { color: tokens.color.fg2, fontSize: 14, fontWeight: '600' },
  dead: { color: tokens.color.fg3, fontSize: 12, fontStyle: 'italic' }
})
