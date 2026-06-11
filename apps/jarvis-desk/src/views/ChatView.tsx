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

/** Chat-mode: orkestrerer transcript (afsluttede beskeder fra SessionContext),
 *  igangværende stream (StreamContext.blocks), composer-send-flow, reconcile på
 *  done, og feedback-bannere efter status. Density=compact (Claude.ai-stil). */
export function ChatView({ sessionId }: { sessionId: string }) {
  const sessions = useSessions()
  const stream = useStream()
  const { settings } = useSettings()
  const reconciledForRun = useRef<string | null>(null)
  const transcriptRef = useRef<HTMLDivElement>(null)
  const [atBottom, setAtBottom] = useState(true)
  const [unread, setUnread] = useState(0)

  useEffect(() => { sessions.select(sessionId) }, [sessionId])

  // Reconcile når stream når done (kun én gang pr. run).
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

  // Auto-scroll: spring til bund ved session-load og når man er nær bunden.
  // Hvis man har scrollet op og der kommer nyt → tæl ulæste (badge) i stedet.
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
    if (atBottom) {
      el.scrollTop = el.scrollHeight
    } else {
      setUnread((u) => u + 1)
    }
  }, [sessions.messages.length, sessionId])

  // Under streaming: følg bunden hvis man er der.
  useEffect(() => {
    const el = transcriptRef.current
    if (el && atBottom) el.scrollTop = el.scrollHeight
  }, [stream.blocks, atBottom])

  const handleSend = (text: string, opts: ComposerSendOpts) => {
    sessions.appendOptimistic({
      id: `u-${Date.now()}`,
      role: 'user',
      content: [{ type: 'text', text }],
      created_at: new Date().toISOString(),
      parent_id: null,
    })
    setAtBottom(true)
    setUnread(0)
    stream.send(text, { sessionId, approvalMode: opts.permission })
  }

  const streaming = stream.status === 'working'
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
        {sessions.messages
          .filter((m) => m.role === 'user' || m.role === 'assistant')
          .map((m) => (
            <MessageRow
              key={m.id}
              role={m.role === 'user' ? 'user' : 'assistant'}
              blocks={m.content}
              density="compact"
              streaming={false}
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
          <ErrorBanner message={stream.error.message} onDismiss={() => { /* banner ryddes ved næste send */ }} />
        )}
      </div>

      {/* Composer-område: scroll-til-bund pil sidder absolut OVER composeren
          (bottom: 100%), så den følger composer-højden — ikke en fast offset. */}
      <div className="composer-area">
        {!atBottom && (
          <button type="button" className="scroll-bottom-btn" onClick={scrollToBottom} aria-label="Til bund">
            <ArrowDown size={16} />
            {unread > 0 && <span className="scroll-badge">{unread} ny{unread > 1 ? 'e' : ''}</span>}
          </button>
        )}
        <Composer disabled={streaming} onSend={handleSend} model="deepseek-flash" thinking="think" />
      </div>
    </div>
  )
}
