import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

const getAlleSideTasks = vi.fn()
const setSideTaskSkjult = vi.fn()
const setSideTaskStatus = vi.fn()
vi.mock('../../lib/sideTasksApi', () => ({
  getAlleSideTasks: (...a: unknown[]) => getAlleSideTasks(...a),
  setSideTaskSkjult: (...a: unknown[]) => setSideTaskSkjult(...a),
  setSideTaskStatus: (...a: unknown[]) => setSideTaskStatus(...a),
}))

import { SideOpgaveListe } from './SideOpgaveListe'

const cfg = { apiBaseUrl: 'http://x', authToken: 't' }
const opg = (id: string, title: string, extra: Record<string, unknown> = {}) => ({
  side_task_id: id, title, prompt: `Gør ${title} færdigt`, tldr: `kort om ${title}`,
  status: 'pending', session_id: 's', created_at: '2026-10-08T10:00:00Z', ...extra,
})

describe('SideOpgaveListe (headerens sideopgave-panel)', () => {
  beforeEach(() => {
    getAlleSideTasks.mockReset().mockResolvedValue([])
    setSideTaskSkjult.mockReset().mockResolvedValue(undefined)
    setSideTaskStatus.mockReset().mockResolvedValue(undefined)
  })

  it('viser ÅBNE opgaver — også den der er skjult i chatten', async () => {
    // Hele grunden til panelet: Bjørn 8/10-2026 «jeg har intet sted jeg kan se
    // dem». Den skjulte opgave er stadig ÅBEN og skal stå her, ellers er den
    // reelt væk — og det var præcis fejlen krydset begik før.
    getAlleSideTasks.mockResolvedValue([opg('a', 'Første'), opg('b', 'Anden', { skjult_i_chat: true })])
    render(<SideOpgaveListe config={cfg} onClose={() => {}} />)
    expect(await screen.findByText('Første')).toBeInTheDocument()
    expect(screen.getByText('Anden')).toBeInTheDocument()
    expect(screen.getByText('skjult i chat')).toBeInTheDocument()
    expect(screen.getByLabelText('Vis «Anden» i chatten')).toBeInTheDocument()
  })

  it('«Vis i chatten» kalder skjul=false — den anden vej tilbage', async () => {
    getAlleSideTasks.mockResolvedValue([opg('b', 'Anden', { skjult_i_chat: true })])
    render(<SideOpgaveListe config={cfg} onClose={() => {}} />)
    fireEvent.click(await screen.findByLabelText('Vis «Anden» i chatten'))
    await waitFor(() => expect(setSideTaskSkjult).toHaveBeenCalledWith(cfg, 'b', false))
  })

  it('«Markér færdig» afslutter uden mellemtrin', async () => {
    getAlleSideTasks.mockResolvedValue([opg('a', 'Første')])
    render(<SideOpgaveListe config={cfg} onClose={() => {}} />)
    fireEvent.click(await screen.findByLabelText('Markér «Første» færdig'))
    await waitFor(() => expect(setSideTaskStatus).toHaveBeenCalledWith(cfg, 'a', 'completed'))
  })

  it('«Fjern for altid» kræver et ekstra klik før noget afskrives', async () => {
    // Fire klik i et hjørne afskrev fire opgaver 8/10, og ingen kunne fortrydes
    // (`resolve` nægter at genåbne). Det ene irreversible tryk i panelet skal
    // derfor spørge — og det første klik må ikke gøre noget ved serveren.
    getAlleSideTasks.mockResolvedValue([opg('a', 'Første')])
    render(<SideOpgaveListe config={cfg} onClose={() => {}} />)
    fireEvent.click(await screen.findByLabelText('Fjern «Første» for altid'))
    expect(setSideTaskStatus).not.toHaveBeenCalled()
    expect(screen.getByText('Fjern for altid?')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Ja' }))
    await waitFor(() => expect(setSideTaskStatus).toHaveBeenCalledWith(cfg, 'a', 'dismissed'))
  })

  it('«Nej» afbryder uden at afskrive', async () => {
    getAlleSideTasks.mockResolvedValue([opg('a', 'Første')])
    render(<SideOpgaveListe config={cfg} onClose={() => {}} />)
    fireEvent.click(await screen.findByLabelText('Fjern «Første» for altid'))
    fireEvent.click(screen.getByRole('button', { name: 'Nej' }))
    expect(setSideTaskStatus).not.toHaveBeenCalled()
    expect(screen.queryByText('Fjern for altid?')).not.toBeInTheDocument()
  })

  it('lukkede opgaver er foldet væk som standard — de er spor, ikke opgaver', async () => {
    getAlleSideTasks.mockResolvedValue([
      opg('a', 'Første'),
      opg('z', 'Gammel', { status: 'dismissed', resolved_at: '2026-10-01T10:00:00Z' }),
    ])
    render(<SideOpgaveListe config={cfg} onClose={() => {}} />)
    await screen.findByText('Første')
    expect(screen.queryByText('Gammel')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /Lukkede/ }))
    expect(await screen.findByText('Gammel')).toBeInTheDocument()
  })

  it('en fejl er ikke en tom liste', async () => {
    getAlleSideTasks.mockRejectedValue(new Error('kunne ikke hente'))
    render(<SideOpgaveListe config={cfg} onClose={() => {}} />)
    expect(await screen.findByRole('alert')).toHaveTextContent('kunne ikke hente')
  })
})
