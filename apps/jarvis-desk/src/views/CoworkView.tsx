import { type ReactNode } from 'react'
import { normalizeZone, type Zone } from '../lib/coworkZone'
import { useSettings } from '../hooks/useSettings'
import { useCoworkData } from '../hooks/useCoworkData'
import { MissionControl } from '../components/cowork/missioncontrol/MissionControl'
import { CoworkZones } from '../components/cowork/CoworkZones'
import { CategoryPage, CategorySection } from '../components/cowork/CategoryPage'
import { JarvisMind } from '../components/cowork/JarvisMind'
import { CentralBadge } from '../components/shell/CentralBadge'
import { MarketplacePane } from '../components/cowork/MarketplacePane'
import { CheapLanePanel } from '../components/cowork/cheaplane/CheapLanePanel'
import { AgentPoolPanel } from '../components/cowork/agentpool/AgentPoolPanel'
import { ProvidersPanel } from '../components/cowork/providers/ProvidersPanel'
import { AccountSection } from '../components/settings/AccountSection'
import { KvoteSection } from '../components/settings/KvoteSection'
import { ThemeSection } from '../components/settings/ThemeSection'
import { SprogSection } from '../components/settings/SprogSection'
import { SvarstilSection } from '../components/settings/SvarstilSection'
import { WorkspaceSection } from '../components/settings/WorkspaceSection'
import { MemorySection } from '../components/settings/MemorySection'
import { PermissionsSection } from '../components/settings/PermissionsSection'
import { JarvisSection } from '../components/settings/JarvisSection'
import { AppsSection } from '../components/settings/AppsSection'
import { McpSection } from '../components/settings/McpSection'
import { WorkbenchSection } from '../components/settings/WorkbenchSection'
import { TotpSetup } from '../components/settings/TotpSetup'
import { PluginsPanel } from '../components/settings/PluginsPanel'
import { ConnectionSection } from '../components/settings/ConnectionSection'
import { LocationSection } from '../components/settings/LocationSection'
import { PresenceSection } from '../components/settings/PresenceSection'
import { NotificationsSection } from '../components/settings/NotificationsSection'
import { DataPrivacyPanel } from '../components/DataPrivacyPanel'
import { KeyboardHelpPanel } from '../components/KeyboardHelpPanel'
import { AboutPanel } from '../components/AboutPanel'

/** Arbejde pages reuse the existing feature components and their backend truth.
 * Zone aliases keep older open_ui_panel and command-palette calls working. */
