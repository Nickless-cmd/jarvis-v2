import { createContext, useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { listSessions, getSession, createSession, renameSession, deleteSession, type ChatSession, type ChatMessage } from '../lib/api'
import { parsePauseAsk } from '../lib/pauseAsk'

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
  /** Ryd aktiv samtale → greeting-skærm (session oprettes først ved første send). */
  newChat: () => void
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
  onRestore,
}: {
  children: ReactNode
  config: { apiBaseUrl: string; authToken: string | null }
  /** Kaldes ÉN gang ved opstart naar en gemt samtale gendannes, med den flade
   *  den hoerer til. Uden den aabnede en kode-session i chat-fladen, og saa saa
   *  det ud som om miljoe-panelet var vaek. */
  onRestore?: (surface: 'chat' | 'code') => void
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

  // Init: hent session-listen (til sidebar).
  useEffect(() => {
    void loadSessions()
  }, [loadSessions])

  // Gendan sidst-valgte samtale ved opstart (Bjørn 8/9-2026: «appen glemmer
  // hvilken session man var på efter genstart og det er rimelig træls»).
  //
  // Det VENDER en tidligere beslutning: 17. juni landede appen med vilje altid
  // på greeting-skærmen («det ser mere seriøst ud»). Id'et er blevet SKREVET til
  // localStorage lige siden — der har bare aldrig været nogen der læste det.
  //
  // Kun hvis samtalen stadig findes i listen. Ellers ville en slettet session
  // genopstå ved hver opstart og hente 404 i det uendelige.
  const gendannetRef = useRef(false)
  useEffect(() => {
    if (gendannetRef.current || sessions.length === 0) return
    gendannetRef.current = true
    let gemt: string | null = null
    try { gemt = localStorage.getItem('jarvis-desk:activeSession') } catch { /* ignore */ }
    if (!gemt) return
    if (!sessions.some((s) => s.id === gemt)) {
      try { localStorage.removeItem('jarvis-desk:activeSession') } catch { /* ignore */ }
      return
    }
    select(gemt)
    // Fladen skal FOELGE samtalen. En kode-session der aabner i chat-fladen
    // viser ikke miljoe-panelet, og saa ser det ud som om det er forsvundet.
    // Sidebarens klik gør præcis det samme opslag (`workspace_kind` sat →
    // code); at gøre noget andet her ville være to definitioner af det samme.
    const s = sessions.find((x) => x.id === gemt)
    if (s) onRestore?.(s.workspace_kind ? 'code' : 'chat')
    // `select` udelades: den gendannes ved hver config-ændring og ville koere
    // gendannelsen igen. `gendannetRef` gør den til en engangs-handling.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessions])

  // Session-listen skal opdatere UDEN at man skifter flade (Bjørn 8/9-2026:
  // «jeg skal trykke over på cowork og tilbage før den opdatere»). Den blev
  // hentet én gang ved mount og aldrig igen; et fladeskift gen-monterede
  // provideren, og DET var opdateringen.
  //
  // To udløsere frem for en poll — en poll-storm har allerede kostet os
  // afbrudte streams én gang:
  //   1) vinduet får fokus igen (han har været et andet sted)
  //   2) den aktive session får sin FØRSTE besked — det er dér serveren nu
  //      omdøber den fra «Ny samtale» til det han skrev, så titlen i panelet
  //      ellers ville blive hængende.
  useEffect(() => {
    const paaFokus = () => { void loadSessions() }
    window.addEventListener('focus', paaFokus)
    document.addEventListener('visibilitychange', paaFokus)
    return () => {
      window.removeEventListener('focus', paaFokus)
      document.removeEventListener('visibilitychange', paaFokus)
    }
  }, [loadSessions])

  const foersteBeskedRef = useRef<string | null>(null)
  useEffect(() => {
    if (!activeId || messages.length === 0) return
    if (foersteBeskedRef.current === activeId) return
    foersteBeskedRef.current = activeId
    void loadSessions()
  }, [activeId, messages.length, loadSessions])

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

  const newChat = useCallback(() => {
    setActiveId(null)
    setMessages([])
    loadedRef.current = null
    try { localStorage.removeItem('jarvis-desk:activeSession') } catch { /* ignore */ }
  }, [])

  const refresh = useCallback(async () => {
    // Listen FØRST: en ny eller netop omdøbt session skal frem i panelet,
    // også når der ikke er en aktiv samtale at hente beskeder for.
    void loadSessions()
    if (!activeId) return
    const { messages: server } = await getSession(config, activeId)
    setMessages((local) => mergeServer(local, server))
  }, [config, activeId, loadSessions])

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
    () => ({ sessions, activeId, messages, loading, select, newChat, create, rename, remove, refresh, appendOptimistic, reconcile }),
    [sessions, activeId, messages, loading, select, newChat, create, rename, remove, refresh, appendOptimistic, reconcile],
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

/** Normalisér en assistant-beskeds synlige tekst til run-afdublering. Samler
 *  text-blokke (ikke thinking/tool_use) og fjerner whitespace-variation, så
 *  den lokale bro-kopi og serverens normaliserede/rensede kopi af SAMME svar
 *  kan genkendes som ÉT svar. Konservativ: matcher kun ren tekst — afviger
 *  indholdet (fx bro=endeligt svar mens server kun har mellem-rundens tekst)
 *  er det IKKE et match, og broen bevares. */
function assistantNorm(m: ChatMessage): string {
  const c = m.content as unknown
  let raw = ''
  if (typeof c === 'string') raw = c
  else if (Array.isArray(c)) {
    raw = c
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
  // TOOL-KORT-BEVARING (Bjørn 9. jul): serveren gemmer KUN tekst (aldrig tool_use/tool_result).
  // Byg et kort normaliseret-assistant-tekst → tool-blokke fra LOKAL state — fra broen ELLER en
  // TIDLIGERE flettet server-besked. Så re-injiceres tool-kortene på HVER merge (code mode poller
  // sessions.refresh gentagne gange; uden dette wipede den 2. merge de kort, den 1. lige flettede).
  type ToolBlock = {
    type?: string
    id?: string
    tool_use_id?: string
    name?: string
    result?: unknown
  }
  const localToolsByNorm = new Map<string, ToolBlock[]>()
  const pendingPauseTools: ToolBlock[] = []
  for (const lm of local) {
    if (lm.role !== 'assistant') continue
    const tb = (Array.isArray(lm.content) ? lm.content : [] as Array<{ type?: string }>).filter(
      (b) => !!b && typeof b === 'object' && ((b as { type?: string }).type === 'tool_use' || (b as { type?: string }).type === 'tool_result'),
    ) as ToolBlock[]
    const norm = assistantNorm(lm)
    if (tb.length > 0 && norm !== '' && !localToolsByNorm.has(norm)) localToolsByNorm.set(norm, tb)
    if (lm.clientStatus === 'server_missing_keep_stream') {
      pendingPauseTools.push(...tb.filter(
        (b) => b.type === 'tool_use' && b.name === 'pause_and_ask' && parsePauseAsk(b.result) !== null,
      ))
    }
  }
  const lastServerAssistantId = [...server].reverse().find((m) => m.role === 'assistant')?.id
  const toolKey = (b: ToolBlock): string =>
    b.type === 'tool_result' ? `result:${b.tool_use_id ?? ''}` : `use:${b.id ?? ''}`
  const result: LocalMessage[] = server.map((m) => {
    const base = { ...m, clientStatus: 'server_confirmed' as ClientStatus }
    if (m.role === 'assistant') {
      const tb = localToolsByNorm.get(assistantNorm(m))
      const content = Array.isArray(base.content) ? (base.content as ToolBlock[]) : []
      // Almindelige tools følger fortsat tekst-match-reglen. pause_and_ask er
      // stærkere: når live-broen afløses af turens seneste server-assistant,
      // skal kortet med over selv hvis persistens normaliserede slutlinjen eller
      // allerede leverede nogle (men ikke alle) tool-blokke.
      const candidates = [
        ...(tb ?? []),
        ...(m.id === lastServerAssistantId ? pendingPauseTools : []),
      ]
      const existing = new Set(content.map(toolKey))
      const missing = candidates.filter((b) => {
        const key = toolKey(b)
        if (existing.has(key)) return false
        existing.add(key)
        return true
      })
      if (missing.length > 0) base.content = [...missing, ...content] as typeof base.content
    }
    return base
  })
  // Har serveren indhentet løbet? = er turen FULDT færdig server-side?
  //
  // KRITISK (Bjørn 2026-06-23, "svar lander → forsvinder i samme sekund"): vi
  // tjekkede før den sidste IKKE-tool-besked. Men i et multi-runde tool-tur
  // persisterer backend mellem-rundes assistant-tekst FØR de efterfølgende
  // tool-resultater → transcript'en står midlertidigt [...user, assistant(mellem),
  // tool, tool] mens det ENDELIGE svar endnu ikke er gemt. "Sidste ikke-tool"
  // landede så på mellem-rundens assistant → serverCaughtUp=true → bro-beskeden
  // (server_missing_keep_stream) der holdt det streamede endelige svar blev
  // DROPPET → svaret forsvandt. Ren timing-race (en refresh i det vindue) → kun
  // ved tool-ture (plain svar har ingen tool-hale). Nu: turen er først færdig når
  // ALLERSIDSTE besked (inkl. tools) er en assistant — slutter den på en tool,
  // kører en runde stadig, og broen SKAL bevares.
  const lastMsg = server.length > 0 ? server[server.length - 1] : undefined
  const serverCaughtUp = lastMsg?.role === 'assistant'
  // RUN-AFDUBLERING (Bjørn 2026-06-29, "3 svar lander samtidig"): én bro-kopi
  // (server_missing_keep_stream) og serverens persisterede kopi af SAMME run er
  // ÉT svar. Det gamle "behold broen til serverCaughtUp" droppede den FØRST når
  // ALLERSIDSTE server-besked var en assistant — men i en multi-runde tool-tur
  // står transcript'en transient [...assistant(svar), tool, tool] (næste runde
  // startede), så serverCaughtUp=false selvom svaret ALLEREDE er persisteret →
  // broen blev holdt VED SIDEN AF serverens kopi → bruger så 2-3 kopier af samme
  // svar lande sammen (selv-heler ved næste refresh). Nu: så snart serveren har
  // en assistant-besked hvis NORMALISEREDE tekst matcher broens, er svaret
  // persisteret → drop broen uanset tool-halen. Konservativt: kræver tekst-match
  // (intet match → distinkt svar → broen bevares, jf. 2026-06-23-regressionen).
  const serverAsstTexts = new Set(
    server.filter((m) => m.role === 'assistant').map(assistantNorm).filter(Boolean),
  )
  for (const lm of local) {
    if (serverIds.has(lm.id)) continue
    if (lm.clientStatus === 'optimistic_user') {
      if (serverCaughtUp) continue // svaret er persisteret → bruger-beskeden er det også
      if (serverUserTexts.has(userText(lm))) continue // serveren har allerede samme tekst
      result.push(lm) // bruger-besked serveren endnu ikke har → behold som bro
    } else if (lm.clientStatus === 'server_missing_keep_stream') {
      // Drop broen hvis serveren allerede har persisteret SAMME svar (run-dedup
      // på indhold) ELLER turen er fuldt færdig (serverCaughtUp). Ellers behold.
      // (Broens tool-blokke er allerede re-injiceret i serverens kopi via localToolsByNorm ovenfor.)
      const persisted = serverCaughtUp || serverAsstTexts.has(assistantNorm(lm))
      if (!persisted) result.push(lm) // bro indtil serveren persisterer svaret
    }
    // persisteret → drop placeholder; serverens rensede besked (nu m. re-injicerede tool-blokke) vises
  }
  return result
}

export { mergeServer, userText }
