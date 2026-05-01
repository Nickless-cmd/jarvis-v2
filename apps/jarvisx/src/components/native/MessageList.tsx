import { memo, useEffect, useRef, useState } from 'react'
import { Copy, Check, ThumbsUp } from 'lucide-react'
import { MarkdownRenderer } from '@ui/components/chat/MarkdownRenderer.jsx'
import { ThinkingBar } from '@ui/components/chat/ChatThinking.jsx'
import { ApprovalCard } from '@ui/components/chat/ApprovalCard.jsx'

interface ChatMessage {
  id?: string
  message_id?: string
  role: string
  content: string
  ts?: string
  created_at?: string
  pending?: boolean
  attachments?: Array<{ id?: string; filename: string; mimeType?: string; url?: string }>
}

interface WorkingStep {
  step?: number
  status?: string
  action?: string
  detail?: string
}

interface Props {
  messages: ChatMessage[]
  workingSteps?: WorkingStep[]
  isStreaming?: boolean
  sessionId?: string | null
}

const SMILEYS: Array<[RegExp, string]> = [
  [/:\-\)/g, '😊'], [/:\)/g, '😊'],
  [/:\-D/g, '😄'], [/:D/g, '😄'],
  [/;\-\)/g, '😉'], [/;\)/g, '😉'],
  [/:\-P/gi, '😛'], [/:P/gi, '😛'],
  [/:\-\(/g, '😢'], [/:\(/g, '😢'],
  [/<3/g, '❤️'],
]
function convertSmileys(t: string) {
  if (!t) return t
  let r = t
  for (const [p, e] of SMILEYS) r = r.replace(p, e)
  return r
}

/**
 * JarvisX-native message list — visually mirrors apps/ui's ChatTranscript
 * (message-row / message-name / message-bubble / message-time + hover
 * actions + ThinkingBar + streaming-cursor) so we get name labels,
 * locked-top thinking bar that flows from "tænker → tool → vurderer →
 * komponerer" and a blinking cursor while streaming.
 *
 * We don't embed ChatTranscript itself because JarvisX owns its own
 * layout (max-width, bg, scroll behaviour) — we just match its DOM
 * shape so apps/ui's global.css applies the same animations.
 */
export function MessageList({ messages, workingSteps, isStreaming, sessionId }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const wasNearBottomRef = useRef(true)
  const prevCountRef = useRef(messages.length)

  useEffect(() => {
    const node = containerRef.current
    if (!node) return
    const onScroll = () => {
      const distance = node.scrollHeight - node.scrollTop - node.clientHeight
      wasNearBottomRef.current = distance < 120
    }
    node.addEventListener('scroll', onScroll, { passive: true })
    return () => node.removeEventListener('scroll', onScroll)
  }, [])

  useEffect(() => {
    const node = containerRef.current
    if (!node) return
    if (prevCountRef.current === 0 || wasNearBottomRef.current) {
      node.scrollTop = node.scrollHeight
    }
    prevCountRef.current = messages.length
  }, [messages])

  useEffect(() => {
    if (!isStreaming) return
    const node = containerRef.current
    if (node && wasNearBottomRef.current) {
      node.scrollTop = node.scrollHeight
    }
  })

  // Hide raw tool messages (their results render inline via [tool_result:..]
  // refs in the assistant message). Empty system messages are hidden too.
  const visible = messages.filter((m) => {
    if (m.role === 'tool') return false
    if (m.role === 'system' && !(m.content && m.content.trim())) return false
    return true
  })

  // Pending tail: if last assistant is pending OR backend says streaming
  // but no pending assistant exists yet, show a standalone thinking bar.
  const lastAssistantPending = (() => {
    for (let i = visible.length - 1; i >= 0; i--) {
      if (visible[i].role === 'assistant') return !!visible[i].pending
      if (visible[i].role === 'user') return false
    }
    return false
  })()
  const showStandaloneThinking = isStreaming && !lastAssistantPending

  return (
    <div
      ref={containerRef}
      className="flex-1 overflow-y-auto"
      style={{ scrollBehavior: 'auto' }}
    >
      <section
        className="transcript mx-auto"
        style={{ width: '100%', maxWidth: 880, padding: '16px 24px' }}
      >
        {visible.length === 0 && !isStreaming && (
          <div className="flex h-full min-h-[40vh] items-center justify-center text-center text-xs text-fg3">
            <div>
              <div className="mb-2 text-base text-fg2">Ny samtale</div>
              <div>Skriv hvad du arbejder på — Jarvis svarer.</div>
            </div>
          </div>
        )}

        {visible.map((m, i) => (
          <Row
            key={m.id ?? m.message_id ?? `${m.role}-${i}`}
            message={m}
            workingSteps={workingSteps}
            sessionId={sessionId}
          />
        ))}

        {showStandaloneThinking && (
          <article className="message-row assistant">
            <div className="message-name">Jarvis</div>
            <div className="message-bubble pending">
              <ThinkingBar workingSteps={workingSteps} isStreaming={true} />
            </div>
          </article>
        )}
      </section>
    </div>
  )
}

const Row = memo(
  function Row({
    message,
    workingSteps,
    sessionId,
  }: {
    message: ChatMessage
    workingSteps?: WorkingStep[]
    sessionId?: string | null
  }) {
    const role = message.role

    if (role === 'compact_marker') {
      return (
        <div className="my-2 rounded border border-warn/20 bg-warn/5 px-3 py-1.5 text-[11px] italic text-warn/80">
          {message.content}
        </div>
      )
    }

    if (role === 'approval_request') {
      return (
        <article className="message-row assistant">
          <div className="message-name">Jarvis</div>
          <div className="message-bubble">
            <ApprovalCard approval={message} />
          </div>
        </article>
      )
    }

    if (role === 'user') {
      return (
        <article className="message-row user">
          <div className="message-name">Du</div>
          <div className={`message-bubble ${message.pending ? 'pending' : ''}`}>
            {message.attachments && message.attachments.length > 0 && (
              <AttachmentStrip attachments={message.attachments} sessionId={sessionId} />
            )}
            {message.content ? (
              <div className="message-content">
                <MarkdownRenderer content={convertSmileys(message.content)} />
              </div>
            ) : null}
          </div>
          {message.ts && <div className="message-time">{message.ts}</div>}
        </article>
      )
    }

    // assistant (and any other role like 'output')
    return (
      <article className="message-row assistant">
        <div className="message-name">Jarvis</div>
        <AssistantBubble message={message} workingSteps={workingSteps} />
        {message.ts && <div className="message-time">{message.ts}</div>}
      </article>
    )
  },
  (prev, next) => {
    if (prev.message === next.message) {
      // even if ref equal, working steps may have advanced for pending bubble
      if (next.message?.pending && prev.workingSteps !== next.workingSteps) return false
      return true
    }
    if (prev.message?.content !== next.message?.content) return false
    if (prev.message?.pending !== next.message?.pending) return false
    if (
      (prev.message?.id ?? prev.message?.message_id) !==
      (next.message?.id ?? next.message?.message_id)
    )
      return false
    if (next.message?.pending && prev.workingSteps !== next.workingSteps) return false
    return true
  },
)

const AssistantBubble = memo(function AssistantBubble({
  message,
  workingSteps,
}: {
  message: ChatMessage
  workingSteps?: WorkingStep[]
}) {
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
      {!message.pending && message.content && (
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
})

function AttachmentStrip({
  attachments,
  sessionId,
}: {
  attachments: NonNullable<ChatMessage['attachments']>
  sessionId?: string | null
}) {
  const images = attachments.filter((a) => (a.mimeType || '').startsWith('image/'))
  const files = attachments.filter((a) => !(a.mimeType || '').startsWith('image/'))
  function srcFor(a: { id?: string; url?: string }) {
    if (a.url) return a.url
    if (a.id && sessionId) return `/attachments/${a.id}?session_id=${sessionId}`
    return null
  }
  return (
    <div>
      {images.length > 0 && (
        <div className="message-attachment-strip">
          {images.map((a, i) => {
            const src = srcFor(a)
            return src ? (
              <a
                key={a.id ?? i}
                href={src}
                target="_blank"
                rel="noopener noreferrer"
                className="message-attachment-thumb"
                title={a.filename}
              >
                <img src={src} alt={a.filename} loading="lazy" />
              </a>
            ) : null
          })}
        </div>
      )}
      {files.map((a, i) => (
        <span key={a.id ?? i} className="message-attachment-pill">
          📎 {a.filename}
        </span>
      ))}
    </div>
  )
}
