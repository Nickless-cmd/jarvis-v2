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
 * Godkendelseskortet — 1:1 med R8, målt på skærmbilledet 2026-09-02.
 *
 * Tre ting er rettet efter at have set referencen frem for at læse om den:
 *
 *   1. Spørgsmålet står INDE i kortet, øverst, i fed hvid — ikke som løs
 *      tekst over kortet, som speccen beskrev.
 *   2. Handlingerne er TEKSTRÆKKER adskilt af tynde linjer, ikke fyldte
 *      knapper. Der er ingen primær-knap-farve; «Godkend» skiller sig ud ved
 *      at stå først, ikke ved at være hvid.
 *   3. Etiketten («Kommandoudførelse») ligger OVER kortet med sit ikon, ikke
 *      som en pille inde i det.
 */
export function WorkApprovalCard({ approval, busy, onApprove, onSkip, now }: Props) {
  const actionable = isActionable(approval)
  const reason = approvalReason(approval)
  const detail = approvalDetail(approval)
  const expired = approval.status === 'expired' || approval.stale
  const at = now ?? new Date()

  return (
    <View style={styles.wrap}>
      <View style={styles.tagRow}>
        <View style={styles.tagIcon}>
          <Text style={styles.tagGlyph}>{'>_'}</Text>
        </View>
        <Text style={styles.tagLabel} numberOfLines={1}>
          {approvalTag(approval)}
        </Text>
        <View style={styles.spacer} />
        <Text style={styles.age}>{formatRelativeTime(approval.requested_at, at)}</Text>
      </View>

      <View style={styles.card}>
        <Text style={styles.question}>{reason || approvalTitle(approval)}</Text>

        {detail ? (
          <View style={styles.code}>
            <Text style={styles.codeText} numberOfLines={8}>
              {detail}
            </Text>
          </View>
        ) : null}

        {isToolIntent(approval) && approval.expires_at ? (
          <Text style={styles.meta} testID="expiry-note">
            Vindue udløber {formatRelativeTime(approval.expires_at, at)}
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
              style={styles.action}
            >
              <Text style={[styles.actionLabel, busy && styles.dim]}>
                {busy ? 'Godkender…' : 'Godkend'}
              </Text>
            </Pressable>

            <View style={styles.divider} />

            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Spring over"
              disabled={busy}
              onPress={() => onSkip(approval)}
              style={styles.action}
            >
              <Text style={[styles.actionLabel, busy && styles.dim]}>Spring over</Text>
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
  wrap: { gap: tokens.spacing.sm },
  tagRow: { flexDirection: 'row', alignItems: 'center', gap: tokens.spacing.sm },
  tagIcon: {
    width: 22,
    height: 22,
    borderRadius: tokens.radius.sm,
    borderWidth: 1,
    borderColor: tokens.color.fg2,
    alignItems: 'center',
    justifyContent: 'center'
  },
  tagGlyph: { color: tokens.color.fg2, fontSize: 10, fontFamily: 'monospace' },
  tagLabel: { color: tokens.color.fg1, fontSize: 14, flexShrink: 1 },
  spacer: { flex: 1 },
  age: { color: tokens.color.fg3, fontSize: 12 },
  card: {
    backgroundColor: tokens.color.bg2,
    borderRadius: tokens.radius.xl,
    padding: tokens.spacing.lg,
    gap: tokens.spacing.md
  },
  question: { color: tokens.color.fg1, fontSize: 15, fontWeight: '700', lineHeight: 21 },
  code: {
    backgroundColor: tokens.color.codeBg,
    borderRadius: tokens.radius.md,
    paddingHorizontal: tokens.spacing.md,
    paddingVertical: tokens.spacing.sm
  },
  codeText: { color: tokens.color.fg1, fontSize: 12.5, fontFamily: 'monospace', lineHeight: 19 },
  meta: { color: tokens.color.fg3, fontSize: 12 },
  actions: { marginTop: tokens.spacing.xs },
  action: { paddingVertical: tokens.spacing.md },
  actionLabel: { color: tokens.color.fg1, fontSize: 15 },
  dim: { color: tokens.color.fg3 },
  divider: { height: StyleSheet.hairlineWidth, backgroundColor: tokens.color.line },
  dead: { color: tokens.color.fg3, fontSize: 13, fontStyle: 'italic' }
})
