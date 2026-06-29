import { createContext, useContext, useMemo, useState, type ReactNode } from 'react'
import { createSession, getSession, listSessions } from '../lib/apiClient'
import type { ApiConfig, ChatMessage, ChatSession } from '../lib/types'

// G1 (spec §10) — porteret fra desk's bevist-virkende mergeServer-bro
// (apps/jarvis-desk/src/contexts/SessionContext.tsx:158). Mobilen wholesale-
// replacede før beskeder uden merge (`setMessages(result.messages)`), så HVER
// foreground-resync / busy→idle-poll / notif-tap der kaldte select() midt i
// svar-halen kunne wipe det netop-streamede local-assistant-snapshot →
// "svaret forsvinder ved reload". De nye retry-events (§4.1) udløser racen
// OFTERE (flere refresh-triggers). Broen bevarer det lokale snapshot indtil
// serverens transcript har INDHENTET (sidste server-besked = assistant).

type ClientStatus =
  | 'optimistic_user'
  | 'streaming_assistant'
  | 'server_confirmed'
  | 'server_missing_keep_stream'

export interface LocalMessage extends ChatMessage {
  clientStatus?: ClientStatus
}

interface SessionContextValue {
  sessions: ChatSession[]
  activeId: string | null
  messages: LocalMessage[]
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
  const [messages, setMessages] = useState<LocalMessage[]>([])
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
          // G1: flet i stedet for at wholesale-replace, så et endnu-ikke-
          // persisteret local-assistant-snapshot ikke blank-forsvinder når en
          // resync/poll-select rammer midt i svar-halen.
          setMessages((local) => mergeServer(local, result.messages))
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
        // Markér klient-status efter rolle (mirror af desk's appendOptimistic/
        // reconcile-split): bruger-beskeder er optimistiske; lokalt-streamede
        // assistant-snapshots er "server_missing_keep_stream" — broen der holdes
        // i live indtil serveren har persisteret svaret.
        const clientStatus: ClientStatus =
          message.role === 'assistant' ? 'server_missing_keep_stream' : 'optimistic_user'
        setMessages((current) => [...current, { ...message, clientStatus }])
      },
      replaceMessages: (nextMessages) => {
        setMessages(nextMessages)
      }
    }),
    [activeId, loading, messages, sessions]
  )

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
}

/** Saml en bruger-beskeds tekst-indhold (til indholds-afdublering). Mobil-content
 *  er en streng, men vi tåler en blok-liste defensivt (parity med desk). */
function userText(message: ChatMessage): string {
  const content = message.content as unknown
  if (typeof content === 'string') return content.trim()
  if (Array.isArray(content)) {
    return content
      .filter((b): b is { type: string; text?: string } => !!b && typeof b === 'object')
      .filter((b) => b.type === 'text')
      .map((b) => b.text || '')
      .join('')
      .trim()
  }
  return ''
}

/** Normalisér en assistant-beskeds synlige tekst til run-afdublering (parity med
 *  desk's assistantNorm). Bro-kopien og serverens normaliserede kopi af SAMME
 *  svar genkendes som ÉT. Konservativ: kun ren tekst — afviger indholdet er det
 *  IKKE et match, og broen bevares. */
function assistantNorm(message: ChatMessage): string {
  const content = message.content as unknown
  let raw = ''
  if (typeof content === 'string') raw = content
  else if (Array.isArray(content)) {
    raw = content
      .filter((b): b is { type: string; text?: string } => !!b && typeof b === 'object')
      .filter((b) => b.type === 'text')
      .map((b) => b.text || '')
      .join('')
  }
  return raw.replace(/\s+/g, ' ').trim()
}

/**
 * Flet server-beskeder ind. Server-beskeder bliver 'server_confirmed'. Lokale
 * beskeder serveren endnu IKKE har (optimistic_user / server_missing_keep_stream)
 * BEVARES — så en endnu-ikke-persisteret besked aldrig blank-forsvinder.
 *
 * Porteret 1:1 fra desk (SessionContext.tsx:158). serverCaughtUp = sidste
 * server-besked er assistant: i et multi-runde tool-tur persisterer backend
 * mellem-rundes assistant-tekst FØR de efterfølgende tool-resultater, så
 * transcript'en kan stå [...user, assistant(mellem), tool, tool] mens det
 * ENDELIGE svar endnu ikke er gemt. Slutter den på en tool/non-assistant kører
 * en runde stadig → broen SKAL bevares. Afdublering på BÅDE id og bruger-tekst
 * (klient-id ≠ server-id for den persisterede kopi).
 */
function mergeServer(local: LocalMessage[], server: ChatMessage[]): LocalMessage[] {
  const serverIds = new Set(server.map((m) => m.id))
  const serverUserTexts = new Set(
    server.filter((m) => m.role === 'user').map(userText).filter(Boolean)
  )
  const result: LocalMessage[] = server.map((m) => ({
    ...m,
    clientStatus: 'server_confirmed' as ClientStatus
  }))
  const lastMsg = server.length > 0 ? server[server.length - 1] : undefined
  const serverCaughtUp = lastMsg?.role === 'assistant'
  // RUN-AFDUBLERING (Bjørn 2026-06-29, "3 svar lander samtidig"; porteret fra
  // desk): én bro-kopi og serverens persisterede kopi af SAMME run er ÉT svar.
  // I en multi-runde tool-tur står transcript'en transient [...assistant(svar),
  // tool, tool] (næste runde startede), så serverCaughtUp=false selvom svaret
  // ALLEREDE er persisteret → broen blev holdt ved siden af serverens kopi →
  // dublet. Nu: så snart serveren har en assistant hvis normaliserede tekst
  // matcher broens, er svaret persisteret → drop broen uanset tool-halen.
  // Konservativt: kræver tekst-match (intet match → distinkt svar → broen bevares).
  const serverAsstTexts = new Set(
    server.filter((m) => m.role === 'assistant').map(assistantNorm).filter(Boolean)
  )
  for (const lm of local) {
    if (serverIds.has(lm.id)) continue
    if (lm.clientStatus === 'optimistic_user') {
      if (serverCaughtUp) continue // svaret er persisteret → bruger-beskeden er det også
      if (serverUserTexts.has(userText(lm))) continue // serveren har allerede samme tekst
      result.push(lm) // bruger-besked serveren endnu ikke har → behold som bro
    } else if (lm.clientStatus === 'server_missing_keep_stream') {
      const persisted = serverCaughtUp || serverAsstTexts.has(assistantNorm(lm))
      if (!persisted) result.push(lm) // bro indtil serveren persisterer svaret
    }
    // persisteret → drop placeholder; serverens rensede besked vises i stedet
  }
  return result
}

export { mergeServer, userText }

export function useSessions(): SessionContextValue {
  const context = useContext(SessionContext)

  if (!context) {
    throw new Error('useSessions must be used within SessionProvider')
  }

  return context
}
