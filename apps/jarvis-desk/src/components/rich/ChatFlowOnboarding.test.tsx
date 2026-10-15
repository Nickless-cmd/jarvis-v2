import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { ReactNode } from 'react'
import { ChatFlowContext, type ChatFlowContextValue } from '../../contexts/ChatFlowContext'
import { DEFAULT_CHAT_FLOW_STATE } from '../../lib/chatFlowApi'
import { deriveChatFlow } from '../../lib/chatFlowModel'
import { ChatFlowOnboarding } from './ChatFlowOnboarding'

function model(lines: string[]) {
  return deriveChatFlow({
    blocks: lines.map((summary, index) => ({
      type: 'tool_use_summary' as const, summary, preceding_tool_use_ids: [`t${index}`],
    })),
    finalAnswerStarted: false,
    status: 'working',
  })
}

describe('ChatFlowOnboarding', () => {
  let frames: FrameRequestCallback[]
  const claim = vi.fn()
  const acknowledge = vi.fn()
  const setPreference = vi.fn()

  beforeEach(() => {
    frames = []
    vi.stubGlobal('requestAnimationFrame', vi.fn((callback: FrameRequestCallback) => {
      frames.push(callback)
      return frames.length
    }))
    vi.stubGlobal('cancelAnimationFrame', vi.fn())
    claim.mockReset().mockResolvedValue({
      ...DEFAULT_CHAT_FLOW_STATE, claimed: true, claim_id: 'claim-1', run_id: 'run-1',
    })
    acknowledge.mockReset().mockResolvedValue(undefined)
    setPreference.mockReset().mockResolvedValue(undefined)
  })

  afterEach(() => vi.unstubAllGlobals())

  function wrapper(children: ReactNode): ReactNode {
    const value: ChatFlowContextValue = {
      state: DEFAULT_CHAT_FLOW_STATE,
      activeModeForRun: () => 'living',
      setPreference,
      setSuggestionsEnabled: vi.fn(),
      claimOnboarding: claim,
      acknowledgeOnboarding: acknowledge,
      recordObservation: vi.fn(),
      recordSuggestionOutcome: vi.fn(),
    }
    return <ChatFlowContext.Provider value={value}>{children}</ChatFlowContext.Provider>
  }

  it('claims once and acknowledges only after the live comparison has painted', async () => {
    render(wrapper(<ChatFlowOnboarding runId="run-1" streaming model={model(['Et', 'To', 'Tre'])} />))
    expect(await screen.findByRole('group', { name: 'Vælg Chat Mode-visning' })).toBeInTheDocument()
    expect(claim).toHaveBeenCalledTimes(1)
    expect(claim).toHaveBeenCalledWith('run-1')
    expect(acknowledge).not.toHaveBeenCalled()

    // Vent paa at komponenten HAR bedt om en frame. `findByRole` ovenfor kan
    // returnere i det oejeblik gruppen er i DOM — altsaa foer effekten der
    // registrerer rAF'en har koert. `frames.shift()` gav da `undefined`,
    // `frame?.()` gjorde intet, og `acknowledge` blev aldrig kaldt (maalt
    // 15/10-2026: 1 af 5 koersler fejlede i CI og lokalt).
    await waitFor(() => expect(frames.length).toBeGreaterThan(0))
    const frame = frames.shift()
    frame?.(performance.now())
    await waitFor(() => expect(acknowledge).toHaveBeenCalledWith('claim-1'))
  })

  it('shows Living and Calm as live projections of the same changing model', async () => {
    const view = render(wrapper(<ChatFlowOnboarding runId="run-1" streaming model={model(['Et', 'To'])} />))
    const group = await screen.findByRole('group', { name: 'Vælg Chat Mode-visning' })
    const living = within(group).getByTestId('onboarding-living')
    const calm = within(group).getByTestId('onboarding-calm')
    expect(within(living).getByText('Et')).toBeInTheDocument()
    expect(within(living).getByText('To')).toBeInTheDocument()
    expect(within(calm).queryByText('Et')).not.toBeInTheDocument()
    expect(within(calm).getByText('To')).toBeInTheDocument()

    view.rerender(wrapper(<ChatFlowOnboarding runId="run-1" streaming model={model(['Et', 'To', 'Tre'])} />))
    expect(within(screen.getByTestId('onboarding-living')).getByText('Tre')).toBeInTheDocument()
    expect(within(screen.getByTestId('onboarding-calm')).getByText('Tre')).toBeInTheDocument()
    expect(screen.getAllByText('Tre')).toHaveLength(2)
    expect(claim).toHaveBeenCalledTimes(1)
  })

  it('labels illustrative material as Eksempel when the run has too little activity', async () => {
    render(wrapper(<ChatFlowOnboarding runId="run-1" streaming model={model([])} />))
    await screen.findByRole('group', { name: 'Vælg Chat Mode-visning' })
    expect(screen.getAllByText('Eksempel')).toHaveLength(2)
  })

  it('supports keyboard selection while ignoring the selector keeps Living implicit', async () => {
    const user = userEvent.setup()
    render(wrapper(<ChatFlowOnboarding runId="run-1" streaming model={model(['Et', 'To'])} />))
    const calm = await screen.findByRole('button', { name: 'Vælg rolig' })
    calm.focus()
    await user.keyboard('{Enter}')
    expect(setPreference).toHaveBeenCalledWith('calm')

    expect(DEFAULT_CHAT_FLOW_STATE.explicit_user_choice).toBe(false)
    expect(setPreference).toHaveBeenCalledTimes(1)
  })

  it('offers Adaptive as a keyboard-accessible choice', async () => {
    const user = userEvent.setup()
    render(wrapper(<ChatFlowOnboarding runId="run-1" streaming model={model(['Et', 'To'])} />))
    const adaptive = await screen.findByRole('button', { name: 'Tilpas automatisk' })
    adaptive.focus()
    await user.keyboard(' ')
    expect(setPreference).toHaveBeenCalledWith('adaptive')
  })

  it('does not block the answer surface when the claim fails', async () => {
    claim.mockRejectedValue(new Error('offline'))
    render(wrapper(<><ChatFlowOnboarding runId="run-1" streaming model={model(['Et'])} />
      <p>Det levende svar fortsætter.</p></>))
    expect(screen.getByText('Det levende svar fortsætter.')).toBeInTheDocument()
    await waitFor(() => expect(claim).toHaveBeenCalledTimes(1))
    expect(screen.queryByRole('group', { name: 'Vælg Chat Mode-visning' })).not.toBeInTheDocument()
  })
})
