import { useSettings } from '../hooks/useSettings'
import { useCoworkData } from '../hooks/useCoworkData'
import { ApprovalQueue } from '../components/cowork/ApprovalQueue'
import { PlansPane } from '../components/cowork/PlansPane'
import { TodoPane } from '../components/cowork/TodoPane'
import { ChannelsPane } from '../components/cowork/ChannelsPane'
import { ShareGuardPane } from '../components/cowork/ShareGuardPane'
import { AgentDispatchPane } from '../components/cowork/AgentDispatchPane'
import { CoworkZones } from '../components/cowork/CoworkZones'
import { AccountSection } from '../components/settings/AccountSection'
import { KvoteSection } from '../components/settings/KvoteSection'
import { ThemeSection } from '../components/settings/ThemeSection'
import { SprogSection } from '../components/settings/SprogSection'
import { WorkspaceSection } from '../components/settings/WorkspaceSection'
import { MemorySection } from '../components/settings/MemorySection'
import { PermissionsSection } from '../components/settings/PermissionsSection'
import { TotpSetup } from '../components/settings/TotpSetup'
import { PluginsPanel } from '../components/settings/PluginsPanel'
import { activeAgentsToView } from '../lib/coworkApi'

/** Cowork command center: to zoner. Mission Control = rolle-bevidst rude-grid
 *  (uændret); Indstillinger = konto + (owner) TOTP/plugins. */
export function CoworkView({ role = 'owner' }: { role?: 'owner' | 'member' | 'guest' }) {
  const { settings, auth } = useSettings()
  const isOwner = role === 'owner'
  const config = settings ? { apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken } : undefined
  const { queue, plans, todos, channels, shareGuard, agents, resolve, resolveShare, refresh } = useCoworkData(config, isOwner)

  const missionControl = (
    <div className="cowork-grid">
      <section className="cowork-pane">
        <div className="cowork-pane-head">Godkendelser <span className="cowork-count">{queue.length}</span></div>
        <ApprovalQueue items={queue} onResolve={resolve} />
      </section>
      <section className="cowork-pane">
        <div className="cowork-pane-head">Planer <span className="cowork-count">{plans.length}</span></div>
        <PlansPane plans={plans} />
      </section>
      <section className="cowork-pane">
        <div className="cowork-pane-head">Todo &amp; initiativer</div>
        <TodoPane todos={todos} config={isOwner ? config : undefined} onChanged={refresh} />
      </section>
      {isOwner && (
        <section className="cowork-pane">
          <div className="cowork-pane-head">Kanaler</div>
          <ChannelsPane channels={channels} />
        </section>
      )}
      {isOwner && agents.length > 0 && (
        <section className="cowork-pane">
          <div className="cowork-pane-head">
            Agenter <span className="cowork-count">{agents.length}</span>
          </div>
          <AgentDispatchPane view={activeAgentsToView(agents)} />
        </section>
      )}
      {isOwner && shareGuard.length > 0 && (
        <section className="cowork-pane">
          <div className="cowork-pane-head">
            Deling-guard <span className="cowork-count">{shareGuard.length}</span>
          </div>
          <ShareGuardPane items={shareGuard} onResolve={resolveShare} />
        </section>
      )}
    </div>
  )

  const settingsZone = (
    <div className="cowork-settings">
      <AccountSection config={config} />
      <WorkspaceSection config={config} />
      <MemorySection config={config} />
      <PermissionsSection config={config} />
      <KvoteSection config={config} />
      <SprogSection config={config} />
      <ThemeSection />
      {auth?.role === 'owner' && <TotpSetup config={config} />}
      {auth?.role === 'owner' && <PluginsPanel config={config} />}
    </div>
  )

  return (
    <div className="coworkview">
      <CoworkZones missionControl={missionControl} settings={settingsZone} />
    </div>
  )
}
