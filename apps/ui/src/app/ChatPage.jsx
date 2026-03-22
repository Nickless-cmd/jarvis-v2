import { useMemo, useState } from 'react'
import { ChatTranscript } from '../components/chat/ChatTranscript'
import { Composer } from '../components/chat/Composer'
import { ChatHeader } from '../components/chat/ChatHeader'
import { SidebarSessions } from '../components/layout/SidebarSessions'
import { MainAgentPanel } from '../components/shared/MainAgentPanel'
import { SecondaryPanels } from '../components/shared/SecondaryPanels'

export function ChatPage({
  sessions,
  activeSession,
  activeSessionId,
  selection,
  missionControl,
  error,
  onSessionSelect,
  onCreateSession,
  onSelectionChange,
  onSend,
}) {
  const [draft, setDraft] = useState('')
  const hero = useMemo(() => ({
    title: activeSession?.title || 'New chat',
    subtitle: activeSession?.subtitle || 'Conversation-first front door',
  }), [activeSession])

  return (
    <div className="chat-shell-grid">
      <SidebarSessions
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelect={onSessionSelect}
        onCreate={onCreateSession}
      />

      <main className="chat-stage">
        <ChatHeader
          session={{ title: hero.title, subtitle: hero.subtitle }}
          selection={selection}
          localLane={missionControl.lanes.local}
        />

        {error ? <div className="inline-error">{error}</div> : null}

        <ChatTranscript messages={activeSession?.messages || []} />

        <Composer
          value={draft}
          onChange={setDraft}
          onSend={() => {
            if (!draft.trim()) return
            onSend(draft.trim())
            setDraft('')
          }}
        />
      </main>

      <aside className="support-rail">
        <MainAgentPanel selection={selection} onSave={onSelectionChange} />
        <SecondaryPanels missionControl={missionControl} selection={selection} />
      </aside>
    </div>
  )
}
