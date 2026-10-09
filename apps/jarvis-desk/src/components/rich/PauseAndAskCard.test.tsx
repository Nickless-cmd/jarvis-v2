import { describe, expect, it, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { PauseAndAskCard } from './PauseAndAskCard'
import { ToolCard } from './ToolCard'
import { BlocksRenderer } from './BlocksRenderer'
import { onPauseSvar } from '../../lib/pauseAsk'

const ask = {
  question: 'Skal jeg splitte db.py før jeg retter?',
  options: ['Ja, split først', 'Nej, bare ret'],
  context: 'db.py er 33.056 linjer',
  urgency: 'high' as const,
}

describe('PauseAndAskCard', () => {
  it('viser spørgsmålet og gør hver option til en knap', () => {
    render(<PauseAndAskCard ask={ask} />)
    expect(screen.getByText(ask.question)).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Ja, split først' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Nej, bare ret' })).toBeTruthy()
  })

  it('sender først et enkelt valg ved Send svar', () => {
    const set = vi.fn()
    const af = onPauseSvar(set)
    render(<PauseAndAskCard ask={ask} />)
    fireEvent.click(screen.getByRole('button', { name: 'Ja, split først' }))
    expect(set).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'Send svar' }))
    expect(set).toHaveBeenCalledWith('Ja, split først')
    af()
  })

  it('samler flere markerede valg i ét svar når Jarvis tillader det', () => {
    const set = vi.fn()
    const af = onPauseSvar(set)
    render(<PauseAndAskCard ask={{ ...ask, options: ['Desk', 'Mobil', 'Web UI'], allowMultiple: true }} />)
    fireEvent.click(screen.getByRole('button', { name: 'Desk' }))
    fireEvent.click(screen.getByRole('button', { name: 'Mobil' }))
    fireEvent.click(screen.getByRole('button', { name: 'Send svar' }))
    expect(set).toHaveBeenCalledWith('Jeg vælger:\n- Desk\n- Mobil')
    af()
  })

  it('lader et eget svar erstatte de markerede muligheder', () => {
    const set = vi.fn()
    const af = onPauseSvar(set)
    render(<PauseAndAskCard ask={ask} />)
    fireEvent.click(screen.getByRole('button', { name: 'Ja, split først' }))
    fireEvent.change(screen.getByRole('textbox', { name: 'Skriv dit eget svar' }), { target: { value: 'Spørg mig i morgen' } })
    fireEvent.click(screen.getByRole('button', { name: 'Send svar' }))
    expect(set).toHaveBeenCalledWith('Spørg mig i morgen')
    af()
  })

  it('giver et skrivefelt når Jarvis ikke har forslag', () => {
    render(<PauseAndAskCard ask={{ ...ask, options: [] }} />)
    expect(screen.getByRole('textbox', { name: 'Skriv dit eget svar' })).toBeTruthy()
  })
})

describe('ToolCard · pause_and_ask', () => {
  const blok = (result: string) => ({
    type: 'tool_use' as const, id: 't1', name: 'pause_and_ask',
    input: {}, status: 'done', result,
  })

  it('viser kortet i stedet for rå JSON — også i kompakt tilstand', () => {
    // Det var hele fejlen: resultatet kom som JSON-streng fra disk og blev
    // dumpet som tekst, foldet sammen, så spørgsmålet aldrig nåede frem.
    const json = JSON.stringify({ kind: 'pause_and_ask', ...ask })
    render(<ToolCard block={blok(json) as never} density="compact" />)
    expect(screen.getByText(ask.question)).toBeTruthy()
    expect(screen.queryByText(/"kind"/)).toBeNull()
  })

  it('rører ikke almindelige tool-kald', () => {
    render(<ToolCard block={{ ...blok('42 linjer'), name: 'bash' } as never} density="full" />)
    expect(screen.queryByText(/venter på dig/i)).toBeNull()
  })

  it('forbliver synligt gennem BlocksRenderer uden at åbne en tool-gruppe', () => {
    const json = JSON.stringify({ kind: 'pause_and_ask', ...ask })
    const { container } = render(
      <BlocksRenderer blocks={[blok(json) as never]} density="compact" streaming />,
    )

    expect(screen.getByText(ask.question)).toBeTruthy()
    expect(container.querySelector('.toolgroup')).toBeNull()
  })
})
