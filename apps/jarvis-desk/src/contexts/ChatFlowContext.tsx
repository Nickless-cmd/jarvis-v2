import { createContext, useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import type { ApiConfig, WhoAmI } from '../lib/api'
import {
  DEFAULT_CHAT_FLOW_STATE,
  acknowledgeChatFlowOnboarding,
  claimChatFlowOnboarding,
  getChatFlowState,
  patchChatFlowState,
  recordChatFlowObservation,
  recordChatFlowSuggestionOutcome,
  type ActiveChatFlowMode,
  type ChatFlowPreference,
  type ChatFlowState,
  type OnboardingClaim,
} from '../lib/chatFlowApi'
import { chooseAdaptiveMode } from '../lib/chatFlowModel'

export interface ChatFlowContextValue {
  state: ChatFlowState
  activeModeForRun: (runId: string) => ActiveChatFlowMode
  setPreference: (preference: ChatFlowPreference) => Promise<void>
  setSuggestionsEnabled: (enabled: boolean) => Promise<void>
  claimOnboarding: (runId: string) => Promise<OnboardingClaim>
  acknowledgeOnboarding: (claimId: string) => Promise<void>
  recordObservation: (input: { meaningful_steps: number; expanded_work: boolean; manual_override?: ActiveChatFlowMode }) => Promise<void>
  recordSuggestionOutcome: (input: { kind: ActiveChatFlowMode; outcome: 'accepted' | 'rejected' | 'dismissed' }) => Promise<void>
}

const FALLBACK: ChatFlowContextValue = {
  state: DEFAULT_CHAT_FLOW_STATE,
  activeModeForRun: () => 'living',
  setPreference: async () => undefined,
  setSuggestionsEnabled: async () => undefined,
  claimOnboarding: async () => ({ ...DEFAULT_CHAT_FLOW_STATE, claimed: false, claim_id: null }),
  acknowledgeOnboarding: async () => undefined,
  recordObservation: async () => undefined,
  recordSuggestionOutcome: async () => undefined,
}

export const ChatFlowContext = createContext<ChatFlowContextValue>(FALLBACK)

function identityKey(identity: WhoAmI): string {
  return identity.user_id || (identity.role === 'owner' ? 'native-owner' : '')
}

function cacheKey(key: string): string { return `jarvis-desk:chat-flow:${key}` }

function readCached(key: string): ChatFlowState {
  if (!key) return DEFAULT_CHAT_FLOW_STATE
  try {
    const parsed = JSON.parse(localStorage.getItem(cacheKey(key)) || 'null') as ChatFlowState | null
    return parsed?.preference ? { ...DEFAULT_CHAT_FLOW_STATE, ...parsed } : DEFAULT_CHAT_FLOW_STATE
  } catch { return DEFAULT_CHAT_FLOW_STATE }
}

export function ChatFlowProvider({ config, identity, children }: {
  config: ApiConfig
  identity: WhoAmI
  children: ReactNode
}) {
  const key = identityKey(identity)
  const [state, setState] = useState<ChatFlowState>(() => readCached(key))
  const keyRef = useRef(key)
  keyRef.current = key
  const modes = useRef(new Map<string, ActiveChatFlowMode>())

  const accept = useCallback((owner: string, next: ChatFlowState) => {
    if (!owner || keyRef.current !== owner) return false
    setState(next)
    try { localStorage.setItem(cacheKey(owner), JSON.stringify(next)) } catch { /* cache is optional */ }
    return true
  }, [])

  useEffect(() => {
    setState(readCached(key))
    modes.current.clear()
    if (!key) return
    let alive = true
    void getChatFlowState(config).then((next) => {
      if (alive) accept(key, next)
    }).catch(() => { /* Living/cached state remains usable offline. */ })
    const storage = (event: StorageEvent) => {
      if (event.key !== cacheKey(key) || !event.newValue) return
      try { accept(key, JSON.parse(event.newValue) as ChatFlowState) } catch { /* ignore corrupt cache */ }
    }
    window.addEventListener('storage', storage)
    return () => { alive = false; window.removeEventListener('storage', storage) }
  }, [accept, config, key])

  const mutate = useCallback(async (body: { preference?: ChatFlowPreference; suggestions_enabled?: boolean }) => {
    const owner = keyRef.current
    try {
      const next = await patchChatFlowState(config, body)
      accept(owner, next)
    } catch {
      // Keep the last confirmed state. Chat presentation must remain usable offline.
    }
  }, [accept, config])

  const value = useMemo<ChatFlowContextValue>(() => ({
    state,
    activeModeForRun: (runId) => {
      const existing = modes.current.get(runId)
      if (existing) return existing
      const chosen = state.preference === 'calm'
        ? 'calm'
        : state.preference === 'adaptive'
          ? chooseAdaptiveMode({
              shortDirectRuns: state.short_direct_runs,
              multiStepRuns: state.multi_step_runs,
              workExpansions: state.work_expansions,
              livingOverrides: state.living_overrides,
              calmOverrides: state.calm_overrides,
            })
          : 'living'
      modes.current.set(runId, chosen)
      return chosen
    },
    setPreference: (preference) => mutate({ preference }),
    setSuggestionsEnabled: (enabled) => mutate({ suggestions_enabled: enabled }),
    claimOnboarding: (runId) => claimChatFlowOnboarding(config, runId),
    acknowledgeOnboarding: async (claimId) => {
      const owner = keyRef.current
      accept(owner, await acknowledgeChatFlowOnboarding(config, claimId))
    },
    recordObservation: async (input) => {
      const owner = keyRef.current
      accept(owner, await recordChatFlowObservation(config, input))
    },
    recordSuggestionOutcome: async (input) => {
      const owner = keyRef.current
      accept(owner, await recordChatFlowSuggestionOutcome(config, input))
    },
  }), [accept, config, mutate, state])

  return <ChatFlowContext.Provider value={value}>{children}</ChatFlowContext.Provider>
}
