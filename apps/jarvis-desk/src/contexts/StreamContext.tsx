import { createContext, useCallback, useMemo, useReducer, useRef, useState, type ReactNode } from 'react'
import { startStream, type StreamControl } from '../lib/streamClient'
import { cancelRun } from '../lib/api'
import { streamReducer, initialStreamState, type StreamStatus } from '../lib/streamReducer'
import type { StreamEvent, ContentBlock } from '../lib/sseProtocol'

export interface SendOpts {
  sessionId: string
  approvalMode?: 'ask' | 'trust'
  thinkingMode?: 'think' | 'fast'
}

export interface StreamContextValue {
  status: StreamStatus
  blocks: ContentBlock[]
  activeRunId: string | null
  elapsedMs: number
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
  const [elapsedMs] = useState(0) // elapsed-timer tilføjes i Fase 5 (feedback)
  // Status hung/interrupted/error kommer fra streamClient-handlers, ikke reducer.
  const [override, setOverride] = useState<null | 'hung' | 'interrupted' | 'error'>(null)

  const send = useCallback((message: string, opts: SendOpts) => {
    setError(null)
    setOverride(null)
    runIdRef.current = null
    startedAtRef.current = Date.now()
    controlRef.current = startStream(
      {
        apiBaseUrl: config.apiBaseUrl,
        authToken: config.authToken,
        sessionId: opts.sessionId,
        message,
        approvalMode: opts.approvalMode,
        thinkingMode: opts.thinkingMode,
        autoReconnect: false,
      },
      {
        onEvent: (e: StreamEvent) => dispatch(e),
        onRunId: (id) => { runIdRef.current = id },
        onHung: () => setOverride('hung'),
        onInterrupted: () => setOverride('interrupted'),
        onError: (err) => { setError(err); setOverride('error') },
        onComplete: () => { /* status=done sættes af message_stop i reducer */ },
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
  const needsAttention =
    (status === 'working' || status === 'hung' || status === 'interrupted') &&
    typeof document !== 'undefined' &&
    document.hidden

  const value = useMemo<StreamContextValue>(
    () => ({
      status,
      blocks: state.blocks,
      activeRunId: state.activeRunId,
      elapsedMs,
      error,
      needsAttention,
      send,
      abort,
      continueFromPartial,
    }),
    [status, state.blocks, state.activeRunId, elapsedMs, error, needsAttention, send, abort, continueFromPartial],
  )
  return <StreamContext.Provider value={value}>{children}</StreamContext.Provider>
}
