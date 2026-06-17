import { createContext, useContext, useMemo, useRef, useState, type ReactNode } from 'react'
import { cancelRun } from '../lib/apiClient'
import { startStream, type StreamControl } from '../lib/streamClient'
import { initialStreamState, streamReducer, type StreamState } from '../lib/streamReducer'
import type { ApiConfig, ChatMessage } from '../lib/types'
import { useSessions } from './SessionContext'

interface StreamContextValue {
  state: StreamState
  send: (config: ApiConfig, sessionId: string, message: string) => void
  stop: (config: ApiConfig) => Promise<void>
}

const StreamContext = createContext<StreamContextValue | null>(null)

export function StreamProvider({ children }: { children: ReactNode }) {
  const { appendLocalMessage } = useSessions()
  const [state, setState] = useState(initialStreamState())
  const control = useRef<StreamControl | null>(null)

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
        setState(initialStreamState())
        control.current = startStream(
          { config, sessionId, message, mode: 'chat' },
          {
            onEvent: (event) => setState((prev) => streamReducer(prev, event)),
            onInterrupted: () => setState((prev) => ({ ...prev, status: 'interrupted' })),
            onError: () => setState((prev) => ({ ...prev, status: 'error' }))
          }
        )
      },
      stop: async (config) => {
        const runId = control.current?.getRunId() ?? state.activeRunId
        control.current?.abort()
        if (runId) {
          await cancelRun(config, runId)
        }
        setState((prev) => ({ ...prev, status: 'interrupted' }))
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
