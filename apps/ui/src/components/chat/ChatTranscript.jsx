import { Bot, User } from 'lucide-react'

export function ChatTranscript({ messages }) {
  return (
    <section className="transcript panel">
      {messages.map((message) => (
        <article key={message.id} className={`message-row ${message.role}`}>
          <div className="message-avatar">
            {message.role === 'assistant' ? <Bot size={15} /> : <User size={15} />}
          </div>
          <div className="message-bubble">
            <div className="message-meta">
              <strong>{message.role === 'assistant' ? 'Jarvis' : 'You'}</strong>
              <span>{message.ts}</span>
            </div>
            <p>{message.content}</p>
          </div>
        </article>
      ))}
    </section>
  )
}
