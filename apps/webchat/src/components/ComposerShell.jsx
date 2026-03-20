export default function ComposerShell() {
  return (
    <section className="composer-shell panel">
      <div className="composer-meta">
        <span className="eyebrow">Composer</span>
        <span className="composer-state">Phase 1 shell</span>
      </div>
      <div className="composer-box">
        <p className="composer-placeholder">
          Skriv til Jarvis her. Streaming, uploads, stemme og approvals kommer
          senere.
        </p>
        <div className="composer-actions">
          <button type="button" disabled>
            Vedhaeft
          </button>
          <button type="button" disabled>
            Diktat
          </button>
          <button type="button" className="primary" disabled>
            Send
          </button>
        </div>
      </div>
    </section>
  );
}
