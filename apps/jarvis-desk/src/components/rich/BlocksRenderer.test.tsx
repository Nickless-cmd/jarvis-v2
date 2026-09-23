import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { BlocksRenderer } from './BlocksRenderer'
import type { ContentBlock } from '../../lib/sseProtocol'

function renderBlocks(blocks: ContentBlock[], streaming = false) {
  return render(<BlocksRenderer blocks={blocks} density="compact" streaming={streaming} />)
}

describe('BlocksRenderer progress', () => {
  // MessageRow viser «Redigerede N filer» efter det færdige svar; denne
  // blok-renderer viser kun selve beskedens indhold.
  it('viser IKKE længere et Forløb-spor under streaming', () => {
    const blocks: ContentBlock[] = [
      { type: 'text', text: 'Færdig.' },
      { type: 'tool_use', id: 'c1', name: 'read_file', input: { path: 'x.py' }, status: 'done' },
      { type: 'progress', tool_use_id: 'c1', parent_tool_use_id: null, message: 'Læste fil: x.py', status: 'done' },
    ]
    renderBlocks(blocks, true)
    expect(screen.queryByText(/Forløb/)).not.toBeInTheDocument()
    expect(screen.queryByText('Læste fil: x.py')).not.toBeInTheDocument()
  })

  it('en LÆST fil er ikke en redigeret fil — intet kort', () => {
    renderBlocks([
      { type: 'tool_use', id: 'c1', name: 'read_file', input: { path: 'x.py' }, status: 'done' },
    ], true)
    expect(screen.queryByText(/Redigerede/)).not.toBeInTheDocument()
  })

  it('kortet ejes af MessageRow og duplikeres ikke i blok-rendereren', () => {
    renderBlocks([
      { type: 'tool_use', id: 'c1', name: 'write_file', input: { path: 'src/x.py' }, status: 'done' },
    ], false)
    expect(screen.queryByText('Redigerede 1 fil')).not.toBeInTheDocument()
  })

  it('lader tekst-only besked være uændret (intet kort)', () => {
    renderBlocks([{ type: 'text', text: 'bare tekst' }])
    expect(screen.getByText('bare tekst')).toBeInTheDocument()
    expect(screen.queryByText(/Redigerede/)).not.toBeInTheDocument()
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
