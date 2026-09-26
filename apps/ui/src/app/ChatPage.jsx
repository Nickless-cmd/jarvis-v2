import { useMemo, useState } from 'react'
import { ChatTranscript } from '../components/chat/ChatTranscript'
import { Composer } from '../components/chat/Composer'
import { ChatHeader } from '../components/chat/ChatHeader'
import { ChatSupportRail } from '../components/chat/ChatSupportRail'
import { useFollowupQueue } from './useFollowupQueue'

export function ChatPage({
  activeSession,
  selection,
  error,
  onSelectionChange,
  onRefresh,
  onSend,
  onCancel,
  onSteer,
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
  steerReady,
}) {
  const [draft, setDraft] = useState('')
  const followups = useFollowupQueue({
    sessionId: activeSession?.id,
    isStreaming,
    onSend,
    onSteer,
  })
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
          isStreaming={isStreaming}
          messages={activeSession?.messages || []}
        />

        {error ? <div className="inline-error">{error}</div> : null}

        <ChatTranscript messages={activeSession?.messages || []} workingSteps={workingSteps} sessionId={activeSession?.id} isStreaming={isStreaming} jarvisSurface={jarvisSurface} />

        <Composer
          value={draft}
          onChange={setDraft}
          isStreaming={isStreaming}
          queuedMessages={followups.items}
          queueError={followups.error}
          steerReady={steerReady}
          onEditQueued={followups.edit}
          onRemoveQueued={followups.remove}
          onMoveQueued={followups.move}
          onSendQueuedNow={followups.sendNow}
          onSend={(msg, opts) => {
            if (isStreaming || followups.items.length) {
              // Queue rather than dispatch — auto-sends when run ends.
              followups.enqueue(msg, opts)
              setDraft('')
              return
            }
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
