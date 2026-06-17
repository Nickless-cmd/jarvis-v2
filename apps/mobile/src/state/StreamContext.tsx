import { createContext, useContext, useMemo, useRef, useState, type ReactNode } from 'react'
import { cancelRun } from '../lib/apiClient'
import type { ContentBlock } from '../lib/sseProtocol'
import { startStream, type StreamControl } from '../lib/streamClient'
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
  send: (config: ApiConfig, sessionId: string, message: string) => void
  stop: (config: ApiConfig) => Promise<void>
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
  const control = useRef<StreamControl | null>(null)
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
  }

  const value = useMemo<StreamContextValue>(
    () => ({
      state,
      send: (config, sessionId, message) => {
        const local: ChatMessage = {
          id: `local-${Date.now()}`,
          role: 'user',
          content: message,
          created_at: new Date().toISOString()
        }

        appendLocalMessage(local)
        persistedRunRef.current = null
        updateState(initialStreamState())
        control.current = startStream(
          { config, sessionId, message, mode: 'chat' },
          {
            onEvent: (event) => {
              updateState((prev) => streamReducer(prev, event))
              if (event.type === 'message_stop') {
                persistAssistantSnapshot('done')
              }
            },
            onInterrupted: () => persistAssistantSnapshot('interrupted'),
            onError: () => persistAssistantSnapshot('error')
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
      }
    }),
    [appendLocalMessage, state]
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
