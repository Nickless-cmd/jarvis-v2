import { useEffect, useRef, useState } from 'react'
import { ChevronRight, Loader2 } from 'lucide-react'
import type { ApiConfig } from '../../lib/api'
import {
  getRoutineRun, listRoutineEvents, listRoutineRuns,
  type RoutineEvent, type RoutineRun,
} from '../../lib/routinesApi'

const visiblePayload = (payload: Record<string, unknown> | undefined): string[] => {
  if (!payload) return []
  // Explicit allow-list: the API has already authorized and decrypted this
  // owner's event. Keep internal identifiers/arguments out, but show the
  // observable model text, tool name/output and terminal summaries.
  const keys = [
    'visible', 'summary', 'message', 'result', 'text', 'name', 'output',
    'diagnostic_code', 'status',
  ]
  return keys.flatMap((key) => {
    const value = payload[key]
    return typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean'
      ? [String(value)] : []
  })
}

export function RoutineRuns({ config, routineId }: { config: ApiConfig; routineId: string }) {
  const [runs, setRuns] = useState<RoutineRun[] | null>(null)
  const [selected, setSelected] = useState<string | null>(null)
  const [detail, setDetail] = useState<RoutineRun | null>(null)
  const [events, setEvents] = useState<RoutineEvent[] | null>(null)
  const [error, setError] = useState('')
  const eventRequest = useRef(0)

  useEffect(() => {
    let alive = true
    eventRequest.current += 1
    setRuns(null); setSelected(null); setDetail(null); setEvents(null); setError('')
    listRoutineRuns(config, routineId).then((items) => { if (alive) setRuns(items) })
      .catch((reason) => { if (alive) setError(reason instanceof Error ? reason.message : 'Kunne ikke hente kørsler') })
    return () => { alive = false }
  }, [config, routineId])

  const open = (runId: string) => {
    const request = ++eventRequest.current
    setSelected(runId); setDetail(null); setEvents(null); setError('')
    // Resultatet og hændelserne hentes parallelt: resultatet er det mennesket
    // kan bruge, hændelserne er detaljen under det. Listen bærer ikke
    // `result` — kun dette kald gør, fordi serveren dekrypterer her.
    void getRoutineRun(config, runId)
      .then((item) => { if (request === eventRequest.current) setDetail(item) })
      .catch((reason) => {
        if (request === eventRequest.current) {
          setError(reason instanceof Error ? reason.message : 'Kunne ikke hente kørslen')
        }
      })
    void listRoutineEvents(config, runId)
      .then((items) => { if (request === eventRequest.current) setEvents(items) })
      .catch((reason) => {
        if (request === eventRequest.current) {
          setError(reason instanceof Error ? reason.message : 'Kunne ikke hente hændelser')
        }
      })
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
            <div className="routine-run-detail">
              {!detail && <p className="routine-empty"><Loader2 size={13} className="spin" /> Henter resultat…</p>}
              {detail?.result && (
                <section className="routine-result" aria-label="Rutinens resultat">
                  <h4>Resultat</h4>
                  <div className="routine-result-text">{detail.result}</div>
                </section>
              )}
              {detail && !detail.result && (
                <p className="routine-empty">
                  {detail.status === 'succeeded'
                    ? 'Kørslen lykkedes, men gemte intet tekstresultat.'
                    : `Ingen resultattekst (status: ${detail.status}).`}
                </p>
              )}
              {detail?.diagnostic_code && (
                <p className="routine-error" role="alert">Diagnose: {detail.diagnostic_code}</p>
              )}
              <details className="routine-events" open>
                <summary>Hændelser ({events?.length ?? 0})</summary>
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
              </details>
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
