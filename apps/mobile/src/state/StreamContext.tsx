import { createContext, useContext, useMemo, useRef, useState, type ReactNode } from 'react'
import { approveTool, cancelRun, denyTool } from '../lib/apiClient'
import type { ApprovalViewModel } from '../components/ApprovalCard'
import type { ContentBlock } from '../lib/sseProtocol'
import { followSession, startStream, type StreamControl } from '../lib/streamClient'
import {
  initialStreamState,
  streamReducer,
  type StreamState,
  type StreamStatus
} from '../lib/streamReducer'
import type { ApiConfig, ChatMessage } from '../lib/types'
import { useSessions } from './SessionContext'

interface StreamContextValue {
  state: StreamState
  approval: ApprovalViewModel | null
  lastError: string | null
  /** Struktureret bruger-vendt fejl (unified fejl-system). Render i ErrorBanner. */
  streamError: StreamErrorInfo | null
  /** Ryd fejlen (luk-knap). */
  clearError: () => void
  reconnecting: boolean
  send: (
    config: ApiConfig,
    sessionId: string,
    message: string,
    opts?: { model?: string; providerChoice?: string; attachmentIds?: string[] }
  ) => void
  stop: (config: ApiConfig) => Promise<void>
  approve: (config: ApiConfig) => Promise<void>
  deny: (config: ApiConfig) => Promise<void>
  /** Følg en sessions live-stream (delte sessioner): se transcript + liveness
   * live uanset hvem der skriver. Passiv — afbrydes automatisk af send(). */
  follow: (config: ApiConfig, sessionId: string) => void
  stopFollow: () => void
}

/** Hvordan runtime forsøger at rette fejlen (central_error_envelope.recoverable).
 *  Styrer hvilken system-handlings-linje ErrorCard viser. */
export type StreamErrorRecoverable = 'auto' | 'retry' | 'user_action' | 'degraded' | 'permanent' | ''

/** Struktureret bruger-vendt fejl (unified fejl-system, central_error_envelope).
 *  Fra backendens `error`-system_event ELLER en terminal klient-fejl. */
export interface StreamErrorInfo {
  code: string
  /** Kanonisk fejl-kind (fx `stream.cutoff`, `provider.timeout`) — familie-taksonomi. */
  kind: string
  severity: 'info' | 'warning' | 'error' | 'critical'
  message: string
  fixHint: string
  retryable: boolean
  correlationId: string
  /** Runtime-selvhelbreds-status (auto/retry/…): driver system-handlings-linjen. */
  recoverable: StreamErrorRecoverable
  /** Fejlens omfang (fx `run`, `session`, `runtime`) — kontekst i transparens. */
  scope: string
}

const RECOVERABLES: StreamErrorRecoverable[] = ['auto', 'retry', 'user_action', 'degraded', 'permanent']

/** Backendens `error`-payload (central_error_envelope) → UI-form. */
function eventToErrorInfo(payload: Record<string, unknown>): StreamErrorInfo {
  const sev = String(payload.severity ?? 'error')
  const rec = String(payload.recoverable ?? '')
  return {
    code: String(payload.code ?? 'unknown'),
    kind: String(payload.kind ?? payload.code ?? 'unknown'),
    severity: (['info', 'warning', 'error', 'critical'].includes(sev) ? sev : 'error') as StreamErrorInfo['severity'],
    message: String(payload.message ?? 'Der opstod en fejl.'),
    fixHint: String(payload.fix_hint ?? ''),
    retryable: Boolean(payload.retryable ?? true),
    correlationId: String(payload.correlation_id ?? ''),
    recoverable: (RECOVERABLES.includes(rec as StreamErrorRecoverable) ? rec : '') as StreamErrorRecoverable,
    scope: String(payload.scope ?? '')
  }
}

