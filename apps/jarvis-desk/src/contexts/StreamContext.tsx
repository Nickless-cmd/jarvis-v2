import { createContext, useCallback, useEffect, useMemo, useReducer, useRef, useState, type ReactNode } from 'react'
import { startStream, type StreamControl } from '../lib/streamClient'
import { cancelRun, approveTool, denyTool } from '../lib/api'
import { streamReducer, initialStreamState, type StreamStatus } from '../lib/streamReducer'
import type { StreamEvent, ContentBlock } from '../lib/sseProtocol'

interface DeskRunBridge {
  setActiveRun?: (runId: string | null) => void
  setRunAuth?: (apiBaseUrl: string, authToken: string | null) => void
  setTrayAttention?: (on: boolean) => void
  notifyTaskDone?: (title: string, body: string) => void
}
function deskRunBridge(): DeskRunBridge | undefined {
  return (window as unknown as { jarvisDesk?: DeskRunBridge }).jarvisDesk
}

export interface SendOpts {
  sessionId: string
  approvalMode?: 'ask' | 'trust'
  thinkingMode?: 'think' | 'fast'
  attachmentIds?: string[]
  mode?: 'chat' | 'cowork' | 'code'
  workspaceKind?: 'container' | 'workstation'
  workspaceRoot?: string
  /** Konkret model-id (owner kan vælge enhver; member sender flash/pro). */
  model?: string
  /** Provider-valg (KUN owner: "deepseek"|"ollama"). Member ignoreres server-side. */
  providerChoice?: string
}

export interface PendingApproval {
  approvalId: string
  tool: string
  action: string
}

export interface PendingAppAction {
  action: 'switch_to_code_mode' | 'request_full_access'
  reason: string
  originalMessage: string
}

export interface StreamContextValue {
  status: StreamStatus
  /** Model/provider/lane det aktive/seneste run faktisk brugte (til footer). */
  activeModel: string
  activeProvider: string
  activeLane: string
  /** Session-id for det aktive run (kun mens status==='working'), ellers null. */
  workingSessionId: string | null
  /** Token-forbrug fra seneste/aktive run (til context-ring #9). */
  usage: { input: number; output: number; cacheHit: number; cacheMiss: number }
  blocks: ContentBlock[]
  activeRunId: string | null
  elapsedMs: number
  workingStep: string | null
  error: Error | null
  needsAttention: boolean
  send: (message: string, opts: SendOpts) => void
  abort: () => Promise<void>
  continueFromPartial: () => void
  /** Afventende tool-godkendelse (code/cowork, permission=ask), ellers null. */
  pendingApproval: PendingApproval | null
  approve: (approvalId: string) => void
  deny: (approvalId: string) => void
  /** Afventende app-action-anmodning (mode/permission-skift), ellers null. */
  pendingAppAction: PendingAppAction | null
  /** Ryd app-action-kortet (efter approve/deny). */
  clearAppAction: () => void
  /** Besked der skal gen-sendes efter et godkendt skift, ellers null. */
  autoContinue: string | null
  /** Arm en auto-continue (kaldes af kort-handler ved godkendelse). */
  armAutoContinue: (message: string) => void
  /** Forbrug + ryd auto-continue (kaldes af den view der gen-sender). */
  consumeAutoContinue: () => string | null
}

export const StreamContext = createContext<StreamContextValue | null>(null)

