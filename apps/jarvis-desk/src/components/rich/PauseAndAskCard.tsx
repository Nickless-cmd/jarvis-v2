import { useEffect, useId, useState } from 'react'
import { emitPauseSvar, type PauseAsk } from '../../lib/pauseAsk'
import '../../styles/pause-ask.css'

/** Only option labels become interactive. Tool text remains inert. */
export function PauseAndAskCard({ ask }: { ask: PauseAsk }) {
  const [selected, setSelected] = useState<string[]>([])
  const [ownAnswer, setOwnAnswer] = useState('')
  const [submitted, setSubmitted] = useState(false)
  const ownId = useId()
  const identity = JSON.stringify([ask.question, ask.options, ask.allowMultiple])

  useEffect(() => {
    setSelected([])
    setOwnAnswer('')
    setSubmitted(false)
  }, [identity])

  const choose = (option: string) => {
    if (submitted) return
    setSelected((current) => ask.allowMultiple
      ? current.includes(option) ? current.filter((item) => item !== option) : [...current, option]
      : [option])
  }

  const send = () => {
    if (submitted) return
    const own = ownAnswer.trim()
    const answer = own || (ask.allowMultiple
      ? selected.length ? `Jeg vælger:\n${ask.options.filter((o) => selected.includes(o)).map((o) => `- ${o}`).join('\n')}` : ''
      : selected[0] || '')
    if (!answer) return
    setSubmitted(true)
    emitPauseSvar(answer)
  }

  return (
    <section className={`pauseask haste-${ask.urgency}`} aria-label="Spørgsmål fra Jarvis">
      <div className="pauseask-head"><span className="pauseask-pulse" aria-hidden="true" />Jarvis venter på dig</div>
      <p className="pauseask-q">{ask.question}</p>
      {ask.context && <p className="pauseask-ctx">{ask.context}</p>}
      {ask.options.length > 0 && (
        <div className="pauseask-valg" aria-label={ask.allowMultiple ? 'Vælg flere muligheder' : 'Vælg én mulighed'}>
          {ask.options.map((option) => (
            <button key={option} type="button" className="pauseask-btn" aria-pressed={selected.includes(option)}
              onClick={() => choose(option)} disabled={submitted}>
              {ask.allowMultiple && <span className="pauseask-circle" aria-hidden="true">{selected.includes(option) ? '●' : ''}</span>}
              <span>{option}</span>
            </button>
          ))}
        </div>
      )}
      <label className="pauseask-own-label" htmlFor={ownId}>Skriv dit eget svar</label>
      <input id={ownId} className="pauseask-own" value={ownAnswer} onChange={(event) => setOwnAnswer(event.target.value)} disabled={submitted} placeholder="Dit svar…" />
      <div className="pauseask-actions">
        <button type="button" className="pauseask-send" onClick={send} disabled={submitted || (!ownAnswer.trim() && selected.length === 0)}>
          {submitted ? 'Sender…' : 'Send svar'}
        </button>
      </div>
    </section>
  )
}
