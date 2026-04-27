import { useEffect, useMemo, useRef, useState } from 'react'
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
}) {
  const [draft, setDraft] = useState('')
  // Queue a follow-up message while Jarvis is still streaming, so the user
  // doesn't have to wait or cancel just to add a thought. Same UX as Claude
  // Code's composer. Auto-flushes when the current run ends.
  const [queuedMessage, setQueuedMessage] = useState(null)
  const wasStreamingRef = useRef(isStreaming)
  const hero = useMemo(() => ({
    title: activeSession?.title || 'New chat',
    subtitle: activeSession?.subtitle || 'Conversation-first front door',
  }), [activeSession])

  // Flush queued message as soon as the active run finishes.
  useEffect(() => {
    if (wasStreamingRef.current && !isStreaming && queuedMessage) {
      const { msg, opts } = queuedMessage
      setQueuedMessage(null)
      // Defer one tick so React has flushed the streaming-end state before
      // we kick off the new run. Otherwise we can race the parent hook.
      setTimeout(() => onSend(msg, opts), 0)
    }
    wasStreamingRef.current = isStreaming
  }, [isStreaming, queuedMessage, onSend])

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

        <ChatTranscript messages={activeSession?.messages || []} workingSteps={workingSteps} sessionId={activeSession?.id} isStreaming={isStreaming} jarvisSurface={jarvisSurface} />

        <Composer
          value={draft}
          onChange={setDraft}
          isStreaming={isStreaming}
          queuedMessage={queuedMessage}
          onClearQueued={() => setQueuedMessage(null)}
          onSend={(msg, opts) => {
            if (isStreaming) {
              // Queue rather than dispatch — auto-sends when run ends.
              setQueuedMessage({ msg, opts })
              setDraft('')
              return
            }
            onSend(msg, opts)
            setDraft('')
          }}
          onCancel={onCancel}
          onSteer={(msg) => {
            if (onSteer) {
              onSteer(msg)
              setDraft('')
            }
          }}
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
