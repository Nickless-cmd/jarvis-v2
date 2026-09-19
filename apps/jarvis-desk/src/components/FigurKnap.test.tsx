import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { FigurKnap } from './FigurKnap'
import { ThemeSection } from './settings/ThemeSection'

describe('Jarvis-figuren til og fra', () => {
  let vist = true
  const bro = { figur: { vist: vi.fn(async () => vist), saetVist: vi.fn(async (v: boolean) => { vist = v; return v }) } }
  beforeEach(() => { vist = true; bro.figur.saetVist.mockClear(); (window as unknown as { jarvisDesk: typeof bro }).jarvisDesk = bro })
  afterEach(() => { delete (window as unknown as { jarvisDesk?: unknown }).jarvisDesk })

  it('headerknappen skjuler figuren, og indstillingen foelger med', async () => {
    render(<><FigurKnap /><ThemeSection /></>)
    const knap = await screen.findByRole('button', { name: 'Skjul Jarvis-figuren' })
    const boks = await screen.findByRole('checkbox')
    expect(boks).toBeChecked()
    fireEvent.click(knap)
    await waitFor(() => expect(bro.figur.saetVist).toHaveBeenCalledWith(false))
    await waitFor(() => expect(screen.getByRole('checkbox')).not.toBeChecked())
    expect(screen.getByRole('button', { name: 'Vis Jarvis-figuren på skrivebordet' })).toHaveAttribute('aria-pressed', 'false')
  })

  it('i en browser-fane (ingen desk) tegnes ingen af dem', async () => {
    delete (window as unknown as { jarvisDesk?: unknown }).jarvisDesk
    render(<><FigurKnap /><ThemeSection /></>)
    expect(screen.queryByRole('checkbox')).toBeNull()
    expect(screen.queryByRole('button', { name: /Jarvis-figuren/ })).toBeNull()
  })
})
