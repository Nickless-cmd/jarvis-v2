import { useEffect, useRef, useState } from 'react'
import { ArrowDown } from 'lucide-react'
import { useSessions } from '../hooks/useSessions'
import { useStream } from '../hooks/useStream'
import { useSettings } from '../hooks/useSettings'
import { MessageRow } from '../components/rich/MessageRow'
import { Composer, type ComposerSendOpts } from '../components/shell/Composer'
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
  const reconciledForRun = useRef<string | null>(null)
  const transcriptRef = useRef<HTMLDivElement>(null)
  const [atBottom, setAtBottom] = useState(true)
  const [unread, setUnread] = useState(0)

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

  const handleSend = async (text: string, opts: ComposerSendOpts) => {
    let sid = sessionId
    console.warn('[DIAG] handleSend start sessionId=', sessionId, 'text=', text)
    if (!sid) {
      const created = await sessions.create('Ny samtale')
      sid = created.id
      console.warn('[DIAG] lazy-created session', sid)
    }
    sessions.appendOptimistic({
      id: `u-${Date.now()}`,
      role: 'user',
      content: [{ type: 'text', text }],
      created_at: new Date().toISOString(),
      parent_id: null,
    })
    setAtBottom(true)
    setUnread(0)
    stream.send(text, { sessionId: sid, approvalMode: opts.permission })
  }

  const visibleMessages = sessions.messages.filter((m) => m.role === 'user' || m.role === 'assistant')
  const streaming = stream.status === 'working'
  const isEmpty =
    !sessionId ||
    (visibleMessages.length === 0 && stream.status === 'idle' && stream.blocks.length === 0)

  const composer = <Composer disabled={streaming} onSend={handleSend} model="deepseek-flash" thinking="think" />

  // ── Tom/ny samtale: composer centreret midt på skærmen ──
  if (isEmpty) {
    return (
      <div className="chatview empty">
        <div className="chat-empty">
          <h2>Hej.</h2>
          <p>Skriv hvad du arbejder på.</p>
          {composer}
        </div>
      </div>
    )
  }

  // ── Aktiv samtale ──
  const activeSession = sessions.sessions.find((s) => s.id === sessionId)
  const chatTitle = activeSession?.title || 'Samtale'
  return (
    <div className="chatview">
      <div className="chatview-head">
        <div className="chatview-head-left">
          <PresenceDot status={stream.status} /> <span className="chat-title">{chatTitle}</span>
        </div>
        {settings && (
          <ConnectionPill config={{ apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken }} />
        )}
      </div>
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
        <LivenessIndicator status={stream.status} elapsedMs={stream.elapsedMs} density="compact" />
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
        {composer}
      </div>
    </div>
  )
}
