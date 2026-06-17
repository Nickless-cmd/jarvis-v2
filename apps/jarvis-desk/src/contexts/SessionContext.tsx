import { createContext, useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { listSessions, getSession, createSession, renameSession, deleteSession, type ChatSession, type ChatMessage } from '../lib/api'

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
  create: (title: string) => Promise<ChatSession>
  rename: (id: string, title: string) => Promise<void>
  remove: (id: string) => Promise<void>
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
    return list
  }, [config])

  // Hvilken session's beskeder er aktuelt loaded. Forhindrer at select()
  // genindlæser (og dermed wiper optimistiske/streamede beskeder) når ChatView
  // re-kalder select for en session vi allerede har — fx en netop oprettet.
  const loadedRef = useRef<string | null>(null)

  // Init: hent KUN session-listen (til sidebar). Gendan IKKE sidst-valgte samtale
  // — appen lander altid på greeting-skærmen ved opstart/genstart (Bjørn 17. jun:
  // "det ser mere seriøst ud man starter på greetings screen"). De gamle samtaler
  // er stadig tilgængelige ved at klikke dem i sidebaren.
  useEffect(() => {
    void loadSessions()
  }, [loadSessions])

  const select = useCallback((id: string) => {
    setActiveId(id)
    try { localStorage.setItem('jarvis-desk:activeSession', id) } catch { /* ignore */ }
    if (loadedRef.current === id) return // allerede loaded → behold lokale beskeder
    const prevLoaded = loadedRef.current
    loadedRef.current = id
    // Ægte skift fra en ANDEN session → ryd den gamles beskeder først.
    if (prevLoaded !== null && prevLoaded !== id) setMessages([])
    setLoading(true)
    getSession(config, id)
      // Merge med NUVÆRENDE lokale beskeder (ikke []) — så en optimistisk
      // besked tilføjet imens overlever (mergeServer bevarer optimistic_user).
      .then(({ messages: server }) => setMessages((prev) => mergeServer(prev, server)))
      .finally(() => setLoading(false))
  }, [config])

  const refresh = useCallback(async () => {
    if (!activeId) return
    const { messages: server } = await getSession(config, activeId)
    setMessages((local) => mergeServer(local, server))
  }, [config, activeId])

  const create = useCallback(async (title: string) => {
    const sess = await createSession(config, title)
    const titled = { ...sess, title: sess.title || title } // server kan returnere tom titel
    loadedRef.current = titled.id // markér som loaded (tom) FØR activeId-skift → select skipper fetch
    setSessions((prev) => [titled, ...prev])
    setActiveId(titled.id)
    setMessages([])
    return titled
  }, [config])

  const rename = useCallback(async (id: string, title: string) => {
    await renameSession(config, id, title)
    setSessions((prev) => prev.map((s) => (s.id === id ? { ...s, title } : s)))
  }, [config])

  const remove = useCallback(async (id: string) => {
    await deleteSession(config, id)
    setSessions((prev) => prev.filter((s) => s.id !== id))
    setActiveId((cur) => (cur === id ? null : cur))
    setMessages((prev) => (activeId === id ? [] : prev))
  }, [config, activeId])

  const appendOptimistic = useCallback((msg: ChatMessage) => {
    setMessages((prev) => [...prev, { ...msg, clientStatus: 'optimistic_user' }])
  }, [])

  const reconcile = useCallback((assistantMsg: ChatMessage) => {
    setMessages((prev) => [...prev, { ...assistantMsg, clientStatus: 'server_missing_keep_stream' }])
  }, [])

  const value = useMemo<SessionContextValue>(
    () => ({ sessions, activeId, messages, loading, select, create, rename, remove, refresh, appendOptimistic, reconcile }),
    [sessions, activeId, messages, loading, select, create, rename, remove, refresh, appendOptimistic, reconcile],
  )
  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
}

/** Saml en bruger-beskeds tekst-indhold til én streng (til indholds-afdublering).
 *  content kan være en streng eller en blok-liste; vi konkatenerer text-blokke. */
function userText(m: ChatMessage): string {
  const c = m.content as unknown
  if (typeof c === 'string') return c.trim()
  if (Array.isArray(c)) {
    return c
      .filter((b): b is { type: string; text?: string } => !!b && typeof b === 'object')
      .filter((b) => b.type === 'text')
      .map((b) => b.text || '')
      .join('')
      .trim()
  }
  return ''
}

/**
 * Flet server-beskeder ind. Server-beskeder bliver 'server_confirmed'. Lokale
 * beskeder serveren endnu IKKE har (optimistic_user / server_missing_keep_stream)
 * BEVARES — så en endnu-ikke-persisteret besked aldrig blank-forsvinder
 * (reconcile-race).
 *
 * KRITISK afdublering: den optimistiske bruger-besked har et KLIENT-id
 * (`u-<ts>`) mens serverens persisterede kopi har et ANDET server-id — så
 * id-only-matchet fanger den ikke, og brugerens besked blev vist BÅDE før
 * (serverens kopi, kronologisk) OG efter (den optimistiske, push'et til sidst)
 * Jarvis' svar indtil hard refresh (Bjørn 2026-06-13). Vi afdublerer derfor
 * også på INDHOLD, og dropper den optimistiske når serveren har indhentet.
 */
function mergeServer(local: LocalMessage[], server: ChatMessage[]): LocalMessage[] {
  const serverIds = new Set(server.map((m) => m.id))
  const serverUserTexts = new Set(
    server.filter((m) => m.role === 'user').map(userText).filter(Boolean),
  )
  const result: LocalMessage[] = server.map((m) => ({ ...m, clientStatus: 'server_confirmed' as ClientStatus }))
  // Har serveren indhentet løbet? Dvs. er den sidste IKKE-tool-besked en assistant?
  // Så er BÅDE bruger-beskeden OG svaret persisteret (renset af backend-guarden/
  // normalizer) → både placeholder OG optimistisk bruger-besked skal DROPPES,
  // ellers hænger lokale kopier ved siden af serverens rensede versioner.
  const lastReal = [...server].reverse().find((m) => m.role === 'user' || m.role === 'assistant')
  const serverCaughtUp = lastReal?.role === 'assistant'
  for (const lm of local) {
    if (serverIds.has(lm.id)) continue
    if (lm.clientStatus === 'optimistic_user') {
      if (serverCaughtUp) continue // svaret er persisteret → bruger-beskeden er det også
      if (serverUserTexts.has(userText(lm))) continue // serveren har allerede samme tekst
      result.push(lm) // bruger-besked serveren endnu ikke har → behold som bro
    } else if (lm.clientStatus === 'server_missing_keep_stream' && !serverCaughtUp) {
      result.push(lm) // bro indtil serveren persisterer svaret
    }
    // serverCaughtUp → drop placeholder; serverens rensede besked vises i stedet
  }
  return result
}

export { mergeServer, userText }
