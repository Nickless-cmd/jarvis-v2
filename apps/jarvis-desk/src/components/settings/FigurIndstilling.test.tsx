import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { ThemeSection } from './ThemeSection'

/** Sektionen har flere afkrydsningsfelter (figuren OG rækkevisningen, 22/9-2026),
 *  så hver test siger hvilket den mener. Et navnløst `findByRole('checkbox')`
 *  fandt bare det første og ville knække næste gang nogen tilføjer et. */
const FIGUR = { name: /figuren på skrivebordet/i }

describe('Jarvis-figuren til og fra', () => {
  let vist = true
  const bro = { figur: { vist: vi.fn(async () => vist), saetVist: vi.fn(async (v: boolean) => { vist = v; return v }) } }
  beforeEach(() => { vist = true; bro.figur.saetVist.mockClear(); (window as unknown as { jarvisDesk: typeof bro }).jarvisDesk = bro })
  afterEach(() => { delete (window as unknown as { jarvisDesk?: unknown }).jarvisDesk })

  it('indstillingen i Udseende skjuler figuren', async () => {
    render(<ThemeSection />)
    const boks = await screen.findByRole('checkbox', FIGUR)
    expect(boks).toBeChecked()
    fireEvent.click(boks)
    await waitFor(() => expect(bro.figur.saetVist).toHaveBeenCalledWith(false))
    await waitFor(() => expect(screen.getByRole('checkbox', FIGUR)).not.toBeChecked())
  })

  it('i en browser-fane (ingen desk) tegnes ingen af dem', async () => {
    delete (window as unknown as { jarvisDesk?: unknown }).jarvisDesk
    render(<ThemeSection />)
    // Figur-felterne er desk-only. Raekkevisningen er IKKE — den er en ren
    // visningspraeference og staar ogsaa i en browser-fane.
    expect(screen.queryByRole('checkbox', FIGUR)).toBeNull()
    expect(screen.getByRole('checkbox', { name: /rækkevisning/i })).toBeInTheDocument()
  })
})