export function CoworkView({
  role = 'owner', sessionId,
}: { role?: 'owner' | 'member' | 'guest'; sessionId?: string | null }) {
  const { settings, auth } = useSettings()
  const isOwner = role === 'owner'
  const config = settings ? { apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken } : undefined
  const { queue, plans, todos, channels, shareGuard, agents, resolve, resolveShare, refresh } = useCoworkData(config, isOwner)
  void agents

  const missionControl = (
    <MissionControl
      config={config}
      isOwner={isOwner}
      queue={queue}
      onResolveQueue={resolve}
      extras={{ plans, todos, channels, shareGuard, refresh, onResolveShare: resolveShare }}
    />
  )

  const page = (zone: Zone): ReactNode => {
    switch (normalizeZone(zone)) {
      case 'mc': return missionControl

      case 'agentPool': return isOwner ? (
        <CategoryPage title="Agent pool" description="Se hvilke agenter der findes, hvad de arbejder på, og hvad deres kørsler koster." wide>
          <AgentPoolPanel config={config} />
        </CategoryPage>
      ) : null

      case 'capacity': return isOwner ? (
        <CategoryPage title="Modeller og kapacitet" description="Følg modeltrafik, ledig kapacitet og de udbydere Jarvis bruger." focusSection={zone} wide>
          <CategorySection id="cheapLane" title="Cheap Lane" description="Fordeling, kapacitet og styring af de billige modelkørsler.">
            <CheapLanePanel config={config} />
          </CategorySection>
          <CategorySection id="providers" title="Udbydere" description="Tilgængelige modeller og forbindelser til dem.">
            <ProvidersPanel config={config} />
          </CategorySection>
        </CategoryPage>
      ) : null

      case 'integrations': return (
        <CategoryPage title="Værktøjer og forbindelser" description="Find nye værktøjer og administrer de apps, MCP-servere og plugins Jarvis kan bruge." focusSection={zone} wide>
          <CategorySection id="marketplace" title="Find værktøjer">
            <MarketplacePane config={config} />
          </CategorySection>
          <CategorySection id="connections" title="Apps, MCP og plugins">
            {isOwner && <McpSection config={config} />}
            <AppsSection config={config} />
            {isOwner && <PluginsPanel config={config} />}
          </CategorySection>
        </CategoryPage>
      )

      case 'general': return (
        <CategoryPage title="Generelt" description="Tilpas hvordan Desk ser ud, svarer og giver dig besked." focusSection={zone}>
          <CategorySection id="appearance" title="Udseende"><ThemeSection /></CategorySection>
          <CategorySection id="sprog" title="Sprog og svarstil">
            <SprogSection config={config} />
            <SvarstilSection config={config} />
          </CategorySection>
          <CategorySection id="notifications" title="Notifikationer"><NotificationsSection config={config} /></CategorySection>
          <CategorySection id="location" title="Lokation" description="Vælg om Jarvis må kende din omtrentlige eller præcise placering.">
            <LocationSection />
          </CategorySection>
        </CategoryPage>
      )

      case 'account': return (
        <CategoryPage title="Konto og sikkerhed" description="Din profil, adgang, enheder og grænser for kontoen." focusSection={zone}>
          <CategorySection id="konto" title="Profil og enheder">
            <AccountSection config={config} />
          </CategorySection>
          <CategorySection title="Kvote"><KvoteSection config={config} /></CategorySection>
          {isOwner && <CategorySection title="Ekstra bekræftelse"><TotpSetup config={config} /></CategorySection>}
          <CategorySection id="privacy" title="Privatliv og tilladelser">
            <DataPrivacyPanel config={config} />
            <PermissionsSection config={config} />
          </CategorySection>
        </CategoryPage>
      )

      case 'workspace': return (
        <CategoryPage title="Arbejdsområde" description="Vælg hvor Jarvis arbejder, og hvordan arbejdet kan styres.">
          <CategorySection id="workspace" title="Mapper og filer"><WorkspaceSection config={config} /></CategorySection>
          {isOwner && (
            <CategorySection title="Arbejdskontrol">
              <WorkbenchSection config={config} sessionId={sessionId} />
            </CategorySection>
          )}
        </CategoryPage>
      )

      case 'jarvis': return (
        <CategoryPage title="Jarvis og hukommelse" description="Styr hvad Jarvis husker, og hvordan han er til stede." focusSection={zone === 'jarvis' ? undefined : zone}>
          <CategorySection id="memory" title="Hukommelse"><MemorySection config={config} /></CategorySection>
          {isOwner && (
            <>
              <CategorySection id="presence" title="Tilstedeværelse"><PresenceSection /></CategorySection>
              <CategorySection id="jarvis" title="Jarvis"><JarvisSection config={config} /></CategorySection>
            </>
          )}
        </CategoryPage>
      )

      case 'system': return isOwner ? (
        <CategoryPage title="Systemstatus" description="Teknisk tilstand og avanceret indsigt i Jarvis' drift." focusSection={zone} wide>
          <CategorySection id="central" title="Central"><CentralBadge config={config} isOwner={isOwner} /></CategorySection>
          <CategorySection id="jarvisMind" title="Jarvis Mind"><JarvisMind config={config} /></CategorySection>
        </CategoryPage>
      ) : null

      case 'about': return (
        <CategoryPage title="Om og hjælp" description="Version, tastaturgenveje og oplysninger om forbindelsen." focusSection={zone}>
          <CategorySection title="Om Desk"><AboutPanel apiBaseUrl={settings?.apiBaseUrl} role={auth?.role} model={settings?.defaultModel} /></CategorySection>
          <CategorySection title="Tastaturgenveje"><KeyboardHelpPanel /></CategorySection>
          <CategorySection title="Forbindelse"><ConnectionSection /></CategorySection>
        </CategoryPage>
      )

      default: return missionControl
    }
  }

  return (
    <div className="coworkview">
      <CoworkZones>{page}</CoworkZones>
    </div>
  )
}
