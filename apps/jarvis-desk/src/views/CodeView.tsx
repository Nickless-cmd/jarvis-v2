import { useEffect, useRef, useState } from 'react'
import { FolderTree, PanelRight, Lock, ShieldCheck, FolderOpen, ArrowDown } from 'lucide-react'
import { useStream } from '../hooks/useStream'
import { useSettings } from '../hooks/useSettings'
import { useSessions } from '../hooks/useSessions'
import { usePanel } from '../hooks/usePanel'
import { MessageRow } from '../components/rich/MessageRow'
import { Composer, type ComposerSendOpts } from '../components/shell/Composer'
import { LivenessIndicator } from '../components/feedback/LivenessIndicator'
import { InterruptedBanner } from '../components/feedback/InterruptedBanner'
import { HangPrompt } from '../components/feedback/HangPrompt'
import { ErrorBanner } from '../components/feedback/ErrorBanner'
import { ApprovalCard } from '../components/rich/ApprovalCard'
import { PresenceDot } from '../components/shell/PresenceDot'
import { ConnectionPill } from '../components/shell/ConnectionPill'
import { GitChip } from '../components/shell/GitChip'
import { CodePanel } from '../components/panel/CodePanel'
import { getWorkspaceTrust, setWorkspaceTrust, getContextInfo } from '../lib/api'

const OWNER_ROOTS = ['docs', 'workspace', 'core', 'apps', 'scripts'] as const
const MEMBER_ROOTS = ['workspace'] as const

type WsKind = 'container' | 'workstation'
type Role = 'owner' | 'member' | 'guest'

/** Native mappe-vælger (Electron). Returnerer valgt sti eller null udenfor app'en. */
async function pickFolder(): Promise<string | null> {
  const bridge = (window as unknown as { jarvisDesk?: { pickFolder?: () => Promise<string | null> } }).jarvisDesk
  if (!bridge?.pickFolder) return null
  return bridge.pickFolder()
}

/** Code mode: Jarvis koder i et valgt workspace — server (repo/dit workspace) eller
 *  en mappe på din egen computer (via operator-bridgen). Stream i midten; foldbare
 *  fil-træ- og preview-paneler i højre. Layout spejler chat (centreret velkomst). */
