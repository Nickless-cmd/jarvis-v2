export function MissionControlPage({ selection, missionControl }) {
  return (
    <div className="mission-control-page">
      <section className="hero-card compact">
        <p className="eyebrow">Mission Control</p>
        <h1>Control room</h1>
        <p>Shared shell, same palette, heavier operator surface.</p>
      </section>

      <section className="mc-overview-grid">
        {missionControl.overview.map((item) => (
          <article className={`mc-stat tone-${item.tone}`} key={item.label}>
            <span>{item.label}</span>
            <strong>{item.value}</strong>
          </article>
        ))}
      </section>

      <section className="mc-panels-grid">
        {missionControl.panels.map((panel) => (
          <article className="support-card" key={panel.title}>
            <h3>{panel.title}</h3>
            <p>{panel.body}</p>
          </article>
        ))}

        <article className="support-card">
          <h3>Main agent target</h3>
          <p>{selection.currentProvider} / {selection.currentModel}</p>
          <p className="muted">Authority: {selection.selectionAuthority}</p>
        </article>
      </section>

      <section className="support-card">
        <h3>Recent events</h3>
        <ul className="event-list">
          {missionControl.events.map((event) => <li key={event}>{event}</li>)}
        </ul>
      </section>
    </div>
  )
}
