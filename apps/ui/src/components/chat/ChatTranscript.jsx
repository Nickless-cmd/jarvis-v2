import { useState, useEffect, useRef } from 'react'
import { Copy, Check, ThumbsUp } from 'lucide-react'
import { MarkdownRenderer } from './MarkdownRenderer'
import { ApprovalCard } from './ApprovalCard'

/**
 * Renders a single assistant message bubble with a hover toolbar.
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
        {message.pending ? (
          <span
            className="working-shimmer"
            style={{ visibility: workingSteps?.some(s => s.status === 'running') ? 'visible' : 'hidden' }}
          >
            {workingSteps?.find((s) => s.status === 'running')?.detail ||
              workingSteps?.find((s) => s.status === 'running')?.action ||
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

/**
 * Renders attachment thumbnails above a user message bubble.
 * Images are clickable to open the lightbox.
 */
function AttachmentStrip({ attachments, sessionId, onOpenLightbox }) {
  if (!attachments || attachments.length === 0) return null

  const images = attachments.filter((a) => a.mimeType?.startsWith('image/'))
  const files = attachments.filter((a) => !a.mimeType?.startsWith('image/'))

  function srcFor(a) {
    if (a.objectUrl) return a.objectUrl
    if (a.id && sessionId) return `/attachments/${a.id}?session_id=${sessionId}`
    return null
  }

  return (
    <div>
      {images.length > 0 && (
        <div className="message-attachment-strip">
          {images.map((a) => {
            const src = srcFor(a)
            return src ? (
              <div
                key={a.id}
                className="message-attachment-thumb"
                onClick={() => onOpenLightbox({ src, filename: a.filename })}
                title={a.filename}
              >
                <img src={src} alt={a.filename} loading="lazy" />
              </div>
            ) : null
          })}
        </div>
      )}
      {files.map((a) => (
        <span key={a.id} className="message-attachment-pill">
          📎 {a.filename}
        </span>
      ))}
    </div>
  )
}

export function ChatTranscript({ messages, workingSteps, sessionId }) {
  const transcriptRef = useRef(null)
  const hasInitialScrolled = useRef(false)
  const prevMessageCount = useRef(0)
  const [lightbox, setLightbox] = useState(null) // {src, filename} or null

  useEffect(() => {
    const node = transcriptRef.current
    if (!node || messages.length === 0) return

    if (!hasInitialScrolled.current) {
      node.scrollTop = node.scrollHeight
      hasInitialScrolled.current = true
      prevMessageCount.current = messages.length
      return
    }

    if (messages.length > prevMessageCount.current) {
      node.scrollTop = node.scrollHeight
      prevMessageCount.current = messages.length
      return
    }

    prevMessageCount.current = messages.length

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
    <>
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
                  {message.attachments?.length > 0 && (
                    <AttachmentStrip
                      attachments={message.attachments}
                      sessionId={sessionId}
                      onOpenLightbox={setLightbox}
                    />
                  )}
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

      {lightbox && (
        <div className="attachment-lightbox-overlay" onClick={() => setLightbox(null)}>
          <div className="attachment-lightbox-inner" onClick={(e) => e.stopPropagation()}>
            <img src={lightbox.src} alt={lightbox.filename} />
          </div>
        </div>
      )}
    </>
  )
}
