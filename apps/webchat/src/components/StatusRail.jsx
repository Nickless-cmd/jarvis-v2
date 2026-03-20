const activityItems = [
  {
    title: "Aktivitet",
    body: "Tool- og tankeaktivitet vises her, mens Jarvis arbejder."
  },
  {
    title: "Arbejdsflade",
    body: "Artifacts, previews og resultater faar et separat arbejdsomraade senere."
  },
  {
    title: "Mission Control",
    body: "Observability og kontrol bliver ved siden af chatten, ikke blandet ind i den."
  }
];

export default function StatusRail() {
  return (
    <aside className="status-rail">
      <section className="panel rail-panel">
        <span className="eyebrow">Jarvis V2</span>
        <h2>Primary Front Door</h2>
        <p>
          Den synlige chatflade er her. Mission Control forbliver et separat
          kontrolplan.
        </p>
        <a className="mc-link" href="http://127.0.0.1:5173" target="_blank" rel="noreferrer">
          Aabn Mission Control
        </a>
      </section>
      <section className="panel rail-panel">
        <span className="eyebrow">Phase 1</span>
        <ul className="activity-list">
          {activityItems.map((item) => (
            <li key={item.title}>
              <strong>{item.title}</strong>
              <p>{item.body}</p>
            </li>
          ))}
        </ul>
      </section>
    </aside>
  );
}
