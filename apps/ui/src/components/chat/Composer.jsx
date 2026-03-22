import { ArrowUp, Paperclip } from 'lucide-react'

export function Composer({ value, onChange, onSend }) {
  return (
    <section className="composer-shell">
      <div className="composer-wrap">
        <button className="icon-btn subtle"><Paperclip size={16} /></button>
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Message Jarvis…"
          rows={1}
        />
        <button className="send-btn" onClick={onSend}>
          <ArrowUp size={16} />
        </button>
      </div>
    </section>
  )
}
