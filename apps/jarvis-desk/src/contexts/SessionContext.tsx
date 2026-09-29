import { createContext, useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { erKodeSamtale } from '../lib/sessionGroups'
import { listSessions, getSession, createSession, renameSession, deleteSession, setSessionFlags, setSessionWorkspace, type ChatSession, type ChatMessage } from '../lib/api'
import { parsePauseAsk } from '../lib/pauseAsk'
import { denseBlocks } from '../lib/blockHelpers'

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
  /** Tom naar alt er vel. Ellers: beskederne blev IKKE hentet, og det der staar
   *  paa skaermen er ikke samtalen (Codex' punkt 2, 21/9-2026). */
  loadFejl: string
  /** Hent den aktive samtales beskeder igen efter en fejlet indlaesning. */
  genindlaes: () => void
  select: (id: string) => void
  /** Ryd aktiv samtale → greeting-skærm (session oprettes først ved første send). */
  newChat: () => void
  create: (title: string, kind?: 'chat' | 'code') => Promise<ChatSession>
  rename: (id: string, title: string) => Promise<void>
  remove: (id: string) => Promise<void>
  /** Fastgoer eller frigoer en samtale. Fastgjorte staar oeVerst — serveren
   *  sorterer selv, saa raekkefoelgen retter sig ved naeste list-hentning. */
  setPinned: (id: string, pinned: boolean) => Promise<void>
  /** Arkivér en samtale. Den flytter til «arkiverede» nederst i panelet — den
   *  forsvinder ikke, og kan hentes tilbage med «Gendan». Er den åben, lukkes
   *  den, ellers stod man i en samtale der ikke længere står i listen. */
  setArchived: (id: string, archived: boolean) => Promise<void>
  /** Bind samtalen til et arbejdstræ — projekt-tilhørslen ER `workspace_root`,
   *  så «flyt til projekt» er dette kald og ikke en flytning i en tabel. */
  setWorkspace: (id: string, kind: 'container' | 'workstation', root: string) => Promise<void>
  refresh: () => Promise<void>
  /** Poll den aabne samtale; opdater sidebar-listen hoejst hvert 15. sekund. */
  refreshMessages: () => Promise<void>
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
  const [loadFejl, setLoadFejl] = useState('')
  const lastListLoadAtRef = useRef(0)

  const loadSessions = useCallback(async () => {
    lastListLoadAtRef.current = Date.now()
    // Arkiverede hentes MED (29/9-2026). Serveren skjuler dem som standard, og
    // panelet havde ingen anden kilde — «Arkivér» gjorde samtalen usynlig i
    // stedet for arkiveret. Nu bærer listen dem, og grupperingen lægger dem i
    // «arkiverede» nederst.
    const list = await listSessions(config, { inkluderArkiverede: true })
    setSessions((current) => stableSessions(current, list))
    return list
  }, [config])

  // Hvilken session's beskeder er aktuelt loaded. Forhindrer at select()
  // genindlæser (og dermed wiper optimistiske/streamede beskeder) når ChatView
  // re-kalder select for en session vi allerede har — fx en netop oprettet.
  const loadedRef = useRef<string | null>(null)
  const etagBySessionRef = useRef(new Map<string, string>())

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
    if (s) onRestore?.(erKodeSamtale(s) ? 'code' : 'chat')
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
    setLoadFejl('')
    getSession(config, id)
      // Merge med NUVÆRENDE lokale beskeder (ikke []) — så en optimistisk
      // besked tilføjet imens overlever (mergeServer bevarer optimistic_user).
      .then(({ messages: server, etag }) => {
        if (etag) etagBySessionRef.current.set(id, etag)
        setMessages((prev) => mergeServer(prev, server))
      })
      // Uden denne stod samtalen TOM naar hentningen fejlede — nøjagtig som en
      // ny samtale. Vi rydder loadedRef igen, saa «Prøv igen» faktisk henter
      // paa ny i stedet for at ramme «allerede loaded»-genvejen ovenfor.
      .catch(() => {
        loadedRef.current = prevLoaded
        setLoadFejl('Samtalens beskeder kunne ikke hentes. Det du ser her er ikke hele samtalen.')
      })
      .finally(() => setLoading(false))
  }, [config])

  const genindlaes = useCallback(() => {
    if (!activeId) return
    loadedRef.current = null
    select(activeId)
  }, [activeId, select])

  const newChat = useCallback(() => {
    setActiveId(null)
    setMessages([])
    loadedRef.current = null
    try { localStorage.removeItem('jarvis-desk:activeSession') } catch { /* ignore */ }
  }, [])

  const refreshActiveSession = useCallback(async () => {
    if (!activeId) return
    const etag = etagBySessionRef.current.get(activeId)
    const snapshot = etag
      ? await getSession(config, activeId, { ifNoneMatch: etag })
      : await getSession(config, activeId)
    if (!snapshot) return
    if (snapshot.etag) etagBySessionRef.current.set(activeId, snapshot.etag)
    setMessages((local) => mergeServer(local, snapshot.messages))
  }, [config, activeId])

  const refresh = useCallback(async () => {
    // Eksplicit refresh opdaterer listen straks, ogsaa uden aktiv samtale.
    void loadSessions()
    await refreshActiveSession()
  }, [loadSessions, refreshActiveSession])

  const refreshMessages = useCallback(async () => {
    // Code/Chat poller hvert 1,5 sekund. Listen aendres sjældent og kræver
    // JSON-parse + sammenligning af alle sessioner; beskederne har egen ETag.
    // Fokus og eksplicit refresh henter fortsat listen med det samme.
    if (Date.now() - lastListLoadAtRef.current >= 15_000) void loadSessions()
    await refreshActiveSession()
  }, [loadSessions, refreshActiveSession])

  const create = useCallback(async (title: string, kind: 'chat' | 'code' = 'chat') => {
    const sess = await createSession(config, title, kind)
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

  // Fastgoer/frigoer. Optimistisk med vilje: listen hentes hoejst hvert 15.
  // sekund (se `refreshMessages`), og uden den lokale opdatering ville klikket
  // se ud som om det ikke virkede. Serveren er den der bestemmer — derfor
  // hentes listen bagefter, saa den rigtige raekkefoelge staar der.
  //
  // Arkivering frigoer fastgoerelsen paa serveren; det spejles lokalt, saa
  // raekken ikke staar med et fastgoerelses-maerke den ikke har laengere.
  const setPinned = useCallback(async (id: string, pinned: boolean) => {
    setSessions((prev) => prev.map((s) => (s.id === id
      ? { ...s, pinned: pinned ? 1 : 0, archived: pinned ? 0 : s.archived }
      : s)))
    await setSessionFlags(config, id, { pinned })
    void loadSessions()
  }, [config, loadSessions])

  // Arkivering flytter samtalen til «arkiverede» nederst — den forsvinder IKKE.
  // Før fjernede vi den fra listen lokalt, og hentede den aldrig igen (serveren
  // skjuler arkiverede), så der var ingen vej tilbage. Nu sætter vi flaget og
  // lader grupperingen flytte rækken; serveren frigør fastgørelsen samtidig,
  // og det spejles lokalt.
  const setArchived = useCallback(async (id: string, archived: boolean) => {
    setSessions((prev) => prev.map((s) => (s.id === id
      ? { ...s, archived: archived ? 1 : 0, pinned: archived ? 0 : s.pinned }
      : s)))
    if (archived && activeId === id) {
      setActiveId(null)
      setMessages([])
      loadedRef.current = null
    }
    await setSessionFlags(config, id, { archived })
    void loadSessions()
  }, [config, activeId, loadSessions])

  // «Flyt til projekt» = bind samtalen til mappen. Projektet ER `workspace_root`;
  // der findes ingen projekt-tabel at flytte rækker i. Optimistisk, så gruppen
  // flytter sig straks, og serveren bekræfter bagefter.
  const setWorkspace = useCallback(async (
    id: string, kind: 'container' | 'workstation', root: string,
  ) => {
    setSessions((prev) => prev.map((s) => (s.id === id
      ? { ...s, workspace_kind: kind, workspace_root: root } : s)))
    await setSessionWorkspace(config, id, kind, root)
    void loadSessions()
  }, [config, loadSessions])

  const appendOptimistic = useCallback((msg: ChatMessage) => {
    setMessages((prev) => [...prev, { ...msg, clientStatus: 'optimistic_user' }])
  }, [])

  const reconcile = useCallback((assistantMsg: ChatMessage) => {
    setMessages((prev) => [...prev, {
      ...compactMessage(assistantMsg), clientStatus: 'server_missing_keep_stream',
    }])
  }, [])

  const value = useMemo<SessionContextValue>(
    () => ({ sessions, activeId, messages, loading, loadFejl, genindlaes, select, newChat, create, rename, remove, setPinned, setArchived, setWorkspace, refresh, refreshMessages, appendOptimistic, reconcile }),
    [sessions, activeId, messages, loading, loadFejl, genindlaes, select, newChat, create, rename, remove, setPinned, setArchived, setWorkspace, refresh, refreshMessages, appendOptimistic, reconcile],
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

/** Finished messages no longer need SSE index alignment; remove empty slots. */
function compactMessage(message: ChatMessage): ChatMessage {
  if (!Array.isArray(message.content)) return message
  const content = denseBlocks(message.content)
  return content.length === message.content.length ? message : { ...message, content }
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
  server = server.map(compactMessage)
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
  // En poll med samme server-sandhed må ikke genrendre 2.000+ Markdown-rækker.
  // Genbrug både de enkelte beskeder og hele arrayet, når indholdet er identisk.
  const localById = new Map(local.map((m) => [m.id, m]))
  const stable = result.map((next) => {
    const previous = localById.get(next.id)
    return previous && sameMessage(previous, next) ? previous : next
  })
  if (stable.length === local.length && stable.every((m, i) => m === local[i])) return local
  return stable
}

function sameMessage(a: LocalMessage, b: LocalMessage): boolean {
  return a.id === b.id && a.role === b.role && a.created_at === b.created_at &&
    (a.parent_id ?? null) === (b.parent_id ?? null) &&
    a.clientStatus === b.clientStatus &&
    JSON.stringify(a.content) === JSON.stringify(b.content)
}

function stableSessions(current: ChatSession[], incoming: ChatSession[]): ChatSession[] {
  const byId = new Map(current.map((s) => [s.id, s]))
  const stable = incoming.map((next) => {
    const previous = byId.get(next.id)
    return previous && JSON.stringify(previous) === JSON.stringify(next) ? previous : next
  })
  if (stable.length === current.length && stable.every((s, i) => s === current[i])) return current
  return stable
}

export { mergeServer, userText }
