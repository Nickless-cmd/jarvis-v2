export function SecondaryPanels({ missionControl, selection }) {
  return (
    <div className="secondary-panels">
      <section className="support-card compact">
        <h3>Runtime summary</h3>
        <div className="compact-grid">
          <div className="compact-metric">
            <span>Main agent</span>
            <strong>{selection.currentProvider} / {selection.currentModel}</strong>
          </div>
          <div className="compact-metric">
            <span>Local lane</span>
            <strong>{missionControl.lanes.local.model || 'unconfigured'} · {missionControl.lanes.local.status}</strong>
          </div>
          <div className="compact-metric">
            <span>Coding lane</span>
            <strong>{missionControl.lanes.coding.status}</strong>
          </div>
          <div className="compact-metric">
            <span>Visible runtime</span>
            <strong>{missionControl.readiness.providerStatus}</strong>
          </div>
        </div>
      </section>

      <details className="support-card disclosure">
        <summary>Operator details</summary>
        <div className="disclosure-body">
          {missionControl.panels.map((panel) => (
            <article key={panel.title} className="disclosure-item">
              <strong>{panel.title}</strong>
              <p>{panel.body}</p>
            </article>
          ))}
          <article className="disclosure-item">
            <strong>Recent runtime notes</strong>
            <ul className="event-list compact-list">
              {missionControl.events.slice(0, 4).map((event) => <li key={event}>{event}</li>)}
            </ul>
          </article>
        </div>
      </details>
    </div>
  )
}
