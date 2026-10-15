import { render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { ReactNode } from 'react'
import { ChatFlowProvider } from './ChatFlowContext'
import { useChatFlow } from '../hooks/useChatFlow'
import type { ChatFlowState } from '../lib/chatFlowApi'

const getState = vi.fn()
const patchState = vi.fn()

vi.mock('../lib/chatFlowApi', async () => {
  const actual = await vi.importActual<typeof import('../lib/chatFlowApi')>('../lib/chatFlowApi')
  return {
    ...actual,
    getChatFlowState: (...args: unknown[]) => getState(...args),
    patchChatFlowState: (...args: unknown[]) => patchState(...args),
  }
})

const living: ChatFlowState = {
  preference: 'living', onboarding_seen: false, explicit_user_choice: false,
  suggestions_enabled: true, last_suggestion_kind: null, last_suggestion_at: null,
  suggestion_rejections: 0, short_direct_runs: 0, multi_step_runs: 0,
  work_expansions: 0, living_overrides: 0, calm_overrides: 0,
  updated_at: '2026-10-15T10:00:00Z',
}
const calm: ChatFlowState = { ...living, preference: 'calm', updated_at: '2026-10-15T11:00:00Z' }
const config = { apiBaseUrl: 'https://jarvis.test', authToken: 'token' }

function Probe() {
  const flow = useChatFlow()
  return <><span data-testid="preference">{flow.state.preference}</span><button onClick={() => void flow.setPreference('calm')}>rolig</button></>
}

function AdaptiveProbe() {
  const flow = useChatFlow()
  const mode = flow.state.updated_at ? flow.activeModeForRun('stable-run') : 'loading'
  return <><span data-testid="active-mode">{mode}</span>
    <button onClick={() => void flow.setPreference('living')}>levende</button></>
}

function provider(userId: string, children: ReactNode = <Probe />) {
  return <ChatFlowProvider config={config} identity={{ user_id: userId, display_name: userId, role: 'member' }}>{children}</ChatFlowProvider>
}

describe('ChatFlowProvider', () => {
  beforeEach(() => {
    localStorage.clear()
    getState.mockReset().mockResolvedValue(living)
    patchState.mockReset().mockResolvedValue(calm)
  })
  afterEach(() => vi.restoreAllMocks())

  it('hydrates from the authenticated server state', async () => {
    getState.mockResolvedValue(calm)
    render(provider('user-a'))
    await waitFor(() => expect(screen.getByTestId('preference')).toHaveTextContent('calm'))
  })

  it('does not apply a late response from the previous account', async () => {
    let resolveFirst!: (state: ChatFlowState) => void
    const first = new Promise<ChatFlowState>((resolve) => { resolveFirst = resolve })
    getState.mockReturnValueOnce(first).mockResolvedValueOnce(calm)
    const view = render(provider('user-a'))
    view.rerender(provider('user-b'))
    resolveFirst(living)
    await waitFor(() => expect(screen.getByTestId('preference')).toHaveTextContent('calm'))
    expect(localStorage.getItem('jarvis-desk:chat-flow:user-a')).toBeNull()
  })

  it('namespaces cached state by authenticated user', async () => {
    getState.mockResolvedValue(calm)
    render(provider('user-a'))
    await waitFor(() => expect(localStorage.getItem('jarvis-desk:chat-flow:user-a')).toContain('"calm"'))
    expect(localStorage.getItem('jarvis-desk:chat-flow:user-b')).toBeNull()
  })

  it('keeps the last confirmed state when persistence fails', async () => {
    patchState.mockRejectedValue(new Error('offline'))
    render(provider('user-a'))
    await waitFor(() => expect(getState).toHaveBeenCalled())
    screen.getByRole('button', { name: 'rolig' }).click()
    await waitFor(() => expect(patchState).toHaveBeenCalled())
    expect(screen.getByTestId('preference')).toHaveTextContent('living')
  })

  it('selects Adaptive from prior counters once and keeps the run stable', async () => {
    const adaptive = { ...living, preference: 'adaptive' as const, short_direct_runs: 6,
      multi_step_runs: 1, calm_overrides: 2 }
    getState.mockResolvedValue(adaptive)
    patchState.mockResolvedValue(living)
    render(provider('user-a', <AdaptiveProbe />))
    await waitFor(() => expect(screen.getByTestId('active-mode')).toHaveTextContent('calm'))
    screen.getByRole('button', { name: 'levende' }).click()
    await waitFor(() => expect(patchState).toHaveBeenCalled())
    expect(screen.getByTestId('active-mode')).toHaveTextContent('calm')
  })
})
