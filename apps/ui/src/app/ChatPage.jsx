import { useMemo, useState } from 'react'
import { ChatTranscript } from '../components/chat/ChatTranscript'
import { Composer } from '../components/chat/Composer'
import { SidebarSessions } from '../components/layout/SidebarSessions'
import { MainAgentPanel } from '../components/shared/MainAgentPanel'
import { SecondaryPanels } from '../components/shared/SecondaryPanels'

export function ChatPage({ sessions, selection, chat, missionControl, onSelectionChange, onSend }) {
  const [draft, setDraft] = useState('')
  const hero = useMemo(() => ({
    eyebrow: 'Jarvis · Unified UI',
    title: chat.title,
    subtitle: chat.subtitle,
  }), [chat])

  return (
    <div className="chat-shell-grid">
      <SidebarSessions sessions={sessions} />

      <main className="chat-stage">
        <section className="hero-card">
          <p className="eyebrow">{hero.eyebrow}</p>
          <h1>{hero.title}</h1>
          <p>{hero.subtitle}</p>
        </section>

        <ChatTranscript messages={chat.messages} />

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
        <SecondaryPanels missionControl={missionControl} />
      </aside>
    </div>
  )
}
