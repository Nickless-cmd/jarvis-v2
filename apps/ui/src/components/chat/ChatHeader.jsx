export function ChatHeader({ session, selection, localLane }) {
  return (
    <section className="hero-card chat-hero">
      <div className="chat-hero-copy">
        <p className="eyebrow">Jarvis · Chat</p>
        <h1>{session?.title || 'New chat'}</h1>
        <p>{session?.subtitle || `Main agent: ${selection.currentProvider} / ${selection.currentModel}`}</p>
      </div>

      <div className="chat-hero-meta">
        <div className="meta-chip">
          <span>Main agent</span>
          <strong>{selection.currentProvider} / {selection.currentModel}</strong>
        </div>
        <div className="meta-chip">
          <span>Local lane</span>
          <strong>{localLane.model || 'unconfigured'} · {localLane.status || 'unknown'}</strong>
        </div>
      </div>
    </section>
  )
}
