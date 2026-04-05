import { useEffect, useRef } from 'react'
import { Bot, User } from 'lucide-react'
import { MarkdownRenderer } from './MarkdownRenderer'

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
      {messages.map((message) => (
        <article key={message.id} className={`message-row ${message.role}`}>
          <div className="message-avatar">
            {message.role === 'assistant' ? <Bot size={15} /> : <User size={15} />}
          </div>
          <div className={`message-bubble ${message.pending ? 'pending' : ''}`}>
            <div className="message-meta">
              <strong>{message.role === 'assistant' ? 'Jarvis' : 'You'}</strong>
              {message.pending && workingSteps?.length > 0 ? (
                <span className="working-shimmer">
                  {workingSteps.find(s => s.status === 'running')?.detail
                    || workingSteps.find(s => s.status === 'running')?.action
                    || 'working…'}
                </span>
              ) : (
                <span>{message.ts}</span>
              )}</div>
            {message.content ? (
              <div className="message-content">
                <MarkdownRenderer content={message.content} />
                {message.pending && <span className="streaming-cursor" />}
              </div>
            ) : null}
          </div>
        </article>
      ))}
    </section>
  )
}
