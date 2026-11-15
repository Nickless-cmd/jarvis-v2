import { useCallback, useEffect, useRef, useState } from 'react'
import { Loader2 } from 'lucide-react'
import { getSession, type ApiConfig } from '../../lib/api'
import { maaPolle } from '../../lib/ro'
import { readModelPrefs } from '../../lib/composerPrefs'
import { MessageRow } from '../rich/MessageRow'
import { Composer, type ComposerSendOpts } from '../shell/Composer'
import { getRoutineChatSession, sendRoutineMessage } from '../../lib/routinesApi'

/** Hvor ofte vi henter nye beskeder. Samme kadence som «Kører nu»: 4 s er nok
 *  til at et svar dukker op mens man ser på det, og billigt nok til at stå åbent. */
const POLL_MS = 4000

type Besked = {
  id: string
  role: 'user' | 'assistant'
  blokke: Parameters<typeof MessageRow>[0]['blocks']
  tid: string
}

/** Rutinens samtale — med husets EGNE komponenter.
 *
 *  Højre pane var ren konfiguration: man kunne se HVAD rutinen var sat til, men
 *  ikke hvad den HAVDE gjort — og slet ikke svare den. Bjørn 15/11-2026: «så jeg
 *  faktisk kan se hvad der er sket i rutinen og skrive til dig i rutinen».
 *
 *  Første udgave byggede sin egen besked-visning og sin egen textarea. Det var
 *  en efterligning, og Bjørn afviste den med rette: «kan du ikk genbruge
 *  chatview og composer istedet?». Nu bruges `MessageRow` og `Composer` — de
 *  samme komponenter ChatView bruger — så værktøjsspor, synteser, fold og
 *  composerens model-/tænke-valg opfører sig ens her og i chatten.
 *
 *  `ChatView` selv kan ikke genbruges: den kalder `sessions.select(sessionId)`
 *  og ville dermed kapre den samtale man sad i. Denne komponent ejer sin egen
 *  læsning og skriver gennem samme stream-endpoint som chat-fladen, så svaret
 *  er et rigtigt run i netop denne session.
 */
export function RoutineChat({ config, routineId, onOpenSession }: {
  config: ApiConfig
  routineId: string
  /** Åbner sessionen i den rigtige chatvisning (til system-rutinernes autonome
   *  sessioner, hvor der også kan ligge værktøjsspor). */
  onOpenSession?: (sessionId: string) => void
}) {
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [kind, setKind] = useState<'routine' | 'origin'>('routine')
  const [beskeder, setBeskeder] = useState<Besked[] | null>(null)
  const [sender, setSender] = useState(false)
  const [fejl, setFejl] = useState('')
  const bundRef = useRef<HTMLDivElement>(null)
  const sessionRef = useRef<string | null>(null)

  useEffect(() => { sessionRef.current = sessionId }, [sessionId])

  useEffect(() => {
    let alive = true
    setSessionId(null); setBeskeder(null); setFejl('')
    getRoutineChatSession(config, routineId)
      .then((svar) => {
        if (!alive) return
        setSessionId(svar.session_id)
        setKind(svar.kind === 'origin' ? 'origin' : 'routine')
      })
      .catch((reason) => {
        if (alive) setFejl(reason instanceof Error ? reason.message : 'Kunne ikke åbne rutinens samtale')
      })
    return () => { alive = false }
  }, [config, routineId])

  const hent = useCallback(async () => {
    if (!sessionId) return
    try {
      const snap = await getSession(config, sessionId)
      const raekker: Besked[] = []
      for (const m of snap.messages) {
        // Rutinens kørsler skrives som opgave/svar. Værktøjs- og
        // system-rækker hører i chatvisningen, ikke i rutinens oversigt.
        if (m.role !== 'user' && m.role !== 'assistant') continue
        raekker.push({ id: m.id, role: m.role, blokke: m.content, tid: m.created_at })
      }
      setBeskeder(raekker)
    } catch {
      // En fejlende poll må ikke rydde det man allerede kan læse.
    }
  }, [config, sessionId])

  useEffect(() => { void hent() }, [hent])

  useEffect(() => {
    if (!sessionId) return
    const timer = window.setInterval(() => {
      if (!maaPolle(`rutine-chat:${sessionId}`, POLL_MS)) return
      void hent()
    }, POLL_MS)
    return () => window.clearInterval(timer)
  }, [sessionId, hent])

  useEffect(() => {
    const el = bundRef.current
    // jsdom (og enkelte indlejrede webviews) har ingen scrollIntoView — en
    // manglende scroll må ikke vælte hele rutinefladen.
    if (el && typeof el.scrollIntoView === 'function') el.scrollIntoView({ block: 'end' })
  }, [beskeder?.length])

  const send = useCallback(async (tekst: string, _opts: ComposerSendOpts) => {
    const sid = sessionRef.current
    const t = tekst.trim()
    if (!t || !sid || sender) return
    setSender(true); setFejl('')
    try {
      await sendRoutineMessage(config, sid, t)
      await hent()
    } catch (reason) {
      setFejl(reason instanceof Error ? reason.message : 'Beskeden kunne ikke sendes')
    } finally {
      setSender(false)
    }
  }, [config, hent, sender])

  const model = readModelPrefs().model || 'standard'

  return (
    <div className="routine-chat">
      <div className="routine-chat-body">
        {fejl && <p className="routine-error" role="alert">{fejl}</p>}
        {!beskeder && !fejl && (
          <div className="routine-empty"><Loader2 size={14} className="spin" /> Henter samtalen…</div>
        )}
        {beskeder && beskeder.length === 0 && (
          <div className="routine-empty">
            {kind === 'origin'
              ? 'Rutinen har ingen session med indhold endnu.'
              : 'Rutinen har ikke kørt endnu. Skriv her, så begynder samtalen.'}
          </div>
        )}
        {beskeder?.map((m) => (
          <div key={m.id} className="msg-block">
            <MessageRow
              role={m.role}
              blocks={m.blokke}
              presentation="chat"
              density="compact"
              streaming={false}
              createdAt={m.tid}
            />
          </div>
        ))}
        <div ref={bundRef} />
      </div>
      <Composer
        streaming={sender}
        onSend={(tekst, opts) => { void send(tekst, opts) }}
        onStop={() => setSender(false)}
        model={model}
        config={config}
        getSessionId={() => Promise.resolve(sessionRef.current ?? '')}
        sessionId={sessionId}
        showPermissions={false}
        showPlanMode={false}
        visKontekstRing={false}
        draftKey={`rutine-${routineId}`}
      />
      {kind === 'origin' && sessionId && onOpenSession && (
        <button type="button" className="routine-chat-aabn" onClick={() => onOpenSession(sessionId)}>
          Åbn i chatvisningen
        </button>
      )}
    </div>
  )
}
