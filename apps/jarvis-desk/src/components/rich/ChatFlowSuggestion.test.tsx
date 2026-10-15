import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { ReactNode } from 'react'
import { ChatFlowContext, type ChatFlowContextValue } from '../../contexts/ChatFlowContext'
import { DEFAULT_CHAT_FLOW_STATE, type ChatFlowState } from '../../lib/chatFlowApi'
import { ChatFlowSuggestion } from './ChatFlowSuggestion'

describe('ChatFlowSuggestion', () => {
  const setPreference = vi.fn()
  const setSuggestionsEnabled = vi.fn()
  const recordOutcome = vi.fn()

  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    vi.setSystemTime(new Date('2026-10-15T12:00:00Z'))
    setPreference.mockReset().mockResolvedValue(undefined)
    setSuggestionsEnabled.mockReset().mockResolvedValue(undefined)
    recordOutcome.mockReset().mockResolvedValue(undefined)
  })

  afterEach(() => vi.useRealTimers())

  function wrapped(state: ChatFlowState, children: ReactNode): ReactNode {
    const value: ChatFlowContextValue = {
      state,
      activeModeForRun: () => state.preference === 'calm' ? 'calm' : 'living',
      setPreference,
      setSuggestionsEnabled,
      claimOnboarding: vi.fn(),
      acknowledgeOnboarding: vi.fn(),
      recordObservation: vi.fn(),
      recordSuggestionOutcome: recordOutcome,
    }
    return <ChatFlowContext.Provider value={value}>{children}</ChatFlowContext.Provider>
  }

  const suggestCalm: ChatFlowState = {
    ...DEFAULT_CHAT_FLOW_STATE,
    onboarding_seen: true,
    preference: 'living',
    short_direct_runs: 8,
    calm_overrides: 2,
  }

  it('is absent during streaming and onboarding', () => {
    const view = render(wrapped(suggestCalm, <ChatFlowSuggestion streaming onboardingActive={false} />))
    expect(screen.queryByRole('group', { name: 'Forslag til Chat Mode' })).not.toBeInTheDocument()
    view.rerender(wrapped({ ...suggestCalm, onboarding_seen: false },
      <ChatFlowSuggestion streaming={false} onboardingActive />))
    expect(screen.queryByRole('group', { name: 'Forslag til Chat Mode' })).not.toBeInTheDocument()
  })

  it('requires repeated behavior, respects cooldown, and suppresses a rejected direction', () => {
    const view = render(wrapped({ ...suggestCalm, calm_overrides: 0 },
      <ChatFlowSuggestion streaming={false} onboardingActive={false} />))
    expect(screen.queryByRole('group', { name: 'Forslag til Chat Mode' })).not.toBeInTheDocument()

    view.rerender(wrapped({ ...suggestCalm, last_suggestion_at: '2026-10-10T12:00:00Z' },
      <ChatFlowSuggestion streaming={false} onboardingActive={false} />))
    expect(screen.queryByRole('group', { name: 'Forslag til Chat Mode' })).not.toBeInTheDocument()

    view.rerender(wrapped({ ...suggestCalm, last_suggestion_kind: 'calm',
      last_suggestion_at: '2026-09-01T12:00:00Z', suggestion_rejections: 1 },
      <ChatFlowSuggestion streaming={false} onboardingActive={false} />))
    expect(screen.queryByRole('group', { name: 'Forslag til Chat Mode' })).not.toBeInTheDocument()
  })

  it('offers Calm after the cooldown and persists accept, reject, Adaptive, and disable actions', async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    const view = render(wrapped({ ...suggestCalm, last_suggestion_at: '2026-09-01T12:00:00Z' },
      <ChatFlowSuggestion streaming={false} onboardingActive={false} />))
    const group = screen.getByRole('group', { name: 'Forslag til Chat Mode' })
    expect(group).toHaveTextContent('Rolig')

    await user.click(screen.getByRole('button', { name: 'Skift til Rolig' }))
    expect(recordOutcome).toHaveBeenCalledWith({ kind: 'calm', outcome: 'accepted' })
    expect(setPreference).toHaveBeenCalledWith('calm')

    await user.click(screen.getByRole('button', { name: 'Behold Levende' }))
    expect(recordOutcome).toHaveBeenCalledWith({ kind: 'calm', outcome: 'rejected' })

    await user.click(screen.getByRole('button', { name: 'Brug Adaptiv' }))
    expect(setPreference).toHaveBeenCalledWith('adaptive')

    await user.click(screen.getByRole('button', { name: 'Foreslå ikke igen' }))
    expect(recordOutcome).toHaveBeenCalledWith({ kind: 'calm', outcome: 'dismissed' })
    expect(setSuggestionsEnabled).toHaveBeenCalledWith(false)

    view.rerender(wrapped({ ...suggestCalm, suggestions_enabled: false },
      <ChatFlowSuggestion streaming={false} onboardingActive={false} />))
    expect(screen.queryByRole('group', { name: 'Forslag til Chat Mode' })).not.toBeInTheDocument()
  })

  it('can suggest Living after repeated work expansion and never steals focus', () => {
    const state: ChatFlowState = {
      ...suggestCalm,
      preference: 'calm',
      short_direct_runs: 0,
      calm_overrides: 0,
      multi_step_runs: 4,
      work_expansions: 2,
    }
    render(wrapped(state, <><button type="button">Behold fokus</button>
      <ChatFlowSuggestion streaming={false} onboardingActive={false} /></>))
    const focus = screen.getByRole('button', { name: 'Behold fokus' })
    focus.focus()
    expect(screen.getByRole('button', { name: 'Skift til Levende' })).toBeInTheDocument()
    expect(document.activeElement).toBe(focus)
  })
})
