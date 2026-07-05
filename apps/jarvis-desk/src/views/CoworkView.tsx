import { type ReactNode } from 'react'
import { normalizeZone, type Zone } from '../lib/coworkZone'
import { useSettings } from '../hooks/useSettings'
import { useCoworkData } from '../hooks/useCoworkData'
import { MissionControl } from '../components/cowork/missioncontrol/MissionControl'
import { CoworkZones } from '../components/cowork/CoworkZones'
import { JarvisMind } from '../components/cowork/JarvisMind'
import { CentralBadge } from '../components/shell/CentralBadge'
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
import { PresenceSection } from '../components/settings/PresenceSection'
import { NotificationsSection } from '../components/settings/NotificationsSection'
import { DataPrivacyPanel } from '../components/DataPrivacyPanel'
import { KeyboardHelpPanel } from '../components/KeyboardHelpPanel'
import { AboutPanel } from '../components/AboutPanel'

/** Cowork command center. 'mc'-zonen = det rigtige Mission Control-kontrolcenter;
 *  de øvrige zoner = én settings-sektion hver (flad simpel navigation, Bjørn 2026-07-01). */
export function CoworkView({ role = 'owner' }: { role?: 'owner' | 'member' | 'guest' }) {
  const { settings, auth } = useSettings()
  const isOwner = role === 'owner'
  const config = settings ? { apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken } : undefined
  const { queue, plans, todos, channels, shareGuard, agents, resolve, resolveShare, refresh } = useCoworkData(config, isOwner)
  void agents  // dispatch-agenter vises nu via MC's /mc/agents-roster (rigere data)

  const missionControl = (
    <MissionControl
      config={config}
      isOwner={isOwner}
      queue={queue}
      onResolveQueue={resolve}
      extras={{ plans, todos, channels, shareGuard, refresh, onResolveShare: resolveShare }}
    />
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
      case 'presence': return wrap(<PresenceSection />)

      case 'memory': return wrap(<MemorySection config={config} />)
      case 'workspace': return wrap(<WorkspaceSection config={config} />)
      case 'connections': return wrap(<>
        {ownerAuth && <McpSection config={config} />}
        <AppsSection config={config} />
        {ownerAuth && <PluginsPanel config={config} />}
      </>)

      case 'central': return (
        <div className="central-zone">
          <CentralBadge config={config} isOwner={isOwner} />
          <div className="central-zone-cap">Central-status — klik for fuld CLI (kun owner)</div>
        </div>
      )
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
