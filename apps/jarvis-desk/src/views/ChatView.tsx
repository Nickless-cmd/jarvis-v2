import { useEffect, useRef } from 'react'
import { useSessions } from '../hooks/useSessions'
import { useStream } from '../hooks/useStream'
import { MessageRow } from '../components/rich/MessageRow'
import { Composer } from '../components/shell/Composer'
import { PresenceDot } from '../components/shell/PresenceDot'
import { LivenessIndicator } from '../components/feedback/LivenessIndicator'
import { InterruptedBanner } from '../components/feedback/InterruptedBanner'
import { HangPrompt } from '../components/feedback/HangPrompt'
import { ErrorBanner } from '../components/feedback/ErrorBanner'

/** Chat-mode: orkestrerer transcript (afsluttede beskeder fra SessionContext),
 *  igangværende stream (StreamContext.blocks), composer-send-flow, reconcile på
 *  done, og feedback-bannere efter status. Density=compact (Claude.ai-stil). */
export function ChatView({ sessionId }: { sessionId: string }) {
  const sessions = useSessions()
  const stream = useStream()
  const reconciledForRun = useRef<string | null>(null)
  const transcriptRef = useRef<HTMLDivElement>(null)

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

  // Auto-scroll: spring til bund ved session-load OG når man er nær bunden
  // (nye beskeder / streaming). Ved session-skift tvinges bund uanset position.
  const lastScrolledSession = useRef<string | null>(null)
  useEffect(() => {
    const el = transcriptRef.current
    if (!el) return
    const isNewSession = lastScrolledSession.current !== sessionId
    const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 200
    if (isNewSession || nearBottom || stream.status === 'working') {
      el.scrollTop = el.scrollHeight
      if (sessions.messages.length > 0) lastScrolledSession.current = sessionId
    }
  }, [sessions.messages, stream.blocks, sessionId, stream.status])

  const handleSend = (text: string) => {
    sessions.appendOptimistic({
      id: `u-${Date.now()}`,
      role: 'user',
      content: [{ type: 'text', text }],
      created_at: new Date().toISOString(),
      parent_id: null,
    })
    stream.send(text, { sessionId })
  }

  const streaming = stream.status === 'working'
  return (
    <div className="chatview">
      <div className="chatview-head">
        <PresenceDot status={stream.status} /> Jarvis
      </div>
      <div className="transcript" ref={transcriptRef}>
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
      <Composer disabled={streaming} onSend={handleSend} model="deepseek-flash" thinking="think" />
    </div>
  )
}
