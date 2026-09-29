import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, within } from '@testing-library/react'

// `vi.hoisted` fordi `vi.mock` løftes op over hele filen: uden den ville
// mock'en referere en variabel der endnu ikke findes.
const { releaseWorkspace } = vi.hoisted(() => ({ releaseWorkspace: vi.fn() }))

// Bjørn 8/9-2026: «sessioner i side panelet er rodet». 278 chat-sessioner,
// 181 autonome og én proaktiv lå i én flad liste — og indtil samme dag hed
// chat-sessionerne alle sammen «Ny samtale», så navnene hjalp heller ikke.
//
// Testdata er hans faktiske session-typer, målt i runtime.
const SESSIONER = [
  { id: 'chat-aaa', title: 'kan du kigge på gaten', updated_at: 'x', workspace_kind: null },
  { id: 'chat-bbb', title: 'Måtte starte en ny session', updated_at: 'x', workspace_kind: null },
  // Projekt-stien er med fra 16/9-2026: sidepanelet grupperer kode-sessioner
  // efter projekt, som i CC («jarvis-v2 · /media/projects»).
  { id: 'chat-ccc', title: 'ret lige den fil', updated_at: 'x', workspace_kind: 'code',
    workspace_root: '/media/projects/jarvis-v2' },
  { id: 'chat-ddd', title: 'andet projekt', updated_at: 'x', workspace_kind: 'code',
    workspace_root: '/home/bs/andet' },
  { id: 'auto-heartbeat-20260908', title: 'Autonom · Hjerteslag · 2026-09-08', updated_at: 'x' },
  { id: 'auto-dream-20260908', title: 'Autonom · Drømme · 2026-09-08', updated_at: 'x' },
  { id: 'proactivity-bridge', title: '💭 Proaktive spørgsmål', updated_at: 'x' },
]

vi.mock('../../hooks/useSessions', () => ({
  useSessions: () => ({
    sessions: SESSIONER, activeId: null,
    select: vi.fn(), create: vi.fn(), rename: vi.fn(), remove: vi.fn(), newChat: vi.fn(),
    releaseWorkspace,
  }),
}))
vi.mock('../../hooks/useSettings', () => ({ useSettings: () => ({ settings: null }) }))
vi.mock('../../hooks/useStream', () => ({ useStream: () => ({ workingSessionId: null }) }))
vi.mock('../../lib/api', () => ({
  searchSessions: vi.fn().mockResolvedValue([]),
  getActiveRuns: vi.fn().mockResolvedValue([]),
}))

import { Sidebar } from './Sidebar'

const vis = (surface: 'chat' | 'code' = 'chat') =>
  render(<Sidebar surface={surface} onSurface={() => {}} userName="Bjørn" />)
const gruppe = (navn: string) => screen.getByRole('button', { name: new RegExp(navn, 'i') })

