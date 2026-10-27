import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, waitFor } from '@testing-library/react'
import { FilPreview } from './FilPreview'

/**
 * Panelet skal kunne SE en fil — ikke kun hente den.
 *
 * Målt 27/10-2026 (Bjørn): «mangler vi visningsflader i desk for de fleste af
 * disse ting?» Filen var et download-kort. Testen her måler det der er nemt
 * at tage fejl af: at den RIGTIGE renderer bliver brugt pr. mime-type. En
 * komponent der altid viser et download-kort ser korrekt ud i kode og gør
 * intet for en PDF.
 *
 * Vi mocker `fetchBlobWithAuth` — ikke `fetch`. jsdom's `Response` tager ikke
 * en Blob som body (`.text()` giver «[object Blob]»), så en fetch-mock måler
 * jsdom, ikke komponenten. Det gjorde den første udgave af denne fil: fire
 * røde tests der så ud som komponentfejl.
 */
vi.mock('../../lib/api', async (importOriginal) => {
  const faktisk = await importOriginal<typeof import('../../lib/api')>()
  return { ...faktisk, fetchBlobWithAuth: vi.fn() }
})

const { fetchBlobWithAuth } = await import('../../lib/api')
const config = { apiBaseUrl: 'https://api.test', authToken: 't' }

function blob(mime: string, tekst = 'indhold') {
  return new Blob([tekst], { type: mime })
}

describe('FilPreview', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    globalThis.URL.createObjectURL = vi.fn(() => 'blob:test-1')
    globalThis.URL.revokeObjectURL = vi.fn()
  })

  it('tegner en PDF i en iframe — ikke et download-kort', async () => {
    vi.mocked(fetchBlobWithAuth).mockResolvedValue(blob('application/pdf'))
    const { container } = render(
      <FilPreview fil={{ navn: 'rapport.pdf', url: '/files/rapport.pdf' }} config={config} />,
    )
    await waitFor(() => {
      const iframe = container.querySelector('iframe')
      expect(iframe).not.toBeNull()
      expect(iframe?.getAttribute('src')).toBe('blob:test-1')
    })
  })

  it('tegner et billede som img', async () => {
    vi.mocked(fetchBlobWithAuth).mockResolvedValue(blob('image/png'))
    const { container } = render(
      <FilPreview fil={{ navn: 'billede.png', url: '/files/billede.png' }} config={config} />,
    )
    await waitFor(() => {
      const img = container.querySelector('img')
      expect(img).not.toBeNull()
      expect(img?.getAttribute('alt')).toBe('billede.png')
    })
  })

  it('viser tekst som tekst, ikke som blob-link', async () => {
    vi.mocked(fetchBlobWithAuth).mockResolvedValue(
      blob('text/plain', 'linje et\nlinje to'),
    )
    const { container } = render(
      <FilPreview fil={{ navn: 'noter.txt', url: '/files/noter.txt' }} config={config} />,
    )
    await waitFor(() => {
      expect(container.querySelector('pre')?.textContent).toContain('linje et')
    })
  })

  it('siger ÆRLIGT at et office-format ikke kan vises — i stedet for en tom rude', async () => {
    vi.mocked(fetchBlobWithAuth).mockResolvedValue(blob(
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'PK',
    ))
    const { container, getByText } = render(
      <FilPreview fil={{ navn: 'brev.docx', url: '/files/brev.docx' }} config={config} />,
    )
    await waitFor(() => {
      expect(getByText(/kan ikke vises i panelet/)).toBeTruthy()
      expect(container.querySelector('iframe')).toBeNull()
      expect(container.querySelector('img')).toBeNull()
    })
  })

  it('viser fejlen når filen ikke kan hentes', async () => {
    vi.mocked(fetchBlobWithAuth).mockRejectedValue(new Error('Fil fejlede: 401'))
    const { getByText } = render(
      <FilPreview fil={{ navn: 'x.pdf', url: '/files/x.pdf' }} config={config} />,
    )
    await waitFor(() => expect(getByText(/401/)).toBeTruthy())
  })

  it('henter med brugerens token — ikke et bart <iframe src>', async () => {
    vi.mocked(fetchBlobWithAuth).mockResolvedValue(blob('application/pdf'))
    render(<FilPreview fil={{ navn: 'a.pdf', url: '/files/a.pdf' }} config={config} />)
    await waitFor(() => expect(fetchBlobWithAuth).toHaveBeenCalledWith(config, '/files/a.pdf'))
  })
})
