import { useEffect, useRef } from 'react'
import { MarkdownRenderer } from './MarkdownRenderer'
import { ApprovalCard } from './ApprovalCard'

export function ChatTranscript({ messages, workingSteps }) {
  const transcriptRef = useRef(null)

  useEffect(() => {
    const node = transcriptRef.current
    if (!node) return
    node.scrollTop = node.scrollHeight
  }, [messages])

  if (!messages.length) {
    return (
      <section ref={transcriptRef} className="transcript empty-transcript">
        <div className="empty-transcript-copy">
          <p className="eyebrow">Front Door</p>
          <strong>Start a conversation</strong>
          <p className="muted">This session is persisted and will still be here after refresh.</p>
        </div>
      </section>
    )
  }

  return (
    <section ref={transcriptRef} className="transcript">
      {messages.filter((m) => m.role !== 'tool').map((message) =>
        message.role === 'approval_request' ? (
          <article key={message.id} className="message-row assistant">
            <div className="message-bubble">
              <ApprovalCard approval={message} />
            </div>
          </article>
        ) : (
          <article key={message.id} className={`message-row ${message.role}`}>
            <div className="message-name">
              {message.role === 'assistant' ? 'Jarvis' : 'Du'}
            </div>
            <div className={`message-bubble ${message.pending ? 'pending' : ''}`}>
              {message.pending && workingSteps?.length > 0 ? (
                <span className="working-shimmer">
                  {workingSteps.find(s => s.status === 'running')?.detail
                    || workingSteps.find(s => s.status === 'running')?.action
                    || 'working…'}
                </span>
              ) : null}
              {message.content ? (
                <div className="message-content">
                  <MarkdownRenderer content={message.content} />
                  {message.pending && <span className="streaming-cursor" />}
                </div>
              ) : null}
            </div>
            <div className="message-time">{message.ts}</div>
          </article>
        )
      )}
    </section>
  )
}
