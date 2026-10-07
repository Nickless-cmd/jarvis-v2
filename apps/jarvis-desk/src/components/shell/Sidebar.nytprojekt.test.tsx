/**
 * «+» i kode-gruppens fold-ud-linje (Bjørn 4/10-2026).
 *
 * «venstre panel hvor projekt fold ud linjen mangler et plus i enden til at
 * oprette nyt projekt.»
 *
 * Et projekt findes ikke som en post nogen steder — det ER den fælles
 * `workspace_root` som en eller flere samtaler deler. «Opret nyt projekt» er
 * derfor: vælg en mappe, og lav en kode-samtale der peger på den.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'

const { create, setWorkspace, pickFolder } = vi.hoisted(() => ({
  create: vi.fn(), setWorkspace: vi.fn(), pickFolder: vi.fn(),
}))

const SESSIONER = [
  { id: 'chat-kode', title: 'ret lige den fil', updated_at: 'x',
    workspace_kind: 'code', workspace_root: '/media/projects/jarvis-v2' },
  { id: 'chat-alm', title: 'en samtale', updated_at: 'x', workspace_kind: null },
  // En ARKIVERET samtale. Den er med fordi `GRUPPER_I_MODE.code` er
  // `['kode', 'arkiv']` — uden den rendrer kun ÉN gruppe paa kode-fladen, og
  // saa kan «staar kun paa kode-gruppen» ikke maales: en mutation der satte
  // plusset paa ALLE grupper gav stadig præcis ét.
  { id: 'chat-gammel', title: 'lagt vaek', updated_at: 'x', archived: true },
]

vi.mock('../../hooks/useSessions', () => ({
  useSessions: () => ({
    sessions: SESSIONER, activeId: null, create, setWorkspace,
    select: vi.fn(), rename: vi.fn(), remove: vi.fn(), newChat: vi.fn(),
    releaseWorkspace: vi.fn(),
  }),
}))
vi.mock('../../hooks/useSettings', () => ({ useSettings: () => ({ settings: null }) }))
vi.mock('../../hooks/useStream', () => ({
  useStream: () => ({ workingSessionId: null }),
  useStreamUdsnit: (vaelg: (v: { workingSessionId: null }) => unknown) =>
    vaelg({ workingSessionId: null }),
}))
vi.mock('../../lib/api', () => ({
  searchSessions: vi.fn().mockResolvedValue([]),
  getActiveRuns: vi.fn().mockResolvedValue([]),
}))

import { Sidebar } from './Sidebar'

/** Kode-fladen: gruppen «Projekter» vises KUN dér (`GRUPPER_I_MODE`), og det
 *  er netop den fold-ud-linje plusset hoerer til. */
const vis = () => render(<Sidebar surface="code" onSurface={() => {}} userName="Bjørn" />)

beforeEach(() => {
  vi.clearAllMocks()
  ;(window as unknown as Record<string, unknown>).jarvisDesk = { pickFolder }
  create.mockResolvedValue({ id: 'ny-session' })
  setWorkspace.mockResolvedValue(undefined)
})

describe('nyt projekt fra fold-ud-linjen', () => {
  it('staar KUN paa Projekter-raekken, ikke paa de andre grupper', () => {
    const { container } = vis()
    // To grupper rendrer paa kode-fladen (`kode` + `arkiv`), og kun den ene
    // maa baere plusset: paa de andre ville knappen ikke kunne lave noget,
    // for der er ingen mappe at pege paa.
    const raekker = [...container.querySelectorAll('.sidebar-group-raekke')]
    expect(raekker.length).toBeGreaterThan(1)
    const medPlus = raekker.filter((r) => r.querySelector('.sidebar-group-plus'))
    expect(medPlus).toHaveLength(1)
    expect(medPlus[0]?.textContent || '').toContain('Projekter')
  })

  it('vaelger mappen FOER samtalen oprettes', async () => {
    // Raekkefoelgen er hele forskellen: oprettede vi samtalen foerst og
    // brugeren fortrod i dialogen, stod der en tom «Ny samtale» tilbage i
    // listen som ingen havde bedt om.
    pickFolder.mockResolvedValue(null)
    vis()
    screen.getByLabelText('Nyt projekt — vælg en mappe').click()
    await waitFor(() => expect(pickFolder).toHaveBeenCalled())
    expect(create).not.toHaveBeenCalled()
    expect(setWorkspace).not.toHaveBeenCalled()
  })

  it('opretter en KODE-samtale og peger den paa mappen', async () => {
    pickFolder.mockResolvedValue('/home/bs/nyt-projekt')
    vis()
    screen.getByLabelText('Nyt projekt — vælg en mappe').click()
    await waitFor(() => expect(setWorkspace).toHaveBeenCalled())
    expect(create).toHaveBeenCalledWith('Ny samtale', 'code')
    expect(setWorkspace).toHaveBeenCalledWith('ny-session', 'workstation', '/home/bs/nyt-projekt')
  })

  it('folder IKKE gruppen sammen naar man rammer plusset', async () => {
    // Knappen ligger i gruppe-raekken. Uden stopPropagation ville klikket
    // OGSAA ramme overskriften, og gruppen ville klappe i mens dialogen kom.
    pickFolder.mockResolvedValue('/home/bs/nyt-projekt')
    vis()
    const gruppe = screen.getByRole('button', { name: /Projekter/i })
    expect(gruppe.getAttribute('aria-expanded')).toBe('true')
    screen.getByLabelText('Nyt projekt — vælg en mappe').click()
    await waitFor(() => expect(setWorkspace).toHaveBeenCalled())
    expect(gruppe.getAttribute('aria-expanded')).toBe('true')
  })

  it('goer intet uden broen — og braekker ikke', () => {
    ;(window as unknown as Record<string, unknown>).jarvisDesk = {}
    vis()
    screen.getByLabelText('Nyt projekt — vælg en mappe').click()
    expect(create).not.toHaveBeenCalled()
  })
})
