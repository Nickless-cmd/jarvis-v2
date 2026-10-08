import { useCallback, useEffect, useRef, useState } from 'react'
import { Square, Trash2, ChevronRight, ChevronDown, X, Play, Maximize2, Minimize2 } from 'lucide-react'
import {
  listJobs, stopJob, pauseJob, resumeJob, varighed, kildeNavn,
  type BackgroundJob,
} from '../../lib/jobsApi'
import { removeProcess } from '../../lib/processesApi'
import type { ApiConfig } from '../../lib/api'
import {
  getKontraktOverblik, kontraktStop, kvitterKontrakt,
  type ContractAgentRow, type ContractOverview,
} from '../../lib/agentContractApi'
import type { AgentReference } from '../../lib/environmentEvidence'
import { AgentJobRows } from './AgentJobRows'

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
  onOpenAgent,
  sessionId,
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
  /** Klik på en agentrække åbner AgentInspector (samme som Miljø-feltet). */
  onOpenAgent?: (agent: AgentReference) => void
  /** Samtalen panelet hører til (8/10-2026). Uden den viste panelet HELE
   *  maskinens arbejde, så en anden samtales builds stod her som ens egne.
   *  Bjørn: «baggrundsjobs panel i desk skal osse være sessions bestemt». */
  sessionId?: string | null
}) {
  const [jobs, setJobs] = useState<BackgroundJob[]>([])
  // Kontrakt-projektionen (G): agentrun fra DB, uafhængigt af /api/jobs og af klientbroen.
  const [kontrakt, setKontrakt] = useState<ContractOverview | null>(null)
  const [kontraktFejl, setKontraktFejl] = useState(false)
  const [broOk, setBroOk] = useState(true)
  // Job der ikke kan henføres til en samtale: maskinens egne services, åbne
  // shells, operatørens filer. De vises i alle samtaler — men et panel der
  // kun viste dem ville se ud som om samtalen ejede dem.
  const [uspecificeret, setUspecificeret] = useState(0)
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
    // To uafhængige kilder: en fejl i den ene må ikke tømme den anden. En fejlet kontrakt-hentning er IKKE en
    // tom agentliste — det siges højt nedenfor.
    const jobsKald = listJobs(config, true, sessionId)
      .then((svar) => {
        setJobs(svar.jobs); setBroOk(svar.bridge_ok); setFejl('')
        setUspecificeret(svar.uspecificeret ?? 0)
      })
      .catch(() => setFejl('kunne ikke hente jobs'))
    const kontraktKald = getKontraktOverblik(config, 'panel')
      .then((svar) => { setKontrakt(svar); setKontraktFejl(false) })
      .catch(() => setKontraktFejl(true))
    void Promise.all([jobsKald, kontraktKald]).finally(() => { undervejs.current = false })
  }, [config, sessionId])

  useEffect(() => {
    hent()
    const id = setInterval(() => { if (!document.hidden) hent() }, 5000)
    return () => clearInterval(id)
  }, [hent])

  // En kontrakt-agent står i registeret og dermed også som «scout» i /api/jobs. Rækken kommer fra kontrakten
  // (rigere og med styring); duplikatet fra jobs-listen fjernes, så ét run ikke står to gange.
  const kontraktIds = new Set((kontrakt?.agents ?? []).map((a) => a.agent_id))
  const alleJobs = jobs.filter((j) => !(j.kilde === 'agent' && kontraktIds.has(j.id)))
  const koerende = alleJobs.filter((j) => j.status === 'running' || j.status === 'paused')
  const faerdige = alleJobs.filter((j) => j.status !== 'running' && j.status !== 'paused')
  const agentRaekker = kontrakt?.agents ?? []
  // To lister, to tal: det der KØRER/venter af sig selv, og det der kræver at nogen gør noget.
  const agenterKoerer = agentRaekker.filter((r) => !r.attention)
  const agenterOpmaerksomhed = agentRaekker.filter((r) => r.attention)
  const koererTotal = koerende.length + agenterKoerer.length

  useEffect(() => { onCount?.(koererTotal) }, [koererTotal, onCount])

  const aabnAgent = (r: ContractAgentRow) => onOpenAgent?.({
    agentId: r.agent_id, role: r.role, goal: r.goal, status: r.bucket, dispatchToolUseId: '',
  })
  // Egne handlinger (ikke `handling` nedenfor): serverens forklaring («kontrakten er slukket», «findes ikke for
  // dig») skal frem — ikke et generisk «handlingen mislykkedes».
  const agentHandling = async (r: ContractAgentRow, fn: () => Promise<void>) => {
    setTravl(r.agent_id); setBesked('')
    try { await fn(); hent() } catch (e) {
      setFejl(e instanceof Error && e.message ? e.message : 'handlingen mislykkedes')
    } finally { setTravl('') }
  }
  const stopAgent = (r: ContractAgentRow) => void agentHandling(r, async () => {
    const svar = await kontraktStop(config!, r.agent_id)
    setBesked(svar.receipt.accepted
      ? `Stop anmodet for «${r.goal || r.agent_id}» — ikke bekræftet endnu.` : 'Stop blev afvist.')
  })
  const kvitterAgent = (r: ContractAgentRow) => void agentHandling(r, async () => {
    await kvitterKontrakt(config!, r.assignment_id)
  })

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
      const shells = faerdige.filter((j) => j.kilde === 'operator').length
      // Færdige scout-agenter er rækker i agent-registret, ikke processer —
      // der er intet at slette. De forsvinder af sig selv efter en time.
      const agenter = faerdige.filter((j) => j.kilde === 'agent').length
      setBesked([
        shells ? `${shells} shell(s) på din maskine kan ikke ryddes herfra` : '',
        agenter ? `${agenter} scout-agent(er) forsvinder af sig selv efter en time` : '',
      ].filter(Boolean).join(' · '))
      hent()
    } catch {
      setFejl('kunne ikke rydde')
    } finally { setTravl('') }
  }

  const kort = (j: BackgroundJob, faerdig: boolean) => (
    <li className={`jobs-kort${faerdig ? ' er-faerdig' : ''}`} key={`${j.kilde}:${j.id}`}>
      <div className="jobs-kort-tekst">
        {/* B (Bjørn 29/9-2026): titlen er hvad jobbet LAVER. Id'et er ude af
            raekken — det staar i tooltip sammen med den tekniske kommando og
            i aria-label, saa to ens job stadig kan skelnes. Formen er CC's:
            titel · type · ur. */}
        <span className="jobs-navn" title={j.kommando ? `${j.id} · ${j.kommando}` : j.id}>
          {j.navn}
        </span>
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
        {/* Linje 3 er FJERNET (Bjørn 29/9-2026): CC viser titel · type · ur,
            og kommandoen staar nu i `title` paa titlen ovenfor. Rækken er
            lavere end før, ikke højere. */}
      </div>
      {isOwner && !faerdig && (j.can_pause || j.can_stop !== false) && (
        <div className="jobs-knapper">
          {j.can_pause && (
            <button
              type="button" className="jobs-stop" disabled={travl === j.id}
              title={j.status === 'paused' ? 'Genoptag' : 'Sæt på pause'}
              aria-label={`${j.status === 'paused' ? 'Genoptag' : 'Pause'} ${j.navn} (${j.id})`}
              onClick={() => void handling(j.id, () => (j.status === 'paused'
                ? resumeJob(config!, j) : pauseJob(config!, j)))}
            >
              {j.status === 'paused' ? <Play size={11} /> : <span className="jobs-pause-ikon" />}
            </button>
          )}
          {/* can_stop === false er et VÆRKTØJSKALD inde i et run: der findes
              ingen rute der kan stoppe det uden at rive turen i stykker. Uden
              denne gren fik rækken en stop-knap der så levende ud og gjorde
              ingenting — samme fejlklasse som panelets lukning begik, og den
              blev først opdaget fordi nogen trykkede på den. */}
          {j.can_stop !== false && (
            <button
              type="button" className="jobs-stop" title="Stop jobbet"
              aria-label={`Stop ${j.navn} (${j.id})`} disabled={travl === j.id}
              onClick={() => void handling(j.id, () => stopJob(config!, j))}
            >
              <Square size={12} />
            </button>
          )}
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

      {kontraktFejl && (
        <div className="jobs-fejl" role="alert">
          Agent-kontrakten kunne ikke hentes — agentlisten er ukendt, ikke tom.
        </div>
      )}
      {kontrakt && !kontrakt.capability.enabled && agentRaekker.length > 0 && (
        <div className="jobs-besked">Agent-kontrakten er slukket for nye opgaver; allerede accepteret arbejde vises stadig.</div>
      )}

      {agenterOpmaerksomhed.length > 0 && (
        <>
          <div className="jobs-section-head ac-opmaerksomhed-hoved" data-testid="ac-opmaerksomhed">
            Kræver opmærksomhed <span className="jobs-count">{agenterOpmaerksomhed.length}</span>
          </div>
          <AgentJobRows rows={agenterOpmaerksomhed} groups={kontrakt?.groups ?? []} busyId={travl}
                        onOpen={aabnAgent} onStop={stopAgent} onAck={kvitterAgent} />
        </>
      )}

      <div className="jobs-section-head">
        Kører {koererTotal > 0 && <span className="jobs-count" data-testid="ac-koerer-tal">{koererTotal}</span>}
      </div>
      {koererTotal === 0 ? (
        <div className="jobs-tom">
          {uspecificeret > 0
            /* Samtalen har ingen EGNE job, men maskinen kører. At sige
               «ingenting kører» ville være usandt — og det er præcis den
               forskel panelet findes for at kunne sige. */
            ? `Ingen job i denne samtale. ${uspecificeret} kører på maskinen.`
            : 'Ingenting kører lige nu.'}
        </div>
      ) : (
        <>
          {agenterKoerer.length > 0 && (
            <AgentJobRows rows={agenterKoerer} groups={kontrakt?.groups ?? []} busyId={travl}
                          onOpen={aabnAgent} onStop={stopAgent} onAck={kvitterAgent} />
          )}
          {koerende.length > 0 && <ul className="jobs-liste">{koerende.map((j) => kort(j, false))}</ul>}
        </>
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
