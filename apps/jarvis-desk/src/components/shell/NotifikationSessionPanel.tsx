import { useCallback, useEffect, useRef, useState } from 'react'
import { ExternalLink, X } from 'lucide-react'
import { approveTool, cancelRun, denyTool, getSession, type ApiConfig, type ChatMessage, type ChatSession } from '../../lib/api'
import { startStream, type StreamControl } from '../../lib/streamClient'
import type { StreamEvent } from '../../lib/sseProtocol'
import { initialStreamState, liveBlokke, streamReducer } from '../../lib/streamReducer'
import { useRammeReducer } from '../../lib/useRammeReducer'
import { MessageRow } from '../rich/MessageRow'
import { Composer, type ComposerSendOpts } from './Composer'
import { PermissionProvider } from '../../contexts/PermissionContext'
import '../../styles/notification-feed.css'

export function NotifikationSessionPanel({ config, sessionId, isOwner, onClose, onOpenFull }: {
  config: ApiConfig
  sessionId: string
  isOwner: boolean
  onClose: () => void
  onOpenFull: (surface: 'chat' | 'code') => void
}) {
  const [session, setSession] = useState<ChatSession | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [sending, setSending] = useState(false)
  const [pendingText, setPendingText] = useState('')
  const [approvalId, setApprovalId] = useState<string | null>(null)
  const [approvalText, setApprovalText] = useState('')
  const [live, dispatch] = useRammeReducer(streamReducer, initialStreamState)
  const control = useRef<StreamControl | null>(null)
  const bottom = useRef<HTMLDivElement | null>(null)

  const refresh = useCallback(async () => {
    try {
      const result = await getSession(config, sessionId)
      if (!result) return
      setSession(result.session)
      setMessages(result.messages)
      setError('')
    } catch {
      setError('Samtalen kunne ikke hentes. Prøv igen.')
    } finally { setLoading(false) }
  }, [config, sessionId])

  useEffect(() => {
    void refresh()
    const timer = window.setInterval(() => { if (!sending) void refresh() }, 4000)
    return () => window.clearInterval(timer)
  }, [refresh, sending])
  useEffect(() => () => control.current?.abort(), [])
  useEffect(() => bottom.current?.scrollIntoView?.({ block: 'end' }), [messages, live.blocks, pendingText])

  const send = (text: string, opts: ComposerSendOpts) => {
    if (sending) return
    const message = text.trim() || opts.attachments.map((item) => item.name).join(', ') || 'Vedhæftet'
    setError('')
    setPendingText(message)
    setSending(true)
    control.current = startStream({
      apiBaseUrl: config.apiBaseUrl,
      authToken: config.authToken,
      sessionId,
      message,
      approvalMode: opts.permission,
      attachmentIds: opts.attachments.map((item) => item.id),
      model: opts.model,
      providerChoice: opts.providerChoice,
      thinkingMode: opts.thinkingMode,
      mode: session?.workspace_kind ? 'code' : 'chat',
      workspaceKind: session?.workspace_kind === 'workstation' ? 'workstation' : session?.workspace_kind === 'container' ? 'container' : undefined,
      workspaceRoot: session?.workspace_root ?? undefined,
      autoReconnect: false,
    }, {
      onEvent: (event: StreamEvent) => {
        if (event.type === 'system_event' && event.kind === 'approval_request') {
          const payload = event.payload as { approval_id?: string; message?: string; detail?: string }
          if (payload.approval_id) {
            setApprovalId(payload.approval_id)
            setApprovalText([payload.message, payload.detail].filter(Boolean).join('\n'))
          }
        }
        dispatch(event)
      },
      onInterrupted: () => { setError('Forbindelsen blev afbrudt. Runnet fortsætter på serveren.'); setSending(false); void refresh() },
      onError: (cause) => { setError(cause.userMessage()); setSending(false); void refresh() },
      onComplete: () => {
        setSending(false)
        setApprovalId(null)
        window.setTimeout(() => { void refresh(); setPendingText('') }, 900)
        window.setTimeout(() => { void refresh() }, 2600)
      },
    })
  }

  const answerApproval = async (approved: boolean) => {
    if (!approvalId) return
    try {
      if (approved) await approveTool(config, approvalId)
      else await denyTool(config, approvalId)
      setApprovalId(null)
    } catch { setError('Godkendelsen kunne ikke sendes. Prøv igen.') }
  }

  const stop = async () => {
    const runId = control.current?.getRunId()
    if (runId) { try { await cancelRun(config, runId) } catch { /* run may already have ended */ } }
    control.current?.abort()
    setSending(false)
    void refresh()
  }

  return (
    <aside className="notif-session-panel" role="dialog" aria-label="Samtale fra notifikation">
      <header className="notif-session-head">
        <div className="notif-session-heading">
          <strong>{session?.title || 'Samtale'}</strong>
          <span>{session?.workspace_kind ? 'Kode-session' : 'Samtale'} · fra notifikation</span>
        </div>
        <button type="button" className="icon-btn" onClick={() => onOpenFull(session?.workspace_kind ? 'code' : 'chat')} aria-label="Åbn hele samtalen" title="Åbn hele samtalen"><ExternalLink size={15} /></button>
        <button type="button" className="icon-btn" onClick={onClose} aria-label="Luk samtalepanel"><X size={16} /></button>
      </header>
      <div className="notif-session-messages">
        {loading && <p className="notif-session-hint">Henter samtalen…</p>}
        {error && <p className="notif-session-error" role="alert">{error}</p>}
        {!loading && !error && messages.length === 0 && <p className="notif-session-hint">Ingen beskeder endnu.</p>}
        {messages.filter((msg) => msg.role === 'user' || msg.role === 'assistant').slice(-30).map((msg) => (
          <MessageRow key={msg.id} role={msg.role as 'user' | 'assistant'} blocks={msg.content}
            density="compact" streaming={false} createdAt={msg.created_at} config={config}
            beskedId={msg.id} sessionId={sessionId} />
        ))}
        {pendingText && <MessageRow role="user" blocks={[{ type: 'text', text: pendingText }]} density="compact" streaming />}
        {sending && live.blocks.length > 0 && <MessageRow role="assistant" blocks={liveBlokke(live)} density="compact" streaming
          rundeEtiketter={live.rundeEtiketter} tankeResumeer={live.tankeResumeer} />}
        <div ref={bottom} />
      </div>
      {approvalId && <div className="notif-session-approval">
        <p>{approvalText || 'Jarvis beder om tilladelse.'}</p>
        <button type="button" onClick={() => void answerApproval(false)}>Afvis</button>
        <button type="button" onClick={() => void answerApproval(true)}>Godkend</button>
      </div>}
      <div className="notif-session-composer">
        <PermissionProvider config={config} sessionId={sessionId}>
          <Composer streaming={sending} onSend={send} onStop={() => void stop()}
            model="deepseek-flash" config={config} getSessionId={async () => sessionId}
            sessionId={sessionId} isOwner={isOwner} showPermissions />
        </PermissionProvider>
      </div>
    </aside>
  )
}
