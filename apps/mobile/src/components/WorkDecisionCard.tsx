import { Pressable, StyleSheet, Text, View } from 'react-native'
import { Compass, Lightbulb } from 'lucide-react-native'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'
import type { Decision, DecisionAction } from '../lib/decisionsApi'

interface Props {
  decision: Decision
  busy?: boolean
  onAct: (decision: Decision, action: DecisionAction) => void
}

const LABEL: Record<DecisionAction, string> = {
  approve: 'Godkend',
  reject: 'Afvis',
  abandon: 'Læg den fra dig'
}

/**
 * Et af Jarvis' egne spørgsmål.
 *
 * Bygget som WorkApprovalCard, med vilje: for den der svarer, er der ingen
 * forskel på «må jeg køre denne kommando» og «skal jeg forfølge dette» — det
 * er samme handling, og to forskellige kort ville få det til at føles som to.
 *
 * Forskellen der ER ægte: et initiativ udløber, et livsprojekt gør ikke. Derfor
 * bærer initiativet «Afvis» og projektet «Læg den fra dig» — det sidste er
 * ingen dom, kun en beslutning om ikke at bære den længere.
 */
export function WorkDecisionCard({ decision, busy, onAct }: Props) {
  const tokens = useTheme()
  const styles = useStyles(makestyles)
  const erProjekt = decision.kind === 'life_project'
  const Ikon = erProjekt ? Compass : Lightbulb

  // Ingen etiket-række over kortet. Godkendelseskortet har én, fordi den siger
  // noget nyt («Kommandoudførelse»); her ville den gentage gruppeoverskriften
  // ord for ord på hvert eneste kort. Ikonet flyttes ind til titlen i stedet —
  // det bærer genkendelsen uden at bruge en linje på den.
  return (
    <View style={styles.wrap}>
      <View style={styles.card}>
        <View style={styles.titleRow}>
          <Ikon size={15} color={tokens.color.fg2} strokeWidth={1.8} style={styles.titleIcon} />
          <Text style={styles.question}>{decision.text}</Text>
        </View>

        {/* Hans hvorfor. Et forslag uden begrundelse kan man kun gætte på. */}
        {decision.why ? <Text style={styles.why}>{decision.why}</Text> : null}

        {decision.actions.length > 0 ? (
          <View style={styles.actions}>
            {decision.actions.map((action) => (
              <Pressable
                key={action}
                disabled={busy}
                onPress={() => onAct(decision, action)}
                style={({ pressed }) => [styles.action, pressed && styles.actionPressed]}
              >
                <Text style={[styles.actionText, busy && styles.actionBusy]}>{LABEL[action]}</Text>
              </Pressable>
            ))}
          </View>
        ) : null}
      </View>
    </View>
  )
}

const makestyles = (tokens: Theme) => StyleSheet.create({
  wrap: { gap: tokens.spacing.xs },
  titleRow: { flexDirection: 'row', alignItems: 'flex-start', gap: tokens.spacing.sm },
  titleIcon: { marginTop: 3 },
  card: {
    backgroundColor: tokens.color.bg1,
    borderRadius: tokens.radius.lg,
    padding: tokens.spacing.md,
    gap: tokens.spacing.sm
  },
  question: { flex: 1, color: tokens.color.fg1, fontSize: 15, fontWeight: '600', lineHeight: 21 },
  why: { color: tokens.color.fg2, fontSize: 13, lineHeight: 19 },
  actions: { marginTop: tokens.spacing.xs },
  action: {
    paddingVertical: tokens.spacing.sm,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: tokens.color.line
  },
  actionPressed: { opacity: 0.6 },
  actionText: { color: tokens.color.fg1, fontSize: 15 },
  actionBusy: { color: tokens.color.fg3 }
})
