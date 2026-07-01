import { type ReactNode } from 'react'
import { normalizeZone, type Zone } from '../lib/coworkZone'
import { useSettings } from '../hooks/useSettings'
import { useCoworkData } from '../hooks/useCoworkData'
import { ApprovalQueue } from '../components/cowork/ApprovalQueue'
import { PlansPane } from '../components/cowork/PlansPane'
import { TodoPane } from '../components/cowork/TodoPane'
import { ChannelsPane } from '../components/cowork/ChannelsPane'
import { ShareGuardPane } from '../components/cowork/ShareGuardPane'
import { AgentDispatchPane } from '../components/cowork/AgentDispatchPane'
import { CoworkZones } from '../components/cowork/CoworkZones'
import { JarvisMind } from '../components/cowork/JarvisMind'
import { CentralHud } from '../components/cowork/CentralHud'
import { MarketplacePane } from '../components/cowork/MarketplacePane'
import { AccountSection } from '../components/settings/AccountSection'
import { KvoteSection } from '../components/settings/KvoteSection'
import { ThemeSection } from '../components/settings/ThemeSection'
import { SprogSection } from '../components/settings/SprogSection'
import { WorkspaceSection } from '../components/settings/WorkspaceSection'
import { MemorySection } from '../components/settings/MemorySection'
import { PermissionsSection } from '../components/settings/PermissionsSection'
import { JarvisSection } from '../components/settings/JarvisSection'
import { AppsSection } from '../components/settings/AppsSection'
import { McpSection } from '../components/settings/McpSection'
import { TotpSetup } from '../components/settings/TotpSetup'
import { PluginsPanel } from '../components/settings/PluginsPanel'
import { ConnectionSection } from '../components/settings/ConnectionSection'
import { LocationSection } from '../components/settings/LocationSection'
import { NotificationsSection } from '../components/settings/NotificationsSection'
import { DataPrivacyPanel } from '../components/DataPrivacyPanel'
import { KeyboardHelpPanel } from '../components/KeyboardHelpPanel'
import { AboutPanel } from '../components/AboutPanel'
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

  const ownerAuth = auth?.role === 'owner'
  const wrap = (children: ReactNode) => <div className="cowork-settings">{children}</div>

  // Hver zone = ÉN klar destination (flad simpel navigation, Bjørn 2026-07-01). Sektions-
  // komponenterne genbruges uændret — de er blot flyttet til hver sin zone i stedet for én
  // samlet scroll. 'settings' (legacy-alias) og ukendte → Konto.
  const zoneContent = (raw: Zone): ReactNode => {
    switch (normalizeZone(raw)) {
      case 'mc': return missionControl
      case 'marketplace': return <MarketplacePane config={config} />

      case 'konto': return wrap(<>
        <AccountSection config={config} />
        <KvoteSection config={config} />
        {ownerAuth && <TotpSetup config={config} />}
      </>)
      case 'privacy': return wrap(<>
        <DataPrivacyPanel config={config} />
        <PermissionsSection config={config} />
      </>)
      case 'notifications': return wrap(<NotificationsSection config={config} />)

      case 'appearance': return wrap(<ThemeSection />)
      case 'sprog': return wrap(<SprogSection config={config} />)
      case 'location': return wrap(<LocationSection />)

      case 'memory': return wrap(<MemorySection config={config} />)
      case 'workspace': return wrap(<WorkspaceSection config={config} />)
      case 'connections': return wrap(<>
        {ownerAuth && <McpSection config={config} />}
        <AppsSection config={config} />
        {ownerAuth && <PluginsPanel config={config} />}
      </>)

      case 'central': return isOwner ? <CentralHud config={config} /> : missionControl
      case 'jarvisMind': return isOwner ? <JarvisMind config={config} /> : missionControl
      case 'jarvis': return ownerAuth ? wrap(<JarvisSection config={config} />) : missionControl

      case 'about': return wrap(<>
        <AboutPanel apiBaseUrl={settings?.apiBaseUrl} role={auth?.role} model={settings?.defaultModel} />
        <KeyboardHelpPanel />
        <ConnectionSection />
      </>)

      default: return wrap(<AccountSection config={config} />)
    }
  }

  return (
    <div className="coworkview">
      <CoworkZones>
        {(zone) => zoneContent(zone)}
      </CoworkZones>
    </div>
  )
}
