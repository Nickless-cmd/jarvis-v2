import { useState } from 'react'
import { Send } from 'lucide-react'
import type { CanvasReference } from '../lib/inspectorTargets'
import { sendCanvas } from '../lib/canvasBus'

/** Redigérbart dokument i sidepanelet. «Send til samtalen» sender den rettede
 *  tekst tilbage som en besked via `canvasBus` (ChatView lytter). */
export function CanvasPanel({ canvas }: { canvas: CanvasReference }) {
  const [tekst, setTekst] = useState(canvas.tekst)
  const [status, setStatus] = useState<'' | 'sendt' | 'ingen-samtale'>('')
  const aendret = tekst !== canvas.tekst

  const send = () => {
    // Ingen lytter = vi står ikke i chatten. Sig det frem for at lade knappen
    // se ud som om noget blev sendt.
    setStatus(sendCanvas({ titel: canvas.titel, tekst }) ? 'sendt' : 'ingen-samtale')
  }

  return (
    <div className="artifact-body canvas-flade">
      <textarea
        className="canvas-tekst"
        aria-label={`Canvas: ${canvas.titel}`}
        value={tekst}
        spellCheck={false}
        onChange={(e) => { setTekst(e.target.value); setStatus('') }}
      />
      <div className="canvas-bund">
        <button type="button" className="canvas-send" disabled={tekst.trim() === ''} onClick={send}>
          <Send size={13} /> Send til samtalen
        </button>
        {status === 'sendt' && <span className="canvas-status">Sendt{aendret ? ' (med dine rettelser)' : ''}.</span>}
        {status === 'ingen-samtale' && (
          <span className="canvas-status canvas-fejl" role="alert">Åbn en chat-samtale for at sende — intet blev sendt.</span>
        )}
      </div>
    </div>
  )
}
