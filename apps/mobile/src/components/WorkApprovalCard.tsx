import { Pressable, StyleSheet, Text, View } from 'react-native'
import { Terminal } from 'lucide-react-native'
import { formatRelativeTime } from '../lib/relativeDate'
import { tokens } from '../theme/tokens'
import { approvalDetail, approvalReason, approvalTag, approvalTitle, isActionable, isToolIntent } from '../lib/mcTypes'
import type { Approval } from '../lib/mcTypes'

interface Props {
  approval: Approval
  busy?: boolean
  onApprove: (a: Approval) => void
  /** «Godkend altid» — kun tilbudt når serveren FAKTISK kan huske en regel. */
  onAlways?: (a: Approval) => void
  onSkip: (a: Approval) => void
  now?: Date
}

/**
 * Serveren har kun ét genbrugeligt vindue: sudo-exec (5 min,
 * sudo_approval_window_allows_request). Der findes ingen generel præfiks-regel
 * for write-capabilities endnu — så knappen vises KUN hvor den kan holde hvad
 * den lover. En «Godkend altid» der i virkeligheden kun gælder én gang er
 * værre end ingen knap.
 */
function alwaysRule(a: Approval): string | null {
  if (a.approval_system !== 'capability') return null
  if (a.execution_mode !== 'sudo-exec-proposal') return null
  const cmd = approvalDetail(a).trim()
  return cmd ? `Kommandoer, der starter med ${cmd}` : null
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
export function WorkApprovalCard({ approval, busy, onApprove, onAlways, onSkip, now }: Props) {
  const actionable = isActionable(approval)
  const reason = approvalReason(approval)
  const detail = approvalDetail(approval)
  const expired = approval.status === 'expired' || approval.stale
  const at = now ?? new Date()
  const rule = onAlways ? alwaysRule(approval) : null

  return (
    <View style={styles.wrap}>
      <View style={styles.tagRow}>
        <View style={styles.tagIcon}>
          <Terminal size={13} color={tokens.color.fg2} strokeWidth={1.8} />
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

            {rule ? (
              <>
                <View style={styles.divider} />
                <Pressable
                  accessibilityRole="button"
                  accessibilityLabel="Godkend altid"
                  disabled={busy}
                  onPress={() => onAlways?.(approval)}
                  style={styles.action}
                >
                  <Text style={[styles.actionLabel, busy && styles.dim]}>Godkend altid</Text>
                  {/* Reglen står ORDRET — «altid» må aldrig være en blank check. */}
                  <Text style={styles.ruleText} numberOfLines={2}>
                    {rule}
                  </Text>
                </Pressable>
              </>
            ) : null}

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
  ruleText: { color: tokens.color.fg2, fontSize: 13, marginTop: 3, lineHeight: 18 },
  dead: { color: tokens.color.fg3, fontSize: 13, fontStyle: 'italic' }
})
