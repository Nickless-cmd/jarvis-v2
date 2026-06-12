import { describe, it, expect, vi } from 'vitest'
import type { ReactNode } from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import { CodeView } from './CodeView'
import { StreamProvider } from '../contexts/StreamContext'
import { SettingsProvider } from '../contexts/SettingsContext'
import { PanelProvider } from '../contexts/PanelContext'

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

function wrap(ui: ReactNode) {
  return render(
    <SettingsProvider initialConfig={cfg}>
      <StreamProvider config={cfg}>
        <PanelProvider defaultWidth={400}>{ui}</PanelProvider>
      </StreamProvider>
    </SettingsProvider>,
  )
}

describe('CodeView', () => {
  it('aktiv samtale: composer + workspace-vælger; fil-træ foldet ind, åbnes via Filer-knap', async () => {
    wrap(<CodeView sessionId="s1" />)
    expect(await screen.findByRole('textbox')).toBeInTheDocument()
    expect(screen.getByRole('combobox')).toBeInTheDocument()
    // Fil-træet er foldet ind fra start → x.py ikke synlig endnu
    expect(screen.queryByText('x.py')).not.toBeInTheDocument()
    fireEvent.click(screen.getByLabelText('Vis/skjul fil-træ'))
    expect(await screen.findByText('x.py')).toBeInTheDocument()
  })

  it('tom samtale: centreret hej-hilsen med brugernavn', () => {
    wrap(<CodeView sessionId={null} userName="Bjørn" />)
    expect(screen.getByText('Hej Bjørn.')).toBeInTheDocument()
  })
})
