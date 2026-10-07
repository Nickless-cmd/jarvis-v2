import { GenoptagelsesVarselHost } from './components/feedback/GenoptagelsesVarselHost'
import { useState, useEffect, useMemo, type ReactNode } from 'react'
import { UpdateHost } from './components/shell/UpdateHost'
import { DependencyCard } from './components/shell/DependencyCard'
import { useSettings } from './hooks/useSettings'
import { SessionProvider } from './contexts/SessionContext'
import { StreamProvider } from './contexts/StreamContext'
import { PermissionProvider } from './contexts/PermissionContext'
import { usePermission } from './hooks/usePermission'
import { useStream } from './hooks/useStream'
import { AppActionCard } from './components/rich/AppActionCard'
import { resolveAppAction } from './lib/appAction'
import { PanelProvider } from './contexts/PanelContext'
import { UiPanelWatcher } from './components/UiPanelWatcher'
import { ViewRequestWatcher } from './components/ViewRequestWatcher'
import { AiTransparencyNotice } from './components/AiTransparencyNotice'
import { GlobalShortcuts } from './components/GlobalShortcuts'
import { ApprovalNotifier } from './components/ApprovalNotifier'
import { NotifikationsToast } from './components/shell/NotifikationsToast'
import { PresenceHost } from './components/PresenceHost'
import { TakeoverHost } from './components/shell/TakeoverHost'
import { SessionSearch } from './components/SessionSearch'
import { usePanel } from './hooks/usePanel'
import { SplitLayout } from './components/panel/SplitLayout'
import { InspectorPanel } from './components/panel/InspectorPanel'
import { useSessions } from './hooks/useSessions'
import { SetupScreen } from './views/SetupScreen'
import { ChatView } from './views/ChatView'
import { PrivacyDialog } from './components/PrivacyDialog'
import { BugRapport } from './components/BugRapport'
import { CoworkView } from './views/CoworkView'
import { emitZone } from './lib/coworkZone'
import { CodeView } from './views/CodeView'
import { MemoryView } from './views/MemoryView'
import { SchedulingView } from './views/SchedulingView'
import { ImageGalleryView } from './views/ImageGalleryView'
import { ArtifactsView } from './views/ArtifactsView'
import { Sidebar, type Surface } from './components/shell/Sidebar'
// OpmaerksomhedsVaert fjernet (Bjørn 29/9-2026): det lille arbejder-felt i
// højre nederste hjørne skulle ud. Komponenten er bevaret — kun renderingen
// er fjernet. Genaktiveres med: import + <OpmaerksomhedsVaert setSurface={setSurface} />
import { DESK_CHROME } from './lib/deskChrome'
import { StatusBar } from './components/shell/StatusBar'
import './styles/tokens.css'
import './styles/app.css'
import './styles/liveness.css'
import './styles/environment-inspector.css'
import './styles/cheap-lane.css'
import './styles/cowork-categories.css'
import './styles/desk-settings.css'
import './styles/raekkevisning.css'
import './styles/chat-reading.css'

/** App = ren wiring. SettingsProvider er wrappet i main.tsx, så useSettings
 *  virker her. Ikke-konfigureret → SetupScreen. Ellers shell med aktiv flade. */
export function App() {
  const { settings, auth, isConfigured, update } = useSettings()
  const [surface, setSurface] = useState<Surface>('chat')

  // Konsolidering (Bjørn 2026-06-21): ÉN settings-flade. Tandhjul/genvej/SecondaryNav
  // navigerede før til en separat SettingsView (dobbelt-truth + ingen scroll). Nu
  // omdirigeres 'settings' instant til cowork-command-centerets Indstillinger-zone,
  // hvor ALLE sektioner bor.
  useEffect(() => {
    if (surface === 'settings') {
      emitZone('settings')
      setSurface('cowork')
    }
  }, [surface])

  // useMemo, ikke et frisk objekt-literal (8/9-2026). Alle fire providers
  // afhænger af `cfg`; et nyt objekt pr. render ville enten få dem til at
  // gen-hente ved hver render, eller — fordi App sjældent re-renderer — aldrig.
  // Session-listen ramte det sidste: den blev hentet én gang ved mount og
  // aldrig igen, så Bjørn måtte skifte til cowork og tilbage for at se nye
  // samtaler. Samme fejl som ArtifactPanel havde.
  //
  // OVER de tidlige returns (rettet 9/9-2026). Foerste udgave laa under dem,
  // og saa koerte hooket ikke saa laenge `settings` var null — men gjorde det
  // saa snart de ankom. React taeller hooks pr. render: «Rendered more hooks
  // than during the previous render», minified #310, og hele visningen faldt.
  // Et hook maa aldrig staa efter en betinget return.
  const cfg = useMemo(
    () => ({
      apiBaseUrl: settings?.apiBaseUrl ?? '',
      authToken: settings?.authToken ?? null,
    }),
    [settings?.apiBaseUrl, settings?.authToken],
  )

  if (!settings) return null
  if (!isConfigured) return <SetupScreen onSave={(cfg) => void update(cfg)} />

  return (
    <SessionProvider config={cfg} onRestore={(s) => setSurface(s)}>
      <StreamProvider config={cfg}>
        <PermissionProvider config={cfg}>
          <PanelProvider defaultWidth={480}>
            <Shell
              surface={surface}
              setSurface={setSurface}
              role={auth?.role ?? 'guest'}
              userName={auth?.display_name ?? 'Bruger'}
              model={settings.defaultModel}
            />
            <UiPanelWatcher config={cfg} setSurface={setSurface} />
            <ViewRequestWatcher config={cfg} />
            {/* OpmaerksomhedsVaert fjernet (Bjørn 29/9-2026) */}
            <AiTransparencyNotice onNavigate={setSurface} />
            <UpdateHost />
            <DependencyHost />
          </PanelProvider>
        </PermissionProvider>
      </StreamProvider>
    </SessionProvider>
  )
}

