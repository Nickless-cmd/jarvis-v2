import { apiFetch, type ApiConfig } from './api'

export type ChatFlowPreference = 'living' | 'calm' | 'adaptive'
export type ActiveChatFlowMode = 'living' | 'calm'

export interface ChatFlowState {
  preference: ChatFlowPreference
  onboarding_seen: boolean
  explicit_user_choice: boolean
  suggestions_enabled: boolean
  last_suggestion_kind: ActiveChatFlowMode | null
  last_suggestion_at: string | null
  suggestion_rejections: number
  short_direct_runs: number
  multi_step_runs: number
  work_expansions: number
  living_overrides: number
  calm_overrides: number
  updated_at: string
}

export interface OnboardingClaim extends ChatFlowState {
  claimed: boolean
  claim_id: string | null
  run_id?: string
}

export const DEFAULT_CHAT_FLOW_STATE: ChatFlowState = {
  preference: 'living', onboarding_seen: false, explicit_user_choice: false,
  suggestions_enabled: true, last_suggestion_kind: null, last_suggestion_at: null,
  suggestion_rejections: 0, short_direct_runs: 0, multi_step_runs: 0,
  work_expansions: 0, living_overrides: 0, calm_overrides: 0, updated_at: '',
}

export function getChatFlowState(config: ApiConfig): Promise<ChatFlowState> {
  return apiFetch(config, '/api/chat-flow/preferences')
}

export function patchChatFlowState(
  config: ApiConfig,
  body: { preference?: ChatFlowPreference; suggestions_enabled?: boolean },
): Promise<ChatFlowState> {
  return apiFetch(config, '/api/chat-flow/preferences', { method: 'PATCH', body })
}

export function claimChatFlowOnboarding(config: ApiConfig, runId: string): Promise<OnboardingClaim> {
  return apiFetch(config, '/api/chat-flow/onboarding/claim', { method: 'POST', body: { run_id: runId } })
}

export function acknowledgeChatFlowOnboarding(
  config: ApiConfig, claimId: string,
): Promise<ChatFlowState> {
  return apiFetch(config, '/api/chat-flow/onboarding/ack', { method: 'POST', body: { claim_id: claimId } })
}

export function recordChatFlowObservation(
  config: ApiConfig,
  body: { meaningful_steps: number; expanded_work: boolean; manual_override?: ActiveChatFlowMode },
): Promise<ChatFlowState> {
  return apiFetch(config, '/api/chat-flow/observations', { method: 'POST', body })
}

export function recordChatFlowSuggestionOutcome(
  config: ApiConfig,
  body: { kind: ActiveChatFlowMode; outcome: 'accepted' | 'rejected' | 'dismissed' },
): Promise<ChatFlowState> {
  return apiFetch(config, '/api/chat-flow/suggestions/outcome', { method: 'POST', body })
}
