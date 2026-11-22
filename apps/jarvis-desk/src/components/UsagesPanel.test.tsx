import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { UsagesPanel } from './UsagesPanel'
import { visning } from './AgentPanel'
import type { ToolEvidence } from '../lib/environmentEvidence'

const tool = (result: string): ToolEvidence => ({
  id: 't1', name: 'find_usages', input: { name: 'foo' }, status: 'done', result,
})

describe('UsagesPanel', () => {
  it('renderer hits og åbner filen ved klik', () => {
    const onOpenFile = vi.fn()
    const result = JSON.stringify({
      status: 'ok', name: 'foo', backend: 'lsp', count: 1, truncated: false,
      hits: [{ file: 'a/b.py', line: 7, snippet: 'foo()', enclosing: 'bar' }],
    })
    render(<UsagesPanel tools={[tool(result)]} onOpenFile={onOpenFile} onClose={() => {}} />)
    fireEvent.click(screen.getByText('a/b.py:7'))
    expect(onOpenFile).toHaveBeenCalledWith('a/b.py', 7)
  })
  it('viser værktøjsfejl åbent', () => {
    render(<UsagesPanel tools={[tool('{"status":"error","error":"ingen LSP"}')]} onOpenFile={() => {}} onClose={() => {}} />)
    expect(screen.getByText('ingen LSP')).toBeTruthy()
  })
})

describe('agent-status', () => {
  it('mapper til de fire tilstande og lader ukendt være ukendt', () => {
    expect(visning('running')).toBe('active')
    expect(visning('planned')).toBe('queued')
    expect(visning('completed')).toBe('done')
    expect(visning('cancelled')).toBe('failed')
    expect(visning('mystisk')).toBeNull()
  })
})
