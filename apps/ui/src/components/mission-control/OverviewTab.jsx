import { ChevronRight } from 'lucide-react'
import { sectionTitleWithMeta } from './meta'

export function OverviewTab({ data, onJump, onOpenEvent }) {
  return (
    <div className="mc-tab-page">
      <section className="mc-summary-grid">
        {(data?.cards || []).map((card) => (
          <button
            className={`mc-stat tone-${card.tone} mc-clickable-card`}
            key={card.id}
            onClick={() => onJump(card.targetTab, card.targetSection)}
            title={sectionTitleWithMeta({
              source: card.source,
              fetchedAt: data?.fetchedAt,
              mode: 'summary card',
            })}
          >
            <span>{card.label}</span>
            <strong>{card.value}</strong>
            <div className="mc-card-footer">
              <small>{card.targetTab}</small>
              <ChevronRight size={14} />
            </div>
          </button>
        ))}
      </section>

      <section className="mc-section-grid">
        <article className="support-card" id="overview-activity" title={sectionTitleWithMeta({
          source: '/mc/overview + /mc/runs',
          fetchedAt: data?.fetchedAt,
          mode: 'summary + jump-off',
        })}>
          <div className="panel-header">
            <div>
              <h3>Current Activity</h3>
              <p className="muted">Snapshot and jump-off summary.</p>
            </div>
            <span className="mc-section-hint">Summary</span>
          </div>
          {data?.activeRun ? (
            <div className="mc-list">
              <button className="mc-list-row" onClick={() => onJump('operations', 'runs')}>
                <div>
                  <strong>{data.activeRun.provider} / {data.activeRun.model}</strong>
                  <span>{data.activeRun.status} · {data.activeRun.lane}</span>
                </div>
                <div className="mc-row-meta">
                  <small>Open runs</small>
                  <ChevronRight size={14} />
                </div>
              </button>
            </div>
          ) : (
            <div className="mc-empty-state">
              <strong>No active run</strong>
              <p className="muted">Execution is idle right now. Open Operations for recent run history.</p>
            </div>
          )}
        </article>

        <article className="support-card" title={sectionTitleWithMeta({
          source: '/mc/approvals + /chat/sessions + /mc/overview',
          fetchedAt: data?.fetchedAt,
          mode: 'summary only',
        })}>
          <div className="panel-header">
            <div>
              <h3>Queue & Cost</h3>
              <p className="muted">Summary only; details live elsewhere.</p>
            </div>
            <span className="mc-section-hint">Summary</span>
          </div>
          <div className="compact-grid">
            <div className="compact-metric">
              <span>Pending approvals</span>
              <strong>{data?.summaries?.pendingApprovals ?? 0}</strong>
            </div>
            <div className="compact-metric">
              <span>Sessions</span>
              <strong>{data?.summaries?.sessionCount ?? 0}</strong>
            </div>
            <div className="compact-metric">
              <span>Failures</span>
              <strong>{data?.summaries?.failureCount ?? 0}</strong>
            </div>
            <div className="compact-metric">
              <span>Total cost</span>
              <strong>${Number(data?.summaries?.totalCostUsd || 0).toFixed(2)}</strong>
            </div>
          </div>
        </article>
      </section>

      <section className="support-card" id="overview-events" title={sectionTitleWithMeta({
        source: '/mc/events + /ws',
        fetchedAt: data?.fetchedAt,
        mode: 'event-assisted summary',
      })}>
        <div className="panel-header">
          <div>
            <h3>Recent Important Events</h3>
            <p className="muted">Canonical event feed lives in Observability.</p>
          </div>
          <span className="mc-section-hint">Jump to detail</span>
        </div>
        <div className="mc-list">
          {(data?.importantEvents || []).map((event) => (
            <button className="mc-list-row" key={`${event.id}-${event.kind}`} onClick={() => onOpenEvent(event)}>
              <div>
                <strong>{event.kind}</strong>
                <span>{event.family} · {event.relativeTime}</span>
              </div>
              <div className="mc-row-meta">
                <small>Inspect</small>
                <ChevronRight size={14} />
              </div>
            </button>
          ))}
        </div>
      </section>
    </div>
  )
}
