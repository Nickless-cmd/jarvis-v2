import { useMemo, useState } from 'react'
import { ChatTranscript } from '../components/chat/ChatTranscript'
import { Composer } from '../components/chat/Composer'
import { ChatHeader } from '../components/chat/ChatHeader'
import { ChatSupportRail } from '../components/chat/ChatSupportRail'

export function ChatPage({
  activeSession,
  selection,
  error,
  onSelectionChange,
  onRefresh,
  onSend,
  onCancel,
  onRename,
  onDelete,
  isRefreshing,
  isStreaming,
  workingSteps,
  capabilityActivity,
  systemHealth,
  jarvisSurface,
  lastRunTokens,
  streamingTokenEstimate,
}) {
  const [draft, setDraft] = useState('')
  const hero = useMemo(() => ({
    title: activeSession?.title || 'New chat',
    subtitle: activeSession?.subtitle || 'Conversation-first front door',
  }), [activeSession])

  return (
    <div className="chat-shell-grid">
      <main className="chat-stage">
        <ChatHeader
          session={{ title: hero.title }}
          onRefresh={onRefresh}
          onRename={onRename}
          onDelete={onDelete}
          isRefreshing={isRefreshing}
          messages={activeSession?.messages || []}
        />

        {error ? <div className="inline-error">{error}</div> : null}

        <ChatTranscript messages={activeSession?.messages || []} workingSteps={workingSteps} sessionId={activeSession?.id} />

        <Composer
          value={draft}
          onChange={setDraft}
          isStreaming={isStreaming}
          onSend={(msg, opts) => {
            if (isStreaming) return
            onSend(msg, opts)
            setDraft('')
          }}
          onCancel={onCancel}
          selection={selection}
          onSelectionChange={onSelectionChange}
          lastRunTokens={lastRunTokens}
          streamingTokenEstimate={streamingTokenEstimate}
          sessionId={activeSession?.id}
        />
      </main>

      <ChatSupportRail
        session={activeSession}
        selection={selection}
        isStreaming={isStreaming}
        jarvisSurface={jarvisSurface}
        systemHealth={systemHealth}
        workingSteps={workingSteps}
        capabilityActivity={capabilityActivity}
      />
    </div>
  )
}
