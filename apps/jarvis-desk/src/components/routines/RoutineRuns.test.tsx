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

const CONFIG = { apiBaseUrl: 'http://desk.test', authToken: 'token' }

const aabn = async (instruction?: string) => {
  render(<RoutineRuns config={CONFIG} routineId="routine-1" instruction={instruction} />)
  fireEvent.click(await screen.findByRole('button', { name: /succeeded/i }))
}

/** Folden måles på `open`-attributten frem for på toBeVisible: attributten er
 *  den faktiske tilstand, mens synligheds-assertioner afhænger af hvordan
 *  jsdom-versionen behandler <details> — og den målte jeg ikke på forhånd. */
const detaljeFold = () => document.querySelector('details.routine-events')

describe('RoutineRuns', () => {
  it('viser rutinens SAMLEDE resultat — ikke kun de rå hændelser', async () => {
    // Målt 26/10-2026: fladen viste kun routine_run_events, så Michelles
    // madopskrift-rutine fremstod tom mens svaret lå i result_enc. En push
    // uden en flade at åbne er et svar der ikke kan læses.
    await aabn()

    await waitFor(() => expect(getRoutineRun).toHaveBeenCalledWith(
      expect.anything(), 'run-1',
    ))
    expect(await screen.findByText(/Tre middagsopskrifter til ugen/)).toBeVisible()
    expect(screen.getByRole('heading', { name: /svar/i })).toBeVisible()
  })

  it('renderer svaret som markdown — ikke som rå tekst', async () => {
    // Målt 27/10-2026: `detail.result` blev skrevet ind i en rå <div>, så
    // **fed**, lister og overskrifter stod som tegn. Et svar der skal læses
    // skal gennem samme renderer som chatten.
    getRoutineRun.mockResolvedValueOnce({
      run_id: 'run-1', routine_id: 'routine-1', status: 'succeeded',
      created_at: '2026-10-13T08:00:00Z',
      result: 'Ugens **bedste** ret er torsk i pakke.',
    })
    await aabn()

    const fed = await screen.findByText('bedste')
    expect(fed.tagName).toBe('STRONG')
    expect(screen.queryByText(/\*\*bedste\*\*/)).toBeNull()
  })

  it('viser rutinens opgave sammen med svaret', async () => {
    // En kørsel uden sin opgave er et svar uden spørgsmål: man kan ikke se
    // hvad rutinen blev bedt om at gøre.
    await aabn('Lav tre middagsopskrifter til ugen')

    expect(await screen.findByText('Lav tre middagsopskrifter til ugen')).toBeVisible()
    expect(screen.getByRole('heading', { name: /opgave/i })).toBeVisible()
  })

  it('holder hændelser og rå tool-payload bag en fold der er LUKKET som standard', async () => {
    // Målt 27/10-2026: `<details ... open>` betød at ALLE hændelser stod åbne
    // fra start, med rå tool-JSON dumpet ind i tidslinjen.
    await aabn()

    await waitFor(() => expect(detaljeFold()).not.toBeNull())
    const fold = detaljeFold()!
    expect(fold.hasAttribute('open')).toBe(false)

    // Payloaden findes stadig — den er bare ikke det man møder først.
    fireEvent.click(screen.getByText(/^Teknisk log/))
    expect(await screen.findByText('Værktøjets svar')).toBeVisible()
    expect(screen.getByText('Det private resultat')).toBeVisible()
  })

  it('siger det hoejt naar et gennemfoert run ikke gemte tekst', async () => {
    getRoutineRun.mockResolvedValueOnce({
      run_id: 'run-1', routine_id: 'routine-1', status: 'succeeded',
      created_at: '2026-10-13T08:00:00Z', result: null,
    })
    await aabn()

    expect(await screen.findByText(/gemte intet tekstresultat/i)).toBeVisible()
  })
})
