import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, within } from '@testing-library/react'

// Bjørn 8/9-2026: «sessioner i side panelet er rodet». 278 chat-sessioner,
// 181 autonome og én proaktiv lå i én flad liste — og indtil samme dag hed
// chat-sessionerne alle sammen «Ny samtale», så navnene hjalp heller ikke.
//
// Testdata er hans faktiske session-typer, målt i runtime.
const SESSIONER = [
  { id: 'chat-aaa', title: 'kan du kigge på gaten', updated_at: 'x', workspace_kind: null },
  { id: 'chat-bbb', title: 'Måtte starte en ny session', updated_at: 'x', workspace_kind: null },
  { id: 'chat-ccc', title: 'ret lige den fil', updated_at: 'x', workspace_kind: 'code' },
  { id: 'auto-heartbeat-20260908', title: 'Autonom · Hjerteslag · 2026-09-08', updated_at: 'x' },
  { id: 'auto-dream-20260908', title: 'Autonom · Drømme · 2026-09-08', updated_at: 'x' },
  { id: 'proactivity-bridge', title: '💭 Proaktive spørgsmål', updated_at: 'x' },
]

vi.mock('../../hooks/useSessions', () => ({
  useSessions: () => ({
    sessions: SESSIONER, activeId: null,
    select: vi.fn(), create: vi.fn(), rename: vi.fn(), remove: vi.fn(), newChat: vi.fn(),
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
    expect(screen.queryByRole('button', { name: /^kode/i })).toBeNull()
    expect(screen.queryByText('ret lige den fil')).not.toBeInTheDocument()
  })

  it('code-mode viser KUN kode', () => {
    vis('code')
    expect(within(gruppe('kode')).getByText('1')).toBeInTheDocument()
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
