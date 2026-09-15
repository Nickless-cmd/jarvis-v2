import { useState } from 'react'
import { AppShell } from '../components/layout/AppShell'
import { SidebarSessions } from '../components/layout/SidebarSessions'
import { ChatPage } from './ChatPage'
import { useUnifiedShell } from './useUnifiedShell'
import { AmbientPresence } from '../components/AmbientPresence'
import { LoginScreen } from '../views/LoginScreen'
import { hentToken, glemToken, erUautoriseret } from '../lib/auth.js'

export function App() {
  // Har vi overhovedet et token? Uden ét fik HVERT kald 401, og skallen blev
  // staaende paa «Loading unified shell…» for evigt (15/9-2026).
  const [token, setToken] = useState(hentToken())
  const {
    shell,
    sessions,
    activeSession,
    activeSessionId,
    handleSessionSelect,
    handleSelectionChange,
    handleSend,
    handleCancel,
    handleSteer,
    handleRenameSession,
    handleDeleteSession,
    handleCreateSession,
    capabilityActivity,
    refreshShell,
    error,
    isRefreshing,
    isStreaming,
    workingSteps,
    systemHealth,
    jarvisSurface,
    lastRunTokens,
    streamingTokenEstimate,
  } = useUnifiedShell()

  // ── DEN TIDLIGE RETUR DER SKJULTE ALT (15/9-2026) ──────────────────────
  // Her stod foer:
  //
  //     if (!shell) return <div className="boot-screen">Loading unified shell…</div>
  //
  // `initialize()` FANGER fejlen og gemmer den i `error` — men `shell` forblev
  // null, saa boot-skaermen returnerede foerst og beskeden naaede aldrig
  // skaermen. Diagnosen fandtes; ingen viste den. Derfor «Loading…» i evighed
  // i stedet for «du er ikke logget ind».
  if (!token) return <LoginScreen onLoggedIn={setToken} />

  if (!shell && erUautoriseret(error)) {
    // Tokenet findes, men serveren afviser det — udloebet eller tilbagekaldt.
    // Smid det vaek og vis login frem for at hamre videre paa 401.
    glemToken()
    return <LoginScreen onLoggedIn={setToken} />
  }

  if (!shell && error) {
    return (
      <div className="boot-screen boot-fejl">
        <p>Kunne ikke åbne fladen.</p>
        <p className="boot-fejl-detalje">{String(error)}</p>
      </div>
    )
  }

  if (!shell) return <div className="boot-screen">Loading unified shell…</div>

  return (
    <AppShell
      systemHealth={systemHealth}
      onNewChat={handleCreateSession}
      sidebarContent={
        <SidebarSessions
          sessions={sessions}
          activeSessionId={activeSessionId}
          onSelect={handleSessionSelect}
          onCreate={handleCreateSession}
          onRename={handleRenameSession}
          onDelete={handleDeleteSession}
        />
      }
    >
      <ChatPage
        activeSession={activeSession}
        selection={shell.selection}
        error={error}
        onSelectionChange={handleSelectionChange}
        onRefresh={refreshShell}
        onSend={handleSend}
        onCancel={handleCancel}
        onSteer={handleSteer}
        onRename={handleRenameSession}
        onDelete={handleDeleteSession}
        isRefreshing={isRefreshing}
        isStreaming={isStreaming}
        workingSteps={workingSteps}
        capabilityActivity={capabilityActivity}
        systemHealth={systemHealth}
        jarvisSurface={jarvisSurface}
        lastRunTokens={lastRunTokens}
        streamingTokenEstimate={streamingTokenEstimate}
      />
      <AmbientPresence />
    </AppShell>
  )
}