interface DepsBridge {
  detect: () => Promise<{ tool: string; present: boolean }[]>
  install: (tool: string) => Promise<{ ok: boolean; log?: string }>
}
function depsBridge(): DepsBridge | undefined {
  return (window as unknown as { jarvisDesk?: { deps?: DepsBridge } }).jarvisDesk?.deps
}

/** Detekterer manglende værktøjer ved opstart og tilbyder at installere dem. */
function DependencyHost() {
  const [missing, setMissing] = useState<string[]>([])
  const [busy, setBusy] = useState('')
  const [dismissed, setDismissed] = useState(false)
  useEffect(() => {
    const d = depsBridge()
    if (!d) return
    let cancelled = false
    void d.detect().then((tools) => {
      if (!cancelled) setMissing(tools.filter((t) => !t.present).map((t) => t.tool))
    }).catch(() => { /* ignore */ })
    return () => { cancelled = true }
  }, [])
  if (dismissed) return null
  const onInstall = (tool: string) => {
    const d = depsBridge()
    if (!d || busy) return
    setBusy(tool)
    void d.install(tool).then((r) => {
      if (r.ok) setMissing((m) => m.filter((t) => t !== tool))
    }).finally(() => setBusy(''))
  }
  return <DependencyCard missing={missing} onInstall={onInstall} onDismiss={() => setDismissed(true)} busy={busy} />
}

/** Lægger den trækbare split om den aktive view; panel viser det åbne artifact. */
function ShellWithPanel({ children }: { children: ReactNode }) {
  const panel = usePanel()
  const { settings } = useSettings()
  // useMemo, ikke et frisk objekt-literal (7/9-2026): ArtifactPanel'ets
  // fetch-effekt afhænger af `config`, så et nyt objekt ved HVER render fik
  // panelet til at nulstille indholdet og genhente ~hvert sekund — det så ud
  // som blink, og scroll-positionen røg med. Panelet var ubrugeligt for lange
  // filer.
  const config = useMemo(
    () => (settings ? { apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken } : undefined),
    [settings?.apiBaseUrl, settings?.authToken],
  )
  return (
    <SplitLayout
      open={panel.open}
      width={panel.width}
      onResize={panel.resize}
      panel={<InspectorPanel
        target={panel.target}
        canGoBack={panel.canGoBack}
        onBack={panel.back}
        onClose={panel.close}
        onOpenTarget={panel.openTarget}
        config={config}
      />}
    >
      {children}
    </SplitLayout>
  )
}

