import { useState } from 'react'
import type { ApiConfig } from '../../../lib/api'
import type { QueueItem, CoworkPlan, CoworkTodo, CoworkChannel, ShareDecision } from '../../../lib/coworkApi'
import { useMissionControl } from '../../../hooks/useMissionControl'
import { ApprovalQueue } from '../ApprovalQueue'
import { PlansPane } from '../PlansPane'
import { TodoPane } from '../TodoPane'
import { ChannelsPane } from '../ChannelsPane'
import { ShareGuardPane } from '../ShareGuardPane'
import { SummaryBar } from './SummaryBar'
import { RunsTable } from './RunsTable'
import { AgentRoster } from './AgentRoster'
import { CostPanel } from './CostPanel'
import { EventStream } from './EventStream'
import { StatusChip } from './StatusChip'

type Tab = 'oversigt' | 'runs' | 'agenter' | 'godkendelser' | 'opgaver' | 'planlagt' | 'cost' | 'haendelser'

const TABS: { id: Tab; label: string; ownerOnly?: boolean }[] = [
  { id: 'oversigt', label: 'Oversigt' },
  { id: 'runs', label: 'Runs' },
  { id: 'agenter', label: 'Agenter', ownerOnly: true },
  { id: 'godkendelser', label: 'Godkendelser' },
  { id: 'opgaver', label: 'Opgaver' },
  { id: 'planlagt', label: 'Planlagt' },
  { id: 'cost', label: 'Cost', ownerOnly: true },
  { id: 'haendelser', label: 'Hændelser', ownerOnly: true },
]

export interface CoworkExtras {
  plans: CoworkPlan[]
  todos: CoworkTodo[]
  channels: CoworkChannel[]
  shareGuard: ShareDecision[]
  refresh: () => void
  onResolveShare: (id: string, shared: boolean) => void
}

/** Mission Control = rigtigt kontrolcenter (ikke bare et fladt grid). To-plan-model:
 *  oversigt → drill til detalje. Genbruger de eksisterende cowork-datasæt (godkendelser,
 *  opgaver, planer, kanaler, share-guard) fra parentens useCoworkData — INTET tabes fra det
 *  gamle grid; resten (runs/agenter/planlagt/overblik) hentes via useMissionControl. */
export function MissionControl({
  config,
  isOwner,
  queue,
  onResolveQueue,
  extras,
}: {
  config: ApiConfig | undefined
  isOwner: boolean
  queue: QueueItem[]
  onResolveQueue: (id: string, decision: 'approve' | 'reject') => void
  extras: CoworkExtras
}) {
  const [tab, setTab] = useState<Tab>('oversigt')
  const { runs, failedCount, agents, scheduled, overview } = useMissionControl(config, isOwner)

  const running = runs.filter((r) => {
    const s = String(r.status || '').toLowerCase()
    return s === 'running' || s === 'active' || s === 'working'
  }).length

  const counts = {
    running,
    failed: failedCount,
    pendingApprovals: queue.length + (isOwner ? extras.shareGuard.length : 0),
    scheduled: scheduled.length,
    agents: agents.length,
    costUsd: overview?.total_cost_usd,
  }

  const tabs = TABS.filter((t) => isOwner || !t.ownerOnly)

  const approvalsPane = (
    <>
      <ApprovalQueue items={queue} onResolve={onResolveQueue} />
      {isOwner && extras.shareGuard.length > 0 && (
        <section className="cowork-pane" style={{ marginTop: 12 }}>
          <div className="cowork-pane-head">Deling-guard <span className="cowork-count">{extras.shareGuard.length}</span></div>
          <ShareGuardPane items={extras.shareGuard} onResolve={extras.onResolveShare} />
        </section>
      )}
    </>
  )

  const liveNow = running > 0
  return (
    <div className="mc">
      <div className="mc-header">
        <div className="mc-header-title">
          <span className={`mc-live-dot ${liveNow ? 'on' : ''}`} />
          <h2>Mission Control</h2>
          <span className="mc-header-sub">{liveNow ? `${running} kører nu` : 'alt roligt'}</span>
        </div>
      </div>

      <SummaryBar counts={counts} onPick={(t) => setTab(t)} />

      <div className="mc-tabs">
        {tabs.map((t) => (
          <button
            key={t.id}
            type="button"
            className={`mc-tab ${tab === t.id ? 'active' : ''}`}
            onClick={() => setTab(t.id)}
          >
            {t.label}
            {t.id === 'godkendelser' && counts.pendingApprovals > 0 && <span className="mc-badge">{counts.pendingApprovals}</span>}
          </button>
        ))}
      </div>

      <div className="mc-body">
        {tab === 'oversigt' && (
          <div className="mc-overview">
            <section className="cowork-pane">
              <div className="cowork-pane-head">Afventer dig <span className="cowork-count">{counts.pendingApprovals}</span></div>
              {approvalsPane}
            </section>
            <section className="cowork-pane">
              <div className="cowork-pane-head">Seneste kørsler</div>
              <RunsTable config={config} runs={runs.slice(0, 8)} />
            </section>
            {isOwner && (
              <section className="cowork-pane">
                <div className="cowork-pane-head">Agenter <span className="cowork-count">{agents.length}</span></div>
                <AgentRoster agents={agents} />
              </section>
            )}
          </div>
        )}
        {tab === 'runs' && <RunsTable config={config} runs={runs} />}
        {tab === 'agenter' && isOwner && <AgentRoster agents={agents} />}
        {tab === 'godkendelser' && approvalsPane}
        {tab === 'opgaver' && (
          <div className="mc-overview">
            <section className="cowork-pane">
              <div className="cowork-pane-head">Todo &amp; initiativer</div>
              <TodoPane todos={extras.todos} config={isOwner ? config : undefined} onChanged={extras.refresh} />
            </section>
            <section className="cowork-pane">
              <div className="cowork-pane-head">Planer <span className="cowork-count">{extras.plans.length}</span></div>
              <PlansPane plans={extras.plans} />
            </section>
            {isOwner && (
              <section className="cowork-pane">
                <div className="cowork-pane-head">Kanaler</div>
                <ChannelsPane channels={extras.channels} />
              </section>
            )}
          </div>
        )}
        {tab === 'cost' && isOwner && <CostPanel config={config} />}
        {tab === 'haendelser' && isOwner && <EventStream config={config} />}
        {tab === 'planlagt' && (
          scheduled.length === 0 ? (
            <div className="cowork-empty">Ingen planlagte opgaver</div>
          ) : (
            <div className="mc-schedules">
              {scheduled.map((s) => (
                <div key={s.task_id} className="mc-schedule-row">
                  <StatusChip status={s.status} />
                  <span className="mc-schedule-focus">{s.focus || s.task_id}</span>
                  <span className="mc-schedule-at mc-mono">{s.run_at ? fmt(s.run_at) : ''}</span>
                </div>
              ))}
            </div>
          )
        )}
      </div>
    </div>
  )
}

function fmt(iso: string): string {
  try {
    return new Date(iso).toLocaleString('da-DK', {
      day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit',
    })
  } catch {
    return iso
  }
}
