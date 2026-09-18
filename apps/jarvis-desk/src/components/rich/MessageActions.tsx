import { useState } from 'react'
import { Copy, Pin, Volume2, Check, RotateCw } from 'lucide-react'
import { formatRelativeTime } from '../../lib/formatTime'
import { skrivTilUdklipsholder } from '../../lib/udklipsholder'

/** Action-række under en besked (opacity 0, fader ind ved hover): tid + kopiér +
 *  pin som kapitel + læs op (+ gensend for bruger-beskeder). Kopiér tager RÅ
 *  tekst; læs op bruger Web Speech Synthesis (da-DK); pin er pt. en lokal
 *  markering (kapitel-feature kommer). onResend vises kun når den gives. */
export function MessageActions({
  text, createdAt, onResend,
}: { text: string; createdAt?: string; onResend?: () => void }) {
  const [copied, setCopied] = useState(false)
  const [pinned, setPinned] = useState(false)
  const [speaking, setSpeaking] = useState(false)
  const [fejl, setFejl] = useState('')

  const copy = async () => {
    setFejl('')
    // Fluebenet satte sig FØR uden at se på svaret. `writeText` returnerer et
    // løfte, og i den pakkede app blev det afvist af Electrons
    // permission-handler — så knappen kvitterede for en kopiering der aldrig
    // skete (Bjørn 18/9-2026). Nu er kvitteringen bundet til resultatet.
    if (await skrivTilUdklipsholder(text)) {
      setCopied(true)
      setTimeout(() => setCopied(false), 1400)
    } else {
      setFejl('Kunne ikke kopiere')
      setTimeout(() => setFejl(''), 2200)
    }
  }

  const readAloud = () => {
    setFejl('')
    const synth = window.speechSynthesis
    if (!synth) { setFejl('Oplæsning findes ikke her'); setTimeout(() => setFejl(''), 2200); return }
    if (speaking) { synth.cancel(); setSpeaking(false); return }
    // Ingen stemmer = ingen lyd, tavst. Det er præcis sådan «læs op» så ud da
    // Chromium manglede broen til speech-dispatcher: knappen lyste op og der
    // skete intet. Sig det i stedet.
    if (synth.getVoices().length === 0) {
      setFejl('Ingen stemmer installeret')
      setTimeout(() => setFejl(''), 2600)
      return
    }
    const u = new SpeechSynthesisUtterance(text)
    u.lang = 'da-DK'
    u.onend = () => setSpeaking(false)
    u.onerror = () => { setSpeaking(false); setFejl('Oplæsningen fejlede'); setTimeout(() => setFejl(''), 2200) }
    synth.cancel()
    synth.speak(u)
    setSpeaking(true)
  }

  return (
    <div className="msg-actions">
      {onResend && (
        <button type="button" className="msg-action-btn" title="Send igen" onClick={onResend}>
          <RotateCw size={13} />
        </button>
      )}
      <button type="button" className="msg-action-btn" title="Kopiér" onClick={() => void copy()}>
        {copied ? <Check size={13} /> : <Copy size={13} />}
      </button>
      <button
        type="button"
        className={`msg-action-btn ${pinned ? 'active' : ''}`}
        title="Pin som kapitel"
        onClick={() => setPinned((p) => !p)}
      >
        <Pin size={13} />
      </button>
      <button
        type="button"
        className={`msg-action-btn ${speaking ? 'active' : ''}`}
        title="Læs op"
        onClick={readAloud}
      >
        <Volume2 size={13} />
      </button>
      {/* En handling der ikke lykkedes skal SIGE det. Rækken stod før og lod
          som ingenting, og så er en død knap ikke til at skelne fra en man
          ramte ved siden af. */}
      {fejl && <span className="msg-action-fejl" role="status">{fejl}</span>}
      {createdAt && <span className="msg-time">{formatRelativeTime(createdAt)}</span>}
    </div>
  )
}
