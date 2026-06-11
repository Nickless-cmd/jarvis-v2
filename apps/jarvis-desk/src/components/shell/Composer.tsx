import { useEffect, useRef, useState } from 'react'
import {
  ArrowUp, Square, Plus, Paperclip, ListChecks, Puzzle, ChevronRight,
  ChevronDown, Mic, ShieldCheck,
} from 'lucide-react'
import { useDictation } from '../../hooks/useDictation'

export interface ComposerSendOpts {
  planMode: boolean
  permission: 'ask' | 'trust'
}

const PERMISSIONS: Array<{ key: 'ask' | 'trust'; label: string }> = [
  { key: 'ask', label: 'Spørg ved værktøjer' },
  { key: 'trust', label: 'Fuld adgang' },
]

/** Composer (Codex-stil): venstre [+] + permissions-dropdown; højre model-pill,
 *  think-pill, dikter-mic, send. [+]-menu folder opad med billeder/filer,
 *  planlægnings-toggle og plugins. Enter sender, Shift+Enter ny linje. */
export function Composer({
  streaming,
  onSend,
  onStop,
  model,
  thinking,
}: {
  streaming: boolean
  onSend: (text: string, opts: ComposerSendOpts) => void
  onStop: () => void
  model: string
  thinking: string
}) {
  const [text, setText] = useState('')
  const [menuOpen, setMenuOpen] = useState(false)
  const [permOpen, setPermOpen] = useState(false)
  const [planMode, setPlanMode] = useState(false)
  const [permission, setPermission] = useState<'ask' | 'trust'>('ask')
  const ref = useRef<HTMLTextAreaElement>(null)
  const fileRef = useRef<HTMLInputElement>(null)
  const dictation = useDictation((t) => setText((cur) => (cur ? cur + ' ' : '') + t))

  // Luk popovers ved klik udenfor.
  useEffect(() => {
    if (!menuOpen && !permOpen) return
    const close = () => { setMenuOpen(false); setPermOpen(false) }
    window.addEventListener('click', close)
    return () => window.removeEventListener('click', close)
  }, [menuOpen, permOpen])

  // Enter sender altid (også under streaming — ChatView lægger den i kø).
  const send = () => {
    const t = text.trim()
    if (!t) return
    onSend(t, { planMode, permission })
    setText('')
  }

  const stop = (e: React.MouseEvent) => e.stopPropagation()
  const permLabel = PERMISSIONS.find((p) => p.key === permission)?.label ?? 'Spørg'

  return (
    <div className="composer">
      <textarea
        ref={ref}
        className="composer-input"
        rows={2}
        value={text}
        placeholder={streaming ? 'Skriv en follow-up (sendes når Jarvis er færdig)…' : 'Skriv en besked til Jarvis...'}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() }
        }}
      />
      <div className="composer-bar">
        <div className="composer-left">
          {/* + knap med opad-menu */}
          <div className="composer-popover-anchor" onClick={stop}>
            <button
              type="button"
              className="composer-icon-btn"
              aria-label="Tilføj"
              onClick={() => { setMenuOpen((o) => !o); setPermOpen(false) }}
            >
              <Plus size={16} />
            </button>
            {menuOpen && (
              <div className="composer-menu">
                <button type="button" onClick={() => { fileRef.current?.click(); setMenuOpen(false) }}>
                  <Paperclip size={14} /> Tilføj billeder og filer
                </button>
                <button type="button" className="menu-toggle-row" onClick={() => setPlanMode((p) => !p)}>
                  <ListChecks size={14} /> Planlægningstilstand
                  <span className={`toggle ${planMode ? 'on' : ''}`}><span className="knob" /></span>
                </button>
                <button type="button" onClick={() => setMenuOpen(false)}>
                  <Puzzle size={14} /> Plugins <ChevronRight size={14} className="menu-chevron" />
                </button>
              </div>
            )}
          </div>

          {/* permissions dropdown */}
          <div className="composer-popover-anchor" onClick={stop}>
            <button
              type="button"
              className={`composer-perm ${permission === 'trust' ? 'trust' : 'ask'}`}
              onClick={() => { setPermOpen((o) => !o); setMenuOpen(false) }}
            >
              <ShieldCheck size={13} /> {permLabel} <ChevronDown size={12} />
            </button>
            {permOpen && (
              <div className="composer-menu perm-menu">
                {PERMISSIONS.map((p) => (
                  <button
                    key={p.key}
                    type="button"
                    className={permission === p.key ? 'active' : ''}
                    onClick={() => { setPermission(p.key); setPermOpen(false) }}
                  >
                    {p.label}
                  </button>
                ))}
              </div>
            )}
          </div>

          <input
            ref={fileRef}
            type="file"
            multiple
            accept="image/*,.txt,.md,.pdf,.json,.py,.ts,.tsx"
            style={{ display: 'none' }}
            onChange={() => { /* attachment-upload: Chat-spec */ }}
          />
        </div>

        <div className="composer-right">
          <button type="button" className="model-pill">
            <span className="dot" />{model}<span className="caret">▾</span>
          </button>
          <button type="button" className="model-pill">
            {thinking}<span className="caret">▾</span>
          </button>
          {dictation.supported && (
            <button
              type="button"
              className={`composer-icon-btn ${dictation.listening ? 'listening' : ''}`}
              aria-label="Dikter"
              onClick={() => (dictation.listening ? dictation.stop() : dictation.start())}
            >
              <Mic size={16} />
            </button>
          )}
          {streaming ? (
            <button
              type="button"
              className="composer-send composer-stop"
              onClick={onStop}
              aria-label="Stop"
              title="Stop Jarvis"
            >
              <Square size={12} strokeWidth={2.5} />
            </button>
          ) : (
            <button
              type="button"
              className="composer-send"
              disabled={!text.trim()}
              onClick={send}
              aria-label="Send"
            >
              <ArrowUp size={14} strokeWidth={2.5} />
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
