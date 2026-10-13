import { useEffect, useState } from 'react'
import { ChevronRight, Loader2 } from 'lucide-react'
import type { ApiConfig } from '../../lib/api'
import { listRoutineEvents, listRoutineRuns, type RoutineEvent, type RoutineRun } from '../../lib/routinesApi'

const visiblePayload = (payload: Record<string, unknown> | undefined): string[] => {
  if (!payload) return []
  const keys = ['visible', 'summary', 'message', 'result', 'diagnostic_code', 'status']
  return keys.flatMap((key) => {
    const value = payload[key]
    return typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean'
      ? [String(value)] : []
  })
}

export function RoutineRuns({ config, routineId }: { config: ApiConfig; routineId: string }) {
  const [runs, setRuns] = useState<RoutineRun[] | null>(null)
  const [selected, setSelected] = useState<string | null>(null)
  const [events, setEvents] = useState<RoutineEvent[] | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let alive = true
    setRuns(null); setSelected(null); setEvents(null); setError('')
    listRoutineRuns(config, routineId).then((items) => { if (alive) setRuns(items) })
      .catch((reason) => { if (alive) setError(reason instanceof Error ? reason.message : 'Kunne ikke hente kørsler') })
    return () => { alive = false }
  }, [config, routineId])

  const open = (runId: string) => {
    setSelected(runId); setEvents(null); setError('')
    void listRoutineEvents(config, runId).then(setEvents)
      .catch((reason) => setError(reason instanceof Error ? reason.message : 'Kunne ikke hente hændelser'))
  }

  if (!runs && !error) return <div className="routine-empty"><Loader2 size={14} className="spin" /> Henter kørsler…</div>
  return (
    <div className="routine-runs">
      {error && <p className="routine-error" role="alert">{error}</p>}
      {runs?.length === 0 && <p className="routine-empty">Rutinen har ikke kørt endnu.</p>}
      {runs?.map((run) => (
        <div className="routine-run" key={run.run_id}>
          <button type="button" className="routine-run-row" aria-expanded={selected === run.run_id} onClick={() => open(run.run_id)}>
            <ChevronRight size={14} /> <span className={`routine-status is-${run.status}`}>{run.status}</span>
            <time>{new Date(run.created_at).toLocaleString('da-DK')}</time>
          </button>
          {selected === run.run_id && (
            <ol className="routine-timeline" aria-label="Kørselshændelser">
              {!events && <li className="routine-empty"><Loader2 size={13} className="spin" /> Henter hændelser…</li>}
              {events?.map((event) => (
                <li key={event.event_id}>
                  <span className="routine-event-kind">{event.kind.replaceAll('_', ' ')}</span>
                  {visiblePayload(event.payload).map((line, index) => <span key={index}>{line}</span>)}
                  <time>{new Date(event.created_at).toLocaleTimeString('da-DK')}</time>
                </li>
              ))}
            </ol>
          )}
        </div>
      ))}
    </div>
  )
}
