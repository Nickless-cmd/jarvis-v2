import { useCallback, useEffect, useRef, useState } from 'react'
import { Loader2, Send } from 'lucide-react'
import { getSession, type ApiConfig } from '../../lib/api'
import { maaPolle } from '../../lib/ro'
import { MarkdownRenderer } from '../rich/MarkdownRenderer'
import { getRoutineChatSession, sendRoutineMessage } from '../../lib/routinesApi'

/** Hvor ofte vi henter nye beskeder. Samme kadence som «Kører nu»: 4 s er nok
 *  til at et svar dukker op mens man ser på det, og billigt nok til at stå åbent. */
const POLL_MS = 4000

type Besked = { id: string; role: string; tekst: string; tid: string }

/** Beskeder gemmes som blokke (tekst/billede), ikke som én streng. Vi vil kun
 *  have teksten — en rutine-samtale har ingen vedhæftninger. */
const tilTekst = (content: unknown): string => {
  if (typeof content === 'string') return content
  if (Array.isArray(content)) {
    return content
      .map((del) =>
        del && typeof del === 'object' && 'text' in del
          ? String((del as { text: unknown }).text ?? '')
          : '',
      )
      .join('')
  }
  return ''
}

/** Rutinens samtale.
 *
 *  Højre pane var ren konfiguration: man kunne se HVAD rutinen var sat til, men
 *  ikke hvad den HAVDE gjort — og slet ikke svare den. Bjørn 15/11-2026: «så jeg
 *  faktisk kan se hvad der er sket i rutinen og skrive til dig i rutinen».
 *
 *  Den genbruger ikke `ChatView`: den er bundet til `SessionContext`, så dens
 *  `select()` ville kapre den samtale man sad i, og dens optimistiske besked
 *  ville lande i chat-fladens liste i stedet for her. Denne komponent ejer sin
 *  egen læsning og skriver gennem samme stream-endpoint som chat-fladen, så
 *  svaret er et rigtigt run i netop denne session.
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
  const [tekst, setTekst] = useState('')
  const [sender, setSender] = useState(false)
  const [fejl, setFejl] = useState('')
  const bundRef = useRef<HTMLDivElement>(null)

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
      setBeskeder(snap.messages.map((m) => ({
        id: m.id, role: m.role, tekst: tilTekst(m.content), tid: m.created_at,
      })))
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

  const send = async () => {
    const t = tekst.trim()
    if (!t || !sessionId || sender) return
    setSender(true); setFejl('')
    try {
      await sendRoutineMessage(config, sessionId, t)
      setTekst('')
      await hent()
    } catch (reason) {
      setFejl(reason instanceof Error ? reason.message : 'Beskeden kunne ikke sendes')
    } finally {
      setSender(false)
    }
  }

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
          <article key={m.id} className={`routine-chat-msg is-${m.role}`}>
            <div className="routine-chat-role">{m.role === 'user' ? 'Opgave' : 'Jarvis'}</div>
            {m.role === 'user'
              ? <p className="routine-chat-tekst">{m.tekst}</p>
              : <MarkdownRenderer text={m.tekst} streaming={false} />}
          </article>
        ))}
        <div ref={bundRef} />
      </div>
      <form
        className="routine-chat-composer"
        onSubmit={(e) => { e.preventDefault(); void send() }}
      >
        <textarea
          aria-label="Skriv til Jarvis i rutinen"
          rows={2}
          value={tekst}
          onChange={(e) => setTekst(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); void send() }
          }}
          placeholder="Skriv til Jarvis i denne rutine…"
        />
        <button
          type="submit"
          className="routine-button"
          aria-label="Send besked til rutinen"
          disabled={sender || !tekst.trim()}
        >
          {sender ? <Loader2 size={13} className="spin" /> : <Send size={13} />} Send
        </button>
      </form>
      {kind === 'origin' && sessionId && onOpenSession && (
        <button type="button" className="routine-chat-aabn" onClick={() => onOpenSession(sessionId)}>
          Åbn i chatvisningen
        </button>
      )}
    </div>
  )
}
