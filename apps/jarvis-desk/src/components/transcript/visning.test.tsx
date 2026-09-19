import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { BlocksRenderer } from '../rich/BlocksRenderer'
import { VisningContext, type Visning } from '../../lib/visning'
import { HeaderMere } from '../shell/HeaderMere'
import { streamReducer, initialStreamState } from '../../lib/streamReducer'
import type { ContentBlock, StreamEvent } from '../../lib/sseProtocol'

/**
 * Claude Desktops tre visninger (cc-desktop-chatview.md §1-2), Bjørn 19/9-2026.
 */
const blokke: ContentBlock[] = [
  { type: 'thinking', thinking: 'Hvor sidder værnet mon?', seconds: 4 } as ContentBlock,
  { type: 'tool_use', id: 't1', name: 'read_file', input: { path: '/a.py' }, status: 'done', result: 'x' },
  { type: 'tool_use', id: 't2', name: 'read_file', input: { path: '/b.py' }, status: 'done', result: 'y' },
  { type: 'tool_use_summary', summary: 'Læste værnet', preceding_tool_use_ids: ['t1', 't2'], thinking_summary: 'Ville finde værnet i ruten' },
  { type: 'text', text: 'Fundet.' },
]

const tegn = (v: Visning) => render(
  <VisningContext.Provider value={v}><BlocksRenderer blocks={blokke} density="compact" streaming={false} /></VisningContext.Provider>,
)

describe('visningerne', () => {
  it('normal: én gruppe, intet resumé', () => {
    const { container } = tegn('normal')
    expect(container.querySelectorAll('.toolgroup:not(.tanke-linje)')).toHaveLength(1)
    expect(screen.queryByTestId('tanke-resume')).toBeNull()
  })

  it('Tænkning: resuméet står OVER gruppen — gemt på tool_use_summary', () => {
    const { container } = tegn('thinking')
    const resume = screen.getByTestId('tanke-resume')
    expect(resume).toHaveTextContent('Ville finde værnet i ruten')
    const gruppe = container.querySelector('.toolgroup:not(.tanke-linje)')!
    expect(resume.compareDocumentPosition(gruppe) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  })

  it('Tænkning: et LIVE resumé fra streamen vinder', () => {
    render(
      <VisningContext.Provider value="thinking">
        <BlocksRenderer blocks={blokke} density="compact" streaming={false} tankeResumeer={{ t1: 'Live-resumé' }} />
      </VisningContext.Provider>,
    )
    expect(screen.getByTestId('tanke-resume')).toHaveTextContent('Live-resumé')
  })

  it('Alt: ingen gruppering — hvert kald for sig og åbent, tanken åben', () => {
    const { container } = tegn('verbose')
    expect(container.querySelectorAll('.toolgroup:not(.tanke-linje)')).toHaveLength(0)
    expect(screen.getAllByText('Læs fil')).toHaveLength(2)
    expect(screen.getByText('Hvor sidder værnet mon?')).toBeInTheDocument()
  })
})

describe('reduceren bærer resuméet', () => {
  it('fra tool_round_label, også uden etiket', () => {
    let s = initialStreamState()
    s = streamReducer(s, { type: 'system_event', kind: 'tool_round_label', payload: { etiket: '', tool_use_ids: ['t1'], tanke_resume: 'Ville læse testen' } } as unknown as StreamEvent)
    expect(s.tankeResumeer).toEqual({ t1: 'Ville læse testen' })
    expect(s.rundeEtiketter ?? {}).toEqual({})
  })
})

describe('vælgeren (nu i headerens flere-menu, 19/9-2026)', () => {
  beforeEach(() => localStorage.clear())
  it('tre radiopunkter; et skift kaldes', () => {
    const onSkift = vi.fn()
    render(<HeaderMere visning="normal" onVisning={onSkift} valg={[]} />)
    fireEvent.click(screen.getByRole('button', { name: 'Flere valg' }))
    const punkter = screen.getAllByRole('menuitemradio')
    expect(punkter.map((p) => p.getAttribute('aria-checked'))).toEqual(['true', 'false', 'false'])
    fireEvent.click(punkter[1]!)
    expect(onSkift).toHaveBeenCalledWith('thinking')
  })
  it('«Gør til standard» husker den lokalt', () => {
    render(<HeaderMere visning="verbose" onVisning={() => {}} valg={[]} />)
    fireEvent.click(screen.getByRole('button', { name: 'Flere valg' }))
    fireEvent.click(screen.getByRole('menuitem', { name: 'Gør Alt til standard' }))
    expect(localStorage.getItem('jarvis-desk:visning-standard')).toBe('verbose')
  })
})
