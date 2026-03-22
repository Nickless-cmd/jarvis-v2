import { useEffect, useState } from 'react'
import { AppShell } from '../components/layout/AppShell'
import { ChatPage } from './ChatPage'
import { MissionControlPage } from './MissionControlPage'
import { backend } from '../lib/adapters'

export function App() {
  const [activeView, setActiveView] = useState('chat')
  const [data, setData] = useState(null)

  useEffect(() => {
    backend.getShell().then(setData)
  }, [])

  if (!data) return <div className="boot-screen">Loading unified shell…</div>

  return (
    <AppShell activeView={activeView} onChangeView={setActiveView}>
      {activeView === 'chat' ? (
        <ChatPage
          sessions={data.sessions}
          selection={data.selection}
          chat={data.chat}
          missionControl={data.missionControl}
          onSelectionChange={async (payload) => {
            const selection = await backend.updateMainAgentSelection(payload)
            setData((prev) => ({ ...prev, selection }))
          }}
          onSend={async (content) => {
            const messages = await backend.sendMessage({ content })
            setData((prev) => ({ ...prev, chat: { ...prev.chat, messages: [...messages] } }))
          }}
        />
      ) : (
        <MissionControlPage selection={data.selection} missionControl={data.missionControl} />
      )}
    </AppShell>
  )
}
