import { createContext, useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { listSessions, getSession, createSession, type ChatSession, type ChatMessage } from '../lib/api'

type ClientStatus =
  | 'optimistic_user'
  | 'streaming_assistant'
  | 'server_confirmed'
  | 'server_missing_keep_stream'

export interface LocalMessage extends ChatMessage {
  clientStatus?: ClientStatus
}

export interface SessionContextValue {
  sessions: ChatSession[]
  activeId: string | null
  messages: LocalMessage[]
  loading: boolean
  select: (id: string) => void
  create: (title: string) => Promise<void>
  refresh: () => Promise<void>
  appendOptimistic: (msg: ChatMessage) => void
  reconcile: (assistantMsg: ChatMessage) => void
}

export const SessionContext = createContext<SessionContextValue | null>(null)

export function SessionProvider({
  children,
  config,
}: {
  children: ReactNode
  config: { apiBaseUrl: string; authToken: string | null }
}) {
  const [sessions, setSessions] = useState<ChatSession[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [messages, setMessages] = useState<LocalMessage[]>([])
  const [loading, setLoading] = useState(false)

  const loadSessions = useCallback(async () => {
    const list = await listSessions(config)
    setSessions(list)
  }, [config])

  // Init: hent session-liste én gang.
  useEffect(() => {
    void loadSessions()
  }, [loadSessions])

  const select = useCallback((id: string) => {
    setActiveId(id)
    setLoading(true)
    getSession(config, id)
      .then(({ messages: server }) => setMessages(mergeServer([], server)))
      .finally(() => setLoading(false))
  }, [config])

  const refresh = useCallback(async () => {
    if (!activeId) return
    const { messages: server } = await getSession(config, activeId)
    setMessages((local) => mergeServer(local, server))
  }, [config, activeId])

  const create = useCallback(async (title: string) => {
    const sess = await createSession(config, title)
    setSessions((prev) => [sess, ...prev])
    setActiveId(sess.id)
    setMessages([])
  }, [config])

  const appendOptimistic = useCallback((msg: ChatMessage) => {
    setMessages((prev) => [...prev, { ...msg, clientStatus: 'optimistic_user' }])
  }, [])

  const reconcile = useCallback((assistantMsg: ChatMessage) => {
    setMessages((prev) => [...prev, { ...assistantMsg, clientStatus: 'server_missing_keep_stream' }])
  }, [])

  const value = useMemo<SessionContextValue>(
    () => ({ sessions, activeId, messages, loading, select, create, refresh, appendOptimistic, reconcile }),
    [sessions, activeId, messages, loading, select, create, refresh, appendOptimistic, reconcile],
  )
  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
}

/**
 * Flet server-beskeder ind. Server-beskeder bliver 'server_confirmed'. Lokale
 * beskeder serveren endnu IKKE har (optimistic_user / server_missing_keep_stream)
 * BEVARES — så en endnu-ikke-persisteret besked aldrig blank-forsvinder
 * (reconcile-race, dagens bug).
 */
function mergeServer(local: LocalMessage[], server: ChatMessage[]): LocalMessage[] {
  const serverIds = new Set(server.map((m) => m.id))
  const result: LocalMessage[] = server.map((m) => ({ ...m, clientStatus: 'server_confirmed' as ClientStatus }))
  for (const lm of local) {
    if (!serverIds.has(lm.id) && (lm.clientStatus === 'server_missing_keep_stream' || lm.clientStatus === 'optimistic_user')) {
      result.push(lm)
    }
  }
  return result
}
