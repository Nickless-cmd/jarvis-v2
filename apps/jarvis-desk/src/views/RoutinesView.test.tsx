import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { PermissionProvider } from '../contexts/PermissionContext'

const listRoutines = vi.fn()
const listRoutineRuns = vi.fn()
const listRoutineEvents = vi.fn()
const routineAction = vi.fn()
const deleteRoutine = vi.fn()
const getRoutineChatSession = vi.fn()
const getSession = vi.fn()
vi.mock('../lib/api', async (original) => ({
  ...(await original<typeof import('../lib/api')>()),
  getSession: (...args: unknown[]) => getSession(...args),
}))
vi.mock('../lib/routinesApi', async (original) => ({
  ...(await original<typeof import('../lib/routinesApi')>()),
  listRoutines: (...args: unknown[]) => listRoutines(...args),
  listRoutineRuns: (...args: unknown[]) => listRoutineRuns(...args),
  listRoutineEvents: (...args: unknown[]) => listRoutineEvents(...args),
  routineAction: (...args: unknown[]) => routineAction(...args),
  deleteRoutine: (...args: unknown[]) => deleteRoutine(...args),
  getRoutineChatSession: (...args: unknown[]) => getRoutineChatSession(...args),
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
    getRoutineChatSession.mockReset().mockResolvedValue({
      session_id: 'routine-r-own', title: 'Rutine · Min rutine', kind: 'routine',
    })
    getSession.mockReset().mockResolvedValue({ session: {}, messages: [], etag: null })
  })

  it('shows an owner only their own routines plus owner-delivered system routines', async () => {
    render(<PermissionProvider><RoutinesView config={config} currentUserId="bjorn" role="owner" onClose={() => {}} onEdit={() => {}} /></PermissionProvider>)
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
    render(<PermissionProvider><RoutinesView config={config} currentUserId="canonical-bjorn" role="owner" onClose={() => {}} onEdit={() => {}} /></PermissionProvider>)

    expect((await screen.findAllByText('Min rutine'))[0]).toBeVisible()
    expect(screen.queryByText('Anden rutine')).not.toBeInTheDocument()
  })

  it('opens create and edit in the dedicated editor surface', async () => {
    const onEdit = vi.fn()
    render(<PermissionProvider><RoutinesView config={config} currentUserId="bjorn" role="owner" onClose={() => {}} onEdit={onEdit} /></PermissionProvider>)
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
    render(<PermissionProvider><RoutinesView config={config} currentUserId="bjorn" role="owner" onClose={() => {}} onEdit={() => {}} /></PermissionProvider>)
    fireEvent.click(await screen.findByRole('listitem', { name: /Min rutine/i }))
    expect(screen.getByRole('button', { name: 'Stop rutine' })).toBeVisible()
    fireEvent.click(screen.getByRole('button', { name: 'Slet rutine' }))
    expect(screen.getByRole('button', { name: 'Bekræft sletning' })).toBeVisible()
    expect(deleteRoutine).not.toHaveBeenCalled()
  })

  /** Bjørn 15/11-2026: «rutiner mangler alt det chatview har og kan … kan vi
   *  ikk genbruge det chatview og composer vi allerede har?». Panelet har
   *  derfor ingen egen samtaleflade: det peger paa rutinens session, og
   *  ChatView (scroll, pacing, kontekst-maaler, kompaktering, tilbagespoling)
   *  er den flade man lander i. */
  it('har ingen indlejret samtale — den aabner rutinens session i chatvisningen', async () => {
    const onOpenSession = vi.fn()
    render(<PermissionProvider><RoutinesView config={config} currentUserId="bjorn" role="owner" onClose={() => {}} onEdit={() => {}} onOpenSession={onOpenSession} /></PermissionProvider>)
    fireEvent.click(await screen.findByRole('listitem', { name: /Min rutine/i }))
    // Ingen composer i panelet — den findes kun i den rigtige chatflade.
    expect(document.querySelector('.composer-input')).toBeNull()
    // Konfigurationen er synlig med det samme; der er ingen tilstand at aabne.
    expect(screen.getByRole('tab', { name: 'Kørsler' })).toBeVisible()
    expect(screen.queryByRole('button', { name: 'Rutineindstillinger' })).not.toBeInTheDocument()
    // Knappen peger paa praecis den session panelet hentede.
    fireEvent.click(await screen.findByRole('button', { name: /bn i chatvisningen/i }))
    expect(onOpenSession).toHaveBeenCalledWith('routine-r-own')
  })

  /** Bjørn 15/11-2026: «i pwa mobil view kan man ikk se rutine listen når man
   *  trykker på rutiner i venstre menu». Aarsagen var at `selected` altid
   *  falder tilbage paa `visible[0]`, saa CSS'ens `:has(.active)` skjulte
   *  biblioteket i samme oejeblik fladen aabnede. Nu er det en tilstand. */
  it('aabner paa rutineLISTEN, og en tilbage-knap foerer dertil igen', async () => {
    render(<PermissionProvider><RoutinesView config={config} currentUserId="bjorn" role="owner" onClose={() => {}} onEdit={() => {}} /></PermissionProvider>)
    const flade = document.querySelector('.routines-view')
    expect(flade?.className).toContain('vis-liste')
    fireEvent.click(await screen.findByRole('listitem', { name: /Min rutine/i }))
    expect(document.querySelector('.routines-view')?.className).not.toContain('vis-liste')
    fireEvent.click(screen.getByRole('button', { name: 'Til rutinelisten' }))
    expect(document.querySelector('.routines-view')?.className).toContain('vis-liste')
  })

  it('closes through the supplied return-mode action', async () => {
    const onClose = vi.fn()
    render(<PermissionProvider><RoutinesView config={config} currentUserId="bjorn" role="member" onClose={onClose} onEdit={() => {}} /></PermissionProvider>)
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
    fireEvent.click(await screen.findByText(/^Teknisk log/))
    await waitFor(() => expect(screen.getByText('ok')).toBeVisible())
    const timeline = screen.getByLabelText('Kørselshændelser')
    expect(within(timeline).queryByText('secret')).not.toBeInTheDocument()
    expect(within(timeline).queryByText('hidden')).not.toBeInTheDocument()
  })
})
