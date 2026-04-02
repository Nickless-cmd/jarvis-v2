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
    handleSessionSelect,
    handleSelectionChange,
    handleSend,
    handleCreateSession,
    refreshShell,
    error,
    isRefreshing,
    isStreaming,
    workingSteps,
    systemHealth,
  } = useUnifiedShell()

  function handleViewChange(view) {
    if (view === 'memory' || view === 'skills') {
      setActiveView('mission-control')
      return
    }
    setActiveView(view)
  }

  if (!shell) return <div className="boot-screen">Loading unified shell…</div>

  return (
    <AppShell
      activeView={activeView}
      onChangeView={handleViewChange}
      systemHealth={systemHealth}
      onNewChat={handleCreateSession}
      sidebarContent={
        activeView === 'chat' ? (
          <SidebarSessions
            sessions={sessions}
            activeSessionId={activeSessionId}
            onSelect={handleSessionSelect}
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
          workingSteps={workingSteps}
        />
      ) : (
        <MissionControlPage
          selection={shell.selection}
          onSelectionChange={handleSelectionChange}
        />
      )}
    </AppShell>
  )
}
