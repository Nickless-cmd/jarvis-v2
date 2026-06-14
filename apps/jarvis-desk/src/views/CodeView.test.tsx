import { describe, it, expect, vi } from 'vitest'
import type { ReactNode } from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import { CodeView } from './CodeView'
import { StreamProvider } from '../contexts/StreamContext'
import { SettingsProvider } from '../contexts/SettingsContext'
import { SessionProvider } from '../contexts/SessionContext'
import { PanelProvider } from '../contexts/PanelContext'

vi.mock('../lib/streamClient', () => ({
  startStream: () => ({ abort: vi.fn(), getRunId: () => 'r1' }),
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
  getGitStatus: vi.fn().mockResolvedValue({ branch: 'main', dirty: 0, added: 0, removed: 0, is_git: true }),
}))

const cfg = { apiBaseUrl: 'http://t', authToken: 't' }

function wrap(ui: ReactNode) {
  return render(
    <SettingsProvider initialConfig={cfg}>
      <SessionProvider config={cfg}>
        <StreamProvider config={cfg}>
          <PanelProvider defaultWidth={400}>{ui}</PanelProvider>
        </StreamProvider>
      </SessionProvider>
    </SettingsProvider>,
  )
}

describe('CodeView', () => {
  it('tom samtale: centreret hej-hilsen med brugernavn', () => {
    wrap(<CodeView sessionId={null} userName="Bjørn" />)
    expect(screen.getByText('Hej Bjørn.')).toBeInTheDocument()
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
})
