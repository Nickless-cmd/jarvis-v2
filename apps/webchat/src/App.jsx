import ComposerShell from "./components/ComposerShell.jsx";
import StatusRail from "./components/StatusRail.jsx";

const transcript = [
  {
    role: "system",
    label: "Jarvis Presence",
    body: "Vedvarende identitet, vaerktoejer og Mission Control-observability samles her."
  },
  {
    role: "user",
    label: "Du",
    body: "Planlaeg dagens arbejde og hold Mission Control opdateret."
  },
  {
    role: "assistant",
    label: "Jarvis",
    body: "Chatstream, arbejdsaktivitet og artifacts kobles pa denne shell i de naeste faser."
  }
];

export default function App() {
  return (
    <div className="webchat-shell">
      <header className="topbar">
        <div>
          <span className="eyebrow">Primary Chat</span>
          <h1>Jarvis V2</h1>
        </div>
        <div className="topbar-meta">
          <span>Visible lane</span>
          <span>Mission Control sidecar</span>
        </div>
      </header>
      <main className="layout">
        <section className="chat-column">
          <section className="panel chat-panel">
            <div className="chat-panel-header">
              <div>
                <span className="eyebrow">Conversation</span>
                <h2>Primary Chat Shell</h2>
              </div>
              <span className="status-pill">Idle</span>
            </div>
            <div className="transcript">
              {transcript.map((item) => (
                <article key={item.label} className={`message ${item.role}`}>
                  <span className="message-label">{item.label}</span>
                  <p>{item.body}</p>
                </article>
              ))}
            </div>
          </section>
          <ComposerShell />
        </section>
        <section className="work-column">
          <section className="panel work-panel">
            <div className="chat-panel-header">
              <div>
                <span className="eyebrow">Work Area</span>
                <h2>Activity and Output</h2>
              </div>
              <span className="status-pill muted">Placeholder</span>
            </div>
            <div className="work-grid">
              <article className="work-card">
                <strong>Live arbejde</strong>
                <p>
                  Her lander senere trinvis aktivitet, tool-status og bounded
                  workflow-signaler.
                </p>
              </article>
              <article className="work-card">
                <strong>Artifacts</strong>
                <p>
                  Resultater, previews og filer faar deres egen flade, men ikke i
                  Phase 1.
                </p>
              </article>
            </div>
          </section>
          <StatusRail />
        </section>
      </main>
    </div>
  );
}
