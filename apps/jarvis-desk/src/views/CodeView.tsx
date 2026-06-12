import { useEffect, useState } from 'react'
import { FolderTree, PanelRight, Lock, ShieldCheck } from 'lucide-react'
import { useStream } from '../hooks/useStream'
import { useSettings } from '../hooks/useSettings'
import { usePanel } from '../hooks/usePanel'
import { MessageRow } from '../components/rich/MessageRow'
import { Composer, type ComposerSendOpts } from '../components/shell/Composer'
import { LivenessIndicator } from '../components/feedback/LivenessIndicator'
import { PresenceDot } from '../components/shell/PresenceDot'
import { CodePanel } from '../components/panel/CodePanel'
import { getWorkspaceTrust, setWorkspaceTrust } from '../lib/api'

const CONTAINER_ROOTS = ['docs', 'workspace', 'core', 'apps', 'scripts'] as const

/** Code mode: Jarvis koder i et valgt workspace. Stream i midten; to foldbare
 *  paneler i højre side — fil-træ (CodePanel) og preview (det globale artifact-
 *  panel) — begge foldet ind fra start, slås til via ikoner i headeren (som chat). */
export function CodeView({ sessionId, userName }: { sessionId: string | null; userName?: string }) {
  const stream = useStream()
  const { settings } = useSettings()
  const panel = usePanel()
  const [root, setRoot] = useState<string>('core')
  const [filesOpen, setFilesOpen] = useState(false) // fil-træ foldet ind fra start
  const [trusted, setTrusted] = useState<boolean | null>(null)
  const config = settings ? { apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken } : undefined

  // Trusted-folder gate: tjek om det valgte workspace er betroet (skrive/exec).
  useEffect(() => {
    if (!config) return
    let cancelled = false
    setTrusted(null)
    getWorkspaceTrust(config, 'container', root)
      .then((t) => { if (!cancelled) setTrusted(t) })
      .catch(() => { if (!cancelled) setTrusted(false) })
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [root, config?.apiBaseUrl, config?.authToken])

  const trustFolder = async () => {
    if (!config) return
    try {
      const t = await setWorkspaceTrust(config, 'container', root, true)
      setTrusted(t)
    } catch { /* lad banneret blive — brugeren kan prøve igen */ }
  }

  const trustBanner = trusted === false ? (
    <div className="trust-banner">
      <Lock size={14} />
      <span><strong>{root}</strong> er ikke betroet — Jarvis kan læse, men ikke skrive eller køre kommandoer her.</span>
      <button type="button" className="trust-btn" onClick={trustFolder}>
        <ShieldCheck size={13} /> Stol på mappen
      </button>
    </div>
  ) : null

  const handleSend = (text: string, opts: ComposerSendOpts) => {
    if (!sessionId) return
    stream.send(text, {
      sessionId,
      approvalMode: opts.permission,
      attachmentIds: opts.attachments.map((a) => a.id),
      mode: 'code',
      workspaceKind: 'container',
      workspaceRoot: root,
    })
  }

  const composer = (
    <Composer
      streaming={stream.status === 'working'}
      onSend={handleSend}
      onStop={() => void stream.abort()}
      model="deepseek-flash"
      thinking="think"
      config={config}
      getSessionId={async () => sessionId ?? ''}
      showPermissions={true}
      contextTokens={stream.usage.input + stream.usage.cacheHit}
      compactAt={0}
    />
  )

  const isEmpty = !sessionId && stream.status === 'idle' && stream.blocks.length === 0

  const header = (
    <div className="chatview-head">
      <div className="chatview-head-left">
        <PresenceDot status={stream.status} /> <span className="chat-title">Code · {root}</span>
      </div>
      <div className="chatview-head-right">
        <button
          type="button"
          className={`panel-toggle ${filesOpen ? 'active' : ''}`}
          aria-label="Vis/skjul fil-træ"
          title="Filer"
          onClick={() => setFilesOpen((o) => !o)}
        >
          <FolderTree size={16} />
        </button>
        <button
          type="button"
          className={`panel-toggle ${panel.open ? 'active' : ''}`}
          aria-label="Vis/skjul preview-panel"
          title="Preview"
          onClick={panel.toggle}
        >
          <PanelRight size={16} />
        </button>
      </div>
    </div>
  )

  // ── Tom/ny samtale: header øverst, composer centreret midt på skærmen (som chat) ──
  if (isEmpty) {
    return (
      <div className="codeview empty">
        {header}
        {trustBanner}
        <div className="chat-empty">
          <h2>Hej{userName ? ` ${userName}` : ''}.</h2>
          <p>Hvad skal vi kode? Vælg et workspace, så går vi i gang.</p>
          <div className="codeview-empty-ws">
            <span className="codeview-toolbar-label">Workspace</span>
            <select value={root} onChange={(e) => setRoot(e.target.value)}>
              {CONTAINER_ROOTS.map((r) => <option key={r} value={r}>{r}</option>)}
            </select>
          </div>
          {composer}
        </div>
      </div>
    )
  }

  // ── Aktiv samtale ──
  return (
    <div className="codeview">
      <div className="codeview-main">
        {header}
        {trustBanner}
        <div className="codeview-toolbar">
          <span className="codeview-toolbar-label">Workspace</span>
          <select value={root} onChange={(e) => setRoot(e.target.value)}>
            {CONTAINER_ROOTS.map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
        </div>
        <div className="transcript">
          {stream.blocks.length > 0 && (
            <MessageRow role="assistant" blocks={stream.blocks} density="full" streaming={stream.status === 'working'} />
          )}
          <LivenessIndicator status={stream.status} elapsedMs={stream.elapsedMs} density="full" workingStep={stream.workingStep} />
        </div>
        <div className="composer-area">{composer}</div>
      </div>
      {config && filesOpen && (
        <div className="codeview-panel">
          <CodePanel config={config} kind="container" root={root} />
        </div>
      )}
    </div>
  )
}
