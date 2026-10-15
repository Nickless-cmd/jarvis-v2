import { useChatFlow } from '../../hooks/useChatFlow'
import type { ActiveChatFlowMode, ChatFlowState } from '../../lib/chatFlowApi'

const COOLDOWN_MS = 14 * 24 * 60 * 60 * 1000

export function suggestedChatFlowMode(
  state: ChatFlowState,
  now = Date.now(),
): ActiveChatFlowMode | null {
  if (!state.suggestions_enabled || state.preference === 'adaptive') return null

  let kind: ActiveChatFlowMode | null = null
  if (state.preference === 'living' && state.short_direct_runs >= 4 && state.calm_overrides >= 2) {
    kind = 'calm'
  } else if (
    state.preference === 'calm'
    && state.multi_step_runs >= 2
    && (state.work_expansions >= 2 || state.living_overrides >= 2)
  ) {
    kind = 'living'
  }
  if (!kind) return null

  const lastAt = state.last_suggestion_at ? Date.parse(state.last_suggestion_at) : Number.NaN
  if (Number.isFinite(lastAt) && now - lastAt < COOLDOWN_MS) return null
  if (state.last_suggestion_kind === kind && state.suggestion_rejections > 0) return null
  return kind
}

export function ChatFlowSuggestion({
  streaming,
  onboardingActive,
}: {
  streaming: boolean
  onboardingActive: boolean
}) {
  const flow = useChatFlow()
  if (streaming || onboardingActive || !flow.state.onboarding_seen) return null
  const kind = suggestedChatFlowMode(flow.state)
  if (!kind) return null

  const proposed = kind === 'calm' ? 'Rolig' : 'Levende'
  const current = flow.state.preference === 'calm' ? 'Rolig' : 'Levende'

  const accept = async () => {
    await flow.recordSuggestionOutcome({ kind, outcome: 'accepted' })
    await flow.setPreference(kind)
  }
  const reject = () => flow.recordSuggestionOutcome({ kind, outcome: 'rejected' })
  const adaptive = async () => {
    await flow.recordSuggestionOutcome({ kind, outcome: 'accepted' })
    await flow.setPreference('adaptive')
  }
  const disable = async () => {
    await flow.recordSuggestionOutcome({ kind, outcome: 'dismissed' })
    await flow.setSuggestionsEnabled(false)
  }

  return (
    <section className="chat-flow-suggestion" role="group" aria-label="Forslag til Chat Mode">
      <p>Du ser ofte ud til at foretrække {proposed}. Skal Chat Mode skifte?</p>
      <div className="chat-flow-suggestion-actions">
        <button type="button" onClick={() => void accept()}>Skift til {proposed}</button>
        <button type="button" onClick={() => void reject()}>Behold {current}</button>
        <button type="button" onClick={() => void adaptive()}>Brug Adaptiv</button>
        <button type="button" onClick={() => void disable()}>Foreslå ikke igen</button>
      </div>
    </section>
  )
}
