import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { ThemeSection } from './ThemeSection'

describe('Jarvis-figuren til og fra', () => {
  let vist = true
  const bro = { figur: { vist: vi.fn(async () => vist), saetVist: vi.fn(async (v: boolean) => { vist = v; return v }) } }
  beforeEach(() => { vist = true; bro.figur.saetVist.mockClear(); (window as unknown as { jarvisDesk: typeof bro }).jarvisDesk = bro })
  afterEach(() => { delete (window as unknown as { jarvisDesk?: unknown }).jarvisDesk })

  it('indstillingen i Udseende skjuler figuren', async () => {
    render(<ThemeSection />)
    const boks = await screen.findByRole('checkbox')
    expect(boks).toBeChecked()
    fireEvent.click(boks)
    await waitFor(() => expect(bro.figur.saetVist).toHaveBeenCalledWith(false))
    await waitFor(() => expect(screen.getByRole('checkbox')).not.toBeChecked())
  })

  it('i en browser-fane (ingen desk) tegnes ingen af dem', async () => {
    delete (window as unknown as { jarvisDesk?: unknown }).jarvisDesk
    render(<ThemeSection />)
    expect(screen.queryByRole('checkbox')).toBeNull()
  })
})
