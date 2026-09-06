import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'

const getReviewAendringer = vi.fn()
vi.mock('../../lib/coworkApi', () => ({
  getReviewAendringer: (...a: unknown[]) => getReviewAendringer(...a),
}))

import { ReviewPanel } from './ReviewPanel'

const cfg = { apiBaseUrl: 'http://x', authToken: 't' }
const svar = (o: Record<string, unknown> = {}) => ({
  branch: 'main', added: 12, removed: 3, diff: '', diff_truncated: false,
  files: [{ path: 'core/db.py', added: 12, removed: 3, binary: false, lines: 2500 }],
  risks: [], ...o,
})

describe('ReviewPanel', () => {
  beforeEach(() => { getReviewAendringer.mockReset() })

  it('viser filerne med grenen og samlet +/−', async () => {
    getReviewAendringer.mockResolvedValue(svar())
    render(<ReviewPanel config={cfg} />)
    expect(await screen.findByText(/1 filer på main/)).toBeTruthy()
    expect(screen.getByText('core/db.py')).toBeTruthy()
  })

  it('viser risikoflagets REGEL, ikke bare en advarsel', async () => {
    getReviewAendringer.mockResolvedValue(svar({
      risks: [{ path: 'core/db.py', regel: 'over 2000 linjer', note: '2500 linjer. Boy Scout-reglen…' }],
    }))
    render(<ReviewPanel config={cfg} />)
    expect(await screen.findByText(/core\/db.py — over 2000 linjer/)).toBeTruthy()
    expect(screen.getByText(/Boy Scout-reglen/)).toBeTruthy()
  })

  it('siger tydeligt når intet er ændret', async () => {
    getReviewAendringer.mockResolvedValue(svar({ files: [], added: 0, removed: 0 }))
    render(<ReviewPanel config={cfg} />)
    expect(await screen.findByText(/Intet ændret i arbejdstræet på main/)).toBeTruthy()
  })

  it('folder diffen ud på klik og siger til når den er afkortet', async () => {
    getReviewAendringer.mockResolvedValue(svar({ diff: '--- a\n+++ b\n', diff_truncated: true }))
    render(<ReviewPanel config={cfg} />)
    fireEvent.click(await screen.findByRole('button', { name: /Vis diff/ }))
    expect(screen.getByText(/\+\+\+ b/)).toBeTruthy()
    expect(screen.getByText(/afkortet/)).toBeTruthy()
  })

  it('sender testKoert videre, så «ingen test kørt» kan afgøres', async () => {
    getReviewAendringer.mockResolvedValue(svar())
    render(<ReviewPanel config={cfg} testKoert />)
    await screen.findByText(/1 filer/)
    expect(getReviewAendringer).toHaveBeenCalledWith(cfg, true)
  })

  it('siger til når kaldet fejler', async () => {
    getReviewAendringer.mockImplementation(() => Promise.reject(new Error('nede')))
    render(<ReviewPanel config={cfg} />)
    expect(await screen.findByText(/Kunne ikke hente ændringerne/)).toBeTruthy()
  })
})
