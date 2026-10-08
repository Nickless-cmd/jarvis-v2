import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

const getSideTasks = vi.fn()
const setSideTaskStatus = vi.fn()
const setSideTaskSkjult = vi.fn()
vi.mock('../../lib/sideTasksApi', () => ({
  getSideTasks: (...a: unknown[]) => getSideTasks(...a),
  setSideTaskStatus: (...a: unknown[]) => setSideTaskStatus(...a),
  setSideTaskSkjult: (...a: unknown[]) => setSideTaskSkjult(...a),
}))

import { SideOpgaveKort, type SideOpgaveHandlinger } from './SideOpgaveKort'

const cfg = { apiBaseUrl: 'http://x', authToken: 't' }
const opg = (id: string, title: string, extra: Record<string, unknown> = {}) => ({
  side_task_id: id, title, prompt: `Gør ${title} færdigt`, tldr: `kort om ${title}`,
  status: 'pending', session_id: 's', created_at: '2026-09-19T10:00:00Z', ...extra,
})
type Mock = ReturnType<typeof vi.fn>
const h = (): SideOpgaveHandlinger & { startLokalt: Mock; baggrund: Mock; loesHer: Mock; worktree: Mock } => ({
  // Handlerne returnerer id'et paa den samtale der LOESER opgaven (3/10-2026).
  startLokalt: vi.fn().mockResolvedValue('chat-ny'),
  baggrund: vi.fn().mockResolvedValue('chat-bg'),
  loesHer: vi.fn().mockReturnValue('chat-her'),
  worktree: vi.fn().mockResolvedValue(undefined),
})

