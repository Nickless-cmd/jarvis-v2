import { useEffect, useRef, useState } from 'react'
import { ChevronDown, ChevronRight, Loader2 } from 'lucide-react'
import type { ApiConfig } from '../../lib/api'
import { hentLiveRuns, type LiveRun } from '../../lib/liveRunsApi'
import { maaPolle } from '../../lib/ro'

/** Hvor ofte vi spørger. 4 s er nok til at en kørsel «dukker op» mens man ser
 *  på listen, og billigt nok til at stå i en sidebar der altid er åben. */
const POLL_MS = 4000

/** Hvor længe en afsluttet række bliver stående mens den fader ud. */
const FADE_MS = 700

/**
 * «Kører nu» — de kørsler der er i gang, og kun dem.
 *
 * Bjørn 15/11-2026: «de kun vises mens de køre … runtime navne fader ind og ud
 * når de er aktive og men de er aktive kan man trykke på dem og så skifter
 * chatview og composer til den session».
 *
 * Derfor: listen er TOM når intet kører — den er en tilstand, ikke et arkiv.
 * En række der forsvinder får et kort `is-fading`-vindue, så øjet ser at den
 * sluttede frem for at den blev revet væk.
 *
 * Klikket fører til det sted hvor indholdet FINDES: en session åbnes i
 * chatview (hvor composer hører til), en rutine åbnes i rutine-fladen.
 */
export function KoererNu({ config, onOpenSession, onOpenRoutine }: {
  config?: ApiConfig | null
  onOpenSession?: (sessionId: string) => void
  onOpenRoutine?: (routineId: string) => void
}) {
  const [runs, setRuns] = useState<LiveRun[]>([])
  const [forsvundne, setForsvundne] = useState<LiveRun[]>([])
  const [foldet, setFoldet] = useState(false)
  const kendte = useRef<LiveRun[]>([])

  useEffect(() => {
    if (!config) return
    let alive = true
    const hent = async () => {
      if (document.visibilityState !== 'visible') return
      // Husets ro-mekanisme: ingen kigger → sjældnere. En blok i en sidebar
      // der altid er åben må ikke spørge i samme takt på en ubetjent maskine.
      if (!maaPolle('koerer-nu', POLL_MS)) return
      try {
        const nye = await hentLiveRuns(config)
        if (!alive) return
        const nyeIds = new Set(nye.map((r) => r.id))
        const vaek = kendte.current.filter((r) => !nyeIds.has(r.id))
        kendte.current = nye
        setRuns(nye)
        if (vaek.length > 0) {
          setForsvundne(vaek)
          window.setTimeout(() => { if (alive) setForsvundne([]) }, FADE_MS)
        }
      } catch {
        // En tom liste er ikke en fejl der skal råbes op i sidebaren. De to
        // kilder fejler hver for sig, så ét fejlet opslag skjuler ikke den
        // anden slags kørsel.
      }
    }
    void hent()
    const timer = window.setInterval(hent, POLL_MS)
    return () => { alive = false; window.clearInterval(timer) }
  }, [config])

  const synlige = [
    ...runs,
    ...forsvundne.filter((f) => !runs.some((r) => r.id === f.id)),
  ]
  if (!config || synlige.length === 0) return null

  return (
    <div className="koerer-nu">
      <button
        type="button"
        className="koerer-nu-head"
        aria-expanded={!foldet}
        onClick={() => setFoldet((f) => !f)}
      >
        <span className="koerer-nu-prik" aria-hidden="true" />
        <span className="koerer-nu-titel">Kører nu</span>
        <span className="koerer-nu-tal">{runs.length}</span>
        {foldet ? <ChevronRight size={13} /> : <ChevronDown size={13} />}
      </button>
      {!foldet && (
        <div className="koerer-nu-liste">
          {synlige.map((r) => {
            const aktiv = runs.some((x) => x.id === r.id)
            const aabn = () => {
              if (r.kind === 'rutine') {
                if (r.routineId) onOpenRoutine?.(r.routineId)
                return
              }
              if (r.sessionId) onOpenSession?.(r.sessionId)
            }
            return (
              <button
                key={r.id}
                type="button"
                className={`koerer-nu-raekke${aktiv ? '' : ' is-fading'}`}
                onClick={aabn}
                title={r.sessionId ?? r.routineId ?? ''}
              >
                {aktiv
                  ? <Loader2 size={12} className="spin" aria-hidden="true" />
                  : <span className="koerer-nu-punkt" aria-hidden="true" />}
                <span className="koerer-nu-navn">{r.navn}</span>
                <span className="koerer-nu-art">{r.kind === 'rutine' ? 'rutine' : 'session'}</span>
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}
