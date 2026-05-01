import { useState } from 'react'
import { Clock, Repeat, Bell, CheckCircle2, AlertCircle, RefreshCw, Calendar } from 'lucide-react'
import { useMcEndpoint } from '../../lib/useMcEndpoint'

interface ScheduledTask {
  task_id?: string
  focus?: string
  status?: string
  run_at?: string
  fired_at?: string
}

interface RecurringTask {
  task_id?: string
  focus?: string
  source?: string
  status?: string
  next_fire_at?: string
  last_fired_at?: string
  fire_count?: number
  interval_minutes?: number
}

interface Wakeup {
  wakeup_id?: string
  prompt?: string
  reason?: string
  status?: string
  fire_at?: string
  fired_at?: string
}

interface SchedulingState {
  scheduled?: {
    pending?: ScheduledTask[]
    recently_fired?: ScheduledTask[]
    cancelled_count?: number
    total?: number
  }
  recurring?: {
    active?: RecurringTask[]
    cancelled_count?: number
    total?: number
  }
  wakeups?: {
    pending?: Wakeup[]
    fired?: Wakeup[]
    consumed?: Wakeup[]
  }
}

type Tab = 'scheduled' | 'recurring' | 'wakeups'

export function SchedulingView({ apiBaseUrl }: { apiBaseUrl: string }) {
  const { data, loading, error, refresh } = useMcEndpoint<SchedulingState>(
    apiBaseUrl,
    '/api/scheduling/state',
    8000,
  )
  const [tab, setTab] = useState<Tab>('scheduled')

  const counts = {
    scheduled: data?.scheduled?.pending?.length ?? 0,
    recurring: data?.recurring?.active?.length ?? 0,
    wakeups:
      (data?.wakeups?.pending?.length ?? 0) + (data?.wakeups?.fired?.length ?? 0),
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <header className="flex flex-shrink-0 items-center justify-between border-b border-line bg-bg1 px-4 py-2">
        <div className="flex items-center gap-3">
          <h2 className="text-sm font-semibold">Planlægning</h2>
          <span className="font-mono text-[10px] text-fg3">live · 8s polling</span>
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

        {/* Tabs */}
        <div className="mb-5 flex gap-2">
          <TabButton
            Icon={Clock}
            label="Scheduled"
            count={counts.scheduled}
            active={tab === 'scheduled'}
            onClick={() => setTab('scheduled')}
          />
          <TabButton
            Icon={Repeat}
            label="Recurring"
            count={counts.recurring}
            active={tab === 'recurring'}
            onClick={() => setTab('recurring')}
          />
          <TabButton
            Icon={Bell}
            label="Self-wakeups"
            count={counts.wakeups}
            active={tab === 'wakeups'}
            onClick={() => setTab('wakeups')}
          />
        </div>

        {loading && !data && (
          <div className="text-xs text-fg3">loading…</div>
        )}

        {tab === 'scheduled' && data?.scheduled && (
          <ScheduledPanel scheduled={data.scheduled} />
        )}
        {tab === 'recurring' && data?.recurring && (
          <RecurringPanel recurring={data.recurring} />
        )}
        {tab === 'wakeups' && data?.wakeups && (
          <WakeupsPanel wakeups={data.wakeups} />
        )}
      </div>
    </div>
  )
}

function TabButton({
  Icon,
  label,
  count,
  active,
  onClick,
}: {
  Icon: typeof Clock
  label: string
  count: number
  active: boolean
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className={[
        'flex items-center gap-2 rounded-md border px-3 py-2 text-xs transition-colors',
        active
          ? 'border-accent/40 bg-accent/10 text-accent'
          : 'border-line2 bg-bg2 text-fg2 hover:border-line2 hover:text-fg',
      ].join(' ')}
    >
      <Icon size={13} />
      <span className="font-medium">{label}</span>
      {count > 0 && (
        <span
          className={[
            'rounded-full px-1.5 py-0.5 font-mono text-[9px]',
            active ? 'bg-accent/20 text-accent' : 'bg-bg0 text-fg3',
          ].join(' ')}
        >
          {count}
        </span>
      )}
    </button>
  )
}

function ScheduledPanel({ scheduled }: { scheduled: NonNullable<SchedulingState['scheduled']> }) {
  const pending = scheduled.pending ?? []
  const fired = scheduled.recently_fired ?? []
  return (
    <div className="space-y-5">
      <Section title={`Pending · ${pending.length}`} Icon={Clock}>
        {pending.length === 0 ? (
          <Empty text="Ingen planlagte tasks venter." />
        ) : (
          pending.map((t, i) => (
            <ItemRow
              key={t.task_id || i}
              title={t.focus || '(no focus)'}
              subtitle={t.run_at ? `fyrer ${formatTime(t.run_at)}` : ''}
              status="pending"
            />
          ))
        )}
      </Section>
      <Section title={`Recently fired · ${fired.length}`} Icon={CheckCircle2}>
        {fired.length === 0 ? (
          <Empty text="Ingen recently fired." />
        ) : (
          fired.map((t, i) => (
            <ItemRow
              key={t.task_id || i}
              title={t.focus || '(no focus)'}
              subtitle={t.fired_at ? `fyret ${formatTime(t.fired_at)}` : ''}
              status="done"
            />
          ))
        )}
      </Section>
    </div>
  )
}

