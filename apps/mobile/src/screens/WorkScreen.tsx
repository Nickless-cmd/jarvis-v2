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
import { WorkDecisionCard } from '../components/WorkDecisionCard'
import { actOnDecision, fetchDecisions, type Decision, type DecisionAction } from '../lib/decisionsApi'

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
 * Hvor mange ting venter reelt på et svar.
 *
 * Livsprojekter tælles IKKE med. De har ligget der i månedsvis og kan kun
 * «lægges fra sig» — tælles de med, står prikken tændt for altid, og en prik
 * der aldrig går væk holder op med at betyde noget. Godkendelser blokerer et
 * kørende run; initiativer er spørgsmål han venter svar på. Kun de to haster.
 */
export function tælVentende(pendingApprovals: number, decisions: Decision[]): number {
  return pendingApprovals + decisions.filter((d) => d.kind === 'initiative').length
}

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
  // Jarvis' egne spørgsmål. Som tankerne: fejler kaldet, står listen tom frem
  // for at lægge en fejlbjælke over de godkendelser der FAKTISK blokerer et run.
  const [decisions, setDecisions] = useState<Decision[]>([])
  const [ubesvarede, setUbesvarede] = useState(0)

  const load = useCallback(async () => {
    if (!config) return
    try {
      const [r, a, d] = await Promise.all([
        fetchRuns(config, 20),
        fetchApprovals(config, 20),
        fetchDecisions(config).catch(() => null)
      ])
      if (d) {
        setDecisions(d.items)
        setUbesvarede(d.expiredUnanswered)
      }
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

  const onDecide = useCallback(
    async (d: Decision, action: DecisionAction) => {
      if (!config) return
      setBusyId(d.id)
      // Fjern kortet med det samme. Serveren er stadig sandheden — næste load
      // henter listen igen — men et kort der bliver stående efter et tryk
      // føles som om trykket ikke landede.
      setDecisions((prev) => prev.filter((x) => x.id !== d.id))
      try {
        const res = await actOnDecision(config, d, action)
        if (!res.ok) setError(res.error || 'Kunne ikke svare på forslaget')
        await load()
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Kunne ikke svare på forslaget')
        await load()
      } finally {
        setBusyId(null)
      }
    },
    [config, load]
  )

  const onSkip = useCallback((a: Approval) => {
    setSkipped((prev) => (prev.includes(a.request_id) ? prev : [...prev, a.request_id]))
  }, [])

  const initiativer = decisions.filter((d) => d.kind === 'initiative')
  const projekter = decisions.filter((d) => d.kind === 'life_project')
  const venter = tælVentende(pending.length, decisions)

  useEffect(() => {
    onPendingCount?.(venter)
  }, [venter, onPendingCount])

  return (
    <View style={[styles.root, { paddingTop: topInset }]}>
      <View style={styles.subTabs}>
        <SegmentedControl<WorkTab>
          compact
          options={[
            { value: 'tasks', label: 'Tasks' },
            { value: 'approve', label: 'Godkend', badge: venter > 0 }
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
              initiativer={initiativer}
              projekter={projekter}
              ubesvarede={ubesvarede}
              busyId={busyId}
              onApprove={(a) => void onApprove(a)}
              onSkip={onSkip}
              onDecide={(d, action) => void onDecide(d, action)}
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

/**
 * Alt der venter på et ja eller et nej — uanset hvem der spørger.
 *
 * Runtimen spørger om lov til at handle; Jarvis spørger om lov til at ville
 * noget. For den der svarer er det samme handling, så de deler fane. De står i
 * hver sin gruppe, fordi hastværket er forskelligt: en godkendelse blokerer et
 * run lige nu, et forslag kan vente til i aften.
 */
function ApproveView({
  approvals,
  initiativer,
  projekter,
  ubesvarede,
  busyId,
  onApprove,
  onSkip,
  onDecide
}: {
  approvals: Approval[]
  initiativer: Decision[]
  projekter: Decision[]
  ubesvarede: number
  busyId: string | null
  onApprove: (a: Approval) => void
  onSkip: (a: Approval) => void
  onDecide: (d: Decision, action: DecisionAction) => void
}) {
  const tokens = useTheme()
  const styles = useStyles(makestyles)

  if (approvals.length === 0 && initiativer.length === 0 && projekter.length === 0) {
    return <Text style={styles.empty}>Ingen ventende godkendelser.</Text>
  }

  return (
    <>
      {approvals.length > 0 ? (
        <>
          <Text style={styles.groupLabel}>Venter på dig</Text>
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
      ) : null}

      {initiativer.length > 0 ? (
        <>
          <Text style={styles.groupLabel}>Han foreslår</Text>
          {initiativer.map((d) => (
            <WorkDecisionCard
              key={d.id}
              decision={d}
              busy={busyId === d.id}
              onAct={onDecide}
            />
          ))}
        </>
      ) : null}

      {projekter.length > 0 ? (
        <>
          <Text style={styles.groupLabel}>Det han arbejder hen imod</Text>
          {projekter.map((d) => (
            <WorkDecisionCard
              key={d.id}
              decision={d}
              busy={busyId === d.id}
              onAct={onDecide}
            />
          ))}
        </>
      ) : null}

      {/* Tallet der gør ondt. Det står til sidst og dæmpet — det er historie,
          ikke en opgave — men det står der, for det er hele grunden til at
          denne fane findes. */}
      {ubesvarede > 0 ? (
        <Text style={styles.ubesvarede}>
          {ubesvarede} tidligere forslag udløb uden svar.
        </Text>
      ) : null}
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
  empty: { color: tokens.color.fg2, fontSize: 14, textAlign: 'center', marginTop: tokens.spacing.xl },
  ubesvarede: {
    color: tokens.color.fg3,
    fontSize: 12,
    textAlign: 'center',
    marginTop: tokens.spacing.md
  }
})
