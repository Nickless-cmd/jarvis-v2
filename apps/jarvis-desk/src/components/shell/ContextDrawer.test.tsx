import { render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { KontekstDetaljer } from './ContextDrawer'

const cfg = { apiBaseUrl: 'http://x', authToken: 't' }

vi.mock('../../lib/coworkApi', () => ({
  getKontekst: vi.fn(async () => ({
    har_data: true,
    filer: ['SOUL.md', 'USER.md'],
    udeladt: [],
    kilder: ['memory recall bundle', 'inner life'],
    tegn: 37260,
    dele: 52,
  })),
  getKrop: vi.fn(async () => ({ krop: null })),
}))

describe('KontekstDetaljer', () => {
  it('viser målte tal, ikke runde estimater', async () => {
    render(<KontekstDetaljer config={cfg} sessionId="s1" />)
    // 37260 tegn / 4 ≈ 9315 tokens → 9,3k
    await waitFor(() => expect(screen.getByText(/2 filer · 2 kilder · ~9\.3k/)).toBeTruthy())
  })

  it('henter for DEN samtale man står i', async () => {
    const { getKontekst } = await import('../../lib/coworkApi')
    render(<KontekstDetaljer config={cfg} sessionId="samtale-7" />)
    await waitFor(() => expect(getKontekst).toHaveBeenCalledWith(cfg, 'samtale-7'))
  })

  it('siger det ærligt når der ingen målt tur er', async () => {
    const { getKontekst } = await import('../../lib/coworkApi')
    ;(getKontekst as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      har_data: false, filer: [], udeladt: [], kilder: [], tegn: 0, dele: 0,
    })
    render(<KontekstDetaljer config={cfg} sessionId="s2" />)
    await waitFor(() => expect(screen.getByText(/Ingen målt tur i denne samtale/)).toBeTruthy())
  })
})

describe('Kontekst-rækken i Miljø', () => {
  it('folder detaljerne ud ved klik — og henter først da', async () => {
    const { RunHealth } = await import('../code/RunHealth')
    const { getKontekst } = await import('../../lib/coworkApi')
    ;(getKontekst as ReturnType<typeof vi.fn>).mockClear()
    const { fireEvent } = await import('@testing-library/react')
    render(<RunHealth config={cfg} tokens={40000} komprimerVed={100000} sessionId="s9" />)
    expect(getKontekst).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: /Kontekst/ }))
    await waitFor(() => expect(screen.getByText(/2 filer · 2 kilder/)).toBeTruthy())
    expect(getKontekst).toHaveBeenCalledWith(cfg, 's9')
  })
})
