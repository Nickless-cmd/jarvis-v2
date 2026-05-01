import { MessageCircle, Send, Globe } from 'lucide-react'
import { useMcEndpoint } from '../lib/useMcEndpoint'

interface Channel {
  id: string
  label: string
  configured: boolean
  connected: boolean
}

interface ChannelsResp { channels: Channel[] }

/**
 * Cross-machine continuity indicator — shows which channels Jarvis is
 * reachable on right now (Discord / Telegram / webchat / desktop).
 * Same conversation continues across them; this pill is just the
 * "where can he hear me" tag.
 */
export function PresencePill({ apiBaseUrl }: { apiBaseUrl: string }) {
  const { data } = useMcEndpoint<ChannelsResp>(apiBaseUrl, '/api/channels/state', 12000)
  if (!data) return null

  const ICONS: Record<string, typeof MessageCircle> = {
    discord: MessageCircle,
    telegram: Send,
    webchat: Globe,
  }
  const live = data.channels.filter((c) => c.connected)

  return (
    <div
      className="flex items-center gap-1.5 rounded-md border border-line2 bg-bg2 px-2 py-1 font-mono text-[10px]"
      title={data.channels
        .map((c) => `${c.label}: ${c.connected ? 'live' : 'offline'}`)
        .join('\n')}
    >
      <span className="text-fg3">on</span>
      {live.length === 0 && <span className="text-danger">—</span>}
      {live.map((c) => {
        const Icon = ICONS[c.id] || Globe
        return (
          <span
            key={c.id}
            className="flex items-center gap-0.5 text-ok"
            title={c.label}
          >
            <Icon size={10} />
          </span>
        )
      })}
    </div>
  )
}
