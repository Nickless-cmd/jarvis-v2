import { memo, useState, useEffect, useRef } from 'react'
import { Copy, Check, ThumbsUp, Globe } from 'lucide-react'
import { MarkdownRenderer } from './MarkdownRenderer'
import { ApprovalCard } from './ApprovalCard'
import { ThinkingBar } from './ChatThinking'

const SMILEY_REPLACEMENTS = [
  [/:\-\)/g, '😊'], [/:\)/g, '😊'],
  [/:\-D/g, '😄'], [/:D/g, '😄'],
  [/;\-\)/g, '😉'], [/;\)/g, '😉'],
  [/:\-P/gi, '😛'], [/:P/gi, '😛'],
  [/:\-\(/g, '😢'], [/:\(/g, '😢'],
  [/:\-O/gi, '😮'], [/:O/gi, '😮'],
  [/:\-\|/g, '😐'], [/:\|/g, '😐'],
  [/>:\(/g, '😠'],
  [/:\*/g, '😘'],
  [/<3/g, '❤️'],
  [/<\/3/g, '💔'],
  [/XD/g, '😆'],
  [/xD/g, '😆'],
]

function convertSmileys(text) {
  if (!text) return text
  let result = text
  for (const [pattern, emoji] of SMILEY_REPLACEMENTS) {
    result = result.replace(pattern, emoji)
  }
  return result
}

function BrowserIndicator({ browserBody }) {
  const status = browserBody?.status
  if (!status || status === 'idle' || status === 'absent') return null

  const label = { navigating: 'navigerer…', observing: 'læser side…', acting: 'interagerer…' }[status] || 'browser aktiv…'
  const url = (browserBody?.last_url || browserBody?.url || '').replace(/^https?:\/\//, '').split('?')[0].slice(0, 52)

  return (
    <div className="browser-indicator">
      <div className="browser-indicator-icon">
        <Globe size={12} />
      </div>
      <div className="browser-indicator-body">
        <span className="browser-indicator-label">{label}</span>
        {url && <span className="browser-indicator-url">{url}</span>}
      </div>
      <div className="browser-scan-bar" />
    </div>
  )
}

/**
 * Renders a single assistant message bubble with a hover toolbar.
 */
// Memoized so that when the parent (ChatTranscript / ChatPage) re-renders
// — e.g. on every keystroke in the Composer — settled messages aren't
// re-rendered. This is essential for sessions with hundreds of messages
// where each bubble owns a MarkdownRenderer + Prism syntax highlighter.
// We only re-render if the message reference changed or if workingSteps
// became relevant to a still-pending message.
const MessageWithActions = memo(function MessageWithActions({ message, workingSteps }) {
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
        {message.pending && !message.content ? (
          <ThinkingBar workingSteps={workingSteps} isStreaming={true} />
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
}, (prev, next) => {
  // Cheap shallow check on the fields that can drive a visible re-render.
  // Reference equality on `message` is enough for settled bubbles; for the
  // currently-streaming bubble we also check content/pending so deltas show.
  if (prev.message !== next.message) {
    if (prev.message?.content !== next.message?.content) return false
    if (prev.message?.pending !== next.message?.pending) return false
    if (prev.message?.message_id !== next.message?.message_id) return false
  }
  // workingSteps only matters for pending bubbles — skip the reference
  // check otherwise. For pending bubbles, identity change forces re-render.
  if (next.message?.pending && prev.workingSteps !== next.workingSteps) return false
  return true
})

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

export function ChatTranscript({ messages, workingSteps, sessionId, isStreaming, jarvisSurface }) {
  const browserBody = jarvisSurface?.continuity?.runtime_work?.browser_body || {}
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
                      <MarkdownRenderer content={convertSmileys(message.content)} />
                    </div>
                  ) : null}
                </div>
              )}
              <div className="message-time">{message.ts}</div>
            </article>
          )
        )}
      </section>

      {isStreaming && <BrowserIndicator browserBody={browserBody} />}

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
