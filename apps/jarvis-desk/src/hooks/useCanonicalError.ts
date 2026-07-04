import { useCallback, useReducer } from 'react'
import { parseCanonicalError, type CanonicalError } from '../lib/canonicalError'
import type { StreamError } from '../lib/streamClient'

const MAX_LOG = 50

export interface CanonicalErrorState {
  /** Nyeste-først log af kanoniske fejl (til transparens-panel). */
  log: CanonicalError[]
  /** Nyeste ukvitterede fejl (til ErrorCard), eller null. */
  current: CanonicalError | null
}

type Action =
  | { type: 'add'; error: CanonicalError }
  | { type: 'dismiss' }
  | { type: 'clear' }

function reducer(state: CanonicalErrorState, action: Action): CanonicalErrorState {
  switch (action.type) {
    case 'add':
      return { log: [action.error, ...state.log].slice(0, MAX_LOG), current: action.error }
    case 'dismiss':
      return { ...state, current: null }
    case 'clear':
      return { log: [], current: null }
    default:
      return state
  }
}

export function initialCanonicalErrorState(): CanonicalErrorState {
  return { log: [], current: null }
}

/**
 * Samler kanoniske fejl fra streamen (system_event kind='error') OG klient-side
 * StreamError i én log + 'current'. Rent lokalt.
 */
export function useCanonicalError() {
  const [state, dispatch] = useReducer(reducer, undefined, initialCanonicalErrorState)

  const addFromEventPayload = useCallback((payload: Record<string, unknown>) => {
    dispatch({ type: 'add', error: parseCanonicalError(payload, 'stream') })
  }, [])

  const addFromStreamError = useCallback((err: StreamError) => {
    const kind = typeof err.canonicalKind === 'function' ? err.canonicalKind() : err.kind
    dispatch({
      type: 'add',
      error: parseCanonicalError(
        {
          code: kind ?? err.category,
          kind,
          severity: err.category === 'network' ? 'warning' : 'error',
          message: err.userMessage(),
          retryable: err.retryable,
          correlation_id: '',
        },
        'client',
      ),
    })
  }, [])

  const dismiss = useCallback(() => dispatch({ type: 'dismiss' }), [])
  const clear = useCallback(() => dispatch({ type: 'clear' }), [])

  return {
    errors: state.log,
    current: state.current,
    addFromEventPayload,
    addFromStreamError,
    dismiss,
    clear,
  }
}
