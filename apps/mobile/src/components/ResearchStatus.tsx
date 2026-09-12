import { ActivityIndicator, StyleSheet, Text, View } from 'react-native'
import { SearchCheck } from 'lucide-react-native'
import type { ResearchUiState } from '../lib/streamReducer'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'

export function ResearchStatus({ research }: { research: ResearchUiState | null }) {
  const tokens = useTheme()
  const styles = useStyles(makeStyles)
  if (!research) return null
  const active = research.phase !== 'completed'
  const label = research.totalTasks > 0
    ? `Research ${research.completedTasks}/${research.totalTasks}`
    : active ? 'Research' : 'Research færdig'
  return (
    <View testID="research-status" style={styles.row}>
      {active
        ? <ActivityIndicator size="small" color={tokens.color.accent} />
        : <SearchCheck size={17} color={tokens.color.accentText} />}
      <Text style={styles.label}>{label}</Text>
      {research.sources > 0 ? <Text style={styles.detail}>{research.sources} kilder</Text> : null}
      {research.warning ? <Text style={styles.warning} numberOfLines={1}>{research.warning}</Text> : null}
    </View>
  )
}

const makeStyles = (tokens: Theme) => StyleSheet.create({
  row: {
    minHeight: 34, marginHorizontal: 18, marginBottom: 4,
    paddingHorizontal: 12, flexDirection: 'row', alignItems: 'center', gap: 8,
    borderRadius: tokens.radius.md, backgroundColor: tokens.color.bg1,
  },
  label: { color: tokens.color.fg1, fontSize: 13, fontWeight: '700' },
  detail: { color: tokens.color.fg3, fontSize: 12 },
  warning: { color: tokens.color.warn, fontSize: 12, flex: 1, textAlign: 'right' },
})
