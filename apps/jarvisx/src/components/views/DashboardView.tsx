import {
  Smile,
  Lightbulb,
  Frown,
  Battery,
  Activity,
  Compass,
  Gauge,
  Heart,
  RefreshCw,
} from 'lucide-react'
import { useMcEndpoint } from '../../lib/useMcEndpoint'

interface AffectiveMetaState {
  state?: string
  bearing?: string
  monitoring_mode?: string
  reflective_load?: string
  summary?: string
  live_emotional_state?: {
    mood?: string
    confidence?: number
    curiosity?: number
    frustration?: number
    fatigue?: number
    trust?: number
    rhythm_phase?: string
    rhythm_energy?: string
    rhythm_social?: string
  }
  source_contributors?: { source: string; signal: string }[]
}

export function DashboardView({ apiBaseUrl }: { apiBaseUrl: string }) {
  const { data, loading, error, refresh } = useMcEndpoint<AffectiveMetaState>(
    apiBaseUrl,
    '/mc/affective-meta-state',
    4000,
  )

  const emo = data?.live_emotional_state ?? {}
  const cards: Array<{
    label: string
    value: number | undefined
    Icon: typeof Smile
    color: string
    invert?: boolean
  }> = [
    { label: 'Confidence', value: emo.confidence, Icon: Smile, color: '#5ab8a0' },
    { label: 'Curiosity', value: emo.curiosity, Icon: Lightbulb, color: '#d4963a' },
    {
      label: 'Frustration',
      value: emo.frustration,
      Icon: Frown,
      color: '#c05050',
      invert: true,
    },
    { label: 'Fatigue', value: emo.fatigue, Icon: Battery, color: '#4a80c0', invert: true },
  ]

  return (
    <div className="flex h-full min-h-0 flex-col">
      <header className="flex flex-shrink-0 items-center justify-between border-b border-line bg-bg1 px-4 py-2">
        <div className="flex items-center gap-3">
          <h2 className="text-sm font-semibold">Dashboard</h2>
          <span className="font-mono text-[10px] text-fg3">live · 4s polling</span>
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

        {/* Headline summary */}
        <div className="mb-5 rounded-lg border border-line bg-bg1 p-4">
          <div className="flex items-baseline gap-3">
            <Activity size={14} className="translate-y-0.5 text-accent" />
            <div className="flex-1">
              <div className="text-[10px] font-semibold uppercase tracking-wider text-fg3">
                State
              </div>
              <div className="mt-0.5 text-base font-medium text-fg">
                {loading && !data ? '…' : data?.summary || 'unknown'}
              </div>
            </div>
            <Pill label="mood" value={emo.mood} accent />
            <Pill label="bearing" value={data?.bearing} />
          </div>
        </div>

        {/* Emotion cards */}
        <div className="mb-5 grid grid-cols-2 gap-3 lg:grid-cols-4">
          {cards.map((c) => (
            <EmotionCard key={c.label} {...c} />
          ))}
        </div>

        {/* Rhythm row */}
        <div className="mb-5 grid grid-cols-2 gap-3 lg:grid-cols-4">
          <SmallStat
            Icon={Compass}
            label="Phase"
            value={emo.rhythm_phase}
            color="#58a6ff"
          />
          <SmallStat
            Icon={Gauge}
            label="Energy"
            value={emo.rhythm_energy}
            color="#5ab8a0"
          />
          <SmallStat
            Icon={Heart}
            label="Social"
            value={emo.rhythm_social}
            color="#bc8cff"
          />
          <SmallStat
            Icon={Activity}
            label="Monitor"
            value={data?.monitoring_mode}
            color="#d4963a"
          />
        </div>

        {/* Trust gauge — special slot, full bar */}
        {typeof emo.trust === 'number' && (
          <div className="mb-5 rounded-lg border border-line bg-bg1 p-4">
            <div className="mb-2 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Heart size={12} className="text-accent" />
                <span className="text-xs font-semibold">Trust</span>
              </div>
              <span className="font-mono text-xs text-fg2">
                {(emo.trust * 100).toFixed(0)}%
              </span>
            </div>
            <Bar value={emo.trust} color="#5ab8a0" height={6} />
          </div>
        )}

        {/* Source contributors */}
        {data?.source_contributors && data.source_contributors.length > 0 && (
          <div className="rounded-lg border border-line bg-bg1 p-4">
            <div className="mb-3 text-[10px] font-semibold uppercase tracking-wider text-fg3">
              Source signals · {data.source_contributors.length}
            </div>
            <div className="grid grid-cols-1 gap-1.5 md:grid-cols-2">
              {data.source_contributors.map((s, i) => (
                <div
                  key={`${s.source}-${i}`}
                  className="flex items-center justify-between rounded-md border border-line/60 bg-bg2/50 px-3 py-1.5"
                >
                  <span className="font-mono text-[10px] text-fg2">{s.source}</span>
                  <span className="font-mono text-[10px] text-fg3">{s.signal}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function EmotionCard({
  label,
  value,
  Icon,
  color,
  invert,
}: {
  label: string
  value?: number
  Icon: typeof Smile
  color: string
  invert?: boolean
}) {
  const pct = typeof value === 'number' ? Math.round(value * 100) : null
  // For "negative" emotions (frustration, fatigue) low is good — flip the
  // color intensity so high-value reads as warning rather than success.
  const tone = invert
    ? pct == null
      ? 'neutral'
      : pct > 60
      ? 'hot'
      : pct > 30
      ? 'warm'
      : 'cool'
    : 'normal'

  return (
    <div className="rounded-lg border border-line bg-bg1 p-4 transition-colors hover:border-line2">
      <div className="mb-2 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Icon size={14} style={{ color }} />
          <span className="text-[10px] font-semibold uppercase tracking-wider text-fg3">
            {label}
          </span>
        </div>
        {tone !== 'normal' && tone !== 'neutral' && (
          <span
            className="rounded-full px-1.5 py-0.5 font-mono text-[8px] uppercase"
            style={{
              background:
                tone === 'hot' ? '#c0505030' : tone === 'warm' ? '#d4963a30' : '#5ab8a030',
              color: tone === 'hot' ? '#c05050' : tone === 'warm' ? '#d4963a' : '#5ab8a0',
            }}
          >
            {tone}
          </span>
        )}
      </div>
      <div className="mb-2 flex items-baseline gap-1">
        <span className="text-2xl font-semibold tabular-nums text-fg">
          {pct != null ? pct : '—'}
        </span>
        {pct != null && <span className="text-xs text-fg3">%</span>}
      </div>
      <Bar value={value ?? 0} color={color} />
    </div>
  )
}

function SmallStat({
  Icon,
  label,
  value,
  color,
}: {
  Icon: typeof Smile
  label: string
  value?: string
  color: string
}) {
  return (
    <div className="rounded-lg border border-line bg-bg1 p-3">
      <div className="flex items-center gap-2">
        <Icon size={12} style={{ color }} />
        <span className="text-[10px] font-semibold uppercase tracking-wider text-fg3">
          {label}
        </span>
      </div>
      <div className="mt-1.5 truncate text-sm font-medium text-fg">
        {value || '—'}
      </div>
    </div>
  )
}

function Pill({ label, value, accent }: { label: string; value?: string; accent?: boolean }) {
  return (
    <div className="flex items-center gap-1.5 rounded-md border border-line2 bg-bg2 px-2.5 py-1">
      <span className="font-mono text-[9px] uppercase tracking-wider text-fg3">
        {label}
      </span>
      <span
        className={`font-mono text-[10px] ${accent ? 'text-accent' : 'text-fg'}`}
      >
        {value || '—'}
      </span>
    </div>
  )
}

function Bar({ value, color, height = 4 }: { value: number; color: string; height?: number }) {
  const pct = Math.max(0, Math.min(1, value))
  return (
    <div
      className="overflow-hidden rounded-full bg-bg2"
      style={{ height }}
    >
      <div
        className="h-full transition-all duration-500 ease-out"
        style={{
          width: `${pct * 100}%`,
          background: `linear-gradient(90deg, ${color}80, ${color})`,
        }}
      />
    </div>
  )
}
