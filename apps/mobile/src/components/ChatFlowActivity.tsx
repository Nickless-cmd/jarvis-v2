import { memo } from 'react'
import { Pressable, StyleSheet, Text, View } from 'react-native'
import { Brain, ChevronRight, Code2 } from 'lucide-react-native'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'
import { GlidendeTekst } from './GlidendeTekst'
import { RullendeUr } from './RullendeTal'

/** Desk Chat's levende syntese + ene aktive rundelinje. */
export const ChatFlowActivity = memo(function ChatFlowActivity({
  synthesis, round, thinkingSeconds, expandable, onExpand,
}: {
  synthesis?: string
  round: string
  thinkingSeconds?: number | null
  expandable?: boolean
  onExpand?: () => void
}) {
  const theme = useTheme()
  const styles = useStyles(makeStyles)
  return (
    <View style={styles.wrap} testID="chat-flow-activity" accessibilityRole="text">
      {synthesis ? (
        <Text style={styles.synthesis} numberOfLines={3} testID="chat-flow-live-synthesis">
          {synthesis}
        </Text>
      ) : null}
      <View style={styles.round}>
        <Brain size={15} color={theme.color.fg2} strokeWidth={1.8} />
        <Text style={styles.thinking}>Tænker</Text>
        {thinkingSeconds != null ? <RullendeUr sek={thinkingSeconds} farve={theme.color.fg2} tegnFarve={theme.color.fg3} /> : null}
        <Text style={styles.divider}>|</Text>
        <Code2 size={15} color={theme.color.fg2} strokeWidth={1.8} />
        <View style={styles.label}><GlidendeTekst text={round} aktiv style={styles.roundText} numberOfLines={1} /></View>
        {expandable ? (
          <Pressable
            testID="chat-flow-round-fold"
            accessibilityRole="button"
            accessibilityLabel="Vis arbejdet"
            onPress={onExpand}
            hitSlop={8}
          >
            <ChevronRight size={16} color={theme.color.fg3} strokeWidth={1.75} />
          </Pressable>
        ) : null}
      </View>
    </View>
  )
})

const makeStyles = (theme: Theme) => StyleSheet.create({
  wrap: { marginHorizontal: theme.spacing.lg, paddingTop: 3, gap: 5, overflow: 'hidden' },
  synthesis: { color: theme.color.fg1, fontSize: 15, lineHeight: 21 },
  round: { flexDirection: 'row', alignItems: 'center', gap: 7, minHeight: 21 },
  thinking: { color: theme.color.fg2, fontSize: 13 },
  divider: { color: theme.color.fg3, opacity: 0.55, fontSize: 13 },
  label: { flexShrink: 1, minWidth: 0 },
  roundText: { color: theme.color.fg2, fontSize: 13 },
})
