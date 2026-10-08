import { useCallback, useEffect, useState } from 'react'
import {
  Check, ChevronDown, ChevronRight, Eye, EyeOff, Maximize2, Minimize2, Trash2, X,
} from 'lucide-react'
import {
  getAlleSideTasks, setSideTaskSkjult, setSideTaskStatus, type SideTask,
} from '../../lib/sideTasksApi'
import type { ApiConfig } from '../../lib/api'
import '../../styles/side-tasks.css'

/**
 * Sideopgaver i højre-stakken — samme form som baggrundsjob.
 *
 * Bjørn 8/10-2026: «jeg har intet sted jeg kan se dem». Der FANDTES et panel,
 * men det lå som en sektion inde i Indstillinger → Arbejdsområde, og det er
 * ikke et sted man leder efter sine egne opgaver. Opgaverne var derfor reelt
 * usynlige — og krydset i chatkortet afskrev dem permanent, så en opgave man
 * trykkede væk var væk for altid. Panelet her er svaret på begge: ét klik i
 * headerens 3-prik-menu, og alt hvad Jarvis har flagget, også det skjulte.
 *
 * ## Skjult er ikke lukket
 *
 * Krydset i chatten sætter `skjult_i_chat` — opgaven forbliver ÅBEN, den
 * vises blot ikke over samtalen. Her kan man se den igen, vise den frem igen,
 * eller lukke den rigtigt. «Fjern for altid» er den eneste irreversible
 * handling i panelet, og den kræver et ekstra klik: fire klik i et hjørne
 * afskrev fire opgaver 8/10, og ingen af dem kunne fortrydes bagefter
 * (`resolve` nægter at genåbne terminale opgaver).
 *
 * Panelet henter kun mens det er ÅBENT — en poll bag et lukket panel er ren
 * omkostning, og poll-omkostning har kostet os afbrudte streams før.
 */
const STATUS_TEKST: Record<string, string> = {
  pending: 'Venter',
  queued: 'I kø',
  activated: 'I gang',
  completed: 'Færdig',
  dismissed: 'Fjernet',
}

/** Alder i klartekst. En opgave der har ligget åben i ti dage skal ikke se
 *  lige så frisk ud som en fra i morges. */
function alder(iso?: string): string {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  const min = Math.floor((Date.now() - d.getTime()) / 60000)
  if (min < 1) return 'nu'
  if (min < 60) return `${min} min`
  const t = Math.floor(min / 60)
  if (t < 24) return `${t} t`
  const dage = Math.floor(t / 24)
  return dage === 1 ? '1 dag' : `${dage} dage`
}

