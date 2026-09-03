import { StyleSheet, Text, View } from 'react-native'
import { formatRelativeTime } from '../lib/relativeDate'
import { tokens } from '../theme/tokens'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'
import type { McRun } from '../lib/mcTypes'

/**
 * Kilden aflæses af run-id-præfikset.
 *
 * `visible_runs` har ingen `source`-kolonne — speccen antog en. Præfikset er
 * den eneste bærende skelnen der findes i dag, og den er dokumenteret her frem
 * for skjult i en formatteringsfunktion.
 */
export type RunSource = 'snak' | 'autonom' | 'agent'

export function sourceOf(run: McRun): RunSource {
  const id = run.run_id ?? ''
  if (id.startsWith('autonomous-')) return 'autonom'
  if (id.startsWith('visible-')) return 'snak'
  return 'agent'
}

const SOURCE_LABEL: Record<RunSource, string> = {
  snak: 'Snak',
  autonom: 'Autonom',
  agent: 'Agent'
}

/**
 * Statusfarven TAGER temaet frem for at læse den statiske palet.
 *
 * En hjælpefunktion kan ikke bruge hooks — den kaldes også uden for en render.
 * Læste den i stedet den importerede `tokens`, ville status-prikkerne blive
 * siddende i mørkt tema med den oprindelige grønne, uanset hvad brugeren har
 * valgt. Så temaet kommer ind ad døren i stedet.
 */
export function statusColor(status: string, t: Theme = tokens as unknown as Theme): string {
  if (status === 'running' || status === 'active') return t.color.accent
  if (status === 'failed' || status === 'error') return t.color.error
  if (status === 'cancelled' || status === 'interrupted') return t.color.warn
  return t.color.fg3
}

export function isActive(run: McRun): boolean {
  return !run.finished_at || run.status === 'running' || run.status === 'active'
}

interface Props {
  run: McRun
  now?: Date
}

/**
 * Ét opgavekort. Read-only i fase 1 — ingen tryk-verber.
 *
 * Bevidst: en knap der antyder cancel eller steer, men ikke virker, er værre
 * end ingen knap. Kortet er et vindue, ikke en fjernbetjening (endnu).
 */
export function WorkTaskCard({ run, now }: Props) {
  const tokens = useTheme()
  const styles = useStyles(makestyles)
  const source = sourceOf(run)
  const model = (run.model ?? '').trim()
  const preview = (run.text_preview ?? '').trim()
  return (
    <View style={styles.card} accessibilityRole="summary" accessibilityLabel={`Kørsel ${run.status}`}>
      <View style={styles.head}>
        <View style={[styles.dot, { backgroundColor: statusColor(run.status, tokens) }]} testID="status-dot" />
        <Text style={styles.tag}>{SOURCE_LABEL[source]}</Text>
        {model ? (
          <Text style={styles.model} numberOfLines={1}>
            {model}
          </Text>
        ) : null}
        <View style={styles.spacer} />
        <Text style={styles.age}>{formatRelativeTime(run.started_at, now ?? new Date())}</Text>
      </View>
      <Text style={styles.preview} numberOfLines={2}>
        {preview || 'Ingen opsummering endnu.'}
      </Text>
      <Text style={styles.status}>{run.status}</Text>
    </View>
  )
}

const makestyles = (tokens: Theme) => StyleSheet.create({
  card: {
    backgroundColor: tokens.color.bg1,
    borderRadius: tokens.radius.lg,
    borderWidth: 1,
    borderColor: tokens.color.line,
    padding: tokens.spacing.md,
    gap: 6
  },
  head: { flexDirection: 'row', alignItems: 'center', gap: tokens.spacing.sm },
  dot: { width: 8, height: 8, borderRadius: 4 },
  tag: { color: tokens.color.fg2, fontSize: 12, fontWeight: '600' },
  model: { color: tokens.color.fg3, fontSize: 11, flexShrink: 1 },
  spacer: { flex: 1 },
  age: { color: tokens.color.fg3, fontSize: 11 },
  preview: { color: tokens.color.fg1, fontSize: 13, lineHeight: 18 },
  status: { color: tokens.color.fg3, fontSize: 11 }
})
