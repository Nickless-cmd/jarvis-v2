export function OverviewTab({ data, onJump, onOpenEvent }) {
  return (
    <div className="mc-tab-page">
      <section className="mc-summary-grid">
        {(data?.cards || []).map((card) => (
          <button
            className={`mc-stat tone-${card.tone} mc-clickable-card`}
            key={card.id}
            onClick={() => onJump(card.targetTab, card.targetSection)}
            title={`Source: ${card.source}`}
          >
            <span>{card.label}</span>
            <strong>{card.value}</strong>
          </button>
        ))}
      </section>

      <section className="mc-section-grid">
        <article className="support-card" id="overview-activity">
          <div className="panel-header">
            <div>
              <h3>Current Activity</h3>
              <p className="muted">Snapshot and jump-off summary.</p>
            </div>
          </div>
          {data?.activeRun ? (
            <div className="mc-list">
              <button className="mc-list-row" onClick={() => onJump('operations', 'runs')}>
                <div>
                  <strong>{data.activeRun.provider} / {data.activeRun.model}</strong>
                  <span>{data.activeRun.status} · {data.activeRun.lane}</span>
                </div>
                <small>Open runs</small>
              </button>
            </div>
          ) : (
            <p className="muted">No active run right now.</p>
          )}
        </article>

        <article className="support-card">
          <div className="panel-header">
            <div>
              <h3>Queue & Cost</h3>
              <p className="muted">Summary only; details live elsewhere.</p>
            </div>
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

      <section className="support-card" id="overview-events">
        <div className="panel-header">
          <div>
            <h3>Recent Important Events</h3>
            <p className="muted">Canonical event feed lives in Observability.</p>
          </div>
        </div>
        <div className="mc-list">
          {(data?.importantEvents || []).map((event) => (
            <button className="mc-list-row" key={`${event.id}-${event.kind}`} onClick={() => onOpenEvent(event)}>
              <div>
                <strong>{event.kind}</strong>
                <span>{event.family} · {event.relativeTime}</span>
              </div>
              <small>Inspect</small>
            </button>
          ))}
        </div>
      </section>
    </div>
  )
}
