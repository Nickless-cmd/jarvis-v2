import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ToolCard } from './ToolCard'
import { paaAendringsFokus } from '../../lib/aendringsFokus'

/**
 * Claude Desktop §9 (19/9-2026): «Click a filename on an Edited or Wrote row
 * to open that file in the diff pane». Og: et udfoldet edit_file-kort viste
 * aldrig sin diff — det læste old_string, værktøjet sender old_text.
 */
describe('ToolCard og Ændringer', () => {
  const edit = { type: 'tool_use' as const, id: 'e1', name: 'edit_file', status: 'done' as const,
    input: { path: '/repo/core/login.py', old_text: 'return None', new_text: 'return bruger' } }

  it('et udfoldet edit_file-kort viser diff\'en fra old_text/new_text', () => {
    const { container } = render(<ToolCard block={edit} density="compact" aabenFraStart />)
    expect(container.textContent).toContain('return None')
    expect(container.textContent).toContain('return bruger')
    expect(container.querySelector('.toolcard-result')).toBeNull()
  })

  it('knappen åbner filen i Ændringer', () => {
    const set: string[] = []
    const af = paaAendringsFokus((s) => set.push(s))
    render(<ToolCard block={edit} density="compact" />)
    fireEvent.click(screen.getByRole('button', { name: 'Vis /repo/core/login.py i Ændringer' }))
    af()
    expect(set).toEqual(['/repo/core/login.py'])
  })

  it('også på et skrive-kald — men ikke på en læsning', () => {
    render(<ToolCard block={{ ...edit, id: 'w1', name: 'write_file', input: { path: '/a.md', content: 'x' } }} density="compact" />)
    expect(screen.getByRole('button', { name: 'Vis /a.md i Ændringer' })).toBeInTheDocument()
    render(<ToolCard block={{ ...edit, id: 'r1', name: 'read_file', input: { path: '/b.md' } }} density="compact" />)
    expect(screen.queryByRole('button', { name: 'Vis /b.md i Ændringer' })).toBeNull()
  })
})