describe('SideOpgaveKort (CC «Suggested task»)', () => {
  beforeEach(() => {
    getSideTasks.mockReset()
    setSideTaskStatus.mockReset().mockResolvedValue(undefined)
    setSideTaskSkjult.mockReset().mockResolvedValue(undefined)
  })

  it.each([
    [1, false, false],
    [2, true, false],
    [3, true, true],
  ])('%i sideopgaver giver det rigtige antal kort i stakken', async (antal, stablet, treLag) => {
    getSideTasks.mockResolvedValue(Array.from({ length: antal }, (_, nr) => opg(`id-${nr}`, `Opgave ${nr + 1}`)))
    render(<SideOpgaveKort config={cfg} handlinger={h()} />)
    const kort = await screen.findByTestId('side-tasks')
    expect(kort.parentElement).toHaveClass('sok-dok')
    expect(kort.parentElement?.classList.contains('sok-dok-stak')).toBe(stablet)
    expect(kort.parentElement?.classList.contains('sok-dok-stak-tre')).toBe(treLag)
  })

  it('et kort ad gangen, stablet, med «1 af 3» og bladring', async () => {
    getSideTasks.mockResolvedValue([opg('a', 'Første'), opg('b', 'Anden'), opg('c', 'Tredje')])
    render(<SideOpgaveKort config={cfg} handlinger={h()} />)
    expect(await screen.findByText('Første')).toBeInTheDocument()
    expect(screen.getByText('1 af 3')).toBeInTheDocument()
    expect(screen.getByTestId('side-tasks')).toHaveClass('sok-stak')
    expect(screen.getByLabelText('Forrige sideopgave')).toBeDisabled()
    fireEvent.click(screen.getByLabelText('Næste sideopgave'))
    expect(screen.getByText('Anden')).toBeInTheDocument()
    expect(screen.getByText('kort om Anden')).toBeInTheDocument()
    expect(screen.getByText('2 af 3')).toBeInTheDocument()
  })

  it('med worktree er det standard; menuen har resten og «Markér som færdig»', async () => {
    getSideTasks.mockResolvedValue([opg('a', 'Første')])
    render(<SideOpgaveKort config={cfg} handlinger={h()} />)
    expect(await screen.findByRole('button', { name: 'Start i worktree' })).toBeInTheDocument()
    fireEvent.click(screen.getByLabelText('Flere valg'))
    const punkter = screen.getAllByRole('menuitem').map((b) => b.textContent)
    expect(punkter).toEqual(['Start i worktreeStandard', 'Start i ny samtale', 'Send til baggrunden', 'Løs i denne samtale', 'Sæt i kø', 'Markér som færdig'])
  })

  it('uden worktree (chat) er «Start i ny samtale» standard', async () => {
    getSideTasks.mockResolvedValue([opg('a', 'Første')])
    const { worktree: _w, ...uden } = h()
    render(<SideOpgaveKort config={cfg} handlinger={uden} />)
    expect(await screen.findByRole('button', { name: 'Start i ny samtale' })).toBeInTheDocument()
    fireEvent.click(screen.getByLabelText('Flere valg'))
    expect(screen.queryByRole('menuitem', { name: /worktree/ })).toBeNull()
  })

  it.each([
    ['Start i ny samtale', 'startLokalt'],
    ['Send til baggrunden', 'baggrund'],
    ['Løs i denne samtale', 'loesHer'],
  ])('%s kalder %s og saetter opgaven i gang', async (navn, handling) => {
    // En lille falsk server der HUSKER status — kortet henter igen efter
    // hvert skift, og så skal svaret være det serveren nu har.
    const server = [opg('a', 'Første')]
    getSideTasks.mockImplementation(async () => server.map((x) => ({ ...x })))
    setSideTaskStatus.mockImplementation(async (_c, id, st) => { const x = server.find((y) => y.side_task_id === id); if (x) x.status = st })
    const hh = h()
    render(<SideOpgaveKort config={cfg} handlinger={hh} />)
    await screen.findByText('Første')
    fireEvent.click(screen.getByLabelText('Flere valg'))
    fireEvent.click(screen.getByRole('menuitem', { name: new RegExp(`^${navn}`) }))
    await waitFor(() => expect(hh[handling as 'startLokalt']).toHaveBeenCalledWith(expect.objectContaining({ side_task_id: 'a' })))
    // Arbejds-sessionen skal FOELGE MED. Uden den kan serveren ikke knytte
    // turen til opgaven, og saa er der ingen der kan lukke den — det var
    // praecis fejlen Bjoern saa 3/10 («maatte jeg minde ham om at markere
    // den flaggede opgave faerdig»).
    const forventet = { startLokalt: 'chat-ny', baggrund: 'chat-bg', loesHer: 'chat-her' }[handling as 'startLokalt']
    await waitFor(() => expect(setSideTaskStatus).toHaveBeenCalledWith(cfg, 'a', 'activated', forventet))
    expect(await screen.findByText('i gang')).toBeInTheDocument()
  })

  it('× SKJULER opgaven i chatten — den afskrives ikke; «Markér som færdig» afslutter den', async () => {
    // Bjørn 8/10-2026: «sørg for X'et ikk sletter dem men bare fjerner dem fra
    // chatview». Før kaldte krydset `setSideTaskStatus(…, 'dismissed')`, og det
    // er TERMINALT — `resolve` nægter at genåbne, og fire klik i et hjørne
    // afskrev fire opgaver for altid. Testen holder fast i at krydset ikke må
    // røre status overhovedet.
    getSideTasks.mockResolvedValueOnce([opg('a', 'Første'), opg('b', 'Anden')]).mockResolvedValue([opg('b', 'Anden')])
    render(<SideOpgaveKort config={cfg} handlinger={h()} />)
    await screen.findByText('Første')
    fireEvent.click(screen.getByLabelText('Skjul i chatten'))
    await waitFor(() => expect(setSideTaskSkjult).toHaveBeenCalledWith(cfg, 'a', true))
    expect(setSideTaskStatus).not.toHaveBeenCalledWith(cfg, 'a', 'dismissed')
    expect(await screen.findByText('Anden')).toBeInTheDocument()
    fireEvent.click(screen.getByLabelText('Flere valg'))
    fireEvent.click(screen.getByRole('menuitem', { name: 'Markér som færdig' }))
    await waitFor(() => expect(setSideTaskStatus).toHaveBeenCalledWith(cfg, 'b', 'completed'))
  })

  it('sæt i kø ændrer status uden at starte en samtale', async () => {
    const server = [opg('a', 'Første')]
    getSideTasks.mockImplementation(async () => server.map((x) => ({ ...x })))
    setSideTaskStatus.mockImplementation(async (_c, id, st) => { const x = server.find((y) => y.side_task_id === id); if (x) x.status = st })
    const hh = h()
    render(<SideOpgaveKort config={cfg} handlinger={hh} />)
    await screen.findByText('Første')
    fireEvent.click(screen.getByLabelText('Flere valg'))
    fireEvent.click(screen.getByRole('menuitem', { name: 'Sæt i kø' }))
    await waitFor(() => expect(setSideTaskStatus).toHaveBeenCalledWith(cfg, 'a', 'queued'))
    expect(hh.startLokalt).not.toHaveBeenCalled()
    expect(hh.baggrund).not.toHaveBeenCalled()
    expect(await screen.findByText('i kø')).toBeInTheDocument()
  })

  it('en start der fejler viser fejlen og saetter IKKE opgaven i gang', async () => {
    getSideTasks.mockResolvedValue([opg('a', 'Første')])
    const hh = h()
    hh.worktree.mockRejectedValue(new Error('Kunne ikke oprette worktree'))
    render(<SideOpgaveKort config={cfg} handlinger={hh} />)
    fireEvent.click(await screen.findByRole('button', { name: 'Start i worktree' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Kunne ikke oprette worktree')
    expect(setSideTaskStatus).not.toHaveBeenCalled()
  })

  it('ikke ejer (403): intet vises, og der spoerges ikke igen', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    getSideTasks.mockRejectedValue(new Error('HTTP 403: Kun ejeren'))
    render(<SideOpgaveKort config={cfg} handlinger={h()} />)
    await vi.advanceTimersByTimeAsync(13000)
    expect(getSideTasks).toHaveBeenCalledTimes(1)
    expect(screen.queryByTestId('side-tasks')).toBeNull()
    vi.useRealTimers()
  })

  it('netvaerksfejl beholder det kendte kort', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    getSideTasks.mockResolvedValueOnce([opg('a', 'Første')]).mockRejectedValue(new Error('Failed to fetch'))
    render(<SideOpgaveKort config={cfg} handlinger={h()} />)
    await screen.findByText('Første')
    await vi.advanceTimersByTimeAsync(6500)
    expect(screen.getByText('Første')).toBeInTheDocument()
    vi.useRealTimers()
  })
})

describe('kortet findes kun i CodeView', () => {
  // Sideopgaver er nu samtale-scope i code, og tegnes ikke i almindelig chat.
  it.each(['ChatView', 'CodeView'])('%s tegner <SideOpgaveKort>', async (vis) => {
    const fs = await import('node:fs')
    const path = await import('node:path')
    const ts = await import('typescript')
    const kilde = fs.readFileSync(path.resolve(__dirname, `../../views/${vis}.tsx`), 'utf8')
    const sf = ts.createSourceFile(`${vis}.tsx`, kilde, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX)
    let fundet = 0
    const besoeg = (n: import('typescript').Node) => {
      if ((ts.isJsxSelfClosingElement(n) || ts.isJsxOpeningElement(n)) && n.tagName.getText(sf) === 'SideOpgaveKort') fundet++
      ts.forEachChild(n, besoeg)
    }
    besoeg(sf)
    expect(fundet).toBe(vis === 'CodeView' ? 1 : 0)
  })
})
