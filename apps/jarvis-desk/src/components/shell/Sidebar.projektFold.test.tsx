import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'

// Bjørn 15/11-2026: «projekter under projekter i venstre panel i code mode
// skal have fold pil i enden af projektnavnet så man kan folde det enkelte
// projekt».
//
// To projekter i testdata, så testen kan bevise at folden rammer SIT eget
// projekt og ikke hele kode-gruppen.
const SESSIONER = [
  { id: 'chat-ccc', title: 'ret lige den fil', updated_at: 'x', workspace_kind: 'code',
    workspace_root: '/media/projects/jarvis-v2' },
  { id: 'chat-eee', title: 'ogsaa jarvis-v2', updated_at: 'x', workspace_kind: 'code',
    workspace_root: '/media/projects/jarvis-v2' },
  { id: 'chat-ddd', title: 'andet projekt', updated_at: 'x', workspace_kind: 'code',
    workspace_root: '/home/bs/andet' },
]

vi.mock('../../hooks/useSessions', () => ({
  useSessions: () => ({
    sessions: SESSIONER, activeId: null,
    select: vi.fn(), create: vi.fn(), rename: vi.fn(), remove: vi.fn(), newChat: vi.fn(),
    releaseWorkspace: vi.fn(),
  }),
}))
vi.mock('../../hooks/useSettings', () => ({ useSettings: () => ({ settings: null }) }))
vi.mock('../../hooks/useStream', () => ({
  useStream: () => ({ workingSessionId: null }),
  useStreamUdsnit: (vaelg: (v: any) => unknown) => vaelg(({ workingSessionId: null })),
}))
vi.mock('../../lib/api', () => ({
  searchSessions: vi.fn().mockResolvedValue([]),
  getActiveRuns: vi.fn().mockResolvedValue([]),
}))

import { Sidebar } from './Sidebar'

const vis = () => render(<Sidebar surface="code" onSurface={() => {}} userName="Bjørn" />)

beforeEach(() => {
  // Fold-tilstanden huskes i localStorage — ellers bærer den over mellem tests.
  localStorage.clear()
})

describe('projekt-fold i kode-tilstand', () => {
  it('hvert projekt har en fold-pil, og projekterne er aabne som udgangspunkt', () => {
    vis()
    expect(screen.getByRole('button', { name: 'Fold jarvis-v2 sammen' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Fold andet sammen' })).toBeInTheDocument()
    expect(screen.getByText('ret lige den fil')).toBeInTheDocument()
    expect(screen.getByText('andet projekt')).toBeInTheDocument()
  })

  it('folden skjuler NETOP dette projekts samtaler — det andet staar urørt', () => {
    vis()
    fireEvent.click(screen.getByRole('button', { name: 'Fold jarvis-v2 sammen' }))
    expect(screen.queryByText('ret lige den fil')).toBeNull()
    expect(screen.queryByText('ogsaa jarvis-v2')).toBeNull()
    // Nabo-projektet maa ikke foelge med: folden er pr. projekt, ikke pr. gruppe.
    expect(screen.getByText('andet projekt')).toBeInTheDocument()
    // Overskriften bliver staaende — det er den man folder ud igen med.
    expect(screen.getByRole('button', { name: 'Fold jarvis-v2 ud' })).toBeInTheDocument()
  })

  it('folden kan aabnes igen', () => {
    vis()
    const pil = () => screen.getByRole('button', { name: /^Fold jarvis-v2/ })
    fireEvent.click(pil())
    expect(screen.queryByText('ret lige den fil')).toBeNull()
    fireEvent.click(pil())
    expect(screen.getByText('ret lige den fil')).toBeInTheDocument()
  })

  it('folden huskes naar panelet rendres igen — den springer ikke op ved hvert poll', () => {
    const foerste = vis()
    fireEvent.click(screen.getByRole('button', { name: 'Fold jarvis-v2 sammen' }))
    foerste.unmount()

    vis()
    expect(screen.queryByText('ret lige den fil')).toBeNull()
    expect(screen.getByRole('button', { name: 'Fold jarvis-v2 ud' })).toBeInTheDocument()
  })
})
