import { useEffect, useMemo, useState } from "react";

const API_BASE = "http://127.0.0.1:8010";

export default function App() {
  const [overview, setOverview] = useState(null);
  const [events, setEvents] = useState([]);

  useEffect(() => {
    fetch(`${API_BASE}/mc/overview`)
      .then((r) => r.json())
      .then(setOverview)
      .catch(() => null);

    fetch(`${API_BASE}/mc/events?limit=20`)
      .then((r) => r.json())
      .then((data) => setEvents(data.items || []))
      .catch(() => null);

    const ws = new WebSocket("ws://127.0.0.1:8010/ws");
    ws.onmessage = (msg) => {
      const item = JSON.parse(msg.data);
      setEvents((prev) => [item, ...prev].slice(0, 50));
    };
    return () => ws.close();
  }, []);

  const header = useMemo(() => {
    if (!overview) return "Loading Jarvis V2…";
    return `Events: ${overview.events} • Cost rows: ${overview.cost_rows} • Total: $${overview.total_cost_usd.toFixed(4)}`;
  }, [overview]);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <h1>Jarvis V2</h1>
        <p>Mission Control</p>
      </aside>
      <main className="content">
        <section className="panel">
          <h2>Overview</h2>
          <p>{header}</p>
        </section>
        <section className="panel">
          <h2>Live Events</h2>
          <ul className="event-list">
            {events.map((item) => (
              <li key={item.id}>
                <strong>{item.kind}</strong>
                <div>{item.created_at}</div>
              </li>
            ))}
          </ul>
        </section>
      </main>
    </div>
  );
}