describe('sessions-listen er inddelt', () => {
  it('chat-mode viser samtaler og de autonome — ikke kode', () => {
    // Bjørn 8/9-2026: «istedet for at vise chat samtale i code mode og omvendt
    // … sådan de samtaler der hører til det pågældende mode kun bliver vist».
    vis('chat')
    expect(within(gruppe('samtaler')).getByText('2')).toBeInTheDocument()
    expect(within(gruppe('proaktive & autonome')).getByText('3')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /^Projekter/i })).toBeNull()
    expect(screen.queryByText('ret lige den fil')).not.toBeInTheDocument()
  })

  it('code-mode viser KUN kode', () => {
    vis('code')
    expect(within(gruppe('Projekter')).getByText('2')).toBeInTheDocument()
    expect(screen.getByText('ret lige den fil')).toBeInTheDocument()
    expect(screen.queryByText('kan du kigge på gaten')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /proaktive/i })).toBeNull()
  })

  it('de autonome følger chat, ikke kode — de har intet workspace', () => {
    // Havde de ligget begge steder, ville de dukke op to gange, og det er
    // præcis den slags rod inddelingen blev lavet for at fjerne.
    vis('code')
    expect(screen.queryByRole('button', { name: /proaktive/i })).toBeNull()
  })

  it('hans egne samtaler er åbne som udgangspunkt', () => {
    vis()
    expect(screen.getByText('kan du kigge på gaten')).toBeInTheDocument()
  })

  it('søgefeltet er væk — søgningen bor i Ctrl+K-paletten', () => {
    // Feltet kaldte samme `searchSessions` som paletten og viste samme uddrag.
    // To indgange til én funktion, hvor den ene tog fast plads i panelet.
    vis()
    expect(screen.queryByPlaceholderText(/Søg i samtaler/i)).toBeNull()
  })

  it('søge-ikonet i toppen åbner paletten', () => {
    const onSearch = vi.fn()
    render(<Sidebar surface="chat" onSurface={() => {}} userName="Bjørn" onSearch={onSearch} />)
    fireEvent.click(screen.getByLabelText(/Søg \(Ctrl\+K\)/i))
    expect(onSearch).toHaveBeenCalled()
  })

  it('de autonome er FOLDET SAMMEN — 181 kørsler ville drukne resten', () => {
    vis()
    expect(screen.queryByText('Autonom · Hjerteslag · 2026-09-08')).not.toBeInTheDocument()
    expect(screen.queryByText('💭 Proaktive spørgsmål')).not.toBeInTheDocument()
    expect(gruppe('proaktive & autonome')).toHaveAttribute('aria-expanded', 'false')
  })

  it('de kan foldes ud', () => {
    vis()
    fireEvent.click(gruppe('proaktive & autonome'))
    expect(screen.getByText('💭 Proaktive spørgsmål')).toBeInTheDocument()
    expect(gruppe('proaktive & autonome')).toHaveAttribute('aria-expanded', 'true')
  })

  it('og hans egne kan foldes sammen', () => {
    vis()
    fireEvent.click(gruppe('samtaler'))
    expect(screen.queryByText('kan du kigge på gaten')).not.toBeInTheDocument()
  })
})

describe('projekt-overskrifter i kode-tilstand', () => {
  it('viser projektet over sessionerne — navn og sti hver for sig', () => {
    vis('code')
    expect(screen.getByText('jarvis-v2')).toBeInTheDocument()
    expect(screen.getByText('/media/projects')).toBeInTheDocument()
    expect(screen.getByText('andet')).toBeInTheDocument()
  })

  it('sessionerne staar under DERES eget projekt', () => {
    vis('code')
    expect(screen.getByText('ret lige den fil')).toBeInTheDocument()
    expect(screen.getByText('andet projekt')).toBeInTheDocument()
  })

  it('chat-tilstand faar INGEN projekt-overskrift', () => {
    // Chat-sessioner har intet workspace; en overskrift ville vaere en gruppe
    // uden indhold.
    vis('chat')
    expect(screen.queryByText('Uden projekt')).not.toBeInTheDocument()
    expect(screen.queryByText('jarvis-v2')).not.toBeInTheDocument()
  })

  it('projekt-menuen kan fjerne projektet — den eneste vej UD af en forkert mappe', () => {
    // Projektet ER `workspace_root`, saa «Fjern projekt» løsner hver samtale i
    // gruppen. Der er ingen tabel at slette en række i — og derfor heller ikke
    // to handlinger: «Løsn alle samtaler» ville være samme knap med et andet
    // navn (Bjørn 29/9-2026).
    releaseWorkspace.mockClear()
    vis('code')
    // Menuen sidder paa projekt-OVERSKRIFTEN, ikke paa raekkerne. Der er to
    // projekter i testdata, saa vi maa gaa ind via overskriftens eget navn.
    const overskrift = screen.getByText('jarvis-v2').closest('.sidebar-projekt') as HTMLElement
    fireEvent.click(within(overskrift).getByRole('button', { name: /Projekt-handlinger/i }))
    fireEvent.click(screen.getByRole('button', { name: /Fjern projekt/i }))
    // Kun samtalens eget projekt — den anden gruppe maa ikke rammes.
    expect(releaseWorkspace).toHaveBeenCalledWith('chat-ccc')
    expect(releaseWorkspace).not.toHaveBeenCalledWith('chat-ddd')
  })
})
