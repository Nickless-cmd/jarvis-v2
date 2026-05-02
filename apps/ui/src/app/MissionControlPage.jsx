import { Command, RefreshCcw } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { s, T, mono } from '../shared/theme/tokens'
import { Chip } from '../components/mission-control/shared'
import { DetailDrawer } from '../components/mission-control/DetailDrawer'
import { ReflectionTab } from '../components/mission-control/ReflectionTab'
import { HardeningTab } from '../components/mission-control/HardeningTab'
import { LabTab } from '../components/mission-control/LabTab'
import { MindTab } from '../components/mission-control/MindTab'
import { MemoryTab } from '../components/mission-control/MemoryTab'
import { MCTabBar } from '../components/mission-control/MCTabBar'
import { ObservabilityTab } from '../components/mission-control/ObservabilityTab'
import { OpsTab } from '../components/mission-control/OpsTab'
import { OverviewTab } from '../components/mission-control/OverviewTab'
import { SkillsTab } from '../components/mission-control/SkillsTab'
import { CouncilTab } from '../components/mission-control/CouncilTab'
import { RelationshipTab } from '../components/mission-control/RelationshipTab'
import { ProprioceptionTab } from '../components/mission-control/ProprioceptionTab'
import { ThreadsTab } from '../components/mission-control/ThreadsTab'
import { CheapBalancerTab } from '../components/mission-control/CheapBalancerTab'
import { formatFreshness, mcUpdateModeLabel } from '../components/mission-control/meta'
import { useMissionControlPhaseA } from './useMissionControlPhaseA'
import { AmbientPresence } from '../components/AmbientPresence'

