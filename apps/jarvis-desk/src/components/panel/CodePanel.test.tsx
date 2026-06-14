import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { CodePanel } from './CodePanel'

vi.mock('../../lib/api', () => ({
  getTree: vi.fn().mockResolvedValue([{ name: 'x.py', kind: 'file' }]),
  getFile: vi.fn().mockResolvedValue({ path: 'core/x.py', content: 'print(1)', language: 'python' }),
}))
// Stub TerminalPane — xterm rører DOM/canvas som jsdom ikke understøtter.
vi.mock('./TerminalPane', () => ({
  TerminalPane: ({ cwd }: { cwd: string }) => <div data-testid="terminal-pane">term:{cwd}</div>,
}))

const cfg = { apiBaseUrl: 'http://t', authToken: 't' }

describe('CodePanel', () => {
  it('åbner en fil i visningen ved klik i træet', async () => {
    render(<CodePanel config={cfg} kind="container" root="core" />)
    fireEvent.click(await screen.findByText('x.py'))
    expect(await screen.findByText(/print\(1\)/)).toBeInTheDocument()
  })

  it('viser IKKE terminal-fanen for container-workspace (kun lokal exec)', () => {
    render(<CodePanel config={cfg} kind="container" root="core" />)
    expect(screen.queryByText('Terminal')).not.toBeInTheDocument()
  })

  it('viser terminal-fanen for workstation og skifter til den ved klik', async () => {
    render(<CodePanel config={cfg} kind="workstation" root="/home/bs/proj" />)
    const tab = screen.getByText('Terminal')
    expect(tab).toBeInTheDocument()
    fireEvent.click(tab)
    expect(await screen.findByTestId('terminal-pane')).toHaveTextContent('term:/home/bs/proj')
  })
})
