import { MainAgentPanel } from '../components/shared/MainAgentPanel'
import { SecondaryPanels } from '../components/shared/SecondaryPanels'

export function MissionControlPage({ selection, missionControl, onSelectionChange }) {
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
        <MainAgentPanel selection={selection} onSave={onSelectionChange} />
        <SecondaryPanels missionControl={missionControl} selection={selection} />

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

        <article className="support-card">
          <h3>Local lane</h3>
          <p>{missionControl.lanes.local.model || 'unconfigured'} / {missionControl.lanes.local.status}</p>
          <p className="muted">{missionControl.lanes.local.baseUrl || 'http://127.0.0.1:11434'}</p>
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
