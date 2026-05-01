import { memo, useEffect, useRef, useState } from 'react'
import {
  Copy,
  Check,
  ThumbsUp,
  RotateCcw,
  Pencil,
  GitBranch,
  X,
} from 'lucide-react'
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

export type MessageAction =
  | { type: 'retry'; userText: string }
  | { type: 'edit-resend'; messageId: string; newText: string }
  | { type: 'fork'; messageId: string }

interface Props {
  messages: ChatMessage[]
  workingSteps?: WorkingStep[]
  isStreaming?: boolean
  sessionId?: string | null
  onAction?: (a: MessageAction) => void
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
export function MessageList({ messages, workingSteps, isStreaming, sessionId, onAction }: Props) {
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

  // Auto-scroll on:
  //   1. first mount (initial paint of an existing session)
  //   2. new message arriving (count went up — always scroll)
  //   3. streaming content growing in the last message (scroll only
  //      if user is near the bottom — don't yank them while reading)
  //
  // The trick that was missing: dependency on the *last message's
  // content* so token-by-token streaming actually fires the effect.
  // We also defer to rAF so layout has settled before measuring
  // scrollHeight — saves a one-frame jitter on long messages.
  const lastMsgKey = (() => {
    const m = messages[messages.length - 1]
    if (!m) return ''
    const id = m.id ?? m.message_id ?? ''
    return `${id}::${(m.content || '').length}`
  })()
  useEffect(() => {
    const node = containerRef.current
    if (!node) return
    const isFirstPaint = prevCountRef.current === 0 && messages.length > 0
    const grew = messages.length > prevCountRef.current
    const shouldScroll = isFirstPaint || grew || wasNearBottomRef.current
    if (shouldScroll) {
      requestAnimationFrame(() => {
        const n = containerRef.current
        if (n) n.scrollTop = n.scrollHeight
      })
    }
    prevCountRef.current = messages.length
  }, [messages.length, lastMsgKey, isStreaming])

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

        {visible.map((m, i) => {
          // Find the most-recent user message preceding this one — retry
          // re-fires that exact text in the session
          let prevUserText = ''
          for (let j = i - 1; j >= 0; j--) {
            if (visible[j].role === 'user') {
              prevUserText = visible[j].content || ''
              break
            }
          }
          return (
            <Row
              key={m.id ?? m.message_id ?? `${m.role}-${i}`}
              message={m}
              workingSteps={workingSteps}
              sessionId={sessionId}
              prevUserText={prevUserText}
              onAction={onAction}
            />
          )
        })}

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
    prevUserText,
    onAction,
  }: {
    message: ChatMessage
    workingSteps?: WorkingStep[]
    sessionId?: string | null
    prevUserText?: string
    onAction?: (a: MessageAction) => void
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
        <UserBubble
          message={message}
          sessionId={sessionId}
          onAction={onAction}
        />
      )
    }

    // assistant (and any other role like 'output')
    return (
      <article className="message-row assistant">
        <div className="message-name">Jarvis</div>
        <AssistantBubble
          message={message}
          workingSteps={workingSteps}
          prevUserText={prevUserText}
          onAction={onAction}
        />
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
  prevUserText,
  onAction,
}: {
  message: ChatMessage
  workingSteps?: WorkingStep[]
  prevUserText?: string
  onAction?: (a: MessageAction) => void
}) {
  const [copied, setCopied] = useState(false)
  const [liked, setLiked] = useState(false)

  function handleCopy() {
    navigator.clipboard.writeText(message.content || '').then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    })
  }

  const messageId = message.id ?? message.message_id ?? ''

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
          {onAction && prevUserText && (
            <button
              onClick={() => onAction({ type: 'retry', userText: prevUserText })}
              title="Retry — re-send foregående besked"
            >
              <RotateCcw size={12} />
            </button>
          )}
          {onAction && messageId && (
            <button
              onClick={() => onAction({ type: 'fork', messageId })}
              title="Fork — kloner samtalen op til denne besked"
            >
              <GitBranch size={12} />
            </button>
          )}
        </div>
      )}
    </div>
  )
})

function UserBubble({
  message,
  sessionId,
  onAction,
}: {
  message: ChatMessage
  sessionId?: string | null
  onAction?: (a: MessageAction) => void
}) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(message.content || '')
  const messageId = message.id ?? message.message_id ?? ''

  function startEdit() {
    setDraft(message.content || '')
    setEditing(true)
  }
  function commitEdit() {
    const trimmed = draft.trim()
    if (!trimmed || trimmed === (message.content || '').trim()) {
      setEditing(false)
      return
    }
    onAction?.({ type: 'edit-resend', messageId, newText: trimmed })
    setEditing(false)
  }

  return (
    <article className="message-row user">
      <div className="message-name">Du</div>
      {editing ? (
        <div className="message-bubble" style={{ minWidth: 280 }}>
          <textarea
            autoFocus
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Escape') {
                setEditing(false)
              } else if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                e.preventDefault()
                commitEdit()
              }
            }}
            rows={Math.max(2, Math.min(12, draft.split('\n').length + 1))}
            className="w-full resize-y rounded border border-accent/40 bg-bg0 px-2 py-1.5 font-mono text-[12px] text-fg outline-none"
          />
          <div className="mt-1.5 flex items-center justify-end gap-2 text-[10px]">
            <span className="mr-auto text-fg3">Ctrl+Enter sender · Esc fortryder</span>
            <button
              onClick={() => setEditing(false)}
              className="flex items-center gap-1 rounded border border-line2 bg-bg2 px-2 py-1 text-fg2 hover:text-fg"
            >
              <X size={10} /> Annullér
            </button>
            <button
              onClick={commitEdit}
              disabled={!draft.trim()}
              className="flex items-center gap-1 rounded bg-accent px-2.5 py-1 font-semibold text-bg0 hover:bg-accent/90 disabled:opacity-40"
            >
              <Check size={10} /> Send
            </button>
          </div>
        </div>
      ) : (
        <div className="message-group">
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
          {!message.pending && message.content && onAction && (
            <div className="message-actions">
              <button onClick={startEdit} title="Edit & resend">
                <Pencil size={12} />
              </button>
              <button
                onClick={() => onAction({ type: 'retry', userText: message.content || '' })}
                title="Retry — re-send denne besked"
              >
                <RotateCcw size={12} />
              </button>
              {messageId && (
                <button
                  onClick={() => onAction({ type: 'fork', messageId })}
                  title="Fork — kloner samtalen op til denne besked"
                >
                  <GitBranch size={12} />
                </button>
              )}
            </div>
          )}
        </div>
      )}
      {message.ts && <div className="message-time">{message.ts}</div>}
    </article>
  )
}

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
