import type { ShareDecision } from '../../lib/coworkApi'

/**
 * Cross-user share-guard-rude (spec §4.4). Når Jarvis nævner en anden bruger end
 * samtalepartneren, dukker en pending "privat eller del?"-beslutning op her. Owner
 * vælger "Okay at dele" eller "Hold privat". Bevidst placeret i Cowork-køen (ikke
 * i den live chat-stream) — detektionen sker post-stream, så et blokerende kort i
 * streamen ville være for sent + risikabelt for streaming-stien.
 */
export function ShareGuardPane({
  items,
  onResolve,
}: {
  items: ShareDecision[]
  onResolve: (id: string, shared: boolean) => void
}) {
  if (items.length === 0) {
    return <div className="cowork-empty">Ingen deling-beslutninger afventer.</div>
  }
  return (
    <ul className="shareguard-list">
      {items.map((d) => (
        <li key={d.id} className="shareguard-item">
          <div className="shareguard-who">
            Nævner: <strong>{d.mentioned_users.join(', ')}</strong>
          </div>
          <div className="shareguard-preview">{d.text_preview}</div>
          <div className="shareguard-actions">
            <button type="button" className="shareguard-share" onClick={() => onResolve(d.id, true)}>
              Okay at dele
            </button>
            <button type="button" className="shareguard-private" onClick={() => onResolve(d.id, false)}>
              Hold privat
            </button>
          </div>
        </li>
      ))}
    </ul>
  )
}
