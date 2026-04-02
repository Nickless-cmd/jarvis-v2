import { Activity, RefreshCcw, Radio, Zap } from 'lucide-react'
import { useMemo, useState } from 'react'
import { DetailDrawer } from '../components/mission-control/DetailDrawer'
import { CostTab } from '../components/mission-control/CostTab'
import { ContinuityTab } from '../components/mission-control/ContinuityTab'
import { DevelopmentTab } from '../components/mission-control/DevelopmentTab'
import { HardeningTab } from '../components/mission-control/HardeningTab'
import { LabTab } from '../components/mission-control/LabTab'
import { LivingMindTab } from '../components/mission-control/LivingMindTab'
import { MemoryTab } from '../components/mission-control/MemoryTab'
import { SelfReviewTab } from '../components/mission-control/SelfReviewTab'
import { MCTabBar } from '../components/mission-control/MCTabBar'
import { ObservabilityTab } from '../components/mission-control/ObservabilityTab'
import { OperationsTab } from '../components/mission-control/OperationsTab'
import { OverviewTab } from '../components/mission-control/OverviewTab'
import { SkillsTab } from '../components/mission-control/SkillsTab'
import { formatFreshness, mcUpdateModeLabel } from '../components/mission-control/meta'
import { useMissionControlPhaseA } from './useMissionControlPhaseA'

export function MissionControlPage({ selection, onSelectionChange }) {
  const {
    activeTab,
    setActiveTab,
    sections,
    drawer,
    isLoading,
    isRefreshing,
    lastRealtimeEventAt,
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

  const filteredObservability = useMemo(() => {
    if (!sections.observability) return sections.observability
    if (eventFamilyFilter === 'all') return sections.observability
    return {
      ...sections.observability,
      events: (sections.observability.events || []).filter((event) => event.family === eventFamilyFilter),
    }
  }, [sections.observability, eventFamilyFilter])

  const activeSectionData = sections[activeTab] || (activeTab === 'living-mind' || activeTab === 'self-review' || activeTab === 'continuity' || activeTab === 'development' ? sections.jarvis : null) || null
  const freshnessLabel = formatFreshness(activeSectionData?.fetchedAt)
  const updateModeLabel = mcUpdateModeLabel(activeTab)

  if (isLoading && !sections.overview) {
    return <div className="boot-screen">Loading Mission Control…</div>
  }

  return (
    <div className="mission-control-phasea">
      <section className="mc-header-card">
        <div className="mc-header-title">
          <p className="eyebrow">Mission Control</p>
        </div>
        <div className="mc-header-actions">
          <div className="mc-shell-status">
            <div className="mc-status-group">
              <span className={`mc-status-indicator ${lastRealtimeEventAt ? 'live' : 'idle'}`} title={lastRealtimeEventAt ? `Last event: ${formatFreshness(lastRealtimeEventAt)}` : 'No recent events'}>
                <Radio size={10} />
                {lastRealtimeEventAt ? 'LIVE' : 'IDLE'}
              </span>
              <span className="mc-status-indicator status-ok" title="Connection healthy">
                <Zap size={10} />
                ACTIVE
              </span>
            </div>
            <div className="mc-status-divider" />
            <div className="mc-meta-strip">
              <span className="mc-meta-pill" title={`Current tab freshness: ${freshnessLabel}`}>{freshnessLabel}</span>
              <span className="mc-meta-pill" title={`Update strategy for ${activeTab}`}>{updateModeLabel}</span>
            </div>
          </div>
          <button className="icon-btn" onClick={() => refreshAll({ background: true })} title="Refresh Mission Control">
            <RefreshCcw size={15} className={isRefreshing ? 'spin' : ''} />
          </button>
        </div>
      </section>

      <MCTabBar
        activeTab={activeTab}
        onChange={setActiveTab}
      />

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
        <OperationsTab
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
        />
      ) : null}

      {activeTab === 'observability' ? (
        <div className="mc-observability-shell">
          <div className="mc-toolbar">
            <label className="mc-filter">
              <span>Event family</span>
              <select value={eventFamilyFilter} onChange={(event) => setEventFamilyFilter(event.target.value)}>
                <option value="all">All</option>
                <option value="runtime">runtime</option>
                <option value="approvals">approvals</option>
                <option value="cost">cost</option>
                <option value="tool">tool</option>
                <option value="channel">channel</option>
                <option value="heartbeat">heartbeat</option>
                <option value="incident">incident</option>
              </select>
            </label>
          </div>
          <ObservabilityTab
            data={filteredObservability}
            onOpenEvent={openEventDetail}
            onOpenRun={openRunDetail}
          />
        </div>
      ) : null}

      {activeTab === 'living-mind' ? (
        <LivingMindTab
          data={sections.jarvis}
          onOpenItem={openJarvisDetail}
          onHeartbeatTick={actOnHeartbeatTick}
          heartbeatBusy={isRefreshing}
        />
      ) : null}

      {activeTab === 'self-review' ? (
        <SelfReviewTab data={sections.jarvis} onOpenItem={openJarvisDetail} />
      ) : null}

      {activeTab === 'continuity' ? (
        <ContinuityTab data={sections.jarvis} onOpenItem={openJarvisDetail} />
      ) : null}

      {activeTab === 'cost' ? <CostTab data={sections.cost} /> : null}

      {activeTab === 'development' ? (
        <DevelopmentTab data={sections.jarvis} onOpenItem={openJarvisDetail} />
      ) : null}

      {activeTab === 'memory' ? <MemoryTab /> : null}
      {activeTab === 'skills' ? <SkillsTab /> : null}
      {activeTab === 'hardening' ? <HardeningTab /> : null}
      {activeTab === 'lab' ? <LabTab /> : null}

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
