/**
 * Kaldene — søgt på SERVEREN, én side ad gangen.
 *
 * Historikken er 90.000 kald. En klient-side-filtrering ville kun kunne søge i
 * den side der tilfældigvis var hentet, og se rigtig ud imens: værre end ingen
 * søgning, fordi et tomt resultat ville ligne et svar. Derfor går hvert filter
 * til serveren, og markøren følger dens `next_cursor`.
 *
 * Siderne gemmes ikke: at holde dem alle i hukommelsen ville gøre en lang
 * jagt til en langsom fane.
 *
 * ## Payload
 *
 * En udeladt payload SIGER at den er udeladt. En tom prompt-boks ser ud som et
 * kald uden prompt — en helt anden, og forkert, historie end «redigeringen
 * fejlede, så vi gemte den ikke». Indholdet vises som ren tekst i `<pre>`;
 * en prompt kan indeholde hvad som helst, og markup fra en fremmed model har
 * intet at gøre i en flade der kan udføre handlinger.
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import type { LogFilter, LogLinje, LogSide } from '../../../lib/cheapLaneApi'

/** Fritekst-søgning venter, så hvert bogstav ikke bliver en forespørgsel. */
export const SOEG_PAUSE_MS = 250

type Detalje = LogLinje & {
  request_payload?: string | null
  response_payload?: string | null
  redacted?: boolean
}

function tid(s?: string | null): string {
  if (!s) return '–'
  const d = new Date(s)
  return Number.isNaN(d.getTime()) ? String(s).slice(0, 16)
    : d.toLocaleString('da-DK', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

export function CheapLaneLogs({
  hentLogs, hentDetalje, timer,
}: {
  hentLogs: (f: LogFilter) => Promise<LogSide>
  hentDetalje: (id: string) => Promise<Detalje>
  timer: number
}) {
  const [søg, setSøg] = useState('')
  const [status, setStatus] = useState('')
  const [cursor, setCursor] = useState('')
  const [side, setSide] = useState<LogSide | null>(null)
  const [fejl, setFejl] = useState('')
  const [valgt, setValgt] = useState<Detalje | null>(null)
  const debounce = useRef<ReturnType<typeof setTimeout> | null>(null)

  const hent = useCallback(async (f: LogFilter) => {
    try {
      setSide(await hentLogs({ hours: timer, limit: 100, ...f }))
      setFejl('')
    } catch (e) {
      setFejl(e instanceof Error ? e.message : 'kunne ikke hente')
    }
  }, [hentLogs, timer])

  // Filter-ændring nulstiller markøren: ellers ville side 3 af en gammel
  // søgning blive til side 3 af en ny, og tallene ville passe til ingenting.
  useEffect(() => {
    if (debounce.current) clearTimeout(debounce.current)
    debounce.current = setTimeout(() => {
      void hent({ query: søg, status, cursor: '' })
      setCursor('')
    }, SOEG_PAUSE_MS)
    return () => { if (debounce.current) clearTimeout(debounce.current) }
  }, [søg, status, hent])

  const rækker = side?.items ?? []

  return (
    <div className="cl-logs">
      <div className="cl-soeg-raekke">
        <label>
          Søg
          <input type="search" value={søg} onChange={(e) => setSøg(e.target.value)}
                 placeholder="fejltekst, model, korrelations-id" />
        </label>
        <label>
          Status
          <select value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">alle</option>
            <option value="ok">ok</option>
            <option value="error">fejl</option>
          </select>
        </label>
        <span className="cl-dæmpet cl-lille">
          Søgningen kører på serveren — den ser hele vinduet, ikke kun denne side.
        </span>
      </div>

      {fejl ? <p className="cl-handling-fejl" role="alert">{fejl}</p> : null}

      <div className="cl-med-inspektor">
        <div>
          {rækker.length === 0 ? (
            <p className="cl-tom">Ingen kald matcher i vinduet.</p>
          ) : (
            <div className="cl-tabel-holder">
              <table className="cl-tabel">
                <thead>
                  <tr>
                    <th scope="col">Tid</th><th scope="col">Udbyder</th>
                    <th scope="col">Status</th><th scope="col">Fejl</th><th scope="col">ms</th>
                  </tr>
                </thead>
                <tbody>
                  {rækker.map((r) => (
                    <tr key={r.invocation_id}>
                      <th scope="row">
                        <button type="button" className="cl-linkknap"
                                onClick={async () => setValgt(await hentDetalje(String(r.invocation_id)))}>
                          {tid(r.at)} <span className="cl-dæmpet cl-lille">{r.invocation_id}</span>
                        </button>
                      </th>
                      <td>{r.provider} / {r.model}</td>
                      <td>{r.status ?? '–'}</td>
                      <td className="cl-besked">{r.error || r.error_class || '–'}</td>
                      <td>{r.latency_ms ?? '–'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <div className="cl-sider">
            <button type="button" className="cl-handling" disabled={!cursor}
                    onClick={() => { setCursor(''); void hent({ query: søg, status, cursor: '' }) }}>
              Første side
            </button>
            <button type="button" className="cl-handling" disabled={!side?.next_cursor}
                    onClick={() => {
                      const n = String(side?.next_cursor ?? '')
                      setCursor(n)
                      void hent({ query: søg, status, cursor: n })
                    }}>
              Næste side
            </button>
          </div>
        </div>

        {valgt ? (
          <aside className="cl-inspektor" aria-label={`Kald ${valgt.invocation_id}`}>
            <div className="cl-inspektor-hoved">
              <h4>{valgt.provider} / {valgt.model}</h4>
              <button type="button" onClick={() => setValgt(null)} aria-label="Luk">×</button>
            </div>
            <dl className="cl-inspektor-felter">
              <div><dt>Status</dt><dd>{valgt.status ?? '–'}</dd></div>
              <div><dt>Korrelation</dt><dd>{valgt.correlation_id || '–'}</dd></div>
              <div><dt>Tokens</dt><dd>{valgt.tokens_in ?? 0} ind / {valgt.tokens_out ?? 0} ud</dd></div>
              <div><dt>Latens</dt><dd>{valgt.latency_ms ?? '–'} ms</dd></div>
            </dl>

            {valgt.request_payload || valgt.response_payload ? (
              <>
                <p className="cl-forklaring-overskrift">
                  Payload {valgt.redacted ? '(redigeret)' : ''}
                </p>
                {/* Ren tekst. En prompt kan indeholde hvad som helst, og markup
                    fra en fremmed model hører ikke hjemme i en flade der kan
                    udføre handlinger. */}
                <pre className="cl-payload">{valgt.request_payload ?? ''}</pre>
                <pre className="cl-payload">{valgt.response_payload ?? ''}</pre>
              </>
            ) : (
              <p className="cl-tom">
                Ingen payload er gemt for dette kald — enten uden for
                opbevaringsvinduet, eller fordi redigeringen ikke kunne
                gennemføres.
              </p>
            )}
          </aside>
        ) : null}
      </div>
    </div>
  )
}
