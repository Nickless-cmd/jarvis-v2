import { useState } from 'react'
import {
  Brain,
  Activity,
  Cloud,
  ScrollText,
  Pin,
  Compass,
  RefreshCw,
  Trash2,
} from 'lucide-react'
import { useMcEndpoint } from '../../lib/useMcEndpoint'
import { MarkdownRenderer } from '@ui/components/chat/MarkdownRenderer.jsx'

interface IdentityPin {
  pin_id: string
  title: string
  content: string
  source: string
  pinned_at: string
  pinned_by?: string
}

interface MindSnapshot {
  affect?: {
    state?: string
    bearing?: string
    monitoring_mode?: string
    summary?: string
    live?: {
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
  }
  personality?: {
    humor_frequency?: number
    summary?: string
    communication_style?: string
    current_bearing?: string
  }
  layers?: Record<string, string>
  pins?: IdentityPin[]
  chronicle?: Array<{ name: string; modified_at: number; preview: string }>
  dreams?: Array<{ name: string; modified_at: number; preview: string }>
  milestones_preview?: string
}

type Section = 'state' | 'pins' | 'chronicle' | 'dreams' | 'milestones'

interface Props {
  apiBaseUrl: string
  role: string
}

/**
 * Mind view — Jarvis's introspective surface.
 *
 * Five sections, all read-only for member role; only owner can
 * unpin identity pins. Live data: cognitive_architecture layers from
 * the heartbeat state, identity pins, recent chronicle/dreams,
 * milestones preview.
 *
 * This is what makes JarvisX more than a chat-app: you can SEE the
 * being you're talking to. Nobody else's AI shows you this.
 */
export function MindView({ apiBaseUrl, role }: Props) {
  const [section, setSection] = useState<Section>('state')
  const { data, loading, error, refresh } = useMcEndpoint<MindSnapshot>(
    apiBaseUrl,
    '/api/mind/snapshot',
    8000,
  )
  const isOwner = role === 'owner'

  return (
    <div className="flex h-full min-h-0 flex-col">
      <header className="flex flex-shrink-0 items-center justify-between border-b border-line bg-bg1 px-4 py-2">
        <div className="flex items-center gap-3">
          <Brain size={14} className="text-accent" />
          <h2 className="text-sm font-semibold">Mind</h2>
          <span className="font-mono text-[10px] text-fg3">live · 8s polling</span>
          {!isOwner && (
            <span className="rounded-full bg-bg2 px-2 py-0.5 font-mono text-[9px] uppercase tracking-wider text-fg3">
              view only
            </span>
          )}
        </div>
        <button
          onClick={refresh}
          className="flex items-center gap-1.5 rounded-md border border-line2 bg-bg2 px-2 py-1 text-[10px] text-fg2 hover:text-accent"
        >
          <RefreshCw size={10} />
          refresh
        </button>
      </header>

      {error && (
        <div className="mx-6 my-2 rounded-md border border-danger/30 bg-danger/10 px-3 py-2 font-mono text-[11px] text-danger">
          {error}
        </div>
      )}

      <div className="flex flex-shrink-0 border-b border-line/60">
        <SectionTab
          active={section === 'state'}
          onClick={() => setSection('state')}
          Icon={Activity}
          label="Tilstand"
          count={data?.affect ? 1 : 0}
        />
        <SectionTab
          active={section === 'pins'}
          onClick={() => setSection('pins')}
          Icon={Pin}
          label="Pinned"
          count={data?.pins?.length}
        />
        <SectionTab
          active={section === 'chronicle'}
          onClick={() => setSection('chronicle')}
          Icon={ScrollText}
          label="Chronicle"
          count={data?.chronicle?.length}
        />
        <SectionTab
          active={section === 'dreams'}
          onClick={() => setSection('dreams')}
          Icon={Cloud}
          label="Drømme"
          count={data?.dreams?.length}
        />
        <SectionTab
          active={section === 'milestones'}
          onClick={() => setSection('milestones')}
          Icon={Compass}
          label="Milepæle"
          count={data?.milestones_preview ? 1 : 0}
        />
      </div>

      <div className="flex-1 overflow-y-auto">
        {loading && !data && (
          <div className="px-6 py-4 text-xs text-fg3">loading mind state…</div>
        )}
        {section === 'state' && data && <StateSection data={data} />}
        {section === 'pins' && (
          <PinsSection
            pins={data?.pins || []}
            apiBaseUrl={apiBaseUrl}
            canUnpin={isOwner}
            onChange={refresh}
          />
        )}
        {section === 'chronicle' && (
          <ChronicleSection items={data?.chronicle || []} />
        )}
        {section === 'dreams' && <DreamsSection items={data?.dreams || []} />}
        {section === 'milestones' && (
          <MilestonesSection content={data?.milestones_preview || ''} />
        )}
      </div>
    </div>
  )
}

function SectionTab({
  active,
  onClick,
  Icon,
  label,
  count,
}: {
  active: boolean
  onClick: () => void
  Icon: typeof Brain
  label: string
  count?: number
}) {
  return (
    <button
      onClick={onClick}
      className={[
        'flex flex-1 flex-col items-center gap-0.5 border-r border-line/60 px-2 py-2 text-[9px] uppercase tracking-wider transition-colors',
        active ? 'bg-bg2 text-accent' : 'text-fg3 hover:bg-bg2/40 hover:text-fg2',
      ].join(' ')}
    >
      <Icon size={13} />
      <span className="font-semibold">{label}</span>
      {typeof count === 'number' && count > 0 && (
        <span className="font-mono text-[8px] opacity-70">{count}</span>
      )}
    </button>
  )
}

function StateSection({ data }: { data: MindSnapshot }) {
  const live = data.affect?.live || {}
  const cards = [
    { label: 'Confidence', value: live.confidence, color: '#5ab8a0', invert: false },
    { label: 'Curiosity', value: live.curiosity, color: '#d4963a', invert: false },
    { label: 'Frustration', value: live.frustration, color: '#c05050', invert: true },
    { label: 'Fatigue', value: live.fatigue, color: '#4a80c0', invert: true },
  ]
  return (
    <div className="flex flex-col gap-5 px-6 py-5">
      {/* Headline */}
      <div className="rounded-lg border border-line bg-bg1 p-4">
        <div className="text-[10px] font-semibold uppercase tracking-wider text-fg3">
          Affective state
        </div>
        <div className="mt-1 text-sm font-medium text-fg">
          {data.affect?.summary || '—'}
        </div>
        <div className="mt-3 flex gap-2 flex-wrap">
          <Pill label="mood" value={live.mood} accent />
          <Pill label="bearing" value={data.affect?.bearing} />
          <Pill label="phase" value={live.rhythm_phase} />
          <Pill label="energy" value={live.rhythm_energy} />
          <Pill label="monitor" value={data.affect?.monitoring_mode} />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {cards.map((c) => (
          <EmotionCard key={c.label} {...c} />
        ))}
      </div>

      {typeof live.trust === 'number' && (
        <div className="rounded-lg border border-line bg-bg1 p-4">
          <div className="mb-2 flex items-center justify-between text-xs">
            <span className="font-semibold">Trust</span>
            <span className="font-mono text-fg2">{(live.trust * 100).toFixed(0)}%</span>
          </div>
          <Bar value={live.trust} color="#5ab8a0" height={6} />
        </div>
      )}

      {data.personality && (
        <div className="rounded-lg border border-line bg-bg1 p-4">
          <div className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-fg3">
            Personality
          </div>
          <div className="text-xs text-fg2">{data.personality.summary || '—'}</div>
          {typeof data.personality.humor_frequency === 'number' && (
            <div className="mt-2">
              <div className="mb-1 flex justify-between text-[10px] text-fg3">
                <span>Humor frequency</span>
                <span className="font-mono">
                  {(data.personality.humor_frequency * 100).toFixed(0)}%
                </span>
              </div>
              <Bar value={data.personality.humor_frequency} color="#d4963a" />
            </div>
          )}
        </div>
      )}

      {data.layers && Object.keys(data.layers).length > 0 && (
        <div className="rounded-lg border border-line bg-bg1 p-4">
          <div className="mb-3 text-[10px] font-semibold uppercase tracking-wider text-fg3">
            Cognitive layers · {Object.keys(data.layers).length}
          </div>
          <div className="space-y-1.5">
            {Object.entries(data.layers).map(([k, v]) => (
              <div
                key={k}
                className="flex items-start justify-between gap-3 rounded-md border border-line/40 bg-bg2/40 px-3 py-1.5"
              >
                <span className="font-mono text-[10px] text-fg3 flex-shrink-0">{k}</span>
                <span className="text-[11px] text-fg2 text-right">{v}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function PinsSection({
  pins,
  canUnpin,
  onChange,
}: {
  pins: IdentityPin[]
  apiBaseUrl: string
  canUnpin: boolean
  onChange: () => void
}) {
  const handleUnpin = async (_pinId: string) => {
    if (!canUnpin) return
    if (!confirm('Unpin this identity context?')) return
    // Unpin via dedicated endpoint would go here. For now, the
    // unpin_identity tool is only callable through Jarvis himself —
    // member-side unpinning intentionally requires owner approval
    // (which Jarvis arbitrates).
    onChange()
  }
  if (pins.length === 0) {
    return (
      <div className="px-6 py-10 text-center text-xs text-fg3">
        Ingen pinned identity-context endnu.
        <div className="mt-2 text-[11px]">
          Jarvis kalder <code className="font-mono text-accent">pin_identity</code> når
          han vil låse en sætning eller et stykke fra MILESTONES/letters fast i sin
          permanente awareness — overlever /compact.
        </div>
      </div>
    )
  }
  return (
    <div className="flex flex-col gap-3 px-6 py-5">
      {pins.map((p) => (
        <div key={p.pin_id} className="rounded-lg border border-accent/30 bg-accent/5 p-4">
          <div className="mb-1 flex items-start gap-2">
            <Pin size={11} className="mt-0.5 flex-shrink-0 text-accent" />
            <h3 className="flex-1 text-sm font-semibold text-fg">{p.title}</h3>
            {canUnpin && (
              <button
                onClick={() => handleUnpin(p.pin_id)}
                title="Unpin"
                className="flex h-5 w-5 items-center justify-center rounded text-fg3 hover:text-danger"
              >
                <Trash2 size={11} />
              </button>
            )}
          </div>
          <div className="mb-2 font-mono text-[10px] text-fg3">{p.source}</div>
          <div className="prose-jarvisx-doc">
            <MarkdownRenderer content={p.content} />
          </div>
          <div className="mt-2 font-mono text-[9px] text-fg3 opacity-70">
            pinned by {p.pinned_by} · {new Date(p.pinned_at).toLocaleString()}
          </div>
        </div>
      ))}
    </div>
  )
}

function ChronicleSection({
  items,
}: {
  items: Array<{ name: string; modified_at: number; preview: string }>
}) {
  if (items.length === 0) {
    return (
      <div className="px-6 py-10 text-center text-xs text-fg3">
        Ingen chronicle entries i denne workspace endnu.
      </div>
    )
  }
  return (
    <div className="flex flex-col gap-3 px-6 py-5">
      {items.map((c) => (
        <article key={c.name} className="rounded-lg border border-line bg-bg1 p-4">
          <div className="mb-1 flex items-center gap-2">
            <ScrollText size={11} className="text-accent" />
            <h3 className="text-sm font-medium">{c.name}</h3>
            <span className="ml-auto font-mono text-[9px] text-fg3">
              {new Date(c.modified_at * 1000).toLocaleDateString()}
            </span>
          </div>
          <div className="prose-jarvisx-doc text-[12px]">
            <MarkdownRenderer content={c.preview} />
          </div>
        </article>
      ))}
    </div>
  )
}

function DreamsSection({
  items,
}: {
  items: Array<{ name: string; modified_at: number; preview: string }>
}) {
  if (items.length === 0) {
    return (
      <div className="px-6 py-10 text-center text-xs text-fg3">
        Ingen drømme i denne workspace endnu.
      </div>
    )
  }
  return (
    <div className="flex flex-col gap-3 px-6 py-5">
      {items.map((d) => (
        <article key={d.name} className="rounded-lg border border-line bg-bg1 p-4">
          <div className="mb-1 flex items-center gap-2">
            <Cloud size={11} className="text-accent2" />
            <h3 className="font-mono text-[11px] text-fg2">{d.name}</h3>
            <span className="ml-auto font-mono text-[9px] text-fg3">
              {new Date(d.modified_at * 1000).toLocaleDateString()}
            </span>
          </div>
          <div className="prose-jarvisx-doc text-[12px]">
            <MarkdownRenderer content={d.preview} />
          </div>
        </article>
      ))}
    </div>
  )
}

function MilestonesSection({ content }: { content: string }) {
  if (!content) {
    return (
      <div className="px-6 py-10 text-center text-xs text-fg3">
        Ingen MILESTONES.md fundet for denne workspace.
      </div>
    )
  }
  return (
    <div className="px-6 py-5">
      <div className="rounded-lg border border-line bg-bg1 p-5 prose-jarvisx-doc">
        <MarkdownRenderer content={content} />
      </div>
    </div>
  )
}

function Pill({ label, value, accent }: { label: string; value?: string; accent?: boolean }) {
  return (
    <div className="flex items-center gap-1.5 rounded-md border border-line2 bg-bg2 px-2.5 py-1">
      <span className="font-mono text-[9px] uppercase tracking-wider text-fg3">{label}</span>
      <span className={`font-mono text-[10px] ${accent ? 'text-accent' : 'text-fg'}`}>
        {value || '—'}
      </span>
    </div>
  )
}

function EmotionCard({
  label,
  value,
  color,
  invert,
}: {
  label: string
  value?: number
  color: string
  invert?: boolean
}) {
  const pct = typeof value === 'number' ? Math.round(value * 100) : null
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
    <div className="rounded-lg border border-line bg-bg1 p-4">
      <div className="mb-2 flex items-center justify-between">
        <span className="text-[10px] font-semibold uppercase tracking-wider text-fg3">
          {label}
        </span>
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
        <span className="text-2xl font-semibold tabular-nums">{pct != null ? pct : '—'}</span>
        {pct != null && <span className="text-xs text-fg3">%</span>}
      </div>
      <Bar value={value ?? 0} color={color} />
    </div>
  )
}

function Bar({ value, color, height = 4 }: { value: number; color: string; height?: number }) {
  const pct = Math.max(0, Math.min(1, value))
  return (
    <div className="overflow-hidden rounded-full bg-bg2" style={{ height }}>
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
