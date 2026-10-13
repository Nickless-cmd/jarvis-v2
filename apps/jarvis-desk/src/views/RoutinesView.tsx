import { useCallback, useEffect, useMemo, useState } from 'react'
import { Clock3, Loader2, Pencil, Play, Plus, RotateCcw, Square, Trash2, X } from 'lucide-react'
import type { ApiConfig } from '../lib/api'
import {
  deleteRoutine, listRoutines, routineAction, runRoutine,
  type Routine, type RoutineAction,
} from '../lib/routinesApi'
import { RoutineRuns } from '../components/routines/RoutineRuns'

type DetailTab = 'overview' | 'runs' | 'access'

const statusName: Record<string, string> = {
  active: 'Aktiv', paused: 'Pauset', stopped: 'Stoppet', archived: 'Arkiveret', draft: 'Forslag',
}

export function RoutinesView({ config, currentUserId, role, onClose, onEdit }: {
  config: ApiConfig
  currentUserId: string
  role: 'owner' | 'partner' | 'member' | 'guest'
  onClose: () => void
  onEdit: (routine: Routine | null) => void
}) {
  const [routines, setRoutines] = useState<Routine[] | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [tab, setTab] = useState<DetailTab>('overview')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState('')
  const [confirmDelete, setConfirmDelete] = useState(false)

  const load = useCallback(async () => {
    setError('')
    try { setRoutines(await listRoutines(config)) }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Kunne ikke hente rutiner') }
  }, [config])

  useEffect(() => { void load() }, [load])

  // API'et er den egentlige privacy-grænse. Dette forsvar gør også klienten
  // fail-closed, hvis en fremtidig server ved en fejl sender en for bred liste.
  const visible = useMemo(() => (routines ?? []).filter((routine) =>
    routine.owner_user_id === currentUserId
      || (role === 'owner' && routine.access_scope === 'system_owner')
  ), [routines, currentUserId, role])
  const selected = visible.find((routine) => routine.routine_id === selectedId) ?? visible[0] ?? null

  useEffect(() => {
    if (selected && selected.routine_id !== selectedId) setSelectedId(selected.routine_id)
  }, [selected, selectedId])

  const act = async (action: RoutineAction) => {
    if (!selected || busy) return
    setBusy(action); setError(''); setConfirmDelete(false)
    try {
      const updated = await routineAction(config, selected.routine_id, action)
      setRoutines((items) => items?.map((item) => item.routine_id === updated.routine_id ? updated : item) ?? [updated])
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Handlingen kunne ikke udføres') }
    finally { setBusy('') }
  }

  const remove = async () => {
    if (!selected || busy) return
    setBusy('delete'); setError('')
    try {
      await deleteRoutine(config, selected.routine_id)
      setRoutines((items) => items?.filter((item) => item.routine_id !== selected.routine_id) ?? [])
      setSelectedId(null); setConfirmDelete(false)
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Rutinen kunne ikke slettes') }
    finally { setBusy('') }
  }

  const runNow = async () => {
    if (!selected || busy) return
    setBusy('run'); setError('')
    try { await runRoutine(config, selected.routine_id); setTab('runs') }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Rutinen kunne ikke startes') }
    finally { setBusy('') }
  }

  return (
    <section className="routines-view">
      <aside className="routine-library" aria-label="Rutinebibliotek">
        <header className="routine-library-head">
          <div><h1>Rutiner</h1><p>Dit arbejde, der kan køre af sig selv</p></div>
          <button type="button" className="routine-icon-button" aria-label="Luk rutiner" onClick={onClose}><X size={17} /></button>
        </header>
        <button type="button" className="routine-new" onClick={() => onEdit(null)}><Plus size={14} /> Ny rutine</button>
        <div className="routine-list" role="list">
          {!routines && !error && <div className="routine-empty"><Loader2 size={14} className="spin" /> Henter…</div>}
          {visible.map((routine) => (
            <button key={routine.routine_id} type="button" role="listitem"
              aria-label={`${routine.name} · ${statusName[routine.status] ?? routine.status}`}
              className={`routine-list-row${selected?.routine_id === routine.routine_id ? ' active' : ''}`}
              onClick={() => { setSelectedId(routine.routine_id); setTab('overview'); setConfirmDelete(false) }}>
              <span className="routine-list-name">{routine.name}</span>
              <span className="routine-list-meta">
                <span className={`routine-dot is-${routine.status}`} />{statusName[routine.status] ?? routine.status}
                {routine.access_scope === 'system_owner' && <span>System · owner</span>}
              </span>
            </button>
          ))}
          {routines && visible.length === 0 && <div className="routine-empty">Du har ingen rutiner endnu.</div>}
        </div>
      </aside>

      <main className="routine-detail">
        {error && <p className="routine-error" role="alert">{error}</p>}
        {!selected ? (
          <div className="routine-detail-empty"><Clock3 size={24} /><h2>Vælg eller opret en rutine</h2><p>Her kan du styre, hvad der kører, og se hvad der skete.</p></div>
        ) : (
          <>
            <header className="routine-detail-head">
              <div><div className="routine-kicker">{selected.access_scope === 'system_owner' ? 'System · owner' : 'Privat rutine'}</div><h2>{selected.name}</h2></div>
              <div className="routine-actions">
                {selected.status === 'active' && <button className="routine-button secondary" type="button" onClick={() => void act('pause')}>Pause</button>}
                {selected.status === 'paused' && <button className="routine-button secondary" type="button" onClick={() => void act('resume')}><RotateCcw size={13} /> Genoptag</button>}
                {selected.status === 'stopped' && <button className="routine-button secondary" type="button" onClick={() => void act('restart')}><RotateCcw size={13} /> Start igen</button>}
                {selected.status === 'active' && <button className="routine-button secondary" type="button" onClick={() => void runNow()}><Play size={13} /> Kør nu</button>}
                {!['stopped', 'archived'].includes(selected.status) && <button className="routine-button secondary" type="button" aria-label="Stop rutine" onClick={() => void act('stop')}><Square size={12} /> Stop</button>}
                <button className="routine-button secondary" type="button" aria-label="Redigér rutine" onClick={() => onEdit(selected)}><Pencil size={13} /> Redigér</button>
              </div>
            </header>
            <nav className="routine-tabs" role="tablist" aria-label="Rutineindhold">
              {([['overview', 'Overblik'], ['runs', 'Kørsler'], ['access', 'Adgang']] as const).map(([key, label]) => (
                <button key={key} type="button" role="tab" aria-selected={tab === key} onClick={() => setTab(key)}>{label}</button>
              ))}
            </nav>
            <div className="routine-detail-body">
              {tab === 'overview' && <RoutineOverview routine={selected} />}
              {tab === 'runs' && <RoutineRuns config={config} routineId={selected.routine_id} />}
              {tab === 'access' && <RoutineAccess routine={selected} />}
              <div className="routine-danger-zone">
                <div><strong>Slet rutine</strong><span>Fjerner definition, kørsler og privat indhold permanent.</span></div>
                {!confirmDelete
                  ? <button type="button" className="routine-button danger" aria-label="Slet rutine" onClick={() => setConfirmDelete(true)}><Trash2 size={13} /> Slet</button>
                  : <div className="routine-confirm"><button type="button" className="routine-button secondary" onClick={() => setConfirmDelete(false)}>Fortryd</button><button type="button" className="routine-button danger" aria-label="Bekræft sletning" onClick={() => void remove()}>Bekræft sletning</button></div>}
              </div>
            </div>
          </>
        )}
      </main>
    </section>
  )
}

function RoutineOverview({ routine }: { routine: Routine }) {
  return <div className="routine-overview">
    <section><h3>Instruktion</h3><p className="routine-instruction">{routine.instruction}</p></section>
    <div className="routine-facts">
      <section><h3>Status</h3><span className={`routine-status is-${routine.status}`}>{statusName[routine.status] ?? routine.status}</span></section>
      <section><h3>Udløser</h3><p>{routine.trigger_kind}</p></section>
      <section><h3>Område</h3><p>{routine.capability_scope}</p></section>
      <section><h3>Version</h3><p>{routine.version}</p></section>
    </div>
  </div>
}

function RoutineAccess({ routine }: { routine: Routine }) {
  const system = routine.access_scope === 'system_owner'
  return <div className="routine-access">
    <h3>{system ? 'System · owner' : 'Kun dig'}</h3>
    <p>{system
      ? 'Denne systemrutine leveres kun til owner. Andre brugeres private indhold er ikke tilgængeligt.'
      : 'Kun du kan læse definitionen, kørslerne og resultaterne. Indholdet lægges aldrig ind i andre samtaler.'}</p>
  </div>
}
