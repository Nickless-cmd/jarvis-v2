import { useCallback, useEffect, useRef, useState } from 'react'
import { Square, Trash2, ChevronRight, ChevronDown, X, Play, Maximize2, Minimize2 } from 'lucide-react'
import {
  listJobs, stopJob, pauseJob, resumeJob, varighed, kildeNavn,
  type BackgroundJob,
} from '../../lib/jobsApi'
import { removeProcess } from '../../lib/processesApi'
import type { ApiConfig } from '../../lib/api'

/**
 * Kørende baggrundsjob — formen er Claude Codes egen «Background tasks».
 *
 * TO RETTELSER 16/9-2026 (Bjørn: «undersøg hvornår han kører baggrundsjobs
 * både på min maskine og sin egen — hvorfor de ikk bliver vist overhovedet»):
 *
 *  1. KILDEN VAR FORKERT. Panelet hentede `/api/processes`, som kun kender
 *     serverens supervisor. Alt Jarvis satte i gang på Bjørns EGEN maskine
 *     (`operator_run_in_background`, filer i /tmp/jarvis-bg/) fandtes aldrig i
 *     den liste. `/api/jobs` samler begge kilder og har eksisteret siden
 *     12/9 — med pause, resume og stop. Ingen klient kaldte den.
 *
 *  2. EN DØD BRO ER IKKE EN TOM LISTE. `bridge_ok: false` betyder at vi ikke
 *     VED hvad der kører på hans maskine. Panelet siger det nu, i stedet for
 *     at vise en tom «Kører»-liste der ligner ro.
 *
 * Panelet henter kun mens det er ÅBENT. En poll bag et lukket panel er ren
 * omkostning, og poll-omkostning har kostet os afbrudte streams før.
 */
