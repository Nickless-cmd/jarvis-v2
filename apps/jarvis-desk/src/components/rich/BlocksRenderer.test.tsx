import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { BlocksRenderer } from './BlocksRenderer'
import type { ContentBlock } from '../../lib/sseProtocol'

function renderBlocks(blocks: ContentBlock[], streaming = false) {
  return render(<BlocksRenderer blocks={blocks} density="compact" streaming={streaming} />)
}

describe('BlocksRenderer progress', () => {
  // Narrationen vises KUN under streaming. Er turen slut, staar den i «Forløb»
  // under beskeden (RunTimeline) — foer stod begge dele samtidig, og Bjoern saa
  // to forloeb paa samme besked (8/9-2026).
  it('rendrer progress som ét foldbart spor MENS der streames', () => {
    const blocks: ContentBlock[] = [
      { type: 'text', text: 'Færdig.' },
      { type: 'tool_use', id: 'c1', name: 'read_file', input: { path: 'x.py' }, status: 'done' },
      { type: 'progress', tool_use_id: 'c1', parent_tool_use_id: null, message: 'Læste fil: x.py', status: 'done' },
    ]
    renderBlocks(blocks, true)
    expect(screen.getByText(/Forløb \(1\)/)).toBeInTheDocument()
    expect(screen.getByText('Læste fil: x.py')).toBeInTheDocument()
  })

  it('coalescer sammenhængende progress-blokke til ét spor', () => {
    const blocks: ContentBlock[] = [
      { type: 'progress', tool_use_id: 'c1', parent_tool_use_id: null, message: 'Trin 1', status: 'done' },
      { type: 'progress', tool_use_id: 'c2', parent_tool_use_id: null, message: 'Trin 2', status: 'done' },
    ]
    renderBlocks(blocks, true)
    // ét spor med to trin, ikke to separate spor
    expect(screen.getByText(/Forløb \(2\)/)).toBeInTheDocument()
    expect(screen.queryByText(/Forløb \(1\)/)).not.toBeInTheDocument()
  })

  it('lader tekst-only besked være uændret (ingen Forløb)', () => {
    renderBlocks([{ type: 'text', text: 'bare tekst' }])
    expect(screen.getByText('bare tekst')).toBeInTheDocument()
    expect(screen.queryByText(/Forløb/)).not.toBeInTheDocument()
  })

  it('viser INTET spor når turen er slut — så der kun er ét forløb', () => {
    renderBlocks([
      { type: 'progress', tool_use_id: 'c1', parent_tool_use_id: null, message: 'Trin 1', status: 'done' },
    ], false)
    expect(screen.queryByText(/Forløb/)).not.toBeInTheDocument()
    expect(screen.queryByText('Trin 1')).not.toBeInTheDocument()
  })

  it('lader tool-only besked være uændret (ingen Forløb)', () => {
    renderBlocks([
      { type: 'tool_use', id: 'c1', name: 'bash', input: {}, status: 'done' },
    ])
    expect(screen.queryByText(/Forløb/)).not.toBeInTheDocument()
  })
})