export function MissionControlPage({ selection, onSelectionChange, initialTab, onViewChange }) {
  const {
    activeTab,
    setActiveTab,
    sections,
    drawer,
    isLoading,
    isRefreshing,
    lastRealtimeEventAt,
    realtimeConnected,
    navigateTo,
    refreshAll,
    closeDrawer,
    openRunDetail,
    openEventDetail,
    openApprovalDetail,
    openSessionDetail,
    openJarvisDetail,
    actOnApproval,
    actOnToolIntent,
    actOnContractCandidate,
    actOnHeartbeatTick,
    actOnDevelopmentFocus,
    toolIntentActionBusy,
    toolIntentActionError,
  } = useMissionControlPhaseA({ active: true, selection })
  const [eventFamilyFilter, setEventFamilyFilter] = useState('all')

  useEffect(() => {
    if (initialTab) {
      setActiveTab(initialTab)
    }
  }, [initialTab])

  const filteredObservability = useMemo(() => {
    if (!sections.observability) return sections.observability
    if (eventFamilyFilter === 'all') return sections.observability
    return {
      ...sections.observability,
      events: (sections.observability.events || []).filter((event) => event.family === eventFamilyFilter),
    }
  }, [sections.observability, eventFamilyFilter])

  const activeSectionData = sections[activeTab] || (activeTab === 'mind' || activeTab === 'reflection' ? sections.jarvis : null) || null
  const freshnessLabel = formatFreshness(activeSectionData?.fetchedAt)
  const updateModeLabel = mcUpdateModeLabel(activeTab)

  // The chip reflects WebSocket connection state, not event arrival —
  // a quiet eventbus shouldn't make the indicator say "Offline" when the
  // socket is actually healthy. lastRealtimeEventAt is still tracked for
  // freshness-style use cases elsewhere.
  const realtimeColor = realtimeConnected ? T.green : T.text3
  const realtimeLabel = realtimeConnected ? 'Realtime: Connected' : 'Realtime: Offline'
  const pendingApprovals = sections.overview?.summaries?.pendingApprovals ?? 0
  const totalCost = sections.overview?.summaries?.totalCostUsd ?? 0

  if (isLoading && !sections.overview) {
    return (
      <div style={s({ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100dvh', background: T.bgBase, color: T.text2, fontFamily: T.sans })}>
        Loading Mission Control…
      </div>
    )
  }

  return (
    <div style={s({ display: 'flex', flexDirection: 'column', height: '100%', width: '100%', background: T.bgBase, fontFamily: T.sans, color: T.text1, overflow: 'hidden' })}>
      <AmbientPresence />

        {/* ── Header (52px, compact) ── */}
        <div
          style={s({
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '0 24px',
            height: 52,
            background: T.headerGlass,
            backdropFilter: 'blur(12px)',
            borderBottom: `1px solid ${T.border0}`,
            flexShrink: 0,
          })}
        >
          <div style={s({ display: 'flex', alignItems: 'center', gap: 12 })}>
            <div style={s({ display: 'flex', alignItems: 'center', gap: 8 })}>
              <Command size={16} color={T.accentText} />
              <span style={s({ fontSize: 14, fontWeight: 600, letterSpacing: '0.04em' })}>Mission Control</span>
            </div>
            <Chip color={realtimeColor}>{realtimeLabel}</Chip>
            <Chip color={T.green}>State: Live</Chip>
            <Chip color={pendingApprovals > 0 ? T.amber : T.text3}>Approvals: {pendingApprovals}</Chip>
          </div>
          <div style={s({ display: 'flex', alignItems: 'center', gap: 8 })}>
            <Chip color={T.text3}>{updateModeLabel}</Chip>
            <Chip color={T.text3}>{freshnessLabel}</Chip>
            <button
              onClick={() => refreshAll({ background: true })}
              title="Refresh Mission Control"
              style={s({
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                width: 32, height: 32, borderRadius: 8, border: `1px solid ${T.border1}`,
                background: T.glass, color: T.text2, cursor: 'pointer',
                transition: 'all 0.2s ease',
              })}
              onMouseEnter={(e) => { e.currentTarget.style.background = T.bgOverlay; e.currentTarget.style.borderColor = T.accent }}
              onMouseLeave={(e) => { e.currentTarget.style.background = T.glass; e.currentTarget.style.borderColor = T.border1 }}
            >
              <RefreshCcw size={13} style={isRefreshing ? { animation: 'spin .8s linear infinite' } : undefined} />
            </button>
          </div>
        </div>

        {/* ── Tab bar ── */}
        <MCTabBar activeTab={activeTab} onChange={setActiveTab} />

        {/* ── Content area ── */}
        <div
          style={s({
            flex: 1,
            minHeight: 0,
            width: '100%',
            overflowX: 'hidden',
            overflowY: 'auto',
            overscrollBehavior: 'contain',
            padding: '20px 24px',
          })}
        >
          {activeTab === 'overview' ? (
            <OverviewTab
              data={sections.overview}
              onJump={navigateTo}
              onOpenEvent={(event) => {
                navigateTo('observability', 'event-timeline')
                openEventDetail(event)
              }}
            />
          ) : null}

          {activeTab === 'operations' ? (
            <OpsTab
              data={sections.operations}
              selection={selection}
              onSelectionChange={onSelectionChange}
              onOpenRun={openRunDetail}
              onOpenSession={openSessionDetail}
              onOpenApproval={openApprovalDetail}
              onOpenItem={openJarvisDetail}
              onToolIntentAction={actOnToolIntent}
              toolIntentActionBusy={toolIntentActionBusy}
              toolIntentActionError={toolIntentActionError}
              thoughtProposals={sections.jarvis?.thoughtProposals || null}
              onResolveThoughtProposal={async (id, decision) => {
                try {
                  await fetch(`/mc/thought-proposals/${id}/resolve`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ decision }),
                  })
                  refreshAll()
                } catch (_) {}
              }}
            />
          ) : null}

          {activeTab === 'observability' ? (
            <div style={s({ display: 'flex', flexDirection: 'column', gap: 12 })}>
              <div style={s({ display: 'flex', alignItems: 'center', gap: 8 })}>
                <span style={s({ ...mono, fontSize: 9, color: T.text3 })}>Event family</span>
                <select
                  value={eventFamilyFilter}
                  onChange={(event) => setEventFamilyFilter(event.target.value)}
                  style={s({
                    padding: '4px 8px', background: T.bgOverlay, border: `1px solid ${T.border1}`,
                    borderRadius: 6, color: T.text1, fontSize: 11, ...mono, outline: 'none',
                  })}
                >
                  <option value="all">All</option>
                  <option value="runtime">runtime</option>
                  <option value="approvals">approvals</option>
                  <option value="cost">cost</option>
                  <option value="tool">tool</option>
                  <option value="channel">channel</option>
                  <option value="heartbeat">heartbeat</option>
                  <option value="incident">incident</option>
                </select>
              </div>
              <ObservabilityTab
                data={filteredObservability}
                onOpenEvent={openEventDetail}
                onOpenRun={openRunDetail}
              />
            </div>
          ) : null}

          {activeTab === 'mind' ? (
            <MindTab
              data={sections.jarvis}
              onOpenItem={openJarvisDetail}
              onHeartbeatTick={actOnHeartbeatTick}
              heartbeatBusy={isRefreshing}
            />
          ) : null}

          {activeTab === 'reflection' ? (
            <ReflectionTab
              data={sections.jarvis}
              onOpenItem={openJarvisDetail}
              onDevelopmentFocusAction={actOnDevelopmentFocus}
            />
          ) : null}


          {activeTab === 'council' ? <CouncilTab /> : null}
          {activeTab === 'memory' ? <MemoryTab /> : null}
          {activeTab === 'skills' ? <SkillsTab /> : null}
          {activeTab === 'hardening' ? <HardeningTab /> : null}
          {activeTab === 'lab' ? <LabTab /> : null}
          {activeTab === 'relationship' ? <RelationshipTab /> : null}
          {activeTab === 'proprioception' ? <ProprioceptionTab /> : null}
{activeTab === 'threads' ? <ThreadsTab /> : null}
          {activeTab === 'balancer' ? <CheapBalancerTab /> : null}
        </div>

      <DetailDrawer
        drawer={drawer}
        onClose={closeDrawer}
        onApprovalAction={actOnApproval}
        onContractCandidateAction={actOnContractCandidate}
        onDevelopmentFocusAction={actOnDevelopmentFocus}
      />
    </div>
  )
}
