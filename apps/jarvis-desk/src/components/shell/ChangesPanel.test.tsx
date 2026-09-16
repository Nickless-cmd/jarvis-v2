import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'

const getReviewAendringer = vi.fn()
vi.mock('../../lib/coworkApi', () => ({
  getReviewAendringer: (...a: unknown[]) => getReviewAendringer(...a),
}))

import { ChangesPanel } from './ChangesPanel'

const cfg = { apiBaseUrl: 'http://x', authToken: 't' }

const DIFF = `diff --git a/src/a.ts b/src/a.ts
--- a/src/a.ts
+++ b/src/a.ts
@@ -1,3 +1,3 @@
-const gammel = 1
+const ny = 2
 uændret
diff --git a/src/b.ts b/src/b.ts
--- a/src/b.ts
+++ b/src/b.ts
@@ -10,2 +10,3 @@
+tilføjet i b
`

const SVAR = {
  branch: 'main',
  files: [
    { path: 'src/a.ts', added: 1, removed: 1, binary: false },
    { path: 'src/b.ts', added: 1, removed: 0, binary: false },
  ],
  added: 2, removed: 1, diff: DIFF, diff_truncated: false, risks: [],
}

beforeEach(() => {
  getReviewAendringer.mockReset().mockResolvedValue(SVAR)
})

/**
 * «Tom» er TRE tilstande, ikke én:
 *   rent træ · kan ikke læse træet · har ikke spurgt færdig endnu
 * Et panel der siger «ingen ændringer» i alle tre lyver i to af dem — samme
 * fejl som jobs-ruden havde med den døde bro.
 */
describe('ChangesPanel', () => {
  it('viser filerne med +/- og grenen', async () => {
    render(<ChangesPanel config={cfg} onClose={() => {}} />)
    expect(await screen.findByText('main')).toBeInTheDocument()
    expect(screen.getByText('src/a.ts')).toBeInTheDocument()
    expect(screen.getByText(/2 filer/)).toBeInTheDocument()
  })

  it('et RENT træ siger «Ingen ændringer»', async () => {
    getReviewAendringer.mockResolvedValue({ ...SVAR, files: [], added: 0, removed: 0, diff: '' })
    render(<ChangesPanel config={cfg} onClose={() => {}} />)
    expect(await screen.findByText('Ingen ændringer')).toBeInTheDocument()
  })

  it('en FEJL er ikke «ingen ændringer»', async () => {
    getReviewAendringer.mockRejectedValue(new Error('git svarede ikke'))
    render(<ChangesPanel config={cfg} onClose={() => {}} />)
    expect(await screen.findByText(/kunne ikke læse arbejdstræet/)).toBeInTheDocument()
    expect(screen.queryByText('Ingen ændringer')).not.toBeInTheDocument()
  })

  it('før første svar står der «Henter…» — ikke «Ingen ændringer»', () => {
    getReviewAendringer.mockImplementation(() => new Promise(() => {}))
    render(<ChangesPanel config={cfg} onClose={() => {}} />)
    expect(screen.getByText('Henter…')).toBeInTheDocument()
    expect(screen.queryByText('Ingen ændringer')).not.toBeInTheDocument()
  })

  it('folder KUN den valgte fils hunks ud', async () => {
    render(<ChangesPanel config={cfg} onClose={() => {}} />)
    fireEvent.click(await screen.findByText('src/a.ts'))
    expect(await screen.findByText(/const ny = 2/)).toBeInTheDocument()
    // b's hunk hører til en anden fil og må ikke komme med.
    expect(screen.queryByText(/tilføjet i b/)).not.toBeInTheDocument()
  })

  it('siger til når diffen er KLIPPET — ellers ligner en manglende fil «uændret»', async () => {
    getReviewAendringer.mockResolvedValue({
      ...SVAR,
      files: [...SVAR.files, { path: 'src/c.ts', added: 9, removed: 0, binary: false }],
      diff_truncated: true,
    })
    render(<ChangesPanel config={cfg} onClose={() => {}} />)
    expect(await screen.findByText('klippet')).toBeInTheDocument()
    fireEvent.click(screen.getByText('src/c.ts'))
    expect(await screen.findByText(/nåede ikke med/)).toBeInTheDocument()
  })

  it('en binær fil får ikke opdigtede linjetal', async () => {
    getReviewAendringer.mockResolvedValue({
      ...SVAR, files: [{ path: 'logo.png', added: 0, removed: 0, binary: true }],
    })
    render(<ChangesPanel config={cfg} onClose={() => {}} />)
    expect(await screen.findByText('binær')).toBeInTheDocument()
    expect(screen.queryByText('+0')).not.toBeInTheDocument()
  })

  it('melder antallet op, så ikonet og listen ikke kan modsige hinanden', async () => {
    const taeller = vi.fn()
    render(<ChangesPanel config={cfg} onClose={() => {}} onCount={taeller} />)
    await waitFor(() => expect(taeller).toHaveBeenCalledWith(2))
  })

  it('starter ikke et nyt opslag mens det forrige er undervejs', async () => {
    // `git diff HEAD` paa et stort repo er ikke gratis. Poll hvert 4. sekund
    // uden vagt ville lægge kald i kø hvis svaret er langsomt.
    vi.useFakeTimers()
    let slip: ((v: unknown) => void) | null = null
    getReviewAendringer.mockImplementation(() => new Promise((r) => { slip = r }))
    render(<ChangesPanel config={cfg} onClose={() => {}} />)
    expect(getReviewAendringer).toHaveBeenCalledTimes(1)
    await vi.advanceTimersByTimeAsync(12000)
    expect(getReviewAendringer).toHaveBeenCalledTimes(1)
    slip!(SVAR)
    await vi.advanceTimersByTimeAsync(4000)
    expect(getReviewAendringer).toHaveBeenCalledTimes(2)
    vi.useRealTimers()
  })
})
