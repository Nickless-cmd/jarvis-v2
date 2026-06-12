import type { CoworkChannel } from '../../lib/coworkApi'

export function ChannelsPane({ channels }: { channels: CoworkChannel[] }) {
  if (channels.length === 0) return <div className="cowork-empty">Ingen kanaler</div>
  return (
    <div className="cowork-channels">
      {channels.map((c) => (
        <div key={c.name} className="cowork-channel">
          <span className="cowork-channel-name">{c.name}</span>
          <span className={`cowork-dot ${c.online ? 'on' : 'off'}`} />
          {c.unread > 0 && <span className="cowork-unread">{c.unread} nye</span>}
        </div>
      ))}
    </div>
  )
}
