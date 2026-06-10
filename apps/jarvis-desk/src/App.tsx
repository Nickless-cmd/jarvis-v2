import { useCallback, useEffect, useRef, useState } from 'react'
import {
  ArrowUp,
  Copy,
  Edit2,
  Plus,
  RotateCw,
  Settings,
  Volume2,
} from 'lucide-react'
import {
  type ChatMessage,
  type ChatSession,
  createSession,
  getSession,
  listSessions,
} from './lib/api'
import { startStream, StreamError, type StreamEvent } from './lib/streamClient'
import './styles/tokens.css'
import './styles/app.css'

declare global {
  interface Window {
    jarvisDesk?: {
      config: {
        get: () => Promise<{ apiBaseUrl: string; authToken: string | null }>
        set: (cfg: { apiBaseUrl: string; authToken: string | null }) => Promise<boolean>
      }
      platform: NodeJS.Platform
    }
  }
}

type Mode = 'chat' | 'cowork' | 'code'

interface Settings {
  apiBaseUrl: string
  authToken: string | null
}

interface StreamState {
  /** Aggregeret tekst-output fra Jarvis under streaming */
  jarvisText: string
  /** Aggregeret thinking — vises kun hvis bruger har det enabled */
  thinkingText: string
  /** Tool-calls observeret under stream */
  toolUses: Array<{ index: number; name: string; input: string }>
  /** Reconnect-meddelelse hvis vi pt prøver at genoprette */
  reconnectMsg: string | null
  /** Endelig fejl */
  error: StreamError | null
  /** True når streamen er aktiv */
  isStreaming: boolean
}

const INITIAL_STREAM: StreamState = {
  jarvisText: '',
  thinkingText: '',
  toolUses: [],
  reconnectMsg: null,
  error: null,
  isStreaming: false,
}

