import { useCallback, useEffect, useState } from 'react'
import { ActivityIndicator, ScrollView, StyleSheet, Text, View } from 'react-native'
import { SegmentedControl } from '../components/SegmentedControl'
import { ErrorBanner } from '../components/ErrorBanner'
import { tokens } from '../theme/tokens'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'
import { useAuth } from '../state/AuthContext'
import { approveRequest, approveToolIntent, fetchApprovals, fetchRuns, pendingApprovals } from '../lib/mcClient'
import { isToolIntent } from '../lib/mcTypes'
import type { Approval, McRun } from '../lib/mcTypes'
import { WorkTaskCard, isActive } from '../components/WorkTaskCard'
import { WorkApprovalCard } from '../components/WorkApprovalCard'
import { ThoughtsList } from '../components/ThoughtsList'
import { fetchThoughts, type Thought } from '../lib/companionClient'

export type WorkTab = 'tasks' | 'approve'

interface Props {
  /** Plads til den svævende header. Måles i App og gives videre — et fast tal
      ville tie stille næste gang bjælken skifter højde. */
  topInset?: number
  /** Stiger når brugeren trykker sync i TopBar. */
  syncSignal?: number
  /** Løftes til AppBody så Arbejde-segmentet kan bære en prik. */
  onPendingCount?: (count: number) => void
  /** Kaldes når en sync-udløst hentning er færdig. */
  onSyncDone?: () => void
}

const POLL_MS = 4000

/**
 * Arbejde-rummet: Tasks (hvad Jarvis laver) og Approve (hvad der venter på Bjørn).
 *
 * State bor på serveren — skærmen abonnerer, den ejer intet. Taber telefonen
 * forbindelsen, dør intet.
 */
export function WorkScreen({ topInset = 72, syncSignal = 0, onPendingCount, onSyncDone }: Props) {
  const tokens = useTheme()
  const styles = useStyles(makestyles)
  const { config } = useAuth()
  const [tab, setTab] = useState<WorkTab>('tasks')
  const [runs, setRuns] = useState<McRun[]>([])
  const [approvals, setApprovals] = useState<Approval[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [tick, setTick] = useState(0)
  const [busyId, setBusyId] = useState<string | null>(null)
  // Jarvis' egne initiativer. Fejler kaldet, står listen tom frem for at vise
  // en fejl — hans tanker er ikke noget rummet KRÆVER for at fungere.
  const [thoughts, setThoughts] = useState<Thought[]>([])
  useEffect(() => {
    if (!config) return
    let cancelled = false
    void fetchThoughts(config).then((t) => { if (!cancelled) setThoughts(t) })
    return () => { cancelled = true }
  }, [config, tick])
  // Sprunget over = lokal afvisning. Serveren har ingen 'denied'-status for
  // capability-requests, så kortet forbliver pending server-side. Den
  // asynkrone model gør at intet run blokerer imens.
  const [skipped, setSkipped] = useState<string[]>([])

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
    void load().finally(() => {
      if (syncSignal > 0) onSyncDone?.()
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [load, syncSignal, tick])

  useEffect(() => {
    const id = setInterval(() => setTick((t) => t + 1), POLL_MS)
    return () => clearInterval(id)
  }, [])

  const pending = pendingApprovals(approvals).filter((a) => !skipped.includes(a.request_id))

  const onApprove = useCallback(
    async (a: Approval) => {
      if (!config) return
      setBusyId(a.request_id)
      try {
        // De to systemer har hver sit endpoint — diskriminanten afgør hvilket.
        if (isToolIntent(a)) {
          await approveToolIntent(config)
        } else {
          await approveRequest(config, a.request_id)
        }
        await load()
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Godkendelse mislykkedes')
      } finally {
        setBusyId(null)
      }
    },
    [config, load]
  )

  const onSkip = useCallback((a: Approval) => {
    setSkipped((prev) => (prev.includes(a.request_id) ? prev : [...prev, a.request_id]))
  }, [])

  useEffect(() => {
    onPendingCount?.(pending.length)
  }, [pending.length, onPendingCount])

  return (
    <View style={[styles.root, { paddingTop: topInset }]}>
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
            <>
              <TasksView runs={runs} />
              {/* Jarvis' egne tanker hører til i Arbejde-rummet: det er dét rum
                  hvor noget venter på én, uden at det er en samtale. */}
              <Text style={styles.groupLabel}>Fra Jarvis</Text>
              <ThoughtsList items={thoughts} />
            </>
          ) : (
            <ApproveView
              approvals={pending}
              busyId={busyId}
              onApprove={(a) => void onApprove(a)}
              onSkip={onSkip}
            />
          )}
        </ScrollView>
      )}
    </View>
  )
}

function TasksView({ runs }: { runs: McRun[] }) {
  const tokens = useTheme()
  const styles = useStyles(makestyles)
  if (runs.length === 0) {
    return <Text style={styles.empty}>Intet arbejde lige nu.</Text>
  }
  const aktive = runs.filter(isActive)
  const afsluttede = runs.filter((r) => !isActive(r))
  return (
    <>
      {aktive.length > 0 ? (
        <>
          <Text style={styles.groupLabel}>Aktive</Text>
          {aktive.map((r) => (
            <WorkTaskCard key={r.run_id} run={r} />
          ))}
        </>
      ) : null}
      {afsluttede.length > 0 ? (
        <>
          <Text style={styles.groupLabel}>Afsluttet</Text>
          {afsluttede.map((r) => (
            <WorkTaskCard key={r.run_id} run={r} />
          ))}
        </>
      ) : null}
    </>
  )
}

function ApproveView({
  approvals,
  busyId,
  onApprove,
  onSkip
}: {
  approvals: Approval[]
  busyId: string | null
  onApprove: (a: Approval) => void
  onSkip: (a: Approval) => void
}) {
  const tokens = useTheme()
  const styles = useStyles(makestyles)
  if (approvals.length === 0) {
    return <Text style={styles.empty}>Ingen ventende godkendelser.</Text>
  }
  return (
    <>
      {approvals.map((a) => (
        <WorkApprovalCard
          key={a.request_id}
          approval={a}
          busy={busyId === a.request_id}
          onApprove={onApprove}
          onSkip={onSkip}
        />
      ))}
    </>
  )
}

const makestyles = (tokens: Theme) => StyleSheet.create({
  root: { flex: 1, backgroundColor: tokens.color.bg0 },
  subTabs: { paddingHorizontal: tokens.spacing.lg, paddingBottom: tokens.spacing.sm },
  list: { padding: tokens.spacing.lg, gap: tokens.spacing.md },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  groupLabel: {
    color: tokens.color.fg3,
    fontSize: 11,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginTop: tokens.spacing.sm
  },
  empty: { color: tokens.color.fg2, fontSize: 14, textAlign: 'center', marginTop: tokens.spacing.xl }
})