export function StreamProvider({
  children,
  config,
}: {
  children: ReactNode
  config: { apiBaseUrl: string; authToken: string | null }
}) {
  const [state, dispatch] = useReducer(streamReducer, undefined, initialStreamState)
  const [error, setError] = useState<Error | null>(null)
  const controlRef = useRef<StreamControl | null>(null)
  const runIdRef = useRef<string | null>(null)
  const startedAtRef = useRef<number>(0)
  const [elapsedMs, setElapsedMs] = useState(0)
  // Status hung/interrupted/error kommer fra streamClient-handlers, ikke reducer.
  const [override, setOverride] = useState<null | 'hung' | 'interrupted' | 'error'>(null)
  // Hvilken session det aktive run hører til — så Sidebar kan vise en
  // arbejds-indikator på den, også når en ANDEN session er fremme (#8).
  const [workingSessionId, setWorkingSessionId] = useState<string | null>(null)
  const [pendingApproval, setPendingApproval] = useState<PendingApproval | null>(null)
  const [pendingAppAction, setPendingAppAction] = useState<PendingAppAction | null>(null)
  const [autoContinue, setAutoContinue] = useState<string | null>(null)
  const autoContinueRef = useRef<string | null>(null)

  const send = useCallback((message: string, opts: SendOpts) => {
    setError(null)
    setOverride(null)
    setPendingApproval(null)
    setPendingAppAction(null)
    autoContinueRef.current = null
    setAutoContinue(null)
    setWorkingSessionId(opts.sessionId)
    runIdRef.current = null
    startedAtRef.current = Date.now()
    deskRunBridge()?.setRunAuth?.(config.apiBaseUrl, config.authToken)
    controlRef.current = startStream(
      {
        apiBaseUrl: config.apiBaseUrl,
        authToken: config.authToken,
        sessionId: opts.sessionId,
        message,
        approvalMode: opts.approvalMode,
        thinkingMode: opts.thinkingMode,
        attachmentIds: opts.attachmentIds,
        mode: opts.mode,
        workspaceKind: opts.workspaceKind,
        workspaceRoot: opts.workspaceRoot,
        model: opts.model,
        providerChoice: opts.providerChoice,
        autoReconnect: false,
      },
      {
        onEvent: (e: StreamEvent) => {
          // Fang approval_request (code/cowork, permission=ask) → vis ApprovalCard.
          // Serveren blokerer streamen indtil approve/deny; ryd ved næste tur-slut.
          if (e.type === 'system_event' && e.kind === 'approval_request') {
            const p = (e.payload || {}) as { approval_id?: string; tool?: string; message?: string; detail?: string }
            if (p.approval_id) {
              setPendingApproval({
                approvalId: p.approval_id,
                tool: p.tool || 'tool',
                action: [p.message, p.detail].filter(Boolean).join('\n') || p.tool || '',
              })
            }
          } else if (e.type === 'system_event' && e.kind === 'app_action_request') {
            const p = (e.payload || {}) as { action?: string; reason?: string; original_message?: string }
            if (p.action === 'switch_to_code_mode' || p.action === 'request_full_access') {
              setPendingAppAction({
                action: p.action,
                reason: p.reason || '',
                originalMessage: p.original_message || '',
              })
            }
          } else if (e.type === 'message_stop') {
            // BEMÆRK: pendingAppAction ryddes IKKE her — kortet skal blive
            // stående efter Jarvis afslutter turen, til brugeren klikker.
            setPendingApproval(null)
          }
          dispatch(e)
        },
        onRunId: (id) => { runIdRef.current = id; deskRunBridge()?.setActiveRun?.(id) },
        onHung: () => setOverride('hung'),
        onInterrupted: () => { setOverride('interrupted'); deskRunBridge()?.setActiveRun?.(null) },
        onError: (err) => { setError(err); setOverride('error'); deskRunBridge()?.setActiveRun?.(null) },
        onComplete: () => {
          deskRunBridge()?.setActiveRun?.(null)
          // Terminal-garanti klient-side: ved bruger-abort kappes forbindelsen
          // lokalt, så serverens message_stop aldrig når frem → status ville
          // hænge på 'working' (liveness/thinking spinner). Tving 'done'.
          // Idempotent: backendens egen message_stop sætter også 'done'.
          dispatch({ type: 'message_stop' } as StreamEvent)
        },
      },
    )
  }, [config])

  const abort = useCallback(async () => {
    const runId = controlRef.current?.getRunId() ?? runIdRef.current
    // R3: server-cancel FØR lokal abort. Men hvis runnet allerede er dødt
    // server-side (proces-/loop-død) fejler cancelRun — det MÅ ikke blokere
    // den lokale oprydning (→ onComplete → message_stop → 'done'), ellers
    // hænger liveness/thinking videre (Bjørn 2026-06-13). Swallow fejlen.
    if (runId) { try { await cancelRun(config, runId) } catch { /* allerede død */ } }
    controlRef.current?.abort()
  }, [config])

  const continueFromPartial = useCallback(() => {
    // Rydder override; caller (ChatView) starter en ny tur via send().
    setOverride(null)
  }, [])

  const approve = useCallback((approvalId: string) => {
    setPendingApproval(null) // optimistisk — streamen fortsætter når serveren resolver
    void approveTool(config, approvalId).catch((e) => setError(e as Error))
  }, [config])
  const deny = useCallback((approvalId: string) => {
    setPendingApproval(null)
    void denyTool(config, approvalId).catch((e) => setError(e as Error))
  }, [config])

  const clearAppAction = useCallback(() => setPendingAppAction(null), [])
  const armAutoContinue = useCallback((message: string) => {
    autoContinueRef.current = message
    setAutoContinue(message)
  }, [])
  const consumeAutoContinue = useCallback((): string | null => {
    const msg = autoContinueRef.current
    autoContinueRef.current = null
    setAutoContinue(null)
    return msg
  }, [])

  const status: StreamStatus = override ?? state.status

  // Elapsed-timer mens status='working'.
  useEffect(() => {
    if (status !== 'working') return
    const id = setInterval(() => setElapsedMs(Date.now() - startedAtRef.current), 500)
    return () => clearInterval(id)
  }, [status])

  const needsAttention =
    (status === 'working' || status === 'hung' || status === 'interrupted') &&
    typeof document !== 'undefined' &&
    document.hidden

  // Systray attention-prik følger needsAttention (Jarvis vil noget mens
  // vinduet er skjult/ude af fokus).
  useEffect(() => {
    deskRunBridge()?.setTrayAttention?.(needsAttention)
  }, [needsAttention])

  // Native "opgave færdig"-notifikation: fyrer hver gang et run går
  // working → done (uanset vindue-fokus, jf. Bjørns valg).
  const prevStatusRef = useRef<StreamStatus>('idle')
  useEffect(() => {
    if (prevStatusRef.current === 'working' && status === 'done') {
      const lastText = [...state.blocks].reverse().find((b) => b.type === 'text') as
        | { type: 'text'; text: string } | undefined
      const body = (lastText?.text || '').trim().slice(0, 140) || 'Opgaven er færdig.'
      deskRunBridge()?.notifyTaskDone?.('Jarvis er færdig', body)
    }
    prevStatusRef.current = status
  }, [status, state.blocks])

  const value = useMemo<StreamContextValue>(
    () => ({
      status,
      activeModel: state.model,
      activeProvider: state.provider,
      activeLane: state.lane,
      blocks: state.blocks,
      activeRunId: state.activeRunId,
      workingSessionId: status === 'working' ? workingSessionId : null,
      usage: state.usage,
      elapsedMs,
      workingStep: state.workingStep,
      error,
      needsAttention,
      send,
      abort,
      continueFromPartial,
      pendingApproval,
      approve,
      deny,
      pendingAppAction,
      clearAppAction,
      autoContinue,
      armAutoContinue,
      consumeAutoContinue,
    }),
    [status, state.model, state.provider, state.lane, state.blocks, state.activeRunId, workingSessionId, state.usage, elapsedMs, state.workingStep, error, needsAttention, send, abort, continueFromPartial, pendingApproval, approve, deny, pendingAppAction, clearAppAction, autoContinue, armAutoContinue, consumeAutoContinue],
  )
  return <StreamContext.Provider value={value}>{children}</StreamContext.Provider>
}
