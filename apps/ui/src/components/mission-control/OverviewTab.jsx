import { ChevronRight } from 'lucide-react'
import { s, T, mono } from '../../shared/theme/tokens'
import { Card, SectionTitle, ListRow, EmptyState, KeyValGrid, KeyValCell } from './shared'
import { sectionTitleWithMeta } from './meta'

export function OverviewTab({ data, onJump, onOpenEvent }) {
  return (
    <div style={s({ display: 'flex', flexDirection: 'column', gap: 16 })}>

      {/* Summary metric cards */}
      <div style={s({ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0, 1fr))', gap: 10 })}>
        {(data?.cards || []).map((card) => (
          <button
            key={card.id}
            onClick={() => onJump(card.targetTab, card.targetSection)}
            title={sectionTitleWithMeta({ source: card.source, fetchedAt: data?.fetchedAt, mode: 'summary card' })}
            style={s({
              padding: '12px 14px',
              background: T.bgRaised,
              border: `1px solid ${T.border0}`,
              borderRadius: 10,
              textAlign: 'left',
              cursor: 'pointer',
              color: T.text1,
              transition: 'border-color .14s ease',
            })}
            onMouseEnter={(e) => { e.currentTarget.style.borderColor = `${T.accent}30` }}
            onMouseLeave={(e) => { e.currentTarget.style.borderColor = T.border0 }}
          >
            <span style={s({ ...mono, fontSize: 9, color: T.text3, letterSpacing: '0.1em', textTransform: 'uppercase' })}>{card.label}</span>
            <div style={s({ fontSize: 24, fontWeight: 400, marginTop: 4, letterSpacing: '-0.02em' })}>{card.value}</div>
            <div style={s({ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 6, color: T.text3, fontSize: 10 })}>
              <small>{card.targetTab}</small>
              <ChevronRight size={11} />
            </div>
          </button>
        ))}
      </div>

      {/* Two-column section grid */}
      <div style={s({ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 12 })}>

        {/* Current Activity */}
        <Card>
          <div style={s({ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 })}>
            <div>
              <SectionTitle>Current Activity</SectionTitle>
              <div style={s({ fontSize: 10, color: T.text3, marginTop: -8 })}>Snapshot and jump-off summary.</div>
            </div>
          </div>
          {data?.activeRun ? (
            <ListRow onClick={() => onJump('operations', 'runs')}>
              <div style={s({ minWidth: 0 })}>
                <div style={s({ fontSize: 12, fontWeight: 500, marginBottom: 3 })}>{data.activeRun.provider} / {data.activeRun.model}</div>
                <div style={s({ fontSize: 10, color: T.text2 })}>{data.activeRun.status} · {data.activeRun.lane}</div>
              </div>
              <div style={s({ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 })}>
                <small style={s({ ...mono, fontSize: 9, color: T.text3 })}>Open runs</small>
                <ChevronRight size={12} color={T.text3} />
              </div>
            </ListRow>
          ) : (
            <EmptyState title="No active run">Execution is idle right now.</EmptyState>
          )}
        </Card>

        {/* Queue & Cost */}
        <Card>
          <div style={s({ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 })}>
            <div>
              <SectionTitle>Queue & Cost</SectionTitle>
              <div style={s({ fontSize: 10, color: T.text3, marginTop: -8 })}>Summary only; details live elsewhere.</div>
            </div>
          </div>
          <KeyValGrid>
            <KeyValCell label="Pending approvals" value={data?.summaries?.pendingApprovals ?? 0} color={data?.summaries?.pendingApprovals > 0 ? T.amber : undefined} />
            <KeyValCell label="Sessions" value={data?.summaries?.sessionCount ?? 0} />
            <KeyValCell label="Failures" value={data?.summaries?.failureCount ?? 0} color={data?.summaries?.failureCount > 0 ? T.red : undefined} />
            <KeyValCell label="Total cost" value={`$${Number(data?.summaries?.totalCostUsd || 0).toFixed(2)}`} />
          </KeyValGrid>
        </Card>
      </div>

      {/* Recent Important Events */}
      <Card>
        <div style={s({ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 })}>
          <div>
            <SectionTitle>Recent Important Events</SectionTitle>
            <div style={s({ fontSize: 10, color: T.text3, marginTop: -8 })}>Canonical event feed lives in Observability.</div>
          </div>
        </div>
        <div style={s({ display: 'flex', flexDirection: 'column', gap: 6 })}>
          {(data?.importantEvents || []).map((event) => (
            <ListRow key={`${event.id}-${event.kind}`} onClick={() => onOpenEvent(event)}>
              <div style={s({ minWidth: 0 })}>
                <div style={s({ fontSize: 12, fontWeight: 500, marginBottom: 3 })}>{event.kind}</div>
                <div style={s({ fontSize: 10, color: T.text2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' })}>{event.family} · {event.relativeTime}</div>
              </div>
              <div style={s({ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 })}>
                <small style={s({ ...mono, fontSize: 9, color: T.text3 })}>Inspect</small>
                <ChevronRight size={12} color={T.text3} />
              </div>
            </ListRow>
          ))}
          {(data?.importantEvents || []).length === 0 && (
            <EmptyState title="No recent events">Waiting for activity.</EmptyState>
          )}
        </div>
      </Card>
    </div>
  )
}