function RecurringPanel({ recurring }: { recurring: NonNullable<SchedulingState['recurring']> }) {
  const active = recurring.active ?? []
  return (
    <Section title={`Active · ${active.length}`} Icon={Repeat}>
      {active.length === 0 ? (
        <Empty text="Ingen recurring tasks aktive." />
      ) : (
        active.map((t, i) => (
          <ItemRow
            key={t.task_id || i}
            title={t.focus || '(no focus)'}
            subtitle={[
              t.interval_minutes ? `every ${t.interval_minutes}m` : null,
              t.next_fire_at ? `next: ${formatTime(t.next_fire_at)}` : null,
              typeof t.fire_count === 'number' ? `${t.fire_count} fires` : null,
            ]
              .filter(Boolean)
              .join(' · ')}
            status="recurring"
          />
        ))
      )}
    </Section>
  )
}

function WakeupsPanel({ wakeups }: { wakeups: NonNullable<SchedulingState['wakeups']> }) {
  const pending = wakeups.pending ?? []
  const fired = wakeups.fired ?? []
  const consumed = wakeups.consumed ?? []
  return (
    <div className="space-y-5">
      <Section title={`Pending · ${pending.length}`} Icon={Bell}>
        {pending.length === 0 ? (
          <Empty text="Ingen self-wakeups planlagt." />
        ) : (
          pending.map((w, i) => (
            <ItemRow
              key={w.wakeup_id || i}
              title={w.prompt || '(no prompt)'}
              subtitle={[
                w.reason ? `reason: ${w.reason}` : null,
                w.fire_at ? `fyrer ${formatTime(w.fire_at)}` : null,
              ]
                .filter(Boolean)
                .join(' · ')}
              status="pending"
            />
          ))
        )}
      </Section>
      <Section title={`Fired (unconsumed) · ${fired.length}`} Icon={AlertCircle}>
        {fired.length === 0 ? (
          <Empty text="Ingen fired wakeups venter handling." />
        ) : (
          fired.map((w, i) => (
            <ItemRow
              key={w.wakeup_id || i}
              title={w.prompt || '(no prompt)'}
              subtitle={w.fired_at ? `fyret ${formatTime(w.fired_at)}` : ''}
              status="fired"
            />
          ))
        )}
      </Section>
      <Section title={`Recently consumed · ${consumed.length}`} Icon={CheckCircle2}>
        {consumed.length === 0 ? (
          <Empty text="Intet recently consumed." />
        ) : (
          consumed.map((w, i) => (
            <ItemRow
              key={w.wakeup_id || i}
              title={w.prompt || '(no prompt)'}
              subtitle={w.fired_at ? `fyret ${formatTime(w.fired_at)}` : ''}
              status="done"
            />
          ))
        )}
      </Section>
    </div>
  )
}

function Section({
  title,
  Icon,
  children,
}: {
  title: string
  Icon: typeof Clock
  children: React.ReactNode
}) {
  return (
    <div>
      <div className="mb-2 flex items-center gap-2">
        <Icon size={12} className="text-fg3" />
        <span className="text-[10px] font-semibold uppercase tracking-wider text-fg3">
          {title}
        </span>
      </div>
      <div className="space-y-1.5">{children}</div>
    </div>
  )
}

function ItemRow({
  title,
  subtitle,
  status,
}: {
  title: string
  subtitle?: string
  status: 'pending' | 'fired' | 'done' | 'recurring'
}) {
  const dotColor = {
    pending: '#d4963a',
    fired: '#f85149',
    done: '#3fb950',
    recurring: '#58a6ff',
  }[status]
  return (
    <div className="flex items-start gap-3 rounded-md border border-line/60 bg-bg1/50 px-3 py-2 transition-colors hover:border-line2">
      <span
        className="mt-1.5 h-1.5 w-1.5 flex-shrink-0 rounded-full"
        style={{ background: dotColor, boxShadow: `0 0 4px ${dotColor}80` }}
      />
      <div className="min-w-0 flex-1">
        <div className="break-words text-xs text-fg">{title}</div>
        {subtitle && (
          <div className="mt-0.5 truncate font-mono text-[10px] text-fg3">
            {subtitle}
          </div>
        )}
      </div>
      <Calendar size={10} className="mt-1 flex-shrink-0 text-fg3 opacity-50" />
    </div>
  )
}

function Empty({ text }: { text: string }) {
  return (
    <div className="rounded-md border border-dashed border-line/50 px-3 py-3 text-center text-[11px] text-fg3">
      {text}
    </div>
  )
}

function formatTime(iso: string): string {
  try {
    const d = new Date(iso)
    if (isNaN(d.getTime())) return iso
    const now = Date.now()
    const delta = d.getTime() - now
    const absMin = Math.abs(Math.floor(delta / 60000))
    if (Math.abs(delta) < 60_000) return delta > 0 ? 'om lidt' : 'lige nu'
    if (absMin < 60) return delta > 0 ? `om ${absMin}m` : `${absMin}m siden`
    const absHr = Math.abs(Math.floor(delta / 3600_000))
    if (absHr < 24) return delta > 0 ? `om ${absHr}t` : `${absHr}t siden`
    const absDay = Math.abs(Math.floor(delta / 86_400_000))
    return delta > 0 ? `om ${absDay}d` : `${absDay}d siden`
  } catch {
    return iso
  }
}
