import { AppShell } from '../components/layout/AppShell'
import { SidebarSessions } from '../components/layout/SidebarSessions'
import { ChatPage } from './ChatPage'
import { useUnifiedShell } from './useUnifiedShell'
import { AmbientPresence } from '../components/AmbientPresence'

export function App() {
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
