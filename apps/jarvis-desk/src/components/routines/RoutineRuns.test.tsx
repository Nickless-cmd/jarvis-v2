import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

const listRoutineRuns = vi.fn().mockResolvedValue([{
  run_id: 'run-1', routine_id: 'routine-1', owner_user_id: 'member-1',
  access_scope: 'user_private', routine_version: 1, status: 'succeeded',
  lease_holder: null, lease_generation: 1, idempotency_key: 'manual:1',
  created_at: '2026-10-13T08:00:00Z',
}])
const listRoutineEvents = vi.fn().mockResolvedValue([
  { event_id: 'event-1', run_id: 'run-1', seq: 1, kind: 'model_fragment',
    payload: { text: 'Det private resultat' }, terminal: false,
    created_at: '2026-10-13T08:00:01Z' },
  { event_id: 'event-2', run_id: 'run-1', seq: 2, kind: 'tool_result',
    payload: { output: 'Værktøjets svar', name: 'safe_tool' }, terminal: false,
    created_at: '2026-10-13T08:00:02Z' },
])
// Resultatet ligger i routine_runs.result_enc og kommer KUN med GET /runs/{id}.
// Listen (list_runs i db-laget) dekrypterer ikke, så den bærer det aldrig.
const getRoutineRun = vi.fn().mockResolvedValue({
  run_id: 'run-1', routine_id: 'routine-1', status: 'succeeded',
  created_at: '2026-10-13T08:00:00Z',
  result: 'Tre middagsopskrifter til ugen: boller i karry, torsk i pakke, gnocchi.',
})

vi.mock('../../lib/routinesApi', async (original) => ({
  ...(await original<typeof import('../../lib/routinesApi')>()),
  listRoutineRuns: (...args: unknown[]) => listRoutineRuns(...args),
  listRoutineEvents: (...args: unknown[]) => listRoutineEvents(...args),
  getRoutineRun: (...args: unknown[]) => getRoutineRun(...args),
}))

import { RoutineRuns } from './RoutineRuns'

describe('RoutineRuns', () => {
  it('shows the observable model and tool output for the authorized run', async () => {
    render(<RoutineRuns
      config={{ apiBaseUrl: 'http://desk.test', authToken: 'token' }}
      routineId="routine-1"
    />)
    const row = await screen.findByRole('button', { name: /succeeded/i })
    fireEvent.click(row)

    await waitFor(() => expect(listRoutineEvents).toHaveBeenCalledWith(
      expect.anything(), 'run-1',
    ))
    expect(await screen.findByText('Det private resultat')).toBeVisible()
    expect(screen.getByText('Værktøjets svar')).toBeVisible()
  })

  it('viser rutinens SAMLEDE resultat — ikke kun de rå hændelser', async () => {
    // Målt 26/10-2026: fladen viste kun routine_run_events, så Michelles
    // madopskrift-rutine fremstod tom mens svaret lå i result_enc. En push
    // uden en flade at åbne er et svar der ikke kan læses.
    render(<RoutineRuns
      config={{ apiBaseUrl: 'http://desk.test', authToken: 'token' }}
      routineId="routine-1"
    />)
    fireEvent.click(await screen.findByRole('button', { name: /succeeded/i }))

    await waitFor(() => expect(getRoutineRun).toHaveBeenCalledWith(
      expect.anything(), 'run-1',
    ))
    expect(await screen.findByText(/Tre middagsopskrifter til ugen/)).toBeVisible()
    expect(screen.getByRole('heading', { name: /resultat/i })).toBeVisible()
  })

  it('siger det hoejt naar et gennemfoert run ikke gemte tekst', async () => {
    getRoutineRun.mockResolvedValueOnce({
      run_id: 'run-1', routine_id: 'routine-1', status: 'succeeded',
      created_at: '2026-10-13T08:00:00Z', result: null,
    })
    render(<RoutineRuns
      config={{ apiBaseUrl: 'http://desk.test', authToken: 'token' }}
      routineId="routine-1"
    />)
    fireEvent.click(await screen.findByRole('button', { name: /succeeded/i }))

    expect(await screen.findByText(/gemte intet tekstresultat/i)).toBeVisible()
  })
})
