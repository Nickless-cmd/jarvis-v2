import { beforeEach, describe, it, expect, vi } from 'vitest'
import type { ReactNode } from 'react'
import { render, screen, fireEvent, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { CodeView } from './CodeView'
import { StreamProvider } from '../contexts/StreamContext'
import { SettingsProvider } from '../contexts/SettingsContext'
import { SessionProvider } from '../contexts/SessionContext'
import { PanelProvider } from '../contexts/PanelContext'
import { PermissionProvider } from '../contexts/PermissionContext'

interface FakeHandlers {
  onEvent: (e: unknown) => void
  onRunId: (id: string) => void
}
const handlersRef: { current: FakeHandlers | null } = { current: null }

vi.mock('../lib/streamClient', () => ({
  startStream: (_r: unknown, h: FakeHandlers) => { handlersRef.current = h; return { abort: vi.fn(), getRunId: () => 'r1' } },
  StreamError: class extends Error {},
}))
vi.mock('../lib/api', () => ({
  listSessions: vi.fn().mockResolvedValue([]),
  getSession: vi.fn().mockResolvedValue({ session: { id: 's1', title: 'T' }, messages: [] }),
  createSession: vi.fn(),
  cancelRun: vi.fn(),
  whoami: vi.fn().mockResolvedValue({ user_id: 'u', display_name: 'Bjørn', role: 'owner' }),
  pingServer: vi.fn().mockResolvedValue(20),
  getVisibleProviders: vi.fn().mockResolvedValue([]),
  getTree: vi.fn().mockResolvedValue([{ name: 'x.py', kind: 'file' }]),
  getFile: vi.fn().mockResolvedValue({ path: 'core/x.py', content: 'print(1)', language: 'python' }),
  getWorkspaceTrust: vi.fn().mockResolvedValue(true),
  setWorkspaceTrust: vi.fn().mockResolvedValue(true),
  getContextInfo: vi.fn().mockResolvedValue({ compact_at: 200000, run_compact_at: 240000 }),
  getModelContext: vi.fn().mockResolvedValue({ window: 1000000, compact_at: 200000, effective: 200000 }),
  getContextUsage: vi.fn().mockResolvedValue({ tokens: 0, compact_at: 130000, effective: 130000, compacting: false, compacted: false }),
  getActiveRuns: vi.fn().mockResolvedValue([]),
  followRun: vi.fn(() => ({ abort: vi.fn() })),
  warmSession: vi.fn().mockResolvedValue(undefined),
  getGitStatus: vi.fn().mockResolvedValue({ branch: 'main', dirty: 0, added: 0, removed: 0, is_git: true }),
}))

const cfg = { apiBaseUrl: 'http://t', authToken: 't' }

function wrap(ui: ReactNode) {
  return render(
    <SettingsProvider initialConfig={cfg}>
      <SessionProvider config={cfg}>
        <StreamProvider config={cfg}>
          <PermissionProvider>
            <PanelProvider defaultWidth={400}>{ui}</PanelProvider>
          </PermissionProvider>
        </StreamProvider>
      </SessionProvider>
    </SettingsProvider>,
  )
}

describe('CodeView', () => {
  beforeEach(() => {
    localStorage.clear()
    handlersRef.current = null
  })

  it('tom samtale: greeting m. brugernavn + composer', () => {
    wrap(<CodeView sessionId={null} userName="Bjørn" />)
    // Greeting via GreetingHero (tids-bevidst hilsen) — navnet skal fremgå.
    expect(screen.getAllByText(/Bjørn/).length).toBeGreaterThan(0)
    // composer + workspace-vælger til stede
    expect(screen.getByRole('textbox')).toBeInTheDocument()
  })

  it('owner ser Server-valg; member ser Mit workspace', () => {
    const { unmount } = wrap(<CodeView sessionId={null} userName="B" role="owner" />)
    expect(screen.getByText('Server')).toBeInTheDocument()
    unmount()
    wrap(<CodeView sessionId={null} userName="M" role="member" />)
    expect(screen.getByText('Mit workspace')).toBeInTheDocument()
  })

  it('workstation-knap viser mappe-vælger', () => {
    wrap(<CodeView sessionId={null} userName="B" role="owner" />)
    fireEvent.click(screen.getByText('Min computer'))
    expect(screen.getByText('Vælg mappe…')).toBeInTheDocument()
  })

  it('viser pause_and_ask sammen med approvals over Code-transcriptet', async () => {
    const { container } = wrap(<CodeView sessionId="s1" userName="B" role="owner" />)
    await userEvent.type(screen.getByRole('textbox'), 'fortsæt{Enter}')
    const result = JSON.stringify({
      kind: 'pause_and_ask',
      question: 'Hvilken fil skal jeg rette?',
      options: ['A', 'B'],
    })
    act(() => {
      handlersRef.current?.onRunId('r1')
      handlersRef.current?.onEvent({ type: 'message_start', message: { id: 'r1', model: 'm', provider: 'p', lane: 'l', session_id: 's1', usage: { input_tokens: 0, output_tokens: 0 } } })
      handlersRef.current?.onEvent({ type: 'content_block_start', index: 0, content_block: { type: 'tool_use', id: 'ask-1', name: 'pause_and_ask', input: {} } })
      handlersRef.current?.onEvent({ type: 'content_block_start', index: 1, content_block: { type: 'tool_result', tool_use_id: 'ask-1', status: 'done', content: result } })
    })

    expect(container.querySelector('.composer-notices .pauseask')).toBeInTheDocument()
    expect(container.querySelector('.transcript .pauseask')).not.toBeInTheDocument()
  })
})
