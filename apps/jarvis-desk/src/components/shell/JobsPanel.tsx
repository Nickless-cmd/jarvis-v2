import { useCallback, useEffect, useState } from 'react'
import { Square, Trash2, ChevronRight, ChevronDown, X } from 'lucide-react'
import { listProcesses, stopProcess, removeProcess, varighed, type ManagedProcess } from '../../lib/processesApi'
import type { ApiConfig } from '../../lib/api'

/**
 * Kørende baggrundsjob — foldet ud som de andre header-paneler.
 *
 * Formen er Claude Codes egen «Background tasks»-rude (Bjørn pegede på den på
 * midterskærmen): en «Kører»-liste med ét kort pr. job, navn øverst, værktøj og
 * forløbet tid under, og en stop-knap i højre side. Færdige job ligger foldet
 * sammen nedenunder med en «Ryd».
 *
 * Panelet henter kun mens det er ÅBENT. En poll bag et lukket panel er ren
 * omkostning, og poll-omkostning har kostet os afbrudte streams før.
 */
export function JobsPanel({
  config,
  onClose,
  isOwner,
  onCount,
}: {
  config?: ApiConfig
  onClose: () => void
  isOwner?: boolean
  /** Melder antal koerende op, saa taelleren paa ikonet og listen ikke kan staa
   *  side om side og vaere uenige. De havde hver sin poll; efter en genstart af
   *  runtime'en viste ikonet 1 mens panelet sagde «Ingenting koerer». */
  onCount?: (n: number) => void
}) {
  const [jobs, setJobs] = useState<ManagedProcess[]>([])
  const [fejl, setFejl] = useState('')
  const [faerdigeAabne, setFaerdigeAabne] = useState(false)
  const [travl, setTravl] = useState('')

  const hent = useCallback(() => {
    if (!config) return
    listProcesses(config)
      .then((p) => { setJobs(p); setFejl('') })
      .catch(() => setFejl('kunne ikke hente jobs'))
  }, [config])

  useEffect(() => {
    hent()
    const id = setInterval(() => { if (!document.hidden) hent() }, 5000)
    return () => clearInterval(id)
  }, [hent])

  const koerende = jobs.filter((j) => j.status === 'running')
  const faerdige = jobs.filter((j) => j.status !== 'running')

  useEffect(() => { onCount?.(koerende.length) }, [koerende.length, onCount])

  const handling = async (navn: string, fn: () => Promise<void>) => {
    setTravl(navn)
    try { await fn(); hent() } catch { setFejl('handlingen mislykkedes') }
    finally { setTravl('') }
  }

  return (
    <aside className="jobs-panel" aria-label="Baggrundsjob">
      <div className="jobs-head">
        <span>Baggrundsjob</span>
        <button type="button" className="jobs-close" onClick={onClose} aria-label="Luk">
          <X size={14} />
        </button>
      </div>

      {fejl && <div className="jobs-fejl">{fejl}</div>}

      <div className="jobs-section-head">Kører {koerende.length > 0 && <span className="jobs-count">{koerende.length}</span>}</div>
      {koerende.length === 0 ? (
        <div className="jobs-tom">Ingenting kører lige nu.</div>
      ) : (
        <ul className="jobs-liste">
          {koerende.map((j) => (
            <li className="jobs-kort" key={j.name}>
              <div className="jobs-kort-tekst">
                <span className="jobs-navn" title={j.command}>{j.name}</span>
                <span className="jobs-meta">
                  {/* Kommandoen frem for et generisk «Bash»: den siger HVAD der
                      kører, og det er det man skal bruge for at afgøre om det
                      skal stoppes. */}
                  <span className="jobs-kommando" title={j.command}>{j.command}</span>
                  {typeof j.uptime_seconds === 'number' && (
                    <span className="jobs-tid">{varighed(j.uptime_seconds)}</span>
                  )}
                </span>
              </div>
              {isOwner && (
                <button
                  type="button"
                  className="jobs-stop"
                  title="Stop jobbet"
                  aria-label={`Stop ${j.name}`}
                  disabled={travl === j.name}
                  onClick={() => void handling(j.name, () => stopProcess(config!, j.name))}
                >
                  <Square size={12} />
                </button>
              )}
            </li>
          ))}
        </ul>
      )}

      {faerdige.length > 0 && (
        <>
          <button
            type="button"
            className="jobs-faerdige-head"
            aria-expanded={faerdigeAabne}
            onClick={() => setFaerdigeAabne((o) => !o)}
          >
            {faerdigeAabne ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
            Færdige <span className="jobs-count">{faerdige.length}</span>
          </button>
          {faerdigeAabne && (
            <ul className="jobs-liste">
              {faerdige.map((j) => (
                <li className="jobs-kort er-faerdig" key={j.name}>
                  <div className="jobs-kort-tekst">
                    <span className="jobs-navn">{j.name}</span>
                    <span className="jobs-meta">
                      <span className="jobs-kommando" title={j.command}>{j.command}</span>
                      {/* `lost` betyder at pid'en er vaek UDEN at vi naaede at
                          se en exit-kode — typisk fordi runtime'en blev
                          genstartet under jobbet. «exit ?» ville vaere et gaet;
                          «mistet» er hvad vi faktisk ved. */}
                      {j.exit_code !== null && j.exit_code !== undefined ? (
                        <span className={`jobs-exit${j.exit_code === 0 ? '' : ' er-fejl'}`}>
                          exit {j.exit_code}
                        </span>
                      ) : (
                        <span className="jobs-exit">{j.status === 'lost' ? 'mistet' : j.status}</span>
                      )}
                    </span>
                  </div>
                  {isOwner && (
                    <button
                      type="button"
                      className="jobs-stop"
                      title="Fjern fra listen"
                      aria-label={`Fjern ${j.name}`}
                      disabled={travl === j.name}
                      onClick={() => void handling(j.name, () => removeProcess(config!, j.name))}
                    >
                      <Trash2 size={12} />
                    </button>
                  )}
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </aside>
  )
}
