import { useState, useEffect, useRef } from 'react'
import { Copy, Check, ThumbsUp } from 'lucide-react'
import { MarkdownRenderer } from './MarkdownRenderer'
import { ApprovalCard } from './ApprovalCard'

/**
 * Renders a single assistant message bubble with a hover toolbar.
 * Toolbar shows: Copy message | Thumbs up
 * Only rendered for non-pending assistant messages.
 */
function MessageWithActions({ message, workingSteps }) {
  const [copied, setCopied] = useState(false)
  const [liked, setLiked] = useState(false)

  function handleCopy() {
    navigator.clipboard.writeText(message.content || '').then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    })
  }

  return (
    <div className="message-group">
      <div className={`message-bubble ${message.pending ? 'pending' : ''}`}>
        {message.pending && workingSteps?.length > 0 ? (
          <span className="working-shimmer">
            {workingSteps.find((s) => s.status === 'running')?.detail ||
              workingSteps.find((s) => s.status === 'running')?.action ||
              'working…'}
          </span>
        ) : null}
        {message.content ? (
          <div className="message-content">
            <MarkdownRenderer content={message.content} streaming={!!message.pending} />
            {message.pending && <span className="streaming-cursor" />}
          </div>
        ) : null}
      </div>
      {!message.pending && (
        <div className="message-actions">
          <button onClick={handleCopy} title="Kopiér besked">
            {copied ? <Check size={12} /> : <Copy size={12} />}
          </button>
          <button
            onClick={() => setLiked((l) => !l)}
            title="Synes godt om"
            className={liked ? 'liked' : ''}
          >
            <ThumbsUp size={12} />
          </button>
        </div>
      )}
    </div>
  )
}

export function ChatTranscript({ messages, workingSteps }) {
  const transcriptRef = useRef(null)

  // On first message load, always scroll to bottom unconditionally.
  // On subsequent updates, only scroll if the user is already near the bottom.
  const hasInitialScrolled = useRef(false)

  useEffect(() => {
    const node = transcriptRef.current
    if (!node || messages.length === 0) return

    if (!hasInitialScrolled.current) {
      node.scrollTop = node.scrollHeight
      hasInitialScrolled.current = true
      return
    }

    const distanceFromBottom = node.scrollHeight - node.scrollTop - node.clientHeight
    if (distanceFromBottom < 120) node.scrollTop = node.scrollHeight
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
            {message.role === 'assistant' ? (
              <MessageWithActions message={message} workingSteps={workingSteps} />
            ) : (
              <div className={`message-bubble ${message.pending ? 'pending' : ''}`}>
                {message.content ? (
                  <div className="message-content">
                    <MarkdownRenderer content={message.content} />
                  </div>
                ) : null}
              </div>
            )}
            <div className="message-time">{message.ts}</div>
          </article>
        )
      )}
    </section>
  )
}
