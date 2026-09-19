import { Bot } from 'lucide-react'
import { useFigurVist } from '../lib/figurVist'

/** Headerens genvej: vis/skjul Jarvis-figuren på skrivebordet (Codex'
 *  «Vis eller skjul virtuelt kæledyr»). Tegnes kun i desk. */
export function FigurKnap() {
  const [vist, saet] = useFigurVist()
  if (vist === null) return null
  const tekst = vist ? 'Skjul Jarvis-figuren' : 'Vis Jarvis-figuren på skrivebordet'
  return (
    <button
      type="button"
      className={`panel-toggle${vist ? ' active' : ''}`}
      aria-label={tekst}
      aria-pressed={vist}
      title={tekst}
      onClick={() => saet(!vist)}
    >
      <Bot size={15} strokeWidth={1.8} />
    </button>
  )
}