export function JobsPanel({
  config,
  onClose,
  isOwner,
  onCount,
  fuld = false,
  onFuld,
}: {
  config?: ApiConfig
  onClose: () => void
  isOwner?: boolean
  /** Fuld visning — ruden fylder hele fladen i stedet for sin halvdel. */
  fuld?: boolean
  onFuld?: (fuld: boolean) => void
  /** Melder antal koerende op, saa taelleren paa ikonet og listen ikke kan staa
   *  side om side og vaere uenige. */
  onCount?: (n: number) => void
}) {
  const [jobs, setJobs] = useState<BackgroundJob[]>([])
  const [broOk, setBroOk] = useState(true)
  const [fejl, setFejl] = useState('')
  // Egen tilstand, IKKE `fejl`. En besked lagt i fejl-feltet blev slettet et
  // oejeblik senere af den naeste hentning (som rydder fejl ved succes), saa
  // forklaringen paa hvad der ikke kunne ryddes naaede aldrig skaermen.
  const [besked, setBesked] = useState('')
  const [faerdigeAabne, setFaerdigeAabne] = useState(false)
  const [travl, setTravl] = useState('')

  // Hvert opslag gaar over broen til Bjoerns maskine og koerer en kommando
  // dér. Uden denne vagt ville en langsom bro give overlappende kald: panelet
  // poller hvert 5. sekund uanset om det forrige svar er kommet, og saa staar
  // der to-tre kald i koe paa hans maskine for ét aabent panel.
  const undervejs = useRef(false)

  const hent = useCallback(() => {
    if (!config || undervejs.current) return
    undervejs.current = true
    listJobs(config, true)
      .then((svar) => { setJobs(svar.jobs); setBroOk(svar.bridge_ok); setFejl('') })
      .catch(() => setFejl('kunne ikke hente jobs'))
      .finally(() => { undervejs.current = false })
  }, [config])

  useEffect(() => {
    hent()
    const id = setInterval(() => { if (!document.hidden) hent() }, 5000)
    return () => clearInterval(id)
  }, [hent])

  const koerende = jobs.filter((j) => j.status === 'running' || j.status === 'paused')
  const faerdige = jobs.filter((j) => j.status !== 'running' && j.status !== 'paused')

  useEffect(() => { onCount?.(koerende.length) }, [koerende.length, onCount])

  const handling = async (id: string, fn: () => Promise<void>) => {
    setTravl(id)
    try { await fn(); hent() } catch { setFejl('handlingen mislykkedes') }
    finally { setTravl('') }
  }

  /** Ryd alle færdige. Kun supervisor-job kan fjernes — operatørens shells er
   *  filer på hans maskine, og der findes ingen rute til at slette dem. Det
   *  siges højt frem for at lade knappen se ud som om den tog dem alle. */
  const rydFaerdige = async () => {
    if (!config) return
    const kanFjernes = faerdige.filter((j) => j.kilde === 'supervisor')
    setTravl('ryd')
    setBesked('')
    try {
      for (const j of kanFjernes) await removeProcess(config, j.navn)
      const tilbage = faerdige.length - kanFjernes.length
      setBesked(tilbage ? `${tilbage} shell(s) på din maskine kan ikke ryddes herfra` : '')
      hent()
    } catch {
      setFejl('kunne ikke rydde')
    } finally { setTravl('') }
  }

  const kort = (j: BackgroundJob, faerdig: boolean) => (
    <li className={`jobs-kort${faerdig ? ' er-faerdig' : ''}`} key={`${j.kilde}:${j.id}`}>
      <div className="jobs-kort-tekst">
        <span className="jobs-navn" title={j.kommando}>{j.navn}</span>
        <span className="jobs-meta">
          {/* Linje 2 som i CC: HVOR den kører + hvor længe. At skelne server
              fra hans egen maskine er hele pointen med den samlede liste. */}
          <span className="jobs-kilde">{kildeNavn(j.kilde)}</span>
          {faerdig ? (
            j.exit_code !== null && j.exit_code !== undefined ? (
              <span className={`jobs-exit${j.exit_code === 0 ? '' : ' er-fejl'}`}>exit {j.exit_code}</span>
            ) : (
              /* `lost` = pid'en er væk UDEN at vi nåede at se en exit-kode,
                 typisk fordi runtime'en blev genstartet under jobbet.
                 «exit ?» ville være et gæt; «mistet» er hvad vi ved. */
              <span className="jobs-exit">{j.status === 'lost' ? 'mistet' : j.status}</span>
            )
          ) : (
            <>
              <span className="jobs-tid">{varighed(j.sekunder)}</span>
              {j.status === 'paused' && <span className="jobs-exit">pauset</span>}
            </>
          )}
        </span>
        {/* Linje 3: selve kommandoen — CC viser «localhost:5174» her. Den
            siger HVAD der kører, og det er det man afgør stop på. */}
        <span className="jobs-kommando" title={j.kommando}>{j.kommando}</span>
      </div>
      {isOwner && !faerdig && (
        <div className="jobs-knapper">
          {j.can_pause && (
            <button
              type="button" className="jobs-stop" disabled={travl === j.id}
              title={j.status === 'paused' ? 'Genoptag' : 'Sæt på pause'}
              aria-label={`${j.status === 'paused' ? 'Genoptag' : 'Pause'} ${j.navn}`}
              onClick={() => void handling(j.id, () => (j.status === 'paused'
                ? resumeJob(config!, j) : pauseJob(config!, j)))}
            >
              {j.status === 'paused' ? <Play size={11} /> : <span className="jobs-pause-ikon" />}
            </button>
          )}
          <button
            type="button" className="jobs-stop" title="Stop jobbet"
            aria-label={`Stop ${j.navn}`} disabled={travl === j.id}
            onClick={() => void handling(j.id, () => stopJob(config!, j))}
          >
            <Square size={12} />
          </button>
        </div>
      )}
    </li>
  )

  return (
    <aside className="jobs-panel" aria-label="Baggrundsjob">
      <div className="jobs-head">
        <span>Baggrundsjob</span>
        {onFuld && (
          <button type="button" className="jobs-close jobs-fuld" onClick={() => onFuld(!fuld)}
                  aria-label={fuld ? 'Formindsk' : 'Fuld visning'}
                  title={fuld ? 'Formindsk' : 'Fuld visning'}>
            {fuld ? <Minimize2 size={13} /> : <Maximize2 size={13} />}
          </button>
        )}
        <button type="button" className="jobs-close" onClick={onClose} aria-label="Luk">
          <X size={14} />
        </button>
      </div>

      {fejl && <div className="jobs-fejl">{fejl}</div>}
      {besked && <div className="jobs-besked">{besked}</div>}
      {!broOk && (
        /* Ikke «ingenting kører». Vi kan ikke SE hans maskine lige nu, og de
           to udsagn er stik modsatte. */
        <div className="jobs-fejl">Kan ikke se din maskine lige nu — kun serverens job vises.</div>
      )}

      <div className="jobs-section-head">
        Kører {koerende.length > 0 && <span className="jobs-count">{koerende.length}</span>}
      </div>
      {koerende.length === 0 ? (
        <div className="jobs-tom">Ingenting kører lige nu.</div>
      ) : (
        <ul className="jobs-liste">{koerende.map((j) => kort(j, false))}</ul>
      )}

      {faerdige.length > 0 && (
        <div className="jobs-faerdige">
          <button
            type="button" className="jobs-faerdige-head" aria-expanded={faerdigeAabne}
            onClick={() => setFaerdigeAabne((o) => !o)}
          >
            {faerdigeAabne ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
            Færdige <span className="jobs-count">{faerdige.length}</span>
          </button>
          {isOwner && (
            <button
              type="button" className="jobs-ryd" aria-label="Ryd færdige"
              title="Ryd færdige" disabled={travl === 'ryd'} onClick={() => void rydFaerdige()}
            >
              <Trash2 size={13} />
            </button>
          )}
        </div>
      )}
      {faerdigeAabne && faerdige.length > 0 && (
        <ul className="jobs-liste">{faerdige.map((j) => kort(j, true))}</ul>
      )}
    </aside>
  )
}
