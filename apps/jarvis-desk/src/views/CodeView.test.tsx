import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { CodeView } from './CodeView'
import { StreamProvider } from '../contexts/StreamContext'
import { SettingsProvider } from '../contexts/SettingsContext'

vi.mock('../lib/streamClient', () => ({
  startStream: () => ({ abort: vi.fn(), getRunId: () => 'r1' }),
  StreamError: class extends Error {},
}))
vi.mock('../lib/api', () => ({
  cancelRun: vi.fn(),
  whoami: vi.fn().mockResolvedValue({ user_id: 'u', display_name: 'Bjørn', role: 'owner' }),
  pingServer: vi.fn().mockResolvedValue(20),
  getTree: vi.fn().mockResolvedValue([{ name: 'x.py', kind: 'file' }]),
  getFile: vi.fn().mockResolvedValue({ path: 'core/x.py', content: 'print(1)', language: 'python' }),
}))

const cfg = { apiBaseUrl: 'http://t', authToken: 't' }

describe('CodeView', () => {
  it('renderer composer + workspace-vælger', async () => {
    render(
      <SettingsProvider initialConfig={cfg}>
        <StreamProvider config={cfg}>
          <CodeView sessionId="s1" />
        </StreamProvider>
      </SettingsProvider>,
    )
    expect(await screen.findByRole('textbox')).toBeInTheDocument()
    // workspace-vælger med 'core'-roden
    expect(screen.getByRole('combobox')).toBeInTheDocument()
    expect(await screen.findByText('x.py')).toBeInTheDocument()
  })
})