function Shell({
  surface,
  setSurface,
  role,
  userName,
  model,
}: {
  surface: Surface
  setSurface: (s: Surface) => void
  role: 'owner' | 'partner' | 'member' | 'guest'
  userName: string
  model: string
}) {
  const { activeId, select } = useSessions()
  const { settings } = useSettings()
  const cfg = settings ? { apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken } : undefined
  const [searchOpen, setSearchOpen] = useState(false)
  const [privacyOpen, setPrivacyOpen] = useState(false)
  // Fejl-rapporten bor her og ikke i Sidebar, af samme grund som
  // privatlivs-dialogen: begge er `<dialog>`-elementer der skal ligge i
  // top-laget MIDT på skærmen, ikke inde i sidens kolonne-layout.
  const [bugOpen, setBugOpen] = useState(false)
  return (
    <div className="window">
      <Sidebar surface={surface} onSurface={setSurface} userName={userName} onSearch={() => setSearchOpen(true)}
               onOpenBug={() => setBugOpen(true)} />
      <main className="main">
        <ShortcutsHost setSurface={setSurface} onSearch={() => setSearchOpen(true)} />
        <PresenceHost />

        <SessionSearch
          open={searchOpen}
          config={cfg}
          onSelect={(id) => { select(id); setSurface('chat') }}
          onClose={() => setSearchOpen(false)}
          erEjer={role === 'owner'}
          // Paletten kan nu ogsaa NAVIGERE (6/9-2026). «zone:x» gaar til
          // Arbejde og aabner zonen via den mekanisme Jarvis selv bruger
          // naar han kalder open_ui_panel; «surface:x» skifter flade.
          onNavigate={(id) => {
            if (id.startsWith('zone:')) {
              setSurface('cowork')
              emitZone(id.slice(5) as Parameters<typeof emitZone>[0])
            } else if (id.startsWith('surface:')) {
              setSurface(id.slice(8) as Surface)
            }
          }}
        />
        <ApprovalNotifierHost />
        <GenoptagelsesVarselHost sessionId={activeId} />
        <AppActionHost setSurface={setSurface} />
        <TakeoverHost surface={surface} setSurface={setSurface} />
        <ShellWithPanel>
          {surface === 'chat' && (
            <ChatView
              sessionId={activeId}
              userName={userName}
              onOpenMarketplace={() => { setSurface('cowork'); emitZone('marketplace') }}
              onOpenPrivacy={() => setPrivacyOpen(true)}
            />
          )}
          {surface === 'cowork' && <CoworkView role={role} sessionId={activeId} />}
          {surface === 'code' && (
            <CodeView
              sessionId={activeId}
              userName={userName}
              role={role}
              onOpenMarketplace={() => { setSurface('cowork'); emitZone('marketplace') }}
              onOpenPrivacy={() => setPrivacyOpen(true)}
            />
          )}
          {surface === 'memory' && <MemoryView role={role} />}
          {surface === 'gallery' && <ImageGalleryView onOpenChat={() => setSurface('chat')} />}
          {surface === 'artifacts' && <ArtifactsView onOpenCode={() => setSurface('code')} />}
          {surface === 'scheduling' && <SchedulingView role={role} />}
        </ShellWithPanel>
        {privacyOpen && <PrivacyDialog config={cfg} onClose={() => setPrivacyOpen(false)} />}
        {bugOpen && <BugRapport config={cfg} onClose={() => setBugOpen(false)} />}
        {DESK_CHROME.statusbar && <StatusBar model={model} sessionId={activeId} />}
        {/* Toasterne fra notifikations-feeden. De bor i Shell og ikke i en
            enkelt flade, saa en godkendelse ogsaa naar frem naar man staar i
            kode- eller arbejds-fladen — det er praecis dér man ikke kigger
            paa klokken. */}
        <NotifikationsToast
          config={cfg ?? null}
          aktivSession={activeId}
          onAabenSession={(id) => { if (id) select(id); setSurface('chat') }}
        />
      </main>
    </div>
  )
}

/** Wirer globale tastaturgenveje med stream-status + surface-skift. */
function ShortcutsHost({ setSurface, onSearch }: { setSurface: (s: Surface) => void; onSearch: () => void }) {
  const stream = useStream()
  return (
    <GlobalShortcuts
      working={stream.status === 'working'}
      onStop={() => { void stream.abort() }}
      onSettings={() => setSurface('settings')}
      onSearch={onSearch}
    />
  )
}

/** Wirer OS-notifikation til afventende godkendelser (Electron gater fokus selv). */
function ApprovalNotifierHost() {
  const stream = useStream()
  const p = stream.pendingApproval
  return (
    <ApprovalNotifier
      approvalId={p?.approvalId ?? null}
      tool={p?.tool}
      action={p?.action}
      notify={(title, body) => {
        const b = (window as unknown as {
          jarvisDesk?: { notifyTaskDone?: (t: string, b: string) => Promise<void> }
        }).jarvisDesk
        void b?.notifyTaskDone?.(title, body)
      }}
    />
  )
}

/** Viser AppActionCard når Jarvis har anmodet om et mode/permission-skift.
 *  Renderes inde i Shell (har adgang til Stream + Permission + setSurface).
 *  Jarvis kan kun ANMODE — kun brugerens klik skifter noget. */
function AppActionHost({ setSurface }: { setSurface: (s: Surface) => void }) {
  const stream = useStream()
  const { setPermission } = usePermission()
  const pending = stream.pendingAppAction
  if (!pending) return null
  return (
    <div className="appaction-host">
      <AppActionCard
        action={pending.action}
        reason={pending.reason}
        onApprove={() => {
          resolveAppAction(
            pending.action,
            {
              setSurface: (s) => setSurface(s),
              setPermission,
              armAutoContinue: stream.armAutoContinue,
            },
            pending.originalMessage,
          )
          stream.clearAppAction()
        }}
        onReject={() => stream.clearAppAction()}
      />
    </div>
  )
}
