import { AppShell } from '../components/layout/AppShell'
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
    error,
  } = useUnifiedShell()

  if (!shell) return <div className="boot-screen">Loading unified shell…</div>

  return (
    <AppShell activeView={activeView} onChangeView={setActiveView}>
      {activeView === 'chat' ? (
        <ChatPage
          sessions={sessions}
          activeSession={activeSession}
          activeSessionId={activeSessionId}
          selection={shell.selection}
          missionControl={shell.missionControl}
          error={error}
          onSessionSelect={setActiveSessionId}
          onCreateSession={handleCreateSession}
          onSelectionChange={handleSelectionChange}
          onSend={handleSend}
        />
      ) : (
        <MissionControlPage selection={shell.selection} missionControl={shell.missionControl} />
      )}
    </AppShell>
  )
}
