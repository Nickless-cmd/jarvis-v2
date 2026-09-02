import { useCallback, useEffect, useState } from 'react'
import { ActivityIndicator, ScrollView, StyleSheet, Text, View } from 'react-native'
import { SegmentedControl } from '../components/SegmentedControl'
import { ErrorBanner } from '../components/ErrorBanner'
import { tokens } from '../theme/tokens'
import { useAuth } from '../state/AuthContext'
import { fetchApprovals, fetchRuns, pendingApprovals } from '../lib/mcClient'
import type { Approval, McRun } from '../lib/mcTypes'

export type WorkTab = 'tasks' | 'approve'

interface Props {
  /** Stiger når brugeren trykker sync i TopBar. */
  syncSignal?: number
  /** Løftes til AppBody så Arbejde-segmentet kan bære en prik. */
  onPendingCount?: (count: number) => void
}

const POLL_MS = 4000

/**
 * Arbejde-rummet: Tasks (hvad Jarvis laver) og Approve (hvad der venter på Bjørn).
 *
 * State bor på serveren — skærmen abonnerer, den ejer intet. Taber telefonen
 * forbindelsen, dør intet.
 */
export function WorkScreen({ syncSignal = 0, onPendingCount }: Props) {
  const { config } = useAuth()
  const [tab, setTab] = useState<WorkTab>('tasks')
  const [runs, setRuns] = useState<McRun[]>([])
  const [approvals, setApprovals] = useState<Approval[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [tick, setTick] = useState(0)

  const load = useCallback(async () => {
    if (!config) return
    try {
      const [r, a] = await Promise.all([fetchRuns(config, 20), fetchApprovals(config, 20)])
      const merged = [r.active_run, ...r.recent_runs].filter((x): x is McRun => Boolean(x))
      const seen = new Set<string>()
      setRuns(merged.filter((x) => (seen.has(x.run_id) ? false : (seen.add(x.run_id), true))))
      setApprovals(a.requests)
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Kunne ikke hente arbejde')
    } finally {
      setLoading(false)
    }
  }, [config])

  useEffect(() => {
    void load()
  }, [load, syncSignal, tick])

  useEffect(() => {
    const id = setInterval(() => setTick((t) => t + 1), POLL_MS)
    return () => clearInterval(id)
  }, [])

  const pending = pendingApprovals(approvals)

  useEffect(() => {
    onPendingCount?.(pending.length)
  }, [pending.length, onPendingCount])

  return (
    <View style={styles.root}>
      <View style={styles.subTabs}>
        <SegmentedControl<WorkTab>
          compact
          options={[
            { value: 'tasks', label: 'Tasks' },
            { value: 'approve', label: 'Godkend', badge: pending.length > 0 }
          ]}
          value={tab}
          onChange={setTab}
        />
      </View>

      {error ? (
        <ErrorBanner
          title="Kunne ikke hente arbejde"
          detail={error}
          actionLabel="Prøv igen"
          onAction={() => void load()}
        />
      ) : null}

      {loading ? (
        <View style={styles.center}>
          <ActivityIndicator color={tokens.color.accent} />
        </View>
      ) : (
        <ScrollView contentContainerStyle={styles.list}>
          {tab === 'tasks' ? (
            <TasksPlaceholder runs={runs} />
          ) : (
            <ApprovePlaceholder count={pending.length} />
          )}
        </ScrollView>
      )}
    </View>
  )
}

function TasksPlaceholder({ runs }: { runs: McRun[] }) {
  if (runs.length === 0) {
    return <Text style={styles.empty}>Intet arbejde lige nu.</Text>
  }
  return (
    <Text style={styles.empty} testID="tasks-count">
      {runs.length} kørsler
    </Text>
  )
}

function ApprovePlaceholder({ count }: { count: number }) {
  return (
    <Text style={styles.empty} testID="approve-count">
      {count === 0 ? 'Ingen ventende godkendelser.' : `${count} venter på dig`}
    </Text>
  )
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: tokens.color.bg0 },
  subTabs: { paddingHorizontal: tokens.spacing.lg, paddingBottom: tokens.spacing.sm },
  list: { padding: tokens.spacing.lg, gap: tokens.spacing.md },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  empty: { color: tokens.color.fg2, fontSize: 14, textAlign: 'center', marginTop: tokens.spacing.xl }
})
