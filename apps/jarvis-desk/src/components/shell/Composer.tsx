import { memo, useCallback, useEffect, useRef, useState } from 'react'
import {
  ArrowUp, Square, Plus, Paperclip, ListChecks, Puzzle, ChevronRight,
  ChevronDown, Mic, ShieldCheck, FileText, X, Loader2,
} from 'lucide-react'
import { emojify } from '../../lib/emojify'
import { useDictation } from '../../hooks/useDictation'
import { ContextRing } from './ContextRing'
import { uploadAttachment, type ApiConfig } from '../../lib/api'
import { PROV_KEY, MODEL_KEY } from '../../lib/composerPrefs'
import { usePermission } from '../../hooks/usePermission'

export interface SentAttachment { id: string; src?: string; name: string; isImage: boolean }

export interface ComposerSendOpts {
  planMode: boolean
  permission: 'ask' | 'trust'
  attachments: SentAttachment[]
  /** Rolle-bevidst routing: konkret model-id + provider-valg (owner-only). */
  model: string
  providerChoice: string
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
// Permission-valget overlever genstart via PermissionContext (Bjørn: "fuld
// adgang" skal huskes). Provider/model-nøgler kommer fra composerPrefs.

/** Memo'd input — isoleret fra forælderens re-renders. ChatView re-renderer på
 *  HVERT stream-token (contextTokens/blocks/elapsed), hvilket før nulstillede
 *  cursoren i en controlled <textarea> midt i indtastning ("som om to skriver",
 *  Bjørn 2026-06-13). memo + stabile (useCallback) handlers gør at stream-tickets
 *  IKKE re-renderer inputtet når teksten er uændret → cursoren bliver stående. */
const ComposerTextArea = memo(function ComposerTextArea({
  value, placeholder, onChange, onKeyDown, inputRef,
}: {
  value: string
  placeholder: string
  onChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => void
  onKeyDown: (e: React.KeyboardEvent<HTMLTextAreaElement>) => void
  inputRef: React.RefObject<HTMLTextAreaElement | null>
}) {
  return (
    <textarea
      ref={inputRef}
      className="composer-input"
      rows={2}
      value={value}
      placeholder={placeholder}
      onChange={onChange}
      onKeyDown={onKeyDown}
    />
  )
})

/** Composer (Codex-stil): venstre [+] + permissions-dropdown; højre model-pill,
 *  think-pill, dikter-mic, send. [+]-menu folder opad med billeder/filer,
 *  planlægnings-toggle og plugins. Enter sender, Shift+Enter ny linje. */
export function Composer({
  streaming,
  onSend,
  onStop,
  thinking,
  config,
  getSessionId,
  showPermissions = true,
  contextTokens = 0,
  compactAt = 0,
  compacting = false,
  isOwner = false,
  onOpenPrivacy,
}: {
  streaming: boolean
  onSend: (text: string, opts: ComposerSendOpts) => void
  onStop: () => void
  model: string
  thinking: string
  config?: ApiConfig
  getSessionId: () => Promise<string>
  /** Åbner Data & privatliv (Settings) fra disclaimer-linjen. */
  onOpenPrivacy?: () => void
  /** Permissions-dropdown vises kun hvor værktøjs-godkendelse er relevant
   *  (cowork/code). I ren chat mode er den skjult. Default true. */
  showPermissions?: boolean
  /** Context-ring (#9): tokens i konteksten + autocompact-tærskel. Ringen vises
   *  altid når compactAt > 0 (tom ved 0 tokens). */
  contextTokens?: number
  compactAt?: number
  /** Compaction kører lige nu → composeren pauses (som i Claude Code) indtil den er færdig. */
  compacting?: boolean
  /** Owner ser provider-vælger + dynamisk model-liste; member ser kun Standard/Pro. */
  isOwner?: boolean
}) {
  const [text, setText] = useState('')
  const [menuOpen, setMenuOpen] = useState(false)
  const [permOpen, setPermOpen] = useState(false)
  const [planMode, setPlanMode] = useState(false)
  const { permission, setPermission } = usePermission()
  const [attachments, setAttachments] = useState<PendingAttachment[]>([])
  const [dragOver, setDragOver] = useState(false)
  // Rolle-bevidst model/provider-valg. Owner: provChoice + konkret model.
  // Member: kun tier ('standard'|'pro') → backend mapper til ollama flash/pro.
  const [provChoice, setProvChoice] = useState<string>(() => {
    try { return localStorage.getItem(PROV_KEY) || 'deepseek' } catch { return 'deepseek' }
  })
  const [selModel, setSelModel] = useState(() => {  // konkret model-id (owner) / tier (member)
    try { return localStorage.getItem(MODEL_KEY) || '' } catch { return '' }
  })
  // Alle visible-klare providers + modeller (owner). Hentes fra /chat/visible-providers.
  const [providers, setProviders] = useState<Array<{ id: string; models: string[] }>>([])
  const [modelOpen, setModelOpen] = useState(false)
  const [provOpen, setProvOpen] = useState(false)
  const ref = useRef<HTMLTextAreaElement>(null)
  const fileRef = useRef<HTMLInputElement>(null)
  const dictation = useDictation((t) => setText((cur) => (cur ? cur + ' ' : '') + t), config)

  // Owner → hent hele paletten af visible-klare providers (engangs).
  useEffect(() => {
    if (!isOwner || !config || providers.length) return
    let alive = true
    import('../../lib/api').then(({ getVisibleProviders }) =>
      getVisibleProviders(config).then((p) => { if (alive) setProviders(p) }),
    )
    return () => { alive = false }
  }, [isOwner, config, providers.length])

  // Persistér provider + model så man ikke ryger tilbage til Deepseek-default.
  // (permission persisteres nu i PermissionContext.)
  useEffect(() => {
    try { localStorage.setItem(PROV_KEY, provChoice) } catch { /* ignore */ }
  }, [provChoice])
  useEffect(() => {
    try { localStorage.setItem(MODEL_KEY, selModel) } catch { /* ignore */ }
  }, [selModel])

  // Ægte context-ring: hent det effektive vindue for den VALGTE provider/model,
  // så ringens nævner er modellens reelle loft (deepseek 1M ≠ et 64k-model).
  // Falder tilbage til den globale autocompat-tærskel (compactAt) ved 0/ukendt.
  const [effectiveCtx, setEffectiveCtx] = useState(0)
  // Afhæng af de PRIMITIVE værdier — ikke `config`-objektets identitet. ChatView
  // (m.fl.) genskaber `{apiBaseUrl, authToken}` som et NYT objekt på hver render;
  // under polling (~2×/sek) gav det en uendelig model-context-refetch-loop der
  // sultede stream-SSE'en på single-worker-API'et → "spinner drejer, stopper,
  // intet svar" (Bjørn 2026-06-16). Primitive deps → kun ægte ændringer refetcher.
  const _apiBaseUrl = config?.apiBaseUrl
  const _authToken = config?.authToken
  useEffect(() => {
    if (!_apiBaseUrl) return
    let alive = true
    const cfg = { apiBaseUrl: _apiBaseUrl, authToken: _authToken ?? null }
    import('../../lib/api').then(({ getModelContext }) =>
      getModelContext(cfg, provChoice, selModel)
        .then((r) => { if (alive) setEffectiveCtx(r.effective || 0) })
        .catch(() => { if (alive) setEffectiveCtx(0) }),
    )
    return () => { alive = false }
  }, [_apiBaseUrl, _authToken, provChoice, selModel])
  const ringDenominator = effectiveCtx || compactAt

  // Member: standard/pro. Owner: konkret model afhænger af valgt provider.
  const memberTier: 'standard' | 'pro' = selModel === 'pro' ? 'pro' : 'standard'
  // Pæne provider-labels; ukendte vises bare med deres id.
  const PROVIDER_LABELS: Record<string, string> = {
    deepseek: 'Deepseek', ollama: 'Ollama', 'github-copilot': 'Copilot', groq: 'Groq',
    mistral: 'Mistral', sambanova: 'SambaNova', 'nvidia-nim': 'NVIDIA',
    openrouter: 'OpenRouter', opencode: 'OpenCode', 'openai-codex': 'Codex',
  }
  const provLabel = (id: string) => PROVIDER_LABELS[id] || id
  // Owner-provider-liste: fetchede providers, eller deepseek/ollama indtil de loader.
  const ownerProviders: string[] = providers.length
    ? providers.map((p) => p.id)
    : ['deepseek', 'ollama']
  const _selProv = providers.find((p) => p.id === provChoice)
  const _deepseekFallback = [
    { id: 'deepseek-v4-flash', label: 'Standard' },
    { id: 'deepseek-v4-pro', label: 'Pro' },
  ]
  const ownerModelOptions: Array<{ id: string; label: string }> = _selProv
    ? _selProv.models.map((m) => ({ id: m, label: m.replace(':cloud', '') }))
    : (provChoice === 'deepseek' ? _deepseekFallback : [])
  const currentModelLabel = isOwner
    ? (ownerModelOptions.find((o) => o.id === selModel)?.label || 'Vælg model')
    : (memberTier === 'pro' ? 'Pro' : 'Standard')

  // Auto-resize: composer vokser med teksten (op til CSS max-height, derefter
  // scroller den indvendigt) i stedet for at være en fast 2-rækkers boks.
  useEffect(() => {
    const el = ref.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${el.scrollHeight}px`
  }, [text])

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
    if (!menuOpen && !permOpen && !modelOpen && !provOpen) return
    const close = () => { setMenuOpen(false); setPermOpen(false); setModelOpen(false); setProvOpen(false) }
    window.addEventListener('click', close)
    return () => window.removeEventListener('click', close)
  }, [menuOpen, permOpen, modelOpen, provOpen])

  // Enter sender altid (også under streaming — ChatView lægger den i kø).
  // useCallback så identiteten er stabil mellem stream-tickets (deps ændrer sig
  // kun ved faktisk input/valg) → den memo'd textarea re-renderer ikke unødigt.
  const doSend = useCallback(() => {
    const t = emojify(text.trim())  // :) ;) :P → 🙂 😉 😛 (vises som emoji i boblen)
    const ready = attachments.filter((a) => a.id && !a.error)
    if (!t && ready.length === 0) return
    // Rolle-bevidst routing: owner sender provider + konkret model; member sender
    // kun tier (backend tvinger ollama + flash/pro). Tom = backend-default.
    const sendModel = isOwner ? selModel : memberTier
    const sendProvider = isOwner ? provChoice : ''
    onSend(t, {
      planMode,
      permission,
      attachments: ready.map((a) => ({ id: a.id as string, src: a.src, name: a.name, isImage: a.isImage })),
      model: sendModel,
      providerChoice: sendProvider,
    })
    setText('')
    setAttachments([])
  }, [text, attachments, isOwner, selModel, memberTier, provChoice, planMode, permission, onSend])

  // Pause under compaction (som Claude Code): mens sessionen komprimeres holdes en send i kø
  // og afsendes AUTOMATISK når compaction er overstået. Teksten bevares imens.
  const [queuedDuringCompact, setQueuedDuringCompact] = useState(false)
  const send = useCallback(() => {
    if (compacting) {
      if (text.trim() || attachments.some((a) => a.id && !a.error)) setQueuedDuringCompact(true)
      return
    }
    doSend()
  }, [compacting, doSend, text, attachments])
  useEffect(() => {
    if (!compacting && queuedDuringCompact) {
      setQueuedDuringCompact(false)
      doSend()
    }
  }, [compacting, queuedDuringCompact, doSend])

  // Stabile handlers til den memo'd textarea (ellers re-renderer den hvert tick).
  const onInputChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => setText(e.target.value), [])
  const onInputKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() }
  }, [send])

  const stop = (e: React.MouseEvent) => e.stopPropagation()
  const permLabel = PERMISSIONS.find((p) => p.key === permission)?.label ?? 'Spørg'

  return (
    <div className="composer-shell">
    <div className={`composer ${dragOver ? 'drag-over' : ''}`}>
      {dragOver && <div className="composer-drop-overlay">Slip filer og billeder her</div>}
      {ringDenominator > 0 && (
        <div className="composer-ring-corner">
          <ContextRing tokens={contextTokens} compactAt={ringDenominator} modelLabel={currentModelLabel} />
        </div>
      )}
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
      <ComposerTextArea
        inputRef={ref}
        value={text}
        placeholder={compacting ? 'Komprimerer kontekst — din besked sendes når den er færdig…' : streaming ? 'Skriv en follow-up (sendes når Jarvis er færdig)…' : 'Spørg Jarvis om noget…'}
        onChange={onInputChange}
        onKeyDown={onInputKeyDown}
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
          {/* Provider-vælger — KUN owner. Hele paletten af visible-klare providers. */}
          {isOwner && (
            <div className="composer-popover-anchor" onClick={stop}>
              <button type="button" className="model-pill"
                onClick={() => { setProvOpen((o) => !o); setModelOpen(false) }}>
                <span className="dot" />{provLabel(provChoice)}<span className="caret">▾</span>
              </button>
              {provOpen && (
                <div className="composer-menu model-menu">
                  {ownerProviders.map((pid) => (
                    <button key={pid} type="button" className={provChoice === pid ? 'active' : ''}
                      onClick={() => { setProvChoice(pid); setSelModel(''); setProvOpen(false) }}>
                      {provLabel(pid)}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
          {/* Model-vælger — alle. Owner: dynamisk liste; member: Standard/Pro. */}
          <div className="composer-popover-anchor" onClick={stop}>
            <button type="button" className="model-pill"
              onClick={() => { setModelOpen((o) => !o); setProvOpen(false) }}>
              <span className="dot" />{currentModelLabel}<span className="caret">▾</span>
            </button>
            {modelOpen && (
              <div className="composer-menu model-menu">
                {isOwner
                  ? ownerModelOptions.map((o) => (
                      <button key={o.id} type="button" className={selModel === o.id ? 'active' : ''}
                        onClick={() => { setSelModel(o.id); setModelOpen(false) }}>{o.label}</button>
                    ))
                  : (['standard', 'pro'] as const).map((tier) => (
                      <button key={tier} type="button" className={memberTier === tier ? 'active' : ''}
                        onClick={() => { setSelModel(tier); setModelOpen(false) }}>{tier === 'pro' ? 'Pro' : 'Standard'}</button>
                    ))}
                {isOwner && ownerModelOptions.length === 0 && (
                  <button type="button" disabled>Henter modeller…</button>
                )}
              </div>
            )}
          </div>
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
          ) : compacting ? (
            <button
              type="button"
              className={`composer-send composer-compacting ${queuedDuringCompact ? 'queued' : ''}`}
              onClick={send}
              aria-label={queuedDuringCompact ? 'I kø — sendes efter compaction' : 'Komprimerer kontekst'}
              title={queuedDuringCompact ? 'Din besked sendes når komprimeringen er færdig' : 'Komprimerer kontekst — vent et øjeblik'}
            >
              <Loader2 size={14} strokeWidth={2.5} className="spin" />
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
    <p className="composer-disclaimer">
      Jarvis kan tage fejl — dobbelttjek vigtige svar.
      {onOpenPrivacy && (
        <> · <button type="button" className="composer-privacy-link" onClick={onOpenPrivacy}>Privatliv &amp; cookies</button></>
      )}
    </p>
    </div>
  )
}
