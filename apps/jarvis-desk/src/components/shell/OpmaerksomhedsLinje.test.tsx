import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

const hent = vi.fn()
const marker = vi.fn().mockResolvedValue(undefined)
vi.mock('../../lib/opmaerksomhed', async (orig) => ({
  ...(await orig<typeof import('../../lib/opmaerksomhed')>()),
  hentOpmaerksomhed: (...a: unknown[]) => hent(...a),
  markerSet: (...a: unknown[]) => marker(...a),
}))

import { OpmaerksomhedsLinje } from './OpmaerksomhedsLinje'

const cfg = { apiBaseUrl: 'http://x', authToken: 't' }
const punkt = (session_id: string, tilstand: string, titel = 'T') =>
  ({ session_id, run_id: 'r', tilstand, titel, tekst: '', tid: 1 })

describe('OpmaerksomhedsLinje', () => {
  beforeEach(() => { hent.mockReset(); marker.mockClear() })

  it('er tavs naar intet kraever dig', async () => {
    hent.mockResolvedValue({ tilstand: 'idle', etiket: 'Intet kræver dig', antal: { waiting: 0, failed: 0, review: 0, running: 0 }, baggrund: 3, fokus: null, punkter: [] })
    render(<OpmaerksomhedsLinje config={cfg} aktivId={null} onAabn={() => {}} />)
    await waitFor(() => expect(hent).toHaveBeenCalled())
    expect(screen.queryByTestId('opmaerksomhed')).toBeNull()
  })

  it('viser den vindende tilstand med antal og aabner fokus-samtalen', async () => {
    const p = punkt('s-1', 'review', 'Kæledyret')
    hent.mockResolvedValue({ tilstand: 'review', etiket: 'Færdig — se svaret', antal: { waiting: 0, failed: 0, review: 2, running: 1 }, baggrund: 0, fokus: p, punkter: [p, punkt('s-2', 'review')] })
    const aabn = vi.fn()
    render(<OpmaerksomhedsLinje config={cfg} aktivId={null} onAabn={aabn} />)
    const knap = await screen.findByTestId('opmaerksomhed')
    expect(knap).toHaveClass('opm-review')
    expect(knap).toHaveTextContent('Færdig — se svaret · 2')
    expect(knap).toHaveTextContent('Kæledyret')
    fireEvent.click(knap)
    expect(aabn).toHaveBeenCalledWith('s-1')
  })

  it('kvitterer paa serveren naar den aabne samtale har et faerdigt svar', async () => {
    const p = punkt('s-1', 'failed')
    hent.mockResolvedValue({ tilstand: 'failed', etiket: 'Noget gik galt', antal: { waiting: 0, failed: 1, review: 0, running: 0 }, baggrund: 0, fokus: p, punkter: [p] })
    render(<OpmaerksomhedsLinje config={cfg} aktivId="s-1" onAabn={() => {}} />)
    await waitFor(() => expect(marker).toHaveBeenCalledWith(cfg, 's-1'))
  })
})
