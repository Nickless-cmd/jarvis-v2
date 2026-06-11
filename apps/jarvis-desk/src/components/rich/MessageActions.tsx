import { useState } from 'react'
import { Copy, Pin, Volume2, Check } from 'lucide-react'
import { formatRelativeTime } from '../../lib/formatTime'

/** Action-række under en besked (opacity 0, fader ind ved hover): tid + kopiér +
 *  pin som kapitel + læs op. Kopiér tager RÅ tekst; læs op bruger Web Speech
 *  Synthesis (da-DK); pin er pt. en lokal markering (kapitel-feature kommer). */
export function MessageActions({ text, createdAt }: { text: string; createdAt?: string }) {
  const [copied, setCopied] = useState(false)
  const [pinned, setPinned] = useState(false)
  const [speaking, setSpeaking] = useState(false)

  const copy = () => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 1400)
  }

  const readAloud = () => {
    const synth = window.speechSynthesis
    if (!synth) return
    if (speaking) { synth.cancel(); setSpeaking(false); return }
    const u = new SpeechSynthesisUtterance(text)
    u.lang = 'da-DK'
    u.onend = () => setSpeaking(false)
    u.onerror = () => setSpeaking(false)
    synth.cancel()
    synth.speak(u)
    setSpeaking(true)
  }

  return (
    <div className="msg-actions">
      {createdAt && <span className="msg-time">{formatRelativeTime(createdAt)}</span>}
      <button type="button" className="msg-action-btn" title="Kopiér" onClick={copy}>
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
    </div>
  )
}
