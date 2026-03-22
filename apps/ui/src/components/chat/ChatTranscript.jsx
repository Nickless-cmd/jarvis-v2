import { Bot, User } from 'lucide-react'

export function ChatTranscript({ messages }) {
  if (!messages.length) {
    return (
      <section className="transcript panel empty-transcript">
        <p className="muted">Start a conversation to open a new Jarvis thread.</p>
      </section>
    )
  }

  return (
    <section className="transcript panel">
      {messages.map((message) => (
        <article key={message.id} className={`message-row ${message.role}`}>
          <div className="message-avatar">
            {message.role === 'assistant' ? <Bot size={15} /> : <User size={15} />}
          </div>
          <div className={`message-bubble ${message.pending ? 'pending' : ''}`}>
            <div className="message-meta">
              <strong>{message.role === 'assistant' ? 'Jarvis' : 'You'}</strong>
              <span>{message.ts}</span>
            </div>
            {message.content ? <p>{message.content}</p> : null}
            {message.pending ? (
              <div className="thinking-indicator">
                <span className="thinking-dot" />
                <span className="thinking-dot" />
                <span className="thinking-dot" />
                <small>Jarvis is working…</small>
              </div>
            ) : null}
          </div>
        </article>
      ))}
    </section>
  )
}
