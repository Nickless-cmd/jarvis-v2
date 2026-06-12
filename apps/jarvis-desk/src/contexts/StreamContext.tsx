import { createContext, useCallback, useEffect, useMemo, useReducer, useRef, useState, type ReactNode } from 'react'
import { startStream, type StreamControl } from '../lib/streamClient'
import { cancelRun } from '../lib/api'
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
}

export interface StreamContextValue {
  status: StreamStatus
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

  const send = useCallback((message: string, opts: SendOpts) => {
    setError(null)
    setOverride(null)
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
        autoReconnect: false,
      },
      {
        onEvent: (e: StreamEvent) => dispatch(e),
        onRunId: (id) => { runIdRef.current = id; deskRunBridge()?.setActiveRun?.(id) },
        onHung: () => setOverride('hung'),
        onInterrupted: () => { setOverride('interrupted'); deskRunBridge()?.setActiveRun?.(null) },
        onError: (err) => { setError(err); setOverride('error'); deskRunBridge()?.setActiveRun?.(null) },
        onComplete: () => { deskRunBridge()?.setActiveRun?.(null) /* status=done sættes af message_stop i reducer */ },
      },
    )
  }, [config])

  const abort = useCallback(async () => {
    const runId = controlRef.current?.getRunId() ?? runIdRef.current
    if (runId) await cancelRun(config, runId) // R3: server-cancel FØR lokal abort
    controlRef.current?.abort()
  }, [config])

  const continueFromPartial = useCallback(() => {
    // Rydder override; caller (ChatView) starter en ny tur via send().
    setOverride(null)
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
    }),
    [status, state.blocks, state.activeRunId, workingSessionId, state.usage, elapsedMs, state.workingStep, error, needsAttention, send, abort, continueFromPartial],
  )
  return <StreamContext.Provider value={value}>{children}</StreamContext.Provider>
}
