import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'

const listProcesses = vi.fn()
const stopProcess = vi.fn()
const removeProcess = vi.fn()
vi.mock('../../lib/processesApi', async () => {
  const rigtig = await vi.importActual<typeof import('../../lib/processesApi')>('../../lib/processesApi')
  return {
    varighed: rigtig.varighed,
    listProcesses: (...a: unknown[]) => listProcesses(...a),
    stopProcess: (...a: unknown[]) => stopProcess(...a),
    removeProcess: (...a: unknown[]) => removeProcess(...a),
  }
})

import { JobsPanel } from './JobsPanel'

const cfg = { apiBaseUrl: 'http://x', authToken: 't' }
const JOBS = [
  { name: 'grid-bot', pid: 1, status: 'running', command: 'python3 -m grid_bot --continuous', uptime_seconds: 11178 },
  { name: 'toku-poller', pid: 2, status: 'running', command: 'node poller.mjs', uptime_seconds: 42 },
  { name: 'gammel', pid: null, status: 'stopped', command: 'ting.sh', exit_code: 1 },
]

beforeEach(() => {
  listProcesses.mockReset().mockResolvedValue(JOBS)
  stopProcess.mockReset().mockResolvedValue(undefined)
  removeProcess.mockReset().mockResolvedValue(undefined)
})

/**
 * Bjørn 8/9-2026: «vi mangler et sted at vise kørende background job … et fold
 * panel som de 2 andre, bare hvor man kan se og lukke jobs.» Formen er Claude
 * Codes egen Background tasks-rude.
 */
describe('JobsPanel', () => {
  it('viser kørende job med kommando og forløbet tid', async () => {
    render(<JobsPanel config={cfg} isOwner onClose={vi.fn()} />)
    expect(await screen.findByText('grid-bot')).toBeInTheDocument()
    // Kommandoen siger HVAD der kører — det er dét man skal bruge for at
    // afgøre om jobbet skal stoppes.
    expect(screen.getByText('python3 -m grid_bot --continuous')).toBeInTheDocument()
    expect(screen.getByText('3t 06m 18s')).toBeInTheDocument()
  })

  it('færdige job er foldet sammen — de kørende må ikke drukne', async () => {
    render(<JobsPanel config={cfg} isOwner onClose={vi.fn()} />)
    await screen.findByText('grid-bot')
    expect(screen.queryByText('gammel')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /Færdige/ }))
    expect(screen.getByText('gammel')).toBeInTheDocument()
    expect(screen.getByText('exit 1')).toBeInTheDocument()
  })

  it('stop kalder serveren og henter listen igen', async () => {
    render(<JobsPanel config={cfg} isOwner onClose={vi.fn()} />)
    await screen.findByText('grid-bot')
    fireEvent.click(screen.getByLabelText('Stop grid-bot'))
    await waitFor(() => expect(stopProcess).toHaveBeenCalledWith(cfg, 'grid-bot'))
    // Listen skal genhentes — ellers står jobbet som kørende til næste poll.
    await waitFor(() => expect(listProcesses.mock.calls.length).toBeGreaterThan(1))
  })

  it('en member ser jobbene, men kan ikke stoppe dem', async () => {
    // Serveren er ejer-gated; knappen skal ikke love noget den ikke kan holde.
    render(<JobsPanel config={cfg} onClose={vi.fn()} />)
    await screen.findByText('grid-bot')
    expect(screen.queryByLabelText('Stop grid-bot')).toBeNull()
  })

  it('siger det tydeligt når intet kører', async () => {
    listProcesses.mockResolvedValue([])
    render(<JobsPanel config={cfg} isOwner onClose={vi.fn()} />)
    expect(await screen.findByText(/Ingenting kører lige nu/)).toBeInTheDocument()
  })

  it('en fejlet hentning vælter ikke panelet', async () => {
    listProcesses.mockRejectedValue(new Error('nede'))
    render(<JobsPanel config={cfg} isOwner onClose={vi.fn()} />)
    expect(await screen.findByText(/kunne ikke hente jobs/)).toBeInTheDocument()
  })
})

describe('tilstande der ikke er «kører» eller «exit N»', () => {
  it('«lost» vises som mistet — ikke som et gættet exit', async () => {
    // pid'en er væk UDEN at vi nåede at se en exit-kode; typisk fordi runtime'en
    // blev genstartet under jobbet. «exit ?» ville være et gæt.
    listProcesses.mockResolvedValue([
      { name: 'grid-bot', pid: 1, status: 'lost', command: 'x', exit_code: null },
    ])
    render(<JobsPanel config={cfg} isOwner onClose={vi.fn()} />)
    fireEvent.click(await screen.findByRole('button', { name: /Færdige/ }))
    expect(screen.getByText('mistet')).toBeInTheDocument()
  })

  it('melder antal kørende op, så tælleren ikke kan modsige listen', async () => {
    const onCount = vi.fn()
    render(<JobsPanel config={cfg} isOwner onCount={onCount} onClose={vi.fn()} />)
    await screen.findByText('grid-bot')
    await waitFor(() => expect(onCount).toHaveBeenCalledWith(2))
  })
})
