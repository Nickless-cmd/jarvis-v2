import { describe, it, expect } from 'vitest'
import { groupReadSearch, type RenderBlock, type ToolGroupBlock } from './groupReadSearch'
import type { ContentBlock } from './sseProtocol'

function read(id: string, status: 'done' | 'error' | 'running' = 'done'): ContentBlock {
  return { type: 'tool_use', id, name: 'read_file', input: { path: `/f/${id}` }, status }
}
function tool(id: string, name: string, status: 'done' | 'error' | 'running' = 'done'): ContentBlock {
  return { type: 'tool_use', id, name, input: {}, status }
}
function text(t: string): ContentBlock {
  return { type: 'text', text: t }
}

function isGroup(b: RenderBlock): b is ToolGroupBlock {
  return b.type === 'tool_group'
}

describe('groupReadSearch', () => {
  it('folds 3+ consecutive reads into one tool_group with count', () => {
    const out = groupReadSearch([read('a'), read('b'), read('c')])
    expect(out).toHaveLength(1)
    const g = out[0]!
    expect(isGroup(g)).toBe(true)
    if (isGroup(g)) {
      expect(g.kind).toBe('read_search')
      expect(g.count).toBe(3)
      expect(g.tools).toHaveLength(3)
      expect(g.tools.map((t) => t.id)).toEqual(['a', 'b', 'c'])
    }
  })

  it('leaves 2 consecutive reads unchanged (below threshold)', () => {
    const input = [read('a'), read('b')]
    const out = groupReadSearch(input)
    expect(out).toHaveLength(2)
    expect(out.every((b) => b.type === 'tool_use')).toBe(true)
  })

  it('does not group across a mutating tool (read -> write -> read)', () => {
    const out = groupReadSearch([read('a'), tool('w', 'write_file'), read('b')])
    expect(out).toHaveLength(3)
    expect(out.some(isGroup)).toBe(false)
  })

  it('breaks a failed read out as its own visible card', () => {
    // 2 ok reads, 1 failed read, 2 ok reads: fail splits into two runs of 2 -> no group at all
    const out = groupReadSearch([read('a'), read('b'), read('x', 'error'), read('c'), read('d')])
    expect(out.some(isGroup)).toBe(false)
    expect(out).toHaveLength(5)
    // failed one is present as tool_use
    expect(out.find((b) => b.type === 'tool_use' && b.id === 'x' && b.status === 'error')).toBeTruthy()
  })

  it('folds group of 3+ around a failed read that breaks out', () => {
    // 3 ok reads, failed read, 3 ok reads -> two groups + failed card in middle
    const out = groupReadSearch([
      read('a'), read('b'), read('c'),
      read('x', 'error'),
      read('d'), read('e'), read('f'),
    ])
    const groups = out.filter(isGroup)
    expect(groups).toHaveLength(2)
    expect(groups[0]!.count).toBe(3)
    expect(groups[1]!.count).toBe(3)
    expect(out.find((b) => b.type === 'tool_use' && b.id === 'x')).toBeTruthy()
  })

  it('groups mixed read/grep/search tools together', () => {
    const out = groupReadSearch([
      read('a'),
      tool('g', 'grep'),
      tool('s', 'search_memory'),
      tool('w', 'web_search'),
    ])
    expect(out).toHaveLength(1)
    const g = out[0]!
    expect(isGroup(g)).toBe(true)
    if (isGroup(g)) expect(g.count).toBe(4)
  })

  it('returns empty unchanged', () => {
    expect(groupReadSearch([])).toEqual([])
  })

  it('leaves messages with no tools unchanged', () => {
    const input = [text('hello'), text('world')]
    const out = groupReadSearch(input)
    expect(out).toHaveLength(2)
    expect(out.every((b) => b.type === 'text')).toBe(true)
  })

  it('breaks the run on interleaved text', () => {
    const out = groupReadSearch([read('a'), read('b'), text('note'), read('c'), read('d')])
    expect(out.some(isGroup)).toBe(false)
    expect(out).toHaveLength(5)
  })

  it('does not fold unknown/unlisted tool names (fail-safe)', () => {
    const out = groupReadSearch([tool('a', 'mystery_tool'), tool('b', 'mystery_tool'), tool('c', 'mystery_tool')])
    expect(out.some(isGroup)).toBe(false)
    expect(out).toHaveLength(3)
  })

  it('folds a running read/search run (status running is not error)', () => {
    const out = groupReadSearch([read('a', 'running'), read('b', 'running'), read('c', 'running')])
    expect(out).toHaveLength(1)
    expect(isGroup(out[0]!)).toBe(true)
  })
})
