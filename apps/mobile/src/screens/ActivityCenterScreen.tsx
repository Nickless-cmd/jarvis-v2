import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native'
import { Activity, Clock3, PackageCheck, X } from 'lucide-react-native'
import type { ActiveRunSnapshot } from '../lib/apiClient'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'

export function ActivityCenterScreen({
  onClose,
  runs,
  outboxCount = 0,
  presenceSummary = ''
}: {
  onClose: () => void
  runs: ActiveRunSnapshot[]
  outboxCount?: number
  presenceSummary?: string
}) {
  const tokens = useTheme()
  const styles = useStyles(makes)
  return (
    <View style={styles.root}>
      <View style={styles.header}>
        <Pressable accessibilityRole="button" accessibilityLabel="Luk" onPress={onClose} style={styles.circle}>
          <X size={20} color={tokens.color.fg1} strokeWidth={2} />
        </Pressable>
        <Text style={styles.title}>Aktivitet</Text>
        <View style={styles.circleGhost} />
      </View>
      <ScrollView contentContainerStyle={styles.body}>
        <View style={styles.summary}>
          <Activity size={18} color={tokens.color.accent} strokeWidth={1.9} />
          <View style={styles.summaryText}>
            <Text style={styles.value}>{runs.length ? `${runs.length} aktive run` : 'Ingen aktive run'}</Text>
            <Text style={styles.muted}>{presenceSummary || 'Device routing ikke hentet endnu'}</Text>
          </View>
          <Text style={styles.badge}>{outboxCount} i kø</Text>
        </View>
        {runs.length ? runs.map((run) => (
          <View key={`${run.sessionId}:${run.runId}`} style={styles.card}>
            <View style={styles.cardHead}>
              <Clock3 size={15} color={tokens.color.fg2} strokeWidth={1.9} />
              <Text style={styles.cardMeta}>{run.status || 'working'}</Text>
            </View>
            <Text style={styles.runId}>{run.runId || 'ukendt run'}</Text>
            <Text style={styles.muted}>Session {run.sessionId}</Text>
          </View>
        )) : (
          <View style={styles.card}>
            <PackageCheck size={18} color={tokens.color.fg2} strokeWidth={1.8} />
            <Text style={styles.value}>Alt er roligt</Text>
            <Text style={styles.muted}>Når Jarvis arbejder i baggrunden, lander det her.</Text>
          </View>
        )}
      </ScrollView>
    </View>
  )
}

const makes = (tokens: Theme) => StyleSheet.create({
  root: { flex: 1, backgroundColor: tokens.color.bg0, paddingTop: 48 },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: tokens.spacing.md, paddingBottom: tokens.spacing.md },
  circle: { width: 40, height: 40, borderRadius: 20, alignItems: 'center', justifyContent: 'center', backgroundColor: tokens.color.bg2 },
  circleGhost: { width: 40, height: 40 },
  title: { color: tokens.color.fg1, fontSize: 17, fontWeight: '700' },
  body: { padding: tokens.spacing.lg, gap: tokens.spacing.sm, paddingBottom: tokens.spacing.xl },
  summary: { flexDirection: 'row', alignItems: 'center', gap: tokens.spacing.md, backgroundColor: tokens.color.bg1, borderRadius: tokens.radius.lg, padding: tokens.spacing.lg },
  summaryText: { flex: 1, gap: 3 },
  value: { color: tokens.color.fg1, fontWeight: '700' },
  muted: { color: tokens.color.fg3, fontSize: 13, lineHeight: 19 },
  badge: { color: tokens.color.accentText, fontSize: 12, fontWeight: '800' },
  card: { backgroundColor: tokens.color.bg2, borderRadius: tokens.radius.lg, padding: tokens.spacing.lg, gap: 7 },
  cardHead: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  cardMeta: { color: tokens.color.fg2, fontSize: 12, fontWeight: '800', textTransform: 'uppercase' },
  runId: { color: tokens.color.fg1, fontSize: 15, fontWeight: '700' }
})
