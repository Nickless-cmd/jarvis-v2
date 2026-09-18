/**
 * Artefakt-fladen (Bjørn 18/9-2026). Formerne i fixturerne er dem serveren
 * FAKTISK sender — kørt mod CT105's data før testen blev skrevet.
 */
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

const hent = vi.fn()
const getFile = vi.fn()
const select = vi.fn()
vi.mock('../lib/artefakter', async (orig) => ({
  ...(await orig<typeof import('../lib/artefakter')>()),
  hentArtefakter: (...a: unknown[]) => hent(...a),
}))
vi.mock('../lib/api', () => ({ getFile: (...a: unknown[]) => getFile(...a) }))
vi.mock('../hooks/useSettings', () => ({ useSettings: () => ({ settings: { apiBaseUrl: 'http://x', authToken: 't' } }) }))
vi.mock('../hooks/useSessions', () => ({ useSessions: () => ({ select }) }))

import { ArtifactsView } from './ArtifactsView'

const ROD = '/media/projects/jarvis-v2'
const artefakt = (rel: string, over: Record<string, unknown> = {}) => ({
  path: `${ROD}/${rel}`, rel, last_at: '2026-09-18T17:40:00+00:00',
  session_id: 'chat-1', session_title: 'yo... du må lige samle op', last_tool: 'edit_file',
  edits: 2, session_count: 1, add: 42, del: 19, ...over,
})

describe('artefakt-fladen', () => {
  beforeEach(() => {
    localStorage.setItem('jarvis-desk:code-ws', JSON.stringify({ kind: 'workstation', wsPath: ROD }))
    hent.mockReset().mockResolvedValue({
      ok: true, root: ROD, scanned: 1460, total: 2,
      artifacts: [artefakt('core/services/decision_review_daemon.py'), artefakt('README.md', { add: 308, del: 0, edits: 1 })],
    })
    getFile.mockReset().mockResolvedValue({ path: 'x', content: 'print(1)', language: 'python' })
    select.mockReset()
  })

  it('henter for den mappe code står i', async () => {
    render(<ArtifactsView onOpenCode={() => {}} />)
    await waitFor(() => expect(hent).toHaveBeenCalled())
    expect(hent.mock.calls[0]![1]).toBe(ROD)
  })

  it('viser filerne med navn, sti og +/−', async () => {
    render(<ArtifactsView onOpenCode={() => {}} />)
    expect(await screen.findByText('decision_review_daemon.py')).toBeTruthy()
    expect(screen.getByText('core/services')).toBeTruthy()
    expect(screen.getByText('+42')).toBeTruthy()
    expect(screen.getByText('−19')).toBeTruthy()
    // En ren tilføjelse viser intet «−0».
    expect(screen.queryByText('−0')).toBeNull()
  })

  // Så et tal der ser lavt ud kan kontrolleres — intet vindue skjuler halen.
  it('siger hvor mange svar der blev læst', async () => {
    render(<ArtifactsView onOpenCode={() => {}} />)
    expect(await screen.findByText(/Læst ud af 1460 svar/)).toBeTruthy()
  })

  it('klik viser filen som den står nu, fra den rigtige mappe', async () => {
    render(<ArtifactsView onOpenCode={() => {}} />)
    fireEvent.click(await screen.findByText('decision_review_daemon.py'))
    await waitFor(() => expect(getFile).toHaveBeenCalled())
    const [, rod, sti, kind] = getFile.mock.calls[0]!
    expect([rod, sti, kind]).toEqual([ROD, 'core/services/decision_review_daemon.py', 'workstation'])
  })

  it('fører tilbage til samtalen hvor filen sidst blev rørt', async () => {
    const tilCode = vi.fn()
    render(<ArtifactsView onOpenCode={tilCode} />)
    fireEvent.click(await screen.findByText('decision_review_daemon.py'))
    fireEvent.click(await screen.findByTitle('Åbn samtalen hvor filen sidst blev rørt'))
    expect(select).toHaveBeenCalledWith('chat-1')
    expect(tilCode).toHaveBeenCalled()
  })

  it('filtrerer på sti', async () => {
    render(<ArtifactsView onOpenCode={() => {}} />)
    await screen.findByText('README.md')
    fireEvent.change(screen.getByLabelText('Filtrér artefakter'), { target: { value: 'daemon' } })
    expect(screen.queryByText('README.md')).toBeNull()
    expect(screen.getByText('decision_review_daemon.py')).toBeTruthy()
  })

  it('siger serverens grund når listen ikke kan hentes', async () => {
    hent.mockResolvedValue({ ok: false, root: '', scanned: 0, total: 0, artifacts: [], error: 'ingen gyldig mappe' })
    render(<ArtifactsView onOpenCode={() => {}} />)
    expect(await screen.findByText('ingen gyldig mappe')).toBeTruthy()
  })
})
