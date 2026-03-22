import { AppShell } from '../components/layout/AppShell'
import { SidebarSessions } from '../components/layout/SidebarSessions'
import { ChatPage } from './ChatPage'
import { MissionControlPage } from './MissionControlPage'
import { useUnifiedShell } from './useUnifiedShell'

export function App() {
  const {
    activeView,
    setActiveView,
    shell,
    sessions,
    activeSession,
    activeSessionId,
    setActiveSessionId,
    handleSelectionChange,
    handleSend,
    handleCreateSession,
    refreshShell,
    error,
    isRefreshing,
    isStreaming,
  } = useUnifiedShell()

  if (!shell) return <div className="boot-screen">Loading unified shell…</div>

  return (
    <AppShell
      activeView={activeView}
      onChangeView={setActiveView}
      sidebarContent={
        activeView === 'chat' ? (
          <SidebarSessions
            sessions={sessions}
            activeSessionId={activeSessionId}
            onSelect={setActiveSessionId}
            onCreate={handleCreateSession}
          />
        ) : null
      }
    >
      {activeView === 'chat' ? (
        <ChatPage
          activeSession={activeSession}
          selection={shell.selection}
          error={error}
          onSelectionChange={handleSelectionChange}
          onRefresh={refreshShell}
          onSend={handleSend}
          isRefreshing={isRefreshing}
          isStreaming={isStreaming}
        />
      ) : (
        <MissionControlPage
          selection={shell.selection}
          missionControl={shell.missionControl}
          onSelectionChange={handleSelectionChange}
        />
      )}
    </AppShell>
  )
}
