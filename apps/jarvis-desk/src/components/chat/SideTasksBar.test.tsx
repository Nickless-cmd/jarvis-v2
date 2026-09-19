import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

const getSideTasks = vi.fn()
const setSideTaskStatus = vi.fn()
vi.mock('../../lib/sideTasksApi', () => ({
  getSideTasks: (...a: unknown[]) => getSideTasks(...a),
  setSideTaskStatus: (...a: unknown[]) => setSideTaskStatus(...a),
}))

import { SideTasksBar } from './SideTasksBar'

const cfg = { apiBaseUrl: 'http://x', authToken: 't' }
const opg = (id: string, title: string, extra: Record<string, unknown> = {}) => ({
  side_task_id: id, title, prompt: `Gør ${title} helt færdigt`, tldr: `kort om ${title}`,
  status: 'pending', session_id: 's', created_at: '2026-09-19T10:00:00Z', ...extra,
})

describe('SideTasksBar', () => {
  beforeEach(() => { getSideTasks.mockReset(); setSideTaskStatus.mockReset() })

  it('viser antal, titel, kort beskrivelse og «i gang» — detaljerne kan foldes ud', async () => {
    getSideTasks.mockResolvedValue([opg('side-1', 'Ryd op', { status: 'activated' }), opg('side-2', 'Opdater README')])
    render(<SideTasksBar config={cfg} />)
    expect(await screen.findByText('Ryd op')).toBeInTheDocument()
    expect(screen.getByText('2')).toBeInTheDocument()
    expect(screen.getByText('kort om Ryd op')).toBeInTheDocument()
    expect(screen.getByText('i gang')).toBeInTheDocument()
    expect(screen.queryByText('Gør Ryd op helt færdigt')).toBeNull()
    fireEvent.click(screen.getByLabelText('Vis detaljer for Ryd op'))
    expect(screen.getByText('Gør Ryd op helt færdigt')).toBeInTheDocument()
  })

  it('Færdig fjerner rækken straks og henter igen', async () => {
    getSideTasks.mockResolvedValueOnce([opg('side-1', 'Ryd op'), opg('side-2', 'README')]).mockResolvedValue([opg('side-2', 'README')])
    setSideTaskStatus.mockResolvedValue(undefined)
    render(<SideTasksBar config={cfg} />)
    await screen.findByText('Ryd op')
    fireEvent.click(screen.getAllByRole('button', { name: 'Færdig' })[0]!)
    await waitFor(() => expect(screen.queryByText('Ryd op')).toBeNull())
    expect(setSideTaskStatus).toHaveBeenCalledWith(cfg, 'side-1', 'completed')
    expect(getSideTasks).toHaveBeenCalledTimes(2)
  })

  it('Fjern der fejler lader rækken staa med fejlen', async () => {
    getSideTasks.mockResolvedValue([opg('side-1', 'Ryd op')])
    setSideTaskStatus.mockRejectedValue(new Error('HTTP 500'))
    render(<SideTasksBar config={cfg} />)
    await screen.findByText('Ryd op')
    fireEvent.click(screen.getByRole('button', { name: 'Fjern' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('HTTP 500')
    expect(screen.getByText('Ryd op')).toBeInTheDocument()
    expect(setSideTaskStatus).toHaveBeenCalledWith(cfg, 'side-1', 'dismissed')
  })

  it('netvaerksfejl bevarer den senest kendte liste', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    getSideTasks.mockResolvedValueOnce([opg('side-1', 'Ryd op')]).mockRejectedValue(new Error('Failed to fetch'))
    render(<SideTasksBar config={cfg} />)
    await screen.findByText('Ryd op')
    await vi.advanceTimersByTimeAsync(6500)
    expect(getSideTasks).toHaveBeenCalledTimes(2)
    expect(screen.getByText('Ryd op')).toBeInTheDocument()
    vi.useRealTimers()
  })

  it('ikke ejer (403): intet vises, og der spoerges ikke igen', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    getSideTasks.mockRejectedValue(new Error('HTTP 403: Kun ejeren kan se sideopgaverne'))
    render(<SideTasksBar config={cfg} />)
    await vi.advanceTimersByTimeAsync(13000)
    expect(getSideTasks).toHaveBeenCalledTimes(1)
    expect(screen.queryByTestId('side-tasks')).toBeNull()
    vi.useRealTimers()
  })

  it('ingen aabne opgaver = ingenting', async () => {
    getSideTasks.mockResolvedValue([])
    render(<SideTasksBar config={cfg} />)
    await waitFor(() => expect(getSideTasks).toHaveBeenCalled())
    expect(screen.queryByTestId('side-tasks')).toBeNull()
  })
})
