import { useRef, useState } from 'react'
import { ArrowUp } from 'lucide-react'

/** Composer (Codex-stil). Enter sender, Shift+Enter ny linje. Tekst bevares ved
 *  fejlet send (caller nulstiller kun ved succes via at vi tømmer her efter
 *  onSend kaldes — onSend må ikke kaste). */
export function Composer({
  disabled,
  onSend,
  model,
  thinking,
}: {
  disabled: boolean
  onSend: (text: string) => void
  model: string
  thinking: string
}) {
  const [text, setText] = useState('')
  const ref = useRef<HTMLTextAreaElement>(null)
  const send = () => {
    const t = text.trim()
    if (!t || disabled) return
    onSend(t)
    setText('')
  }
  return (
    <div className="composer">
      <textarea
        ref={ref}
        className="composer-input"
        rows={2}
        disabled={disabled}
        value={text}
        placeholder={disabled ? 'Jarvis svarer…' : 'Skriv en besked til Jarvis...'}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            send()
          }
        }}
      />
      <div className="composer-bar">
        <div className="composer-right">
          <button type="button" className="model-pill">
            <span className="dot" />
            {model}
            <span className="caret">▾</span>
          </button>
          <button type="button" className="model-pill">
            {thinking}
            <span className="caret">▾</span>
          </button>
          <button
            type="button"
            className="composer-send"
            disabled={!text.trim() || disabled}
            onClick={send}
            aria-label="Send"
          >
            <ArrowUp size={14} strokeWidth={2.5} />
          </button>
        </div>
      </div>
    </div>
  )
}
