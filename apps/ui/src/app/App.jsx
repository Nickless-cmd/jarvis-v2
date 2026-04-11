import { AppShell } from '../components/layout/AppShell'
import { SidebarSessions } from '../components/layout/SidebarSessions'
import { ChatPage } from './ChatPage'
import { MissionControlPage } from './MissionControlPage'
import { useUnifiedShell } from './useUnifiedShell'
import { useRef } from 'react'
import { AmbientPresence } from '../components/AmbientPresence'

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
        <SidebarSessions
          sessions={sessions}
          activeSessionId={activeSessionId}
          onSelect={(id) => {
            handleSessionSelect(id)
            setActiveView('chat')
          }}
          onCreate={handleCreateSession}
          onRename={handleRenameSession}
          onDelete={handleDeleteSession}
        />
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
      ) : (
        <MissionControlPage
          selection={shell.selection}
          onSelectionChange={handleSelectionChange}
          initialTab={mcInitialTabRef.current}
        />
      )}
      <AmbientPresence />
    </AppShell>
  )
}