/** Terminal klient-fejl (efter at den indbyggede reconnect er opbrugt) → UI-form. */
function clientErrorToInfo(_err: Error | undefined): StreamErrorInfo {
  return {
    code: 'stream',
    kind: 'stream.disconnected',
    severity: 'error',
    message: 'Forbindelsen til Jarvis blev afbrudt.',
    fixHint: 'Tjek din forbindelse og prøv igen.',
    retryable: true,
    correlationId: '',
    recoverable: 'retry',
    scope: 'session'
  }
}

const StreamContext = createContext<StreamContextValue | null>(null)

function blocksToAssistantText(blocks: ContentBlock[]): string {
  return blocks
    .map((block) => {
      if (block.type === 'text') return block.text
      if (block.type === 'thinking') return block.thinking
      return ''
    })
    .join('')
}

export function StreamProvider({ children }: { children: ReactNode }) {
  const { appendLocalMessage } = useSessions()
  const [state, setState] = useState(initialStreamState())
  const [approval, setApproval] = useState<ApprovalViewModel | null>(null)
  const [lastError, setLastError] = useState<string | null>(null)
  const [streamError, setStreamError] = useState<StreamErrorInfo | null>(null)
  const [reconnecting, setReconnecting] = useState(false)
  const control = useRef<StreamControl | null>(null)
  const followControl = useRef<StreamControl | null>(null)
  const stateRef = useRef(state)
  const persistedRunRef = useRef<string | null>(null)

  const updateState = (next: StreamState | ((current: StreamState) => StreamState)) => {
    const resolved = typeof next === 'function' ? next(stateRef.current) : next
    stateRef.current = resolved
    setState(resolved)
  }

  const persistAssistantSnapshot = (status: StreamStatus) => {
    const current = stateRef.current
    const assistantText = blocksToAssistantText(current.blocks).trim()
    const runId = current.activeRunId ?? control.current?.getRunId() ?? 'local'

    if (assistantText && persistedRunRef.current !== runId) {
      persistedRunRef.current = runId
      appendLocalMessage({
        id: `local-assistant-${runId}-${Date.now()}`,
        role: 'assistant',
        content: assistantText,
        created_at: new Date().toISOString()
      })
    }

    updateState((prev) => ({ ...prev, status, blocks: [] }))
    // Send afsluttet → frigiv send-controlleren, så en passiv live-attach
    // (delt-session sync) må køre igen. control.current != null ⟺ aktiv send.
    control.current = null
  }

  const value = useMemo<StreamContextValue>(
    () => ({
      state,
      approval,
      lastError,
      streamError,
      clearError: () => { setStreamError(null); setLastError(null) },
      reconnecting,
      send: (config, sessionId, message, opts) => {
        const local: ChatMessage = {
          id: `local-${Date.now()}`,
          role: 'user',
          content: message,
          created_at: new Date().toISOString()
        }

        // En aktiv send ejer streamen → stop enhver passiv follow først.
        followControl.current?.abort()
        followControl.current = null
        appendLocalMessage(local)
        persistedRunRef.current = null
        setApproval(null)
        setLastError(null)
        setStreamError(null)
        setReconnecting(false)
        updateState(initialStreamState())
        control.current = startStream(
          {
            config,
            sessionId,
            message,
            mode: 'chat',
            model: opts?.model,
            providerChoice: opts?.providerChoice,
            attachmentIds: opts?.attachmentIds
          },
          {
            onReconnecting: () => setReconnecting(true),
            onEvent: (event) => {
              // Ubetinget: enhver indkommende frame = forbindelsen er i live igen.
              // (Ikke `if (reconnecting)` — closuren fanger en forældet
              // reconnecting-værdi fra send-tidspunktet, så guarden ryddede aldrig
              // banneret. setReconnecting(false) er en no-op hvis allerede false.)
              setReconnecting(false)
              if (event.type === 'system_event' && event.kind === 'approval_request') {
                setApproval({
                  approvalId: String(event.payload.approval_id ?? ''),
                  tool: String(event.payload.tool ?? ''),
                  message: String(event.payload.message ?? 'Jarvis beder om tilladelse.'),
                  detail:
                    typeof event.payload.detail === 'string' ? event.payload.detail : undefined
                })
              } else if (event.type === 'system_event' && event.kind === 'error') {
                // Unified fejl-system: backendens envelope → struktureret bruger-fejl.
                const info = eventToErrorInfo(event.payload as Record<string, unknown>)
                setStreamError(info)
                setLastError(info.message)
              }
              updateState((prev) => streamReducer(prev, event))
              if (event.type === 'message_stop') {
                persistAssistantSnapshot('done')
              }
            },
            onInterrupted: () => persistAssistantSnapshot('interrupted'),
            onError: (err) => {
              // Fyrer FØRST når den indbyggede reconnect (offset-baseret re-attach)
              // er opbrugt → ægte terminal fejl. Struktureret + retryable.
              setReconnecting(false)
              const info = clientErrorToInfo(err)
              setStreamError(info)
              setLastError(err?.message ?? info.message)
              persistAssistantSnapshot('error')
            }
          }
        )
      },
      stop: async (config) => {
        const runId = control.current?.getRunId() ?? state.activeRunId
        control.current?.abort()
        persistAssistantSnapshot('interrupted')
        if (runId) {
          try {
            await cancelRun(config, runId)
          } catch {
            // Local interruption must win even if the server-side cancel request fails.
          }
        }
      },
      approve: async (config) => {
        if (!approval?.approvalId) return
        await approveTool(config, approval.approvalId)
        setApproval(null)
      },
      deny: async (config) => {
        if (!approval?.approvalId) return
        await denyTool(config, approval.approvalId)
        setApproval(null)
      },
      follow: (config, sessionId) => {
        // Passiv: ALDRIG oven på en aktiv send (control.current != null ⟺ vi
        // sender selv → vores egen send-stream ER live-visningen). Dette er
        // værnet der forhindrer den dobbelt-render der knækkede follow før.
        if (control.current) return
        followControl.current?.abort()
        let skip = false
        followControl.current = followSession(config, sessionId, {
          onRunId: (runId) => {
            // Dedup: er dette run allerede persisteret (vores eget afsluttede,
            // eller set før), så er der intet nyt at vise live → drop follow.
            if (runId && persistedRunRef.current === runId) {
              skip = true
              followControl.current?.abort()
              followControl.current = null
            }
          },
          onEvent: (event) => {
            if (skip) return
            if (event.type === 'system_event' && event.kind === 'approval_request') {
              setApproval({
                approvalId: String(event.payload.approval_id ?? ''),
                tool: String(event.payload.tool ?? ''),
                message: String(event.payload.message ?? 'Jarvis beder om tilladelse.'),
                detail:
                  typeof event.payload.detail === 'string' ? event.payload.detail : undefined
              })
            }
            updateState((prev) => streamReducer(prev, event))
            if (event.type === 'message_stop') persistAssistantSnapshot('done')
          },
          // Follow der lukker uden svar er normalt (intet aktivt run) → tilbage til idle.
          onComplete: () => {
            followControl.current = null
            if (!skip && stateRef.current.blocks.length === 0) {
              updateState((prev) => (prev.status === 'working' ? { ...prev, status: 'idle' } : prev))
            }
          },
          onError: () => {
            followControl.current = null
          }
        })
      },
      stopFollow: () => {
        followControl.current?.abort()
        followControl.current = null
      }
    }),
    [appendLocalMessage, approval, state, lastError, streamError, reconnecting]
  )

  return <StreamContext.Provider value={value}>{children}</StreamContext.Provider>
}

export function useStream(): StreamContextValue {
  const ctx = useContext(StreamContext)

  if (!ctx) {
    throw new Error('useStream must be used within StreamProvider')
  }

  return ctx
}