export function App() {
  const [settings, setSettings] = useState<Settings | null>(null)
  const [mode, setMode] = useState<Mode>('chat')
  const [sessions, setSessions] = useState<ChatSession[]>([])
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [composerText, setComposerText] = useState('')
  const [stream, setStream] = useState<StreamState>(INITIAL_STREAM)
  const [loadError, setLoadError] = useState<string | null>(null)

  const abortStreamRef = useRef<(() => void) | null>(null)
  const transcriptRef = useRef<HTMLDivElement>(null)
  const composerInputRef = useRef<HTMLTextAreaElement>(null)

  // ─── Initial load: indstillinger + sessioner ──────────────────────
  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        // I dev-mode (browser uden Electron) bruger vi defaults.
        const cfg = window.jarvisDesk
          ? await window.jarvisDesk.config.get()
          : { apiBaseUrl: 'http://10.0.0.39', authToken: null }
        if (cancelled) return
        setSettings(cfg)
      } catch (e) {
        if (cancelled) return
        setLoadError(
          `Kunne ikke læse indstillinger: ${(e as Error).message}`,
        )
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  // ─── Load sessioner når settings er klar ──────────────────────────
  useEffect(() => {
    if (!settings) return
    let cancelled = false
    ;(async () => {
      try {
        const list = await listSessions(settings)
        if (cancelled) return
        setSessions(list)
        if (list.length > 0 && !activeSessionId && list[0]) {
          setActiveSessionId(list[0].id)
        }
      } catch (e) {
        if (cancelled) return
        const msg =
          e instanceof StreamError
            ? e.userMessage()
            : `Kunne ikke hente samtaler: ${(e as Error).message}`
        setLoadError(msg)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [settings, activeSessionId])

  // ─── Load aktive session's messages ───────────────────────────────
  useEffect(() => {
    if (!settings || !activeSessionId) return
    let cancelled = false
    ;(async () => {
      try {
        const { messages: msgs } = await getSession(settings, activeSessionId)
        if (cancelled) return
        // Filtrér tool-rows fra — de rendres inline i assistant-bobler.
        setMessages(msgs.filter((m) => m.role !== 'tool' && m.role !== 'system'))
      } catch (e) {
        if (cancelled) return
        const msg =
          e instanceof StreamError
            ? e.userMessage()
            : `Kunne ikke hente samtalen: ${(e as Error).message}`
        setLoadError(msg)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [settings, activeSessionId])

  // ─── Auto-scroll transcript når der streames ──────────────────────
  useEffect(() => {
    const el = transcriptRef.current
    if (!el) return
    // Kun auto-scroll hvis brugeren er tæt på bunden.
    const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 200
    if (nearBottom) el.scrollTop = el.scrollHeight
  }, [messages, stream])

  // ─── Send besked ──────────────────────────────────────────────────
  const handleSend = useCallback(() => {
    if (!settings || !activeSessionId) return
    const text = composerText.trim()
    if (!text) return
    if (stream.isStreaming) return

    // Optimistisk: tilføj user-besked + placeholder
    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: text,
      created_at: new Date().toISOString(),
    }
    setMessages((prev) => [...prev, userMsg])
    setComposerText('')
    setStream({ ...INITIAL_STREAM, isStreaming: true })

    const abort = startStream(
      {
        apiBaseUrl: settings.apiBaseUrl,
        authToken: settings.authToken,
        sessionId: activeSessionId,
        message: text,
        approvalMode: 'ask',
        thinkingMode: 'think',
      },
      {
        onEvent: (event: StreamEvent) => {
          setStream((s) => applyEvent(s, event))
        },
        onReconnect: (attempt, delayMs) => {
          setStream((s) => ({
            ...s,
            reconnectMsg: `Forbindelse afbrudt. Genopretter (forsøg ${attempt}, om ${Math.round(delayMs / 1000)}s)…`,
          }))
        },
        onError: (err) => {
          setStream((s) => ({
            ...s,
            error: err,
            isStreaming: false,
            reconnectMsg: null,
          }))
        },
        onComplete: () => {
          // Persistér final text som ny assistant-besked.
          setStream((s) => {
            if (s.jarvisText) {
              const jarvisMsg: ChatMessage = {
                id: `assistant-${Date.now()}`,
                role: 'assistant',
                content: s.jarvisText,
                created_at: new Date().toISOString(),
              }
              setMessages((prev) => [...prev, jarvisMsg])
            }
            return { ...INITIAL_STREAM }
          })
        },
      },
    )
    abortStreamRef.current = abort
  }, [settings, activeSessionId, composerText, stream.isStreaming])

  // Cleanup: abort eventuel aktiv stream ved unmount/session-skift
  useEffect(() => {
    return () => {
      abortStreamRef.current?.()
      abortStreamRef.current = null
    }
  }, [activeSessionId])

  const handleNewSession = useCallback(async () => {
    if (!settings) return
    try {
      const sess = await createSession(settings, 'Ny samtale')
      setSessions((prev) => [sess, ...prev])
      setActiveSessionId(sess.id)
      setMessages([])
    } catch (e) {
      const msg =
        e instanceof StreamError
          ? e.userMessage()
          : `Kunne ikke oprette samtale: ${(e as Error).message}`
      setLoadError(msg)
    }
  }, [settings])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        handleSend()
      }
    },
    [handleSend],
  )

  // ─── Render ───────────────────────────────────────────────────────
  const activeSession = sessions.find((s) => s.id === activeSessionId)

  return (
    <div className="window">

      {/* ─── Sidebar ─── */}
      <aside className="sidebar">

        <div className="sidebar-head">
          <span className="dot" /> jarvis-desk
        </div>

        <div className="mode-slider">
          {(['chat', 'cowork', 'code'] as const).map((m) => (
            <button
              key={m}
              className={`mode-seg ${mode === m ? 'active' : ''}`}
              onClick={() => setMode(m)}
              type="button"
            >
              {m === 'chat' ? 'Chat' : m === 'cowork' ? 'Cowork' : 'Code'}
            </button>
          ))}
        </div>

        <div className="sessions">
          <button className="new-chat" onClick={handleNewSession} type="button">
            <Plus size={14} /> Ny samtale
          </button>

          {sessions.length > 0 && (
            <>
              <div className="sidebar-label">samtaler</div>
              {sessions.map((s) => (
                <button
                  key={s.id}
                  className={`session-item ${s.id === activeSessionId ? 'active' : ''}`}
                  onClick={() => setActiveSessionId(s.id)}
                  type="button"
                >
                  {s.title || 'Uden titel'}
                  <span className="session-time">{formatTime(s.updated_at)}</span>
                </button>
              ))}
            </>
          )}
        </div>

        <div className="sidebar-foot">
          <div className="who">
            <span className="avatar">B</span>
            <span>Bjørn</span>
          </div>
          <button className="icon-btn" title="Indstillinger" type="button">
            <Settings size={14} />
          </button>
        </div>

      </aside>

      {/* ─── Main ─── */}
      <main className="main">

        <div className="main-head">
          {activeSession?.title || (mode === 'chat' ? 'Chat' : mode === 'cowork' ? 'Cowork' : 'Code')}
        </div>

        {loadError && (
          <div className="error-banner">
            <span>{loadError}</span>
            <button className="dismiss" onClick={() => setLoadError(null)}>×</button>
          </div>
        )}

        {stream.reconnectMsg && (
          <div className="reconnect-banner">{stream.reconnectMsg}</div>
        )}
        {stream.error && (
          <div className="error-banner">
            <span>{stream.error.userMessage()}</span>
            <button
              className="dismiss"
              onClick={() =>
                setStream((s) => ({ ...s, error: null }))
              }
            >
              ×
            </button>
          </div>
        )}

        <div className="transcript" ref={transcriptRef}>
          <div className="messages">
            {messages.length === 0 && !stream.isStreaming && (
              <div className="empty-state">
                <div>
                  <h2>Hej.</h2>
                  <div>Skriv hvad du arbejder på.</div>
                </div>
              </div>
            )}

            {messages.map((m) => (
              <MessageRow key={m.id} message={m} />
            ))}

            {stream.isStreaming && (
              <StreamingJarvis stream={stream} />
            )}
          </div>
        </div>

        <div className="composer-wrap">
          <div className="composer">
            <textarea
              ref={composerInputRef}
              className="composer-input"
              rows={2}
              placeholder={
                stream.isStreaming
                  ? 'Jarvis svarer…'
                  : 'Skriv en besked til Jarvis...'
              }
              value={composerText}
              onChange={(e) => setComposerText(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={stream.isStreaming}
            />
            <div className="composer-bar">
              <div className="composer-left">
                <button className="add-context" type="button">
                  <Plus size={13} /> Tilføj kontekst
                </button>
              </div>
              <div className="composer-right">
                <button className="model-pill" type="button">
                  <span className="dot" />
                  <span>deepseek-flash</span>
                  <span className="caret">▾</span>
                </button>
                <button className="model-pill" type="button">
                  <span>think</span>
                  <span className="caret">▾</span>
                </button>
                <button
                  className="composer-send"
                  onClick={handleSend}
                  disabled={!composerText.trim() || stream.isStreaming}
                  type="button"
                  title="Send (⏎)"
                >
                  <ArrowUp size={14} strokeWidth={2.5} />
                </button>
              </div>
            </div>
          </div>
        </div>

        <footer className="statusbar">
          <div className="left">
            <span><span className="dot" />primary · deepseek-v4-flash</span>
            <span>session: {activeSessionId?.slice(0, 12) || '–'}</span>
          </div>
          <div>{settings?.apiBaseUrl || '–'}</div>
        </footer>

      </main>
    </div>
  )
}

// ─── Apply v2 stream event til state ─────────────────────────────────
function applyEvent(state: StreamState, event: StreamEvent): StreamState {
  switch (event.type) {
    case 'message_start':
      return { ...state, isStreaming: true }
    case 'content_block_delta': {
      const d = event.delta
      if (d.type === 'text_delta') {
        return { ...state, jarvisText: state.jarvisText + d.text }
      }
      if (d.type === 'thinking_delta') {
        return { ...state, thinkingText: state.thinkingText + d.thinking }
      }
      return state
    }
    case 'content_block_start': {
      if (event.content_block.type === 'tool_use') {
        return {
          ...state,
          toolUses: [
            ...state.toolUses,
            { index: event.index, name: event.content_block.name, input: '' },
          ],
        }
      }
      return state
    }
    case 'message_stop':
      return { ...state, isStreaming: false, reconnectMsg: null }
    case 'system_event':
      // Vi gemmer disse til ledger senere — for nu ignorerer vi i UI.
      return state
    case 'ping':
      return { ...state, reconnectMsg: null }
    default:
      return state
  }
}

// ─── Message rendering ────────────────────────────────────────────────
function MessageRow({ message }: { message: ChatMessage }) {
  if (message.role === 'user') {
    return (
      <div className="msg-user-wrap">
        <div className="bubble">{message.content}</div>
        <div className="msg-actions">
          <span className="msg-time">{formatRelative(message.created_at)}</span>
          <button className="msg-action-btn" title="Kopiér" type="button">
            <Copy size={12} />
          </button>
          <button className="msg-action-btn" title="Rediger" type="button">
            <Edit2 size={12} />
          </button>
          <button className="msg-action-btn" title="Send igen" type="button">
            <RotateCw size={12} />
          </button>
        </div>
      </div>
    )
  }

  // Assistant message
  return (
    <div className="msg-jarvis-wrap">
      <article className="msg-jarvis">
        <div className="avatar-jarvis">J</div>
        <div>
          <div className="jarvis-name">Jarvis</div>
          <div className="jarvis-body">
            {message.content.split('\n\n').map((para, i) => (
              <p key={i}>{para}</p>
            ))}
          </div>
        </div>
      </article>
      <div className="msg-actions">
        <span className="msg-time">{formatRelative(message.created_at)}</span>
        <button className="msg-action-btn" title="Kopiér" type="button">
          <Copy size={12} />
        </button>
        <button className="msg-action-btn" title="Læs op" type="button">
          <Volume2 size={12} />
        </button>
        <button className="msg-action-btn" title="Send igen" type="button">
          <RotateCw size={12} />
        </button>
      </div>
    </div>
  )
}

function StreamingJarvis({ stream }: { stream: StreamState }) {
  return (
    <div className="msg-jarvis-wrap">
      <article className="msg-jarvis">
        <div className="avatar-jarvis">J</div>
        <div>
          <div className="jarvis-name">Jarvis</div>
          <div className="jarvis-body">
            {stream.jarvisText
              ? stream.jarvisText.split('\n\n').map((para, i) => (
                  <p key={i}>{para}</p>
                ))
              : (
                <p style={{ color: 'var(--fg-3)' }}>
                  {stream.toolUses.length > 0
                    ? `Kører ${stream.toolUses[stream.toolUses.length - 1]?.name}...`
                    : 'tænker…'}
                </p>
              )}
          </div>
        </div>
      </article>
    </div>
  )
}

// ─── Helpers ──────────────────────────────────────────────────────────
function formatTime(iso: string): string {
  try {
    const date = new Date(iso)
    const now = new Date()
    const sameDay = date.toDateString() === now.toDateString()
    if (sameDay) {
      return date.toLocaleTimeString('da-DK', {
        hour: '2-digit',
        minute: '2-digit',
      })
    }
    return date.toLocaleDateString('da-DK', { day: 'numeric', month: 'short' })
  } catch {
    return ''
  }
}

function formatRelative(iso: string): string {
  try {
    const date = new Date(iso)
    const diffMs = Date.now() - date.getTime()
    const min = Math.round(diffMs / 60_000)
    if (min < 1) return 'lige nu'
    if (min < 60) return `${min} min siden`
    const hr = Math.round(min / 60)
    if (hr < 24) return `${hr} t siden`
    return formatTime(iso)
  } catch {
    return ''
  }
}
