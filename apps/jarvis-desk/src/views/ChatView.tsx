import { useEffect, useRef, useState } from 'react'
import { ArrowDown, PanelRight } from 'lucide-react'
import { useSessions } from '../hooks/useSessions'
import { useStream } from '../hooks/useStream'
import { useSettings } from '../hooks/useSettings'
import { usePanel } from '../hooks/usePanel'
import { MessageRow } from '../components/rich/MessageRow'
import { Composer, type ComposerSendOpts } from '../components/shell/Composer'
import { getContextInfo } from '../lib/api'
import { PresenceDot } from '../components/shell/PresenceDot'
import { ConnectionPill } from '../components/shell/ConnectionPill'
import { LivenessIndicator } from '../components/feedback/LivenessIndicator'
import { InterruptedBanner } from '../components/feedback/InterruptedBanner'
import { HangPrompt } from '../components/feedback/HangPrompt'
import { ErrorBanner } from '../components/feedback/ErrorBanner'

const NEAR_BOTTOM_PX = 120

/** Chat-mode. Ved tom/ny samtale: composer centreret midt på skærmen. Ved
 *  første besked oprettes session (hvis nødvendigt) og layoutet skifter — composer
 *  hopper ned i bunden, transcript fylder. */
export function ChatView({ sessionId }: { sessionId: string | null }) {
  const sessions = useSessions()
  const stream = useStream()
  const { settings } = useSettings()
  const panel = usePanel()
  const reconciledForRun = useRef<string | null>(null)
  const transcriptRef = useRef<HTMLDivElement>(null)
  const [atBottom, setAtBottom] = useState(true)
  const [unread, setUnread] = useState(0)
  const [compactAt, setCompactAt] = useState(0)

  // Context-ring (#9): hent autocompact-tærsklen én gang.
  useEffect(() => {
    if (!settings) return
    getContextInfo({ apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken })
      .then((r) => setCompactAt(r.compact_at))
      .catch(() => setCompactAt(0))
  }, [settings])

  // Context-ring: vis det RIGTIGE niveau fra start. Når en tur slutter kender
  // vi de ægte kontekst-tokens (usage.input + cache) — vi gemmer dem pr. session
  // i localStorage, så de vises straks ved genåbning (i stedet for tom ring).
  const [seededTokens, setSeededTokens] = useState(0)
  useEffect(() => {
    const v = sessionId ? Number(localStorage.getItem(`jarvis-desk:ctx:${sessionId}`) || '0') : 0
    setSeededTokens(Number.isFinite(v) ? v : 0)
  }, [sessionId])
  const liveTokens = stream.usage.input + stream.usage.cacheHit
  useEffect(() => {
    if (sessionId && liveTokens > 0) {
      localStorage.setItem(`jarvis-desk:ctx:${sessionId}`, String(liveTokens))
      setSeededTokens(liveTokens)
    }
  }, [liveTokens, sessionId])
  const contextTokens = Math.max(liveTokens, seededTokens)

  useEffect(() => { if (sessionId) sessions.select(sessionId) }, [sessionId])

  useEffect(() => {
    if (stream.status === 'done' && stream.blocks.length > 0 && reconciledForRun.current !== stream.activeRunId) {
      reconciledForRun.current = stream.activeRunId
      sessions.reconcile({
        id: `a-${stream.activeRunId ?? Date.now()}`,
        role: 'assistant',
        content: stream.blocks,
        created_at: new Date().toISOString(),
        parent_id: null,
      })
    }
  }, [stream.status])

  const scrollToBottom = () => {
    const el = transcriptRef.current
    if (el) el.scrollTop = el.scrollHeight
    setUnread(0)
  }

  const onScroll = () => {
    const el = transcriptRef.current
    if (!el) return
    const near = el.scrollHeight - el.scrollTop - el.clientHeight < NEAR_BOTTOM_PX
    setAtBottom(near)
    if (near) setUnread(0)
  }

  const lastScrolledSession = useRef<string | null>(null)
  useEffect(() => {
    const el = transcriptRef.current
    if (!el) return
    const isNewSession = lastScrolledSession.current !== sessionId
    if (isNewSession) {
      el.scrollTop = el.scrollHeight
      if (sessions.messages.length > 0) lastScrolledSession.current = sessionId
      setUnread(0)
      return
    }
    if (atBottom) el.scrollTop = el.scrollHeight
    else setUnread((u) => u + 1)
  }, [sessions.messages.length, sessionId])

  useEffect(() => {
    const el = transcriptRef.current
    if (el && atBottom) el.scrollTop = el.scrollHeight
  }, [stream.blocks, atBottom])

  const doSend = async (text: string, opts: ComposerSendOpts) => {
    let sid = sessionId
    if (!sid) {
      const created = await sessions.create('Ny samtale')
      sid = created.id
    }
    // v2-stream kræver en ikke-tom besked. Ved billede-kun send bruges filnavnene
    // som fallback-tekst (backend afviser ellers med 400). Jarvis ser endnu ikke
    // selve billedet — vision-wiring i start_visible_run er en separat backend-opgave.
    const message = text.trim() || opts.attachments.map((a) => a.name).join(', ') || 'Vedhæftet'
    const imageBlocks = opts.attachments
      .filter((a) => a.isImage && a.src)
      .map((a) => ({ type: 'image' as const, src: a.src as string, alt: a.name }))
    const content = [
      ...(text.trim() ? [{ type: 'text' as const, text }] : []),
      ...imageBlocks,
      ...(!text.trim() && imageBlocks.length === 0 ? [{ type: 'text' as const, text: message }] : []),
    ]
    sessions.appendOptimistic({
      id: `u-${Date.now()}`,
      role: 'user',
      content,
      created_at: new Date().toISOString(),
      parent_id: null,
    })
    setAtBottom(true)
    setUnread(0)
    stream.send(message, {
      sessionId: sid,
      approvalMode: opts.permission,
      attachmentIds: opts.attachments.map((a) => a.id),
    })
  }

  const streaming = stream.status === 'working'

  // Follow-up kø: skriver man mens Jarvis streamer, lægges beskeden i kø og
  // sendes automatisk når turen er færdig (done). Deterministisk — ikke nudge.
  const [queued, setQueued] = useState<{ text: string; opts: ComposerSendOpts } | null>(null)
  const handleSend = (text: string, opts: ComposerSendOpts) => {
    if (streaming) setQueued({ text, opts })
    else void doSend(text, opts)
  }
  useEffect(() => {
    if (stream.status === 'done' && queued) {
      const q = queued
      setQueued(null)
      void doSend(q.text, q.opts)
    }
  }, [stream.status, queued])

  const visibleMessages = sessions.messages.filter((m) => m.role === 'user' || m.role === 'assistant')
  const isEmpty =
    !sessionId ||
    (visibleMessages.length === 0 && stream.status === 'idle' && stream.blocks.length === 0 && !queued)

  const ensureSessionId = async () => {
    if (sessionId) return sessionId
    const created = await sessions.create('Ny samtale')
    return created.id
  }

  const composer = (
    <Composer
      streaming={streaming}
      onSend={handleSend}
      onStop={() => void stream.abort()}
      model="deepseek-flash"
      thinking="think"
      config={settings ? { apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken } : undefined}
      getSessionId={ensureSessionId}
      showPermissions={false}
      contextTokens={contextTokens}
      compactAt={compactAt}
    />
  )

  const activeSession = sessions.sessions.find((s) => s.id === sessionId)
  const chatTitle = activeSession?.title || (isEmpty ? 'Ny samtale' : 'Samtale')
  const header = (
    <div className="chatview-head">
      <div className="chatview-head-left">
        <PresenceDot status={stream.status} /> <span className="chat-title">{chatTitle}</span>
      </div>
      <div className="chatview-head-right">
        {settings && (
          <ConnectionPill config={{ apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken }} />
        )}
        <button
          type="button"
          className={`panel-toggle ${panel.open ? 'active' : ''}`}
          aria-label="Vis/skjul panel"
          title="Panel"
          onClick={panel.toggle}
        >
          <PanelRight size={16} />
        </button>
      </div>
    </div>
  )

  // ── Tom/ny samtale: header øverst, composer centreret midt på skærmen ──
  if (isEmpty) {
    return (
      <div className="chatview empty">
        {header}
        <div className="chat-empty">
          <h2>Hej.</h2>
          <p>Skriv hvad du arbejder på.</p>
          {composer}
        </div>
      </div>
    )
  }

  // ── Aktiv samtale ──
  return (
    <div className="chatview">
      {header}
      <div className="transcript" ref={transcriptRef} onScroll={onScroll}>
        {visibleMessages.map((m) => (
          <MessageRow
            key={m.id}
            role={m.role === 'user' ? 'user' : 'assistant'}
            blocks={m.content}
            density="compact"
            streaming={false}
            createdAt={m.created_at}
          />
        ))}
        {streaming && stream.blocks.length > 0 && (
          <MessageRow role="assistant" blocks={stream.blocks} density="compact" streaming />
        )}
        <LivenessIndicator status={stream.status} elapsedMs={stream.elapsedMs} density="compact" workingStep={stream.workingStep} />
        {stream.status === 'interrupted' && <InterruptedBanner onResume={() => stream.continueFromPartial()} />}
        {stream.status === 'hung' && (
          <HangPrompt onResume={() => stream.continueFromPartial()} onAbort={() => void stream.abort()} />
        )}
        {stream.status === 'error' && stream.error && (
          <ErrorBanner message={stream.error.message} onDismiss={() => { /* ryddes ved næste send */ }} />
        )}
      </div>

      <div className="composer-area">
        {!atBottom && (
          <button type="button" className="scroll-bottom-btn" onClick={scrollToBottom} aria-label="Til bund">
            <ArrowDown size={16} />
            {unread > 0 && <span className="scroll-badge">{unread} ny{unread > 1 ? 'e' : ''}</span>}
          </button>
        )}
        {queued && (
          <div className="queued-chip">
            <span className="queued-label">I kø</span>
            <span className="queued-text">{queued.text}</span>
            <button type="button" className="queued-cancel" onClick={() => setQueued(null)} aria-label="Fjern fra kø">×</button>
          </div>
        )}
        {composer}
      </div>
    </div>
  )
}
