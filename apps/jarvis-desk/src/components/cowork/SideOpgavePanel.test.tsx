import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('../../lib/sideTasksApi', () => ({
  getAlleSideTasks: vi.fn(),
  setSideTaskStatus: vi.fn(),
}))

// Se SideOpgaveListe.test.tsx: strømmen er transport, ikke komponent-adfærd.
vi.mock('../../lib/sideTasksStream', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../lib/sideTasksStream')>()
  return { ...actual, startSideTasksStream: () => ({ abort: () => {} }) }
})
import { getAlleSideTasks, setSideTaskStatus } from '../../lib/sideTasksApi'
import { SideOpgavePanel } from './SideOpgavePanel'

const cfg = { apiBaseUrl: 'http://x', authToken: 't' }
const post = (o: Partial<Record<string, unknown>> = {}) => ({
  side_task_id: 'side-1', title: 'Fix tests', prompt: 'p', tldr: '', status: 'pending',
  session_id: 's', created_at: '2026-10-03T13:14:33+00:00', ...o,
})

describe('SideOpgavePanel', () => {
  beforeEach(() => {
    vi.mocked(getAlleSideTasks).mockReset().mockResolvedValue([])
    vi.mocked(setSideTaskStatus).mockReset().mockResolvedValue(undefined)
  })

  it('viser ogsaa de LUKKEDE — det var hele manglen', async () => {
    // Bjoern 3/10: «desk har ikk noget panel der viser opgaver der er flagged
    // selv om jeg har trykket dem vaek». Maalt: alle seks poster i hans fil
    // var terminale, saa kortet i chatten var KORREKT tomt — men umuligt at
    // skelne fra tabt data.
    vi.mocked(getAlleSideTasks).mockResolvedValue([
      post({ side_task_id: 'side-a', title: 'Lukket af automatikken', status: 'completed',
             resolved_at: '2026-10-03T13:37:13+00:00', lukket_af: 'auto:stilstand 42min' }),
      post({ side_task_id: 'side-b', title: 'Stadig aaben', status: 'activated' }),
    ] as never)
    render(<SideOpgavePanel config={cfg} />)
    expect(await screen.findByText('Lukket af automatikken')).toBeInTheDocument()
    expect(screen.getByText('Stadig aaben')).toBeInTheDocument()
    // Og det skal kunne SES hvem der lukkede den — ellers er sporet ubrugeligt.
    expect(screen.getByText(/auto:stilstand 42min/)).toBeInTheDocument()
    expect(screen.getByText('1 åbne · 1 lukkede', { exact: false })).toBeInTheDocument()
  })

  it('en TOM liste og en FEJL er ikke det samme', async () => {
    // Praecis den forvirring der startede det hele: «er den lukket, eller gik
    // den tabt?». En fejl skal sige fejl.
    vi.mocked(getAlleSideTasks).mockRejectedValue(new Error('403 forbudt'))
    render(<SideOpgavePanel config={cfg} />)
    expect(await screen.findByRole('alert')).toHaveTextContent('403 forbudt')
    expect(screen.queryByText(/har ikke flagget nogen opgaver/)).toBeNull()
  })

  it('tom liste siger det tydeligt', async () => {
    render(<SideOpgavePanel config={cfg} />)
    expect(await screen.findByText(/har ikke flagget nogen opgaver endnu/)).toBeInTheDocument()
  })

  it('en LUKKET opgave kan ikke lukkes igen — ingen knapper', async () => {
    vi.mocked(getAlleSideTasks).mockResolvedValue([
      post({ status: 'dismissed', resolved_at: '2026-10-03T13:37:13+00:00' }),
    ] as never)
    render(<SideOpgavePanel config={cfg} />)
    await screen.findByText('Fix tests')
    expect(screen.queryByRole('button', { name: 'Markér færdig' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Fjern' })).toBeNull()
  })

  it('en AABEN opgave kan lukkes herfra — men KUN med et bevis (16/10-2026)', async () => {
    // Bjoern: «Krav ved completed — men dismissed med begrundelse er altid en
    // vej ud». Et tomt felt er ikke en begrundelse; formen fanger det FOER
    // kaldet, saa et afvist server-svar ikke ser ud som en doed knap.
    vi.mocked(getAlleSideTasks).mockResolvedValue([post({ status: 'activated' })] as never)
    render(<SideOpgavePanel config={cfg} />)
    await userEvent.click(await screen.findByRole('button', { name: 'Markér færdig' }))
    expect(setSideTaskStatus).not.toHaveBeenCalled()

    const felt = await screen.findByLabelText(/Hvad blev gjort/)
    await userEvent.type(felt, 'ok')
    await userEvent.click(screen.getByRole('button', { name: 'Bekræft færdig' }))
    expect(setSideTaskStatus).not.toHaveBeenCalled()
    expect(await screen.findByRole('alert')).toHaveTextContent(/hvad der faktisk blev gjort/i)

    await userEvent.clear(felt)
    await userEvent.type(felt, 'Rettet i commit abc1234')
    await userEvent.click(screen.getByRole('button', { name: 'Bekræft færdig' }))
    await waitFor(() => expect(setSideTaskStatus).toHaveBeenCalledWith(
      cfg, 'side-1', 'completed', { bevis: 'Rettet i commit abc1234' }))
    expect(vi.mocked(getAlleSideTasks).mock.calls.length).toBeGreaterThan(1)
  })

  it('«Fjern» kraever en grund og sender den som reason', async () => {
    vi.mocked(getAlleSideTasks).mockResolvedValue([post({ status: 'pending' })] as never)
    render(<SideOpgavePanel config={cfg} />)
    await userEvent.click(await screen.findByRole('button', { name: 'Fjern' }))
    const felt = await screen.findByLabelText(/Hvorfor skal den ikke løses/)
    await userEvent.type(felt, 'duplikat af en anden opgave')
    await userEvent.click(screen.getByRole('button', { name: 'Bekræft fjern' }))
    await waitFor(() => expect(setSideTaskStatus).toHaveBeenCalledWith(
      cfg, 'side-1', 'dismissed', { reason: 'duplikat af en anden opgave' }))
  })

  it('lukningen kan SES bagefter — beviset staar paa posten', async () => {
    vi.mocked(getAlleSideTasks).mockResolvedValue([
      post({ status: 'completed', resolved_at: '2026-10-16T20:00:00+00:00',
             bevis: 'Commit 0ddcd976b landede' }),
      post({ side_task_id: 'side-2', status: 'dismissed', resolved_at: '2026-10-16T20:00:00+00:00',
             dismiss_reason: 'ikke laengere relevant' }),
    ] as never)
    render(<SideOpgavePanel config={cfg} />)
    expect(await screen.findByText(/Commit 0ddcd976b landede/)).toBeInTheDocument()
    expect(screen.getByText(/ikke laengere relevant/)).toBeInTheDocument()
  })

  it('status-ordene er paa dansk og ikke rå felter', async () => {
    vi.mocked(getAlleSideTasks).mockResolvedValue([
      post({ side_task_id: 'a', status: 'pending' }),
      post({ side_task_id: 'q', status: 'queued' }),
      post({ side_task_id: 'b', status: 'activated' }),
      post({ side_task_id: 'c', status: 'completed', resolved_at: '2026-10-03T13:37:13+00:00' }),
      post({ side_task_id: 'd', status: 'dismissed', resolved_at: '2026-10-03T13:37:13+00:00' }),
    ] as never)
    render(<SideOpgavePanel config={cfg} />)
    for (const ord of ['Venter', 'I kø', 'I gang', 'Færdig', 'Fjernet']) {
      expect(await screen.findByText(ord)).toBeInTheDocument()
    }
    expect(screen.getByText('3 åbne · 2 lukkede', { exact: false })).toBeInTheDocument()
  })
})
