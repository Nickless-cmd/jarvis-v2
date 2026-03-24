import { RefreshCcw } from 'lucide-react'
import { useMemo, useState } from 'react'
import { DetailDrawer } from '../components/mission-control/DetailDrawer'
import { JarvisTab } from '../components/mission-control/JarvisTab'
import { MCTabBar } from '../components/mission-control/MCTabBar'
import { ObservabilityTab } from '../components/mission-control/ObservabilityTab'
import { OperationsTab } from '../components/mission-control/OperationsTab'
import { OverviewTab } from '../components/mission-control/OverviewTab'
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

  const activeSectionData = sections[activeTab] || null
  const freshnessLabel = formatFreshness(activeSectionData?.fetchedAt)
  const updateModeLabel = mcUpdateModeLabel(activeTab)

  if (isLoading && !sections.overview) {
    return <div className="boot-screen">Loading Mission Control…</div>
  }

  return (
    <div className="mission-control-phasea">
      <section className="hero-card compact mc-header-card">
        <div>
          <p className="eyebrow">Mission Control</p>
          <h1>Control room</h1>
          <p>Observability, execution, and evidence for Jarvis as an experiment.</p>
        </div>
        <div className="mc-header-actions">
          <div className="mc-meta-strip">
            <span className="mc-meta-pill" title={`Current tab freshness: ${freshnessLabel}`}>{freshnessLabel}</span>
            <span className="mc-meta-pill" title={`Update strategy for ${activeTab}`}>{updateModeLabel}</span>
            <span
              className={`mc-meta-pill ${lastRealtimeEventAt ? 'live' : ''}`}
              title="Shared realtime manager active only while Mission Control is open"
            >
              {lastRealtimeEventAt ? `Last event ${formatFreshness(lastRealtimeEventAt)}` : 'MC live'}
            </span>
          </div>
          <button className="icon-btn" onClick={() => refreshAll({ background: true })} title="Refresh Mission Control">
            <RefreshCcw size={15} className={isRefreshing ? 'spin' : ''} />
          </button>
        </div>
      </section>

      <MCTabBar activeTab={activeTab} onChange={setActiveTab} />

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

      {activeTab === 'jarvis' ? (
        <JarvisTab
          data={sections.jarvis}
          onOpenItem={openJarvisDetail}
        />
      ) : null}

      <DetailDrawer drawer={drawer} onClose={closeDrawer} onApprovalAction={actOnApproval} />
    </div>
  )
}
