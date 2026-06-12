import { useEffect, useRef, useState } from 'react'
import {
  ArrowUp, Square, Plus, Paperclip, ListChecks, Puzzle, ChevronRight,
  ChevronDown, Mic, ShieldCheck, FileText, X,
} from 'lucide-react'
import { useDictation } from '../../hooks/useDictation'
import { uploadAttachment, type ApiConfig } from '../../lib/api'

export interface SentAttachment { id: string; src?: string; name: string; isImage: boolean }

export interface ComposerSendOpts {
  planMode: boolean
  permission: 'ask' | 'trust'
  attachments: SentAttachment[]
}

interface PendingAttachment {
  localId: string
  id?: string
  name: string
  src?: string
  isImage: boolean
  uploading: boolean
  error?: boolean
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
  config,
  getSessionId,
  showPermissions = true,
}: {
  streaming: boolean
  onSend: (text: string, opts: ComposerSendOpts) => void
  onStop: () => void
  model: string
  thinking: string
  config?: ApiConfig
  getSessionId: () => Promise<string>
  /** Permissions-dropdown vises kun hvor værktøjs-godkendelse er relevant
   *  (cowork/code). I ren chat mode er den skjult. Default true. */
  showPermissions?: boolean
}) {
  const [text, setText] = useState('')
  const [menuOpen, setMenuOpen] = useState(false)
  const [permOpen, setPermOpen] = useState(false)
  const [planMode, setPlanMode] = useState(false)
  const [permission, setPermission] = useState<'ask' | 'trust'>('ask')
  const [attachments, setAttachments] = useState<PendingAttachment[]>([])
  const [dragOver, setDragOver] = useState(false)
  const ref = useRef<HTMLTextAreaElement>(null)
  const fileRef = useRef<HTMLInputElement>(null)
  const dictation = useDictation((t) => setText((cur) => (cur ? cur + ' ' : '') + t), config)

  // Upload droppede/valgte filer; vis chip straks (object-URL preview), sæt id når
  // uploadet. session_id resolves ÉN gang pr. drop (lazy-opretter ved ny chat).
  const addFiles = async (files: FileList | File[]) => {
    const list = Array.from(files)
    const entries = list.map((file) => {
      const localId = `${file.name}-${file.size}-${performance.now()}-${Math.round(file.lastModified)}`
      const isImage = file.type.startsWith('image/')
      const src = isImage ? URL.createObjectURL(file) : undefined
      setAttachments((a) => [...a, { localId, name: file.name, src, isImage, uploading: true }])
      return { file, localId }
    })
    const fail = (localId: string) =>
      setAttachments((a) => a.map((x) => (x.localId === localId ? { ...x, uploading: false, error: true } : x)))
    if (!config) { entries.forEach((e) => fail(e.localId)); return }
    let sid: string
    try { sid = await getSessionId() } catch { entries.forEach((e) => fail(e.localId)); return }
    for (const { file, localId } of entries) {
      uploadAttachment(config, file, sid)
        .then((r) => setAttachments((a) => a.map((x) => (x.localId === localId ? { ...x, id: r.id, uploading: false } : x))))
        .catch(() => fail(localId))
    }
  }

  const removeAttachment = (localId: string) => setAttachments((a) => a.filter((x) => x.localId !== localId))

  // Electron fanger fil-drops på window-niveau og navigerer væk medmindre vi
  // preventDefault DER. Håndtér selve droppet globalt (ref → altid nyeste addFiles).
  const addFilesRef = useRef(addFiles)
  addFilesRef.current = addFiles
  useEffect(() => {
    const onDragOver = (e: DragEvent) => {
      e.preventDefault()
      if (e.dataTransfer) e.dataTransfer.dropEffect = 'copy'
      setDragOver(true)
    }
    const onDragLeave = (e: DragEvent) => { if (e.relatedTarget === null) setDragOver(false) }
    const onDrop = (e: DragEvent) => {
      e.preventDefault()
      setDragOver(false)
      if (e.dataTransfer?.files?.length) addFilesRef.current(e.dataTransfer.files)
    }
    window.addEventListener('dragover', onDragOver)
    window.addEventListener('dragleave', onDragLeave)
    window.addEventListener('drop', onDrop)
    return () => {
      window.removeEventListener('dragover', onDragOver)
      window.removeEventListener('dragleave', onDragLeave)
      window.removeEventListener('drop', onDrop)
    }
  }, [])

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
    const ready = attachments.filter((a) => a.id && !a.error)
    if (!t && ready.length === 0) return
    onSend(t, {
      planMode,
      permission,
      attachments: ready.map((a) => ({ id: a.id as string, src: a.src, name: a.name, isImage: a.isImage })),
    })
    setText('')
    setAttachments([])
  }

  const stop = (e: React.MouseEvent) => e.stopPropagation()
  const permLabel = PERMISSIONS.find((p) => p.key === permission)?.label ?? 'Spørg'

  return (
    <div className={`composer ${dragOver ? 'drag-over' : ''}`}>
      {dragOver && <div className="composer-drop-overlay">Slip filer og billeder her</div>}
      {attachments.length > 0 && (
        <div className="composer-attachments">
          {attachments.map((a) => (
            <div key={a.localId} className={`attach-chip ${a.error ? 'error' : ''}`}>
              {a.isImage && a.src
                ? <img src={a.src} alt={a.name} className="attach-thumb" />
                : <FileText size={14} />}
              <span className="attach-name">{a.error ? 'Fejlede' : a.uploading ? 'Uploader…' : a.name}</span>
              <button type="button" className="attach-remove" aria-label="Fjern" onClick={() => removeAttachment(a.localId)}>
                <X size={12} />
              </button>
            </div>
          ))}
        </div>
      )}
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

          {/* permissions dropdown — kun i cowork/code, ikke ren chat */}
          {showPermissions && (
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
          )}

          <input
            ref={fileRef}
            type="file"
            multiple
            accept="image/*,.txt,.md,.pdf,.json,.py,.ts,.tsx"
            style={{ display: 'none' }}
            onChange={(e) => { if (e.target.files?.length) addFiles(e.target.files); e.target.value = '' }}
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
              className={`composer-icon-btn ${dictation.listening ? 'listening' : ''} ${dictation.transcribing ? 'transcribing' : ''}`}
              aria-label={dictation.transcribing ? 'Transskriberer…' : dictation.listening ? 'Stop optagelse' : 'Dikter'}
              title={dictation.transcribing ? 'Transskriberer…' : dictation.listening ? 'Stop optagelse' : 'Dikter'}
              disabled={dictation.transcribing}
              onClick={() => (dictation.listening ? dictation.stop() : void dictation.start())}
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
