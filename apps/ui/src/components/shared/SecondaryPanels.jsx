export function SecondaryPanels({ missionControl }) {
  return (
    <div className="secondary-panels">
      <section className="support-card compact">
        <h3>Operator summary</h3>
        <ul className="event-list compact-list">
          {missionControl.events.slice(0, 3).map((event) => <li key={event}>{event}</li>)}
        </ul>
      </section>

      <details className="support-card disclosure">
        <summary>Runtime details</summary>
        <div className="disclosure-body">
          {missionControl.panels.map((panel) => (
            <article key={panel.title} className="disclosure-item">
              <strong>{panel.title}</strong>
              <p>{panel.body}</p>
            </article>
          ))}
        </div>
      </details>
    </div>
  )
}
