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
              }
              updateState((prev) => streamReducer(prev, event))
              if (event.type === 'message_stop') {
                persistAssistantSnapshot('done')
              }
            },
            onInterrupted: () => persistAssistantSnapshot('interrupted'),
            onError: (err) => {
              setReconnecting(false)
              setLastError(err?.message ?? 'ukendt')
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
    [appendLocalMessage, approval, state, lastError, reconnecting]
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
