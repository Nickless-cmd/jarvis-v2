import { AppShell } from '../components/layout/AppShell'
import { SidebarSessions } from '../components/layout/SidebarSessions'
import { ChatPage } from './ChatPage'
import { MissionControlPage } from './MissionControlPage'
import { useUnifiedShell } from './useUnifiedShell'
import { useRef } from 'react'

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
    handleCancel,
    handleCreateSession,
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

  const mcInitialTabRef = useRef(null)

  function handleViewChange(view) {
    if (view === 'memory' || view === 'skills') {
      mcInitialTabRef.current = view
      setActiveView('mission-control')
      return
    }
    mcInitialTabRef.current = null
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
          onCancel={handleCancel}
          isRefreshing={isRefreshing}
          isStreaming={isStreaming}
          workingSteps={workingSteps}
          jarvisSurface={jarvisSurface}
          lastRunTokens={lastRunTokens}
          streamingTokenEstimate={streamingTokenEstimate}
        />
      ) : (
        <MissionControlPage
          selection={shell.selection}
          onSelectionChange={handleSelectionChange}
          initialTab={mcInitialTabRef.current}
        />
      )}
    </AppShell>
  )
}
