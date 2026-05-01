import { Radio, MessageCircle, Send, Globe, RefreshCw, AlertCircle } from 'lucide-react'
import { useMcEndpoint } from '../../lib/useMcEndpoint'

interface Channel {
  id: string
  label: string
  configured: boolean
  connected: boolean
  last_message_at?: string | null
  message_count?: number
  guild_name?: string | null
  active_sessions?: number
  session_count?: number
  error?: string | null
}

interface ChannelsResp {
  channels: Channel[]
}

const ICON_BY_ID: Record<string, typeof Radio> = {
  discord: MessageCircle,
  telegram: Send,
  webchat: Globe,
}

const COLOR_BY_ID: Record<string, string> = {
  discord: '#5865f2',
  telegram: '#26a5e4',
  webchat: '#5ab8a0',
}

export function ChannelsView({ apiBaseUrl }: { apiBaseUrl: string }) {
  const { data, loading, error, refresh } = useMcEndpoint<ChannelsResp>(
    apiBaseUrl,
    '/api/channels/state',
    6000,
  )

  return (
    <div className="flex h-full min-h-0 flex-col">
      <header className="flex flex-shrink-0 items-center justify-between border-b border-line bg-bg1 px-4 py-2">
        <div className="flex items-center gap-3">
          <h2 className="text-sm font-semibold">Channels</h2>
          <span className="font-mono text-[10px] text-fg3">live · 6s polling</span>
        </div>
        <button
          onClick={refresh}
          className="flex items-center gap-1.5 rounded-md border border-line2 bg-bg2 px-2 py-1 text-[10px] text-fg2 hover:text-accent"
        >
          <RefreshCw size={10} />
          refresh
        </button>
      </header>

      <div className="flex-1 overflow-y-auto px-6 py-5">
        {error && (
          <div className="mb-4 rounded-md border border-danger/30 bg-danger/10 px-3 py-2 font-mono text-[11px] text-danger">
            {error}
          </div>
        )}

        {loading && !data && (
          <div className="text-xs text-fg3">loading channels…</div>
        )}

        <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
          {(data?.channels ?? []).map((c) => (
            <ChannelCard key={c.id} channel={c} />
          ))}
        </div>

        <div className="mt-6 rounded-lg border border-line/60 bg-bg1/40 p-4">
          <div className="flex items-start gap-3">
            <Radio size={14} className="mt-0.5 text-fg3" />
            <div className="text-[11px] text-fg3">
              <span className="font-semibold text-fg2">Coming soon:</span>{' '}
              WhatsApp gateway via Baileys (Phase 4 i analysen). Channel-cards
              tilføjes automatisk når runtime'en eksponerer dem.
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function ChannelCard({ channel }: { channel: Channel }) {
  const Icon = ICON_BY_ID[channel.id] || Radio
  const color = COLOR_BY_ID[channel.id] || '#6e7681'
  const status: 'up' | 'down' | 'unconfigured' = !channel.configured
    ? 'unconfigured'
    : channel.connected
    ? 'up'
    : 'down'

  return (
    <div className="rounded-lg border border-line bg-bg1 p-4 transition-colors hover:border-line2">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div
            className="flex h-8 w-8 items-center justify-center rounded-md"
            style={{ background: `${color}20` }}
          >
            <Icon size={16} style={{ color }} />
          </div>
          <div>
            <div className="text-sm font-semibold text-fg">{channel.label}</div>
            <div className="font-mono text-[9px] uppercase tracking-wider text-fg3">
              {channel.id}
            </div>
          </div>
        </div>
        <StatusPill status={status} />
      </div>

      <div className="grid grid-cols-2 gap-2">
        {channel.guild_name && (
          <KV label="Guild" value={channel.guild_name} />
        )}
        {typeof channel.message_count === 'number' && (
          <KV label="Messages" value={channel.message_count.toString()} />
        )}
        {typeof channel.active_sessions === 'number' && (
          <KV label="Active sessions" value={channel.active_sessions.toString()} />
        )}
        {typeof channel.session_count === 'number' && (
          <KV label="Sessions" value={channel.session_count.toString()} />
        )}
        {channel.last_message_at && (
          <KV
            label="Last activity"
            value={relativeTime(channel.last_message_at)}
            wide
          />
        )}
      </div>

      {channel.error && (
        <div className="mt-3 flex items-start gap-2 rounded-md border border-danger/30 bg-danger/10 px-2 py-1.5">
          <AlertCircle size={11} className="mt-0.5 flex-shrink-0 text-danger" />
          <span className="font-mono text-[10px] text-danger">{channel.error}</span>
        </div>
      )}
    </div>
  )
}

function StatusPill({ status }: { status: 'up' | 'down' | 'unconfigured' }) {
  const config = {
    up: { label: 'live', color: '#3fb950', bg: '#3fb95020' },
    down: { label: 'offline', color: '#f85149', bg: '#f8514920' },
    unconfigured: { label: 'ikke konfigureret', color: '#6e7681', bg: '#6e768120' },
  }[status]
  return (
    <div
      className="flex items-center gap-1.5 rounded-full px-2.5 py-0.5"
      style={{ background: config.bg }}
    >
      <span
        className="h-1.5 w-1.5 rounded-full"
        style={{
          background: config.color,
          boxShadow: status === 'up' ? `0 0 6px ${config.color}` : undefined,
        }}
      />
      <span className="font-mono text-[9px] uppercase" style={{ color: config.color }}>
        {config.label}
      </span>
    </div>
  )
}

function KV({ label, value, wide }: { label: string; value: string; wide?: boolean }) {
  return (
    <div
      className={[
        'rounded-md border border-line/60 bg-bg2/40 px-2.5 py-1.5',
        wide ? 'col-span-2' : '',
      ].join(' ')}
    >
      <div className="text-[9px] font-semibold uppercase tracking-wider text-fg3">
        {label}
      </div>
      <div className="mt-0.5 truncate font-mono text-[11px] text-fg">{value}</div>
    </div>
  )
}

function relativeTime(iso: string): string {
  try {
    const delta = Date.now() - new Date(iso).getTime()
    if (isNaN(delta) || delta < 0) return iso
    const sec = Math.floor(delta / 1000)
    if (sec < 60) return 'lige nu'
    const min = Math.floor(sec / 60)
    if (min < 60) return `${min}m siden`
    const hr = Math.floor(min / 60)
    if (hr < 24) return `${hr}t siden`
    return `${Math.floor(hr / 24)}d siden`
  } catch {
    return iso
  }
}
