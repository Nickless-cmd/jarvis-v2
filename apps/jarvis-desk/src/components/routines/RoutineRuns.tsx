import { useEffect, useRef, useState } from 'react'
import { ChevronRight, Loader2 } from 'lucide-react'
import type { ApiConfig } from '../../lib/api'
import { MarkdownRenderer } from '../rich/MarkdownRenderer'
import {
  getRoutineRun, listOriginSessions, listRoutineEvents, listRoutineRuns,
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

export function RoutineRuns({ config, routineId, instruction, onOpenSession }: {
  config: ApiConfig
  routineId: string
  /** Rutinens opgave. Bjørn 27/10-2026: en kørsel skal vise opgave + svar —
   *  opgaven er det mennesket bad om, svaret er det de fik. Alt andet er log. */
  instruction?: string
  /** Åbner en oprindelses-session. En system-rutine har ingen kørsler, så
   *  dens indhold kan kun ses ved at åbne sessionen (15/11-2026). */
  onOpenSession?: (sessionId: string) => void
}) {
  const [runs, setRuns] = useState<RoutineRun[] | null>(null)
  const [originSessioner, setOriginSessioner] = useState<{ session_id: string; title: string; updated_at: string }[] | null>(null)
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
    // System-rutiner («System · heartbeat», «System · dream», «System · wakeup»)
    // har nul `routine_runs` — deres spor er autonome sessioner. Uden dette
    // opslag stod fanen tom og det så ud som om rutinen aldrig havde kørt
    // (Bjørn 15/11-2026: «så jeg kan aldrig se hvad der sker i sessionerne»).
    listOriginSessions(config, routineId).then((items) => { if (alive) setOriginSessioner(items) })
      .catch(() => { if (alive) setOriginSessioner([]) })
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
      {runs?.length === 0 && (originSessioner?.length ?? 0) === 0 && (
        <p className="routine-empty">Rutinen har ikke kørt endnu.</p>
      )}
      {(originSessioner?.length ?? 0) > 0 && (
        <section className="routine-origin" aria-label="Rutinens sessioner">
          <h4>Sessioner</h4>
          <p className="routine-origin-note">
            Rutinen har ingen kørsler i kørsels-loggen — dens arbejde ligger i
            disse sessioner.
          </p>
          {originSessioner?.map((session) => (
            <button
              key={session.session_id}
              type="button"
              className="routine-run-row"
              onClick={() => onOpenSession?.(session.session_id)}
            >
              <ChevronRight size={14} />
              <span className="routine-origin-titel">{session.title || session.session_id}</span>
              <time>{new Date(session.updated_at).toLocaleString('da-DK')}</time>
            </button>
          ))}
        </section>
      )}
      {runs?.map((run) => (
        <div className="routine-run" key={run.run_id}>
          <button type="button" className="routine-run-row" aria-expanded={selected === run.run_id} onClick={() => open(run.run_id)}>
            <ChevronRight size={14} /> <span className={`routine-status is-${run.status}`}>{run.status}</span>
            <time>{new Date(run.created_at).toLocaleString('da-DK')}</time>
          </button>
          {selected === run.run_id && (
            <div className="routine-run-detail">
              {!detail && <p className="routine-empty"><Loader2 size={13} className="spin" /> Henter resultat…</p>}
              {instruction && (
                <section className="routine-task" aria-label="Rutinens opgave">
                  <h4>Opgave</h4>
                  <p className="routine-task-text">{instruction}</p>
                </section>
              )}
              {detail?.result && (
                <section className="routine-result" aria-label="Rutinens resultat">
                  <h4>Svar</h4>
                  <div className="routine-result-text jarvis-body">
                    <MarkdownRenderer text={detail.result} streaming={false} />
                  </div>
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
              <details className="routine-events">
                <summary>Teknisk log ({events?.length ?? 0} hændelser)</summary>
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
