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
  const innerRef = useRef<HTMLElement>(null)
  // wasNearBottom is the user-intent signal: are they parked at the
  // bottom (= want auto-follow) or scrolled up reading (= leave them
  // alone). Initialized true so first paint of a fresh session lands
  // at the bottom.
  const wasNearBottomRef = useRef(true)
  const prevCountRef = useRef(messages.length)
  const isFirstPaintRef = useRef(true)

  // Track scroll position so we know whether to auto-follow.
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

  // ResizeObserver on the inner section catches every height change
  // — markdown reflow, streaming tokens, image loads, syntax-highlight
  // settling, ANYTHING. This is what makes auto-scroll bulletproof:
  // it doesn't matter whether React.memo blocked a render or whether
  // the message array reference changed — if the rendered DOM grew,
  // we react. Same trick most chat apps end up with after the
  // dependency-array approach fails them.
  useEffect(() => {
    const container = containerRef.current
    const inner = innerRef.current
    if (!container || !inner) return
    const observer = new ResizeObserver(() => {
      if (wasNearBottomRef.current || isFirstPaintRef.current) {
        // Defer to next frame so layout has fully settled
        requestAnimationFrame(() => {
          if (container) {
            container.scrollTop = container.scrollHeight
            isFirstPaintRef.current = false
          }
        })
      }
    })
    observer.observe(inner)
    return () => observer.disconnect()
  }, [])

  // New-message arrival (count went up) is a hard signal: always
  // scroll, even if the user was scrolled up. The reasoning: a new
  // message you sent should bring you back to the bottom; an
  // assistant message arriving means the conversation moved on.
  // (Streaming token growth is handled by ResizeObserver above with
  // user-intent gating.)
  useEffect(() => {
    if (messages.length > prevCountRef.current) {
      wasNearBottomRef.current = true  // override stale "scrolled up"
      const node = containerRef.current
      if (node) {
        requestAnimationFrame(() => {
          if (node) node.scrollTop = node.scrollHeight
        })
      }
    }
    prevCountRef.current = messages.length
  }, [messages.length])

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
        ref={innerRef}
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
              title={
                'Replay prompt — sender den foregående user-besked igen.\n' +
                'Original besked og dette svar bevares uændret i historien.\n' +
                'Note: runtime-state kan have ændret sig siden — du får ikke ' +
                'nødvendigvis præcis samme svar.'
              }
            >
              <RotateCcw size={12} />
            </button>
          )}
          {onAction && messageId && (
            <button
              onClick={() => onAction({ type: 'fork', messageId })}
              title={
                'Fork — opretter ny session med kopi af samtalehistorik op til ' +
                'og med denne besked. Tool-results referencer overlever; staged ' +
                'edits, pending plans, terminal-processes og file-preview state ' +
                'følger IKKE med — det bliver en ren samtalegren.'
              }
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
              <button
                onClick={startEdit}
                title={
                  'Edit & resend — sender en redigeret version som NY besked.\n' +
                  'Den originale besked bliver stående i historikken (audit-' +
                  'sporet er intakt). Hvis du vil have samtalen til at føle sig ' +
                  'rettet, brug Fork i stedet.'
                }
              >
                <Pencil size={12} />
              </button>
              <button
                onClick={() => onAction({ type: 'retry', userText: message.content || '' })}
                title={
                  'Replay prompt — sender denne tekst igen som ny besked.\n' +
                  'Original og evt. svar bevares.'
                }
              >
                <RotateCcw size={12} />
              </button>
              {messageId && (
                <button
                  onClick={() => onAction({ type: 'fork', messageId })}
                  title={
                    'Fork — ny session med samtalehistorik op til og med denne ' +
                    'besked. Ren gren — ingen aktive processes/plans/edits ' +
                    'følger med.'
                  }
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