export function SideOpgaveListe({ config, onClose, fuld = false, onFuld }: {
  config?: ApiConfig
  onClose: () => void
  fuld?: boolean
  onFuld?: (fuld: boolean) => void
}) {
  const [opgaver, setOpgaver] = useState<SideTask[] | null>(null)
  const [fejl, setFejl] = useState('')
  const [travl, setTravl] = useState('')
  const [lukkedeAabne, setLukkedeAabne] = useState(false)
  // Hvilken række der venter på bekræftelse på «Fjern for altid».
  const [bekraeft, setBekraeft] = useState('')

  const hent = useCallback(async () => {
    if (!config) return
    try {
      setOpgaver(await getAlleSideTasks(config))
      setFejl('')
    } catch (e) {
      // Tom liste og en fejl er IKKE det samme — og det var hele problemet
      // panelet blev bygget for at løse.
      setFejl(e instanceof Error ? e.message : 'Kunne ikke hente sideopgaverne')
    }
  }, [config])

  useEffect(() => {
    void hent()
    const id = setInterval(() => { if (!document.hidden) void hent() }, 8000)
    return () => clearInterval(id)
  }, [hent])

  const handling = async (t: SideTask, fn: () => Promise<void>) => {
    if (!config || travl) return
    setTravl(t.side_task_id); setFejl('')
    try {
      await fn()
      await hent()
    } catch (e) {
      setFejl(e instanceof Error ? e.message : 'Handlingen lykkedes ikke')
    } finally {
      setTravl('')
    }
  }

  const aabne = (opgaver ?? []).filter(
    (t) => t.status === 'pending' || t.status === 'queued' || t.status === 'activated')
  const lukkede = (opgaver ?? []).filter(
    (t) => t.status === 'completed' || t.status === 'dismissed')

  const raekke = (t: SideTask, lukket: boolean) => (
    <li key={t.side_task_id} className={`sop-post sop-${t.status}`}>
      <div className="sop-top">
        <span className="sop-status">{STATUS_TEKST[t.status] ?? t.status}</span>
        {t.skjult_i_chat ? (
          <span className="sol-skjult" title="Skjult i chatten — opgaven er stadig åben">
            <EyeOff size={11} /> skjult i chat
          </span>
        ) : null}
        <span className="sol-alder">{alder(t.created_at)}</span>
      </div>
      <div className="sop-titel">{t.title}</div>
      {t.tldr ? <p className="sop-tldr">{t.tldr}</p> : null}
      {!lukket && (
        <div className="sop-knapper sol-knapper">
          {t.skjult_i_chat ? (
            <button
              type="button" className="sol-knap" disabled={travl === t.side_task_id}
              title="Vis i chatten igen" aria-label={`Vis «${t.title}» i chatten`}
              onClick={() => void handling(t, () => setSideTaskSkjult(config!, t.side_task_id, false))}
            >
              <Eye size={12} />
            </button>
          ) : null}
          <button
            type="button" className="sol-knap" disabled={travl === t.side_task_id}
            title="Markér som færdig" aria-label={`Markér «${t.title}» færdig`}
            onClick={() => void handling(t, () => setSideTaskStatus(config!, t.side_task_id, 'completed'))}
          >
            <Check size={12} />
          </button>
          {bekraeft === t.side_task_id ? (
            <>
              <span className="sol-bekraeft">Fjern for altid?</span>
              <button
                type="button" className="sol-knap sol-farlig" disabled={travl === t.side_task_id}
                onClick={() => {
                  setBekraeft('')
                  void handling(t, () => setSideTaskStatus(config!, t.side_task_id, 'dismissed'))
                }}
              >
                Ja
              </button>
              <button type="button" className="sol-knap" onClick={() => setBekraeft('')}>Nej</button>
            </>
          ) : (
            <button
              type="button" className="sol-knap" disabled={travl === t.side_task_id}
              title="Fjern for altid — kan ikke fortrydes"
              aria-label={`Fjern «${t.title}» for altid`}
              onClick={() => setBekraeft(t.side_task_id)}
            >
              <Trash2 size={12} />
            </button>
          )}
        </div>
      )}
    </li>
  )

  return (
    <aside className="jobs-panel" aria-label="Sideopgaver" data-testid="side-opgave-liste">
      <div className="jobs-head">
        <span>Sideopgaver</span>
        {onFuld && (
          <button
            type="button" className="jobs-close jobs-fuld" onClick={() => onFuld(!fuld)}
            aria-label={fuld ? 'Formindsk' : 'Fuld visning'}
            title={fuld ? 'Formindsk' : 'Fuld visning'}
          >
            {fuld ? <Minimize2 size={13} /> : <Maximize2 size={13} />}
          </button>
        )}
        <button type="button" className="jobs-close" onClick={onClose} aria-label="Luk">
          <X size={14} />
        </button>
      </div>

      {fejl ? <div className="jobs-fejl" role="alert">{fejl}</div> : null}
      {opgaver === null && !fejl ? <div className="jobs-tom">Henter…</div> : null}

      {opgaver !== null && (
        <>
          <div className="jobs-section-head">
            Åbne {aabne.length > 0 && <span className="jobs-count">{aabne.length}</span>}
          </div>
          {aabne.length === 0 ? (
            <div className="jobs-tom">Ingen åbne sideopgaver.</div>
          ) : (
            <ul className="jobs-liste">{aabne.map((t) => raekke(t, false))}</ul>
          )}

          {lukkede.length > 0 && (
            <>
              <button
                type="button" className="jobs-faerdige-head" aria-expanded={lukkedeAabne}
                onClick={() => setLukkedeAabne((o) => !o)}
              >
                {lukkedeAabne ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
                Lukkede <span className="jobs-count">{lukkede.length}</span>
              </button>
              {lukkedeAabne && <ul className="jobs-liste">{lukkede.map((t) => raekke(t, true))}</ul>}
            </>
          )}
        </>
      )}
    </aside>
  )
}
