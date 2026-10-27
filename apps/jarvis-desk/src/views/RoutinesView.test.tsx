import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'

const listRoutines = vi.fn()
const listRoutineRuns = vi.fn()
const listRoutineEvents = vi.fn()
const routineAction = vi.fn()
const deleteRoutine = vi.fn()
vi.mock('../lib/routinesApi', async (original) => ({
  ...(await original<typeof import('../lib/routinesApi')>()),
  listRoutines: (...args: unknown[]) => listRoutines(...args),
  listRoutineRuns: (...args: unknown[]) => listRoutineRuns(...args),
  listRoutineEvents: (...args: unknown[]) => listRoutineEvents(...args),
  routineAction: (...args: unknown[]) => routineAction(...args),
  deleteRoutine: (...args: unknown[]) => deleteRoutine(...args),
}))

import { RoutineRuns } from '../components/routines/RoutineRuns'
import { RoutinesView } from './RoutinesView'
import type { Routine } from '../lib/routinesApi'

const config = { apiBaseUrl: 'http://desk.test', authToken: 'token' }
const routine = (over: Partial<Routine> = {}): Routine => ({
  routine_id: 'r-own', owner_user_id: 'bjorn', access_scope: 'user_private', name: 'Min rutine',
  instruction: 'Gør noget', capability_scope: 'chat', trigger_kind: 'manual', trigger_config: {},
  permission_policy: {}, delivery_policy: {}, inbox_policy: {}, retention_policy: {}, failure_policy: {},
  jarvis_restart_allowed: false, status: 'active', version: 1,
  created_at: '2026-10-12T08:00:00Z', updated_at: '2026-10-12T08:00:00Z', ...over,
})

describe('RoutinesView', () => {
  beforeEach(() => {
    listRoutines.mockReset().mockResolvedValue([
      routine(),
      routine({ routine_id: 'r-system', owner_user_id: 'jarvis', access_scope: 'system_owner', name: 'Systemrutine' }),
      routine({ routine_id: 'r-other', owner_user_id: 'lotte', name: 'Anden brugers private rutine' }),
    ])
    listRoutineRuns.mockReset().mockResolvedValue([])
    listRoutineEvents.mockReset().mockResolvedValue([])
    routineAction.mockReset()
    deleteRoutine.mockReset()
  })

  it('shows an owner only their own routines plus owner-delivered system routines', async () => {
    render(<RoutinesView config={config} currentUserId="bjorn" role="owner" onClose={() => {}} onEdit={() => {}} />)
    expect((await screen.findAllByText('Min rutine'))[0]).toBeVisible()
    expect(screen.getByText('Systemrutine')).toBeVisible()
    expect(screen.getByRole('heading', { name: 'Mine rutiner' })).toBeVisible()
    expect(screen.getByRole('heading', { name: 'System · owner' })).toBeVisible()
    expect(screen.queryByText('Anden brugers private rutine')).not.toBeInTheDocument()
  })

  it('matches private routines by the canonical id returned by whoami', async () => {
    listRoutines.mockResolvedValue([
      routine({ owner_user_id: 'canonical-bjorn' }),
      routine({ routine_id: 'r-other', owner_user_id: 'canonical-lotte', name: 'Anden rutine' }),
    ])
    render(<RoutinesView config={config} currentUserId="canonical-bjorn" role="owner" onClose={() => {}} onEdit={() => {}} />)

    expect((await screen.findAllByText('Min rutine'))[0]).toBeVisible()
    expect(screen.queryByText('Anden rutine')).not.toBeInTheDocument()
  })

  it('opens create and edit in the dedicated editor surface', async () => {
    const onEdit = vi.fn()
    render(<RoutinesView config={config} currentUserId="bjorn" role="owner" onClose={() => {}} onEdit={onEdit} />)
    fireEvent.click(await screen.findByRole('button', { name: 'Ny rutine' }))
    expect(onEdit).toHaveBeenCalledWith(null)
    // `findByRole`, ikke `getByRole`: 'Ny rutine'-knappen staar i DOM fra foerste
    // render, saa ventningen ovenfor kan loese i samme tick som listen endnu ikke
    // er hentet (`listRoutines` resolver i en microtask, og React schedulerer
    // re-renderet bagefter). Maalt 16/10-2026: 0 af 20 isolerede koersler fejlede,
    // men CI fejlede paa netop denne linje — racen viser sig under last, ikke alene.
    // De to nabotests venter allerede paa samme faktum.
    fireEvent.click(await screen.findByRole('listitem', { name: /Min rutine/i }))
    fireEvent.click(screen.getByRole('button', { name: 'Redigér rutine' }))
    expect(onEdit).toHaveBeenCalledWith(expect.objectContaining({ routine_id: 'r-own' }))
  })

  it('keeps Stop and Delete separate and requires an inline deletion confirmation', async () => {
    render(<RoutinesView config={config} currentUserId="bjorn" role="owner" onClose={() => {}} onEdit={() => {}} />)
    fireEvent.click(await screen.findByRole('listitem', { name: /Min rutine/i }))
    expect(screen.getByRole('button', { name: 'Stop rutine' })).toBeVisible()
    fireEvent.click(screen.getByRole('button', { name: 'Slet rutine' }))
    expect(screen.getByRole('button', { name: 'Bekræft sletning' })).toBeVisible()
    expect(deleteRoutine).not.toHaveBeenCalled()
  })

  it('closes through the supplied return-mode action', async () => {
    const onClose = vi.fn()
    render(<RoutinesView config={config} currentUserId="bjorn" role="member" onClose={onClose} onEdit={() => {}} />)
    await screen.findByRole('listitem', { name: /Min rutine/i })
    fireEvent.click(screen.getByRole('button', { name: 'Luk rutiner' }))
    expect(onClose).toHaveBeenCalledOnce()
  })
})

describe('RoutineRuns', () => {
  it('renders observable output but never private reasoning fields', async () => {
    listRoutineRuns.mockResolvedValue([{ run_id: 'run-1', routine_id: 'r-own', status: 'succeeded', created_at: '2026-10-12T08:00:00Z' }])
    listRoutineEvents.mockResolvedValue([
      { event_id: 'e-1', kind: 'tool_result', created_at: '2026-10-12T08:01:00Z', payload: { visible: 'ok' }, reasoning: 'secret', chain_of_thought: 'hidden' },
    ])
    render(<RoutineRuns config={config} routineId="r-own" />)
    const run = await screen.findByRole('button', { name: /succeeded/i })
    fireEvent.click(run)
    // Hændelserne er foldet sammen som standard (27/10-2026) — de er detaljen,
    // ikke svaret. Testen åbner folden for at måle hvad der SKJULES i den.
    fireEvent.click(await screen.findByText(/^Detaljer/))
    await waitFor(() => expect(screen.getByText('ok')).toBeVisible())
    const timeline = screen.getByLabelText('Kørselshændelser')
    expect(within(timeline).queryByText('secret')).not.toBeInTheDocument()
    expect(within(timeline).queryByText('hidden')).not.toBeInTheDocument()
  })
})
