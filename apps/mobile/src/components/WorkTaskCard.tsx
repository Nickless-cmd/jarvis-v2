import { useState } from 'react'
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native'
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
  busy?: boolean
  onSteer?: (run: McRun, content: string) => void
  onCancel?: (run: McRun) => void
}

/**
 * Ét opgavekort. Read-only i fase 1 — ingen tryk-verber.
 *
 * Bevidst: en knap der antyder cancel eller steer, men ikke virker, er værre
 * end ingen knap. Kortet er et vindue, ikke en fjernbetjening (endnu).
 */
export function WorkTaskCard({ run, now, busy, onSteer, onCancel }: Props) {
  const tokens = useTheme()
  const styles = useStyles(makestyles)
  const [steering, setSteering] = useState(false)
  const [steerText, setSteerText] = useState('')
  const source = sourceOf(run)
  const model = (run.model ?? '').trim()
  const preview = (run.text_preview ?? '').trim()
  const active = isActive(run)
  const canSteer = active && Boolean(onSteer)
  const canCancel = active && Boolean(onCancel)
  const submitSteer = () => {
    const text = steerText.trim()
    if (!text || !onSteer) return
    onSteer(run, text)
    setSteerText('')
    setSteering(false)
  }
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
      {canSteer || canCancel ? (
        <View style={styles.actions}>
          {canSteer ? (
            <Pressable
              accessibilityRole="button"
              disabled={busy}
              onPress={() => setSteering((v) => !v)}
              style={styles.action}
            >
              <Text style={styles.actionText}>Styr</Text>
            </Pressable>
          ) : null}
          {canCancel ? (
            <Pressable
              accessibilityRole="button"
              disabled={busy}
              onPress={() => onCancel?.(run)}
              style={styles.action}
            >
              <Text style={styles.actionText}>Stop</Text>
            </Pressable>
          ) : null}
        </View>
      ) : null}
      {steering ? (
        <View style={styles.steerBox}>
          <TextInput
            testID="work-steer-input"
            value={steerText}
            onChangeText={setSteerText}
            placeholder="Giv en ny instruks"
            placeholderTextColor={tokens.color.fg3}
            style={styles.steerInput}
          />
          <Pressable
            accessibilityRole="button"
            disabled={!steerText.trim() || busy}
            onPress={submitSteer}
            style={[styles.sendSteer, (!steerText.trim() || busy) && styles.disabled]}
          >
            <Text style={styles.sendSteerText}>Send</Text>
          </Pressable>
        </View>
      ) : null}
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
  status: { color: tokens.color.fg3, fontSize: 11 },
  actions: {
    flexDirection: 'row',
    gap: tokens.spacing.sm,
    marginTop: tokens.spacing.xs
  },
  action: {
    paddingHorizontal: tokens.spacing.md,
    paddingVertical: 7,
    borderRadius: tokens.radius.md,
    backgroundColor: tokens.color.bg2
  },
  actionText: { color: tokens.color.fg1, fontWeight: '700', fontSize: 13 },
  steerBox: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: tokens.spacing.sm,
    backgroundColor: tokens.color.bg2,
    borderRadius: tokens.radius.md,
    padding: tokens.spacing.xs
  },
  steerInput: {
    flex: 1,
    color: tokens.color.fg1,
    paddingHorizontal: tokens.spacing.sm,
    paddingVertical: 6
  },
  sendSteer: {
    paddingHorizontal: tokens.spacing.md,
    paddingVertical: 7,
    borderRadius: tokens.radius.sm,
    backgroundColor: tokens.color.accent
  },
  sendSteerText: { color: tokens.color.bg0, fontWeight: '700' },
  disabled: { opacity: 0.5 }
})
