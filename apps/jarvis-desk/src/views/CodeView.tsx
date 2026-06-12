import { useEffect, useState } from 'react'
import { FolderTree, PanelRight, Lock, ShieldCheck, FolderOpen } from 'lucide-react'
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

type WsKind = 'container' | 'workstation'

/** Native mappe-vælger (Electron). Returnerer valgt sti eller null udenfor app'en. */
async function pickFolder(): Promise<string | null> {
  const bridge = (window as unknown as { jarvisDesk?: { pickFolder?: () => Promise<string | null> } }).jarvisDesk
  if (!bridge?.pickFolder) return null
  return bridge.pickFolder()
}

/** Code mode: Jarvis koder i et valgt workspace — enten container-repoet eller en
 *  mappe på din egen computer (workstation, via operator-bridgen). Stream i midten;
 *  to foldbare paneler (fil-træ + preview) i højre, slået til via header-ikoner. */
export function CodeView({ sessionId, userName }: { sessionId: string | null; userName?: string }) {
  const stream = useStream()
  const { settings } = useSettings()
  const panel = usePanel()
  const [kind, setKind] = useState<WsKind>('container')
  const [root, setRoot] = useState<string>('core')
  const [wsPath, setWsPath] = useState<string>('') // valgt workstation-mappe
  const [filesOpen, setFilesOpen] = useState(false) // fil-træ foldet ind fra start
  const [trusted, setTrusted] = useState<boolean | null>(null)
  const config = settings ? { apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken } : undefined

  // Effektiv workspace-rod: container bruger repo-undermappe, workstation den valgte sti.
  const effRoot = kind === 'container' ? root : wsPath
  const ready = !!effRoot // workstation kræver at en mappe er valgt

  // Trusted-folder gate: tjek om det valgte workspace er betroet (skrive/exec).
  useEffect(() => {
    if (!config || !ready) { setTrusted(ready ? null : true); return }
    let cancelled = false
    setTrusted(null)
    getWorkspaceTrust(config, kind, effRoot)
      .then((t) => { if (!cancelled) setTrusted(t) })
      .catch(() => { if (!cancelled) setTrusted(false) })
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [kind, effRoot, config?.apiBaseUrl, config?.authToken])

  const trustFolder = async () => {
    if (!config || !ready) return
    try {
      const t = await setWorkspaceTrust(config, kind, effRoot, true)
      setTrusted(t)
    } catch { /* lad banneret blive — brugeren kan prøve igen */ }
  }

  const choosePath = async () => {
    const p = await pickFolder()
    if (p) { setKind('workstation'); setWsPath(p) }
  }

  const handleSend = (text: string, opts: ComposerSendOpts) => {
    if (!sessionId || !ready) return
    stream.send(text, {
      sessionId,
      approvalMode: opts.permission,
      attachmentIds: opts.attachments.map((a) => a.id),
      mode: 'code',
      workspaceKind: kind,
      workspaceRoot: effRoot,
    })
  }

  const trustBanner = trusted === false ? (
    <div className="trust-banner">
      <Lock size={14} />
      <span><strong>{effRoot}</strong> er ikke betroet — Jarvis kan læse, men ikke skrive eller køre kommandoer her.</span>
      <button type="button" className="trust-btn" onClick={trustFolder}>
        <ShieldCheck size={13} /> Stol på mappen
      </button>
    </div>
  ) : null

  // Workspace-vælger (kind-toggle + enten container-select eller workstation-mappe).
  const workspaceSelector = (
    <div className="codeview-empty-ws">
      <div className="codeview-kind">
        <button type="button" className={kind === 'container' ? 'active' : ''} onClick={() => setKind('container')}>Server</button>
        <button type="button" className={kind === 'workstation' ? 'active' : ''} onClick={() => setKind('workstation')}>Min computer</button>
      </div>
      {kind === 'container' ? (
        <select value={root} onChange={(e) => setRoot(e.target.value)}>
          {CONTAINER_ROOTS.map((r) => <option key={r} value={r}>{r}</option>)}
        </select>
      ) : (
        <button type="button" className="codeview-pick" onClick={choosePath} title={wsPath || 'Vælg mappe'}>
          <FolderOpen size={13} />
          <span className="path">{wsPath || 'Vælg mappe…'}</span>
        </button>
      )}
    </div>
  )

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
        <PresenceDot status={stream.status} />{' '}
        <span className="chat-title">Code · {ready ? effRoot : 'vælg workspace'}</span>
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
          {workspaceSelector}
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
        <div className="codeview-toolbar">{workspaceSelector}</div>
        <div className="transcript">
          {stream.blocks.length > 0 && (
            <MessageRow role="assistant" blocks={stream.blocks} density="full" streaming={stream.status === 'working'} />
          )}
          <LivenessIndicator status={stream.status} elapsedMs={stream.elapsedMs} density="full" workingStep={stream.workingStep} />
        </div>
        <div className="composer-area">{composer}</div>
      </div>
      {config && filesOpen && ready && (
        <div className="codeview-panel">
          <CodePanel config={config} kind={kind} root={effRoot} />
        </div>
      )}
    </div>
  )
}
