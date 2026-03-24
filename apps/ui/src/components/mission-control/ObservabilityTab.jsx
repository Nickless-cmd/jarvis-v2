function summarizeFailures(data) {
  const failed = data?.failures?.failedRuns || []
  return {
    count: failed.length,
    latest: failed[0] || null,
  }
}

export function ObservabilityTab({ data, onOpenEvent, onOpenRun }) {
  const failure = summarizeFailures(data)
  const costSummary = data?.costs?.summary || {}
  const healthItems = [
    ['Visible', data?.providerHealth?.visible],
    ['Cheap', data?.providerHealth?.cheap],
    ['Coding', data?.providerHealth?.coding],
    ['Local', data?.providerHealth?.local],
  ]

  return (
    <div className="mc-tab-page">
      <section className="mc-summary-grid">
        <article className="mc-stat tone-blue" id="cost-usage" title="Source: /mc/costs">
          <span>Total cost</span>
          <strong>${Number(costSummary.total_cost_usd || 0).toFixed(2)}</strong>
        </article>
        <article className={`mc-stat ${failure.count > 0 ? 'tone-amber' : 'tone-green'}`} id="failure-summary" title="Source: /mc/runs + /mc/events">
          <span>Failures</span>
          <strong>{failure.count}</strong>
        </article>
        <article className="mc-stat tone-accent" id="provider-health" title="Source: /mc/runtime">
          <span>Visible Provider</span>
          <strong>{data?.providerHealth?.visible?.provider_status || 'unknown'}</strong>
        </article>
        <article className="mc-stat tone-blue" title="Source: /mc/events">
          <span>Recent events</span>
          <strong>{(data?.events || []).length}</strong>
        </article>
      </section>

      <section className="mc-section-grid">
        <article className="support-card" id="failure-summary-panel">
          <div className="panel-header">
            <div>
              <h3>Failure & Error Summary</h3>
              <p className="muted">Recent failed or cancelled runs.</p>
            </div>
          </div>
          <div className="mc-list">
            {(data?.failures?.failedRuns || []).slice(0, 8).map((run) => (
              <button className="mc-list-row" key={run.runId} onClick={() => onOpenRun(run)}>
                <div>
                  <strong>{run.provider} / {run.model}</strong>
                  <span>{run.status} · {run.error || run.textPreview || 'No error detail'}</span>
                </div>
                <small>{run.finishedAt || run.startedAt || 'unknown'}</small>
              </button>
            ))}
          </div>
        </article>

        <article className="support-card" id="provider-health-panel">
          <div className="panel-header">
            <div>
              <h3>Provider-Lane Health</h3>
              <p className="muted">Canonical home for provider and lane status evidence.</p>
            </div>
          </div>
          <div className="compact-grid">
            {healthItems.map(([label, item]) => (
              <div className="compact-metric" key={label}>
                <span>{label}</span>
                <strong>{item?.status || item?.provider_status || 'unknown'}</strong>
                <p className="muted">{item?.auth_status || item?.provider_status || 'unknown'}</p>
              </div>
            ))}
          </div>
        </article>
      </section>

      <section className="mc-section-grid">
        <article className="support-card" id="event-timeline">
          <div className="panel-header">
            <div>
              <h3>Event Timeline</h3>
              <p className="muted">Canonical event feed for Mission Control.</p>
            </div>
          </div>
          <div className="mc-list dense">
            {(data?.events || []).map((event) => (
              <button className="mc-list-row" key={`${event.id}-${event.kind}`} onClick={() => onOpenEvent(event)}>
                <div>
                  <strong>{event.kind}</strong>
                  <span>{event.family} · {event.relativeTime}</span>
                </div>
                <small>Inspect</small>
              </button>
            ))}
          </div>
        </article>

        <article className="support-card" id="run-evidence">
          <div className="panel-header">
            <div>
              <h3>Run Evidence</h3>
              <p className="muted">Recent run and work evidence surfaces.</p>
            </div>
          </div>
          <div className="mc-list">
            {(data?.runEvidence?.recentWorkUnits || []).map((item) => (
              <div className="mc-list-row static" key={item.work_id}>
                <div>
                  <strong>{item.provider} / {item.model}</strong>
                  <span>{item.status} · {item.user_message_preview || 'No preview'}</span>
                </div>
                <small>{item.finished_at || item.started_at || 'unknown'}</small>
              </div>
            ))}
          </div>
        </article>
      </section>
    </div>
  )
}
