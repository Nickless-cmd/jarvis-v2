import { createContext, useContext, useMemo, useState, type ReactNode } from 'react'
import { createSession, getSession, listSessions } from '../lib/apiClient'
import type { ApiConfig, ChatMessage, ChatSession } from '../lib/types'

interface SessionContextValue {
  sessions: ChatSession[]
  activeId: string | null
  messages: ChatMessage[]
  loading: boolean
  refresh: (config: ApiConfig) => Promise<void>
  select: (config: ApiConfig, sessionId: string) => Promise<void>
  create: (config: ApiConfig) => Promise<ChatSession>
  appendLocalMessage: (message: ChatMessage) => void
  replaceMessages: (messages: ChatMessage[]) => void
}

const SessionContext = createContext<SessionContextValue | null>(null)

export function SessionProvider({ children }: { children: ReactNode }) {
  const [sessions, setSessions] = useState<ChatSession[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [loading, setLoading] = useState(false)

  const value = useMemo<SessionContextValue>(
    () => ({
      sessions,
      activeId,
      messages,
      loading,
      refresh: async (config) => {
        setLoading(true)

        try {
          setSessions(await listSessions(config))
        } finally {
          setLoading(false)
        }
      },
      select: async (config, sessionId) => {
        setLoading(true)

        try {
          const result = await getSession(config, sessionId)
          setActiveId(result.session.id)
          setMessages(result.messages)
        } finally {
          setLoading(false)
        }
      },
      create: async (config) => {
        const session = await createSession(config)
        setSessions((current) => [session, ...current.filter((item) => item.id !== session.id)])
        setActiveId(session.id)
        setMessages([])
        return session
      },
      appendLocalMessage: (message) => {
        setMessages((current) => [...current, message])
      },
      replaceMessages: (nextMessages) => {
        setMessages(nextMessages)
      }
    }),
    [activeId, loading, messages, sessions]
  )

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
}

export function useSessions(): SessionContextValue {
  const context = useContext(SessionContext)

  if (!context) {
    throw new Error('useSessions must be used within SessionProvider')
  }

  return context
}
