import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { CodePanel } from './CodePanel'

vi.mock('../../lib/api', () => ({
  getTree: vi.fn().mockResolvedValue([{ name: 'x.py', kind: 'file' }]),
  getFile: vi.fn().mockResolvedValue({ path: 'core/x.py', content: 'print(1)', language: 'python' }),
  writeFile: vi.fn().mockResolvedValue({ status: 'ok', path: 'core/x.py' }),
  openExternal: vi.fn().mockResolvedValue({ status: 'ok', path: '/x' }),
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

  it('viser terminal-fanen for container (server-side exec) og skifter ved klik', async () => {
    // Container-default cwd er tom → backend bruger repo-roden (named roots gør
    // root-navnet 'repo' uegnet som cwd; "Åbn i terminal" sætter en konkret mappe).
    render(<CodePanel config={cfg} kind="container" root="repo" />)
    const tab = screen.getByText('Terminal')
    expect(tab).toBeInTheDocument()
    fireEvent.click(tab)
    expect(await screen.findByTestId('terminal-pane')).toHaveTextContent('term:')
  })

  it('viser terminal-fanen for workstation og skifter til den ved klik', async () => {
    render(<CodePanel config={cfg} kind="workstation" root="/home/bs/proj" />)
    const tab = screen.getByText('Terminal')
    expect(tab).toBeInTheDocument()
    fireEvent.click(tab)
    expect(await screen.findByTestId('terminal-pane')).toHaveTextContent('term:/home/bs/proj')
  })

  it('højreklik på fil giver editor/terminal-menu; editor åbner redigerbar visning', async () => {
    render(<CodePanel config={cfg} kind="container" root="repo" />)
    fireEvent.contextMenu(await screen.findByText('x.py'))
    expect(screen.getByText('Åbn i editor')).toBeInTheDocument()
    expect(screen.getByText('Åbn i terminal')).toBeInTheDocument()
    fireEvent.click(screen.getByText('Åbn i editor'))
    // Editoren loader filens indhold i en textarea + viser Gem.
    expect(await screen.findByDisplayValue('print(1)')).toBeInTheDocument()
    expect(screen.getByTitle('Gem')).toBeInTheDocument()
  })

  it('Jarvis-highlight åbner filen i preview', async () => {
    render(<CodePanel config={cfg} kind="container" root="repo" highlightPath="x.py" />)
    expect(await screen.findByText(/print\(1\)/)).toBeInTheDocument()
  })
})