export function CodeView({
  sessionId, userName, role = 'owner',
}: { sessionId: string | null; userName?: string; role?: Role }) {
  const stream = useStream()
  const { settings } = useSettings()
  const sessions = useSessions()
  const panel = usePanel()
  const isOwner = role === 'owner'
  const serverRoots = isOwner ? OWNER_ROOTS : MEMBER_ROOTS
  const serverLabel = isOwner ? 'Server' : 'Mit workspace'

  // Husk sidste workspace-valg på tværs af genstart (kind/root/sti). Trust ligger
  // server-side; uden dette mistede man bare SELEKTIONEN og skulle re-vælge mappe.
  const savedWs = (() => {
    try { return JSON.parse(localStorage.getItem('jarvis-desk:code-ws') || '{}') } catch { return {} }
  })() as { kind?: WsKind; root?: string; wsPath?: string }

  const [kind, setKind] = useState<WsKind>(savedWs.kind === 'workstation' ? 'workstation' : 'container')
  const [root, setRoot] = useState<string>(savedWs.root && serverRoots.includes(savedWs.root as never) ? savedWs.root : serverRoots[0])
  const [wsPath, setWsPath] = useState<string>(savedWs.wsPath || '') // valgt workstation-mappe
  const [filesOpen, setFilesOpen] = useState(false) // fil-træ foldet ind fra start
  const [trusted, setTrusted] = useState<boolean | null>(null)
  const [compactAt, setCompactAt] = useState(0)
  const [gitRefresh, setGitRefresh] = useState(0) // bumpes når et run slutter → GitChip gen-henter
  const config = settings ? { apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken } : undefined

  // Context-ring: hent autocompact-tærsklen (samme som chat).
  useEffect(() => {
    if (!config) return
    getContextInfo(config).then((r) => setCompactAt(r.compact_at)).catch(() => setCompactAt(0))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [config?.apiBaseUrl, config?.authToken])

  // Persistér workspace-valget ved enhver ændring.
  useEffect(() => {
    try {
      localStorage.setItem('jarvis-desk:code-ws', JSON.stringify({ kind, root, wsPath }))
    } catch { /* localStorage utilgængelig — ignorér */ }
  }, [kind, root, wsPath])

  const effRoot = kind === 'container' ? root : wsPath
  const ready = !!effRoot // workstation kræver at en mappe er valgt

  // Autoscroll + scroll-til-bund-pil (som chat).
  const transcriptRef = useRef<HTMLDivElement>(null)
  const [atBottom, setAtBottom] = useState(true)
  const [unread, setUnread] = useState(0)
  const NEAR_BOTTOM_PX = 120
  const scrollToBottom = () => {
    const el = transcriptRef.current
    if (el) el.scrollTop = el.scrollHeight
    setUnread(0)
  }
  const onScroll = () => {
    const el = transcriptRef.current
    if (!el) return
    const near = el.scrollHeight - el.scrollTop - el.clientHeight < NEAR_BOTTOM_PX
    setAtBottom(near)
    if (near) setUnread(0)
  }

  useEffect(() => { if (sessionId) sessions.select(sessionId) }, [sessionId])

  // Reconcile assistant-svar ind i transcript når et run slutter (som chat).
  useEffect(() => {
    if (stream.status === 'done' && stream.blocks.length > 0) {
      sessions.reconcile({
        id: `a-${stream.activeRunId ?? Date.now()}`,
        role: 'assistant',
        content: stream.blocks,
        created_at: new Date().toISOString(),
        parent_id: null,
      })
      setGitRefresh((k) => k + 1) // Jarvis kan have ændret filer → opdater git-chip
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stream.status])

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

  const doSend = async (text: string, opts: ComposerSendOpts) => {
    if (!ready) return
    let sid = sessionId
    if (!sid) sid = (await sessions.create('Kode-session')).id
    const message = text.trim() || 'Vedhæftet'
    sessions.appendOptimistic({
      id: `u-${Date.now()}`,
      role: 'user',
      content: [{ type: 'text', text: message }],
      created_at: new Date().toISOString(),
      parent_id: null,
    })
    stream.send(message, {
      sessionId: sid,
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

  const workspaceSelector = (
    <div className="codeview-empty-ws">
      <div className="codeview-kind">
        <button type="button" className={kind === 'container' ? 'active' : ''} onClick={() => setKind('container')}>{serverLabel}</button>
        <button type="button" className={kind === 'workstation' ? 'active' : ''} onClick={() => setKind('workstation')}>Min computer</button>
      </div>
      {kind === 'container' ? (
        serverRoots.length > 1 ? (
          <select value={root} onChange={(e) => setRoot(e.target.value)}>
            {serverRoots.map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
        ) : (
          <span className="codeview-toolbar-label">{serverRoots[0]}</span>
        )
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
      onSend={(t, o) => void doSend(t, o)}
      onStop={() => void stream.abort()}
      model="deepseek-flash"
      thinking="think"
      config={config}
      getSessionId={async () => sessionId ?? (await sessions.create('Kode-session')).id}
      showPermissions={true}
      contextTokens={stream.usage.input + stream.usage.cacheHit}
      compactAt={compactAt}
    />
  )

  const visibleMessages = sessions.messages.filter((m) => m.role === 'user' || m.role === 'assistant')

  // Autoscroll: ved nye beskeder/stream-tokens, hold bunden hvis vi er nær den.
  useEffect(() => {
    const el = transcriptRef.current
    if (el && atBottom) el.scrollTop = el.scrollHeight
    else if (!atBottom) setUnread((u) => u + 1)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [visibleMessages.length, sessionId])
  useEffect(() => {
    const el = transcriptRef.current
    if (el && atBottom) el.scrollTop = el.scrollHeight
  }, [stream.blocks, atBottom])

  const isEmpty =
    !sessionId ||
    (visibleMessages.length === 0 && stream.status === 'idle' && stream.blocks.length === 0)

  const header = (
    <div className="chatview-head">
      <div className="chatview-head-left">
        <PresenceDot status={stream.status} />{' '}
        <span className="chat-title">Code · {ready ? effRoot : 'vælg workspace'}</span>
      </div>
      <div className="chatview-head-right">
        {config && ready && <GitChip config={config} kind={kind} root={effRoot} refreshKey={gitRefresh} />}
        {config && <ConnectionPill config={config} />}
        <button
          type="button"
          className={`panel-toggle ${filesOpen ? 'active' : ''}`}
          aria-label="Vis/skjul fil-træ" title="Filer"
          onClick={() => setFilesOpen((o) => !o)}
        >
          <FolderTree size={16} />
        </button>
        <button
          type="button"
          className={`panel-toggle ${panel.open ? 'active' : ''}`}
          aria-label="Vis/skjul preview-panel" title="Preview"
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
        <div className="transcript" ref={transcriptRef} onScroll={onScroll}>
          {visibleMessages.map((m) => (
            <MessageRow key={m.id} role={m.role === 'user' ? 'user' : 'assistant'} blocks={m.content} density="compact" streaming={false} createdAt={m.created_at} />
          ))}
          {stream.status === 'working' && stream.blocks.length > 0 && (
            <MessageRow role="assistant" blocks={stream.blocks} density="compact" streaming />
          )}
          <LivenessIndicator status={stream.status} elapsedMs={stream.elapsedMs} density="compact" workingStep={stream.workingStep} tokens={stream.usage.output} />
        </div>
        <div className="composer-area">
          <div className="composer-notices">
            {stream.pendingApproval && (
              <ApprovalCard
                approvalId={stream.pendingApproval.approvalId}
                tool={stream.pendingApproval.tool}
                action={stream.pendingApproval.action}
                risk="medium"
                canApprove={isOwner}
                onApprove={(id) => stream.approve(id)}
                onDeny={(id) => stream.deny(id)}
              />
            )}
            {stream.status === 'interrupted' && <InterruptedBanner onResume={() => stream.continueFromPartial()} />}
            {stream.status === 'hung' && (
              <HangPrompt onResume={() => stream.continueFromPartial()} onAbort={() => void stream.abort()} />
            )}
            {stream.status === 'error' && stream.error && (
              <ErrorBanner message={stream.error.message} onDismiss={() => { /* ryddes ved næste send */ }} />
            )}
          </div>
          {!atBottom && (
            <button type="button" className="scroll-bottom-btn" onClick={scrollToBottom} aria-label="Til bund">
              <ArrowDown size={16} />
              {unread > 0 && <span className="scroll-badge">{unread} ny{unread > 1 ? 'e' : ''}</span>}
            </button>
          )}
          {composer}
        </div>
      </div>
      {config && filesOpen && ready && (
        <div className="codeview-panel">
          <CodePanel config={config} kind={kind} root={effRoot} />
        </div>
      )}
    </div>
  )
}
