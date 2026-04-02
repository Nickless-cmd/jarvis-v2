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
  isRefreshing,
  isStreaming,
  workingSteps,
  jarvisSurface,
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
          selection={selection}
          onRefresh={onRefresh}
          isRefreshing={isRefreshing}
          isStreaming={isStreaming}
        />

        {error ? <div className="inline-error">{error}</div> : null}

        <ChatTranscript messages={activeSession?.messages || []} workingSteps={workingSteps} />

        <Composer
          value={draft}
          onChange={setDraft}
          isStreaming={isStreaming}
          onSend={() => {
            if (!draft.trim() || isStreaming) return
            onSend(draft.trim())
            setDraft('')
          }}
        />
      </main>

      <ChatSupportRail
        session={activeSession}
        selection={selection}
        isStreaming={isStreaming}
        jarvisSurface={jarvisSurface}
      />
    </div>
  )
}
