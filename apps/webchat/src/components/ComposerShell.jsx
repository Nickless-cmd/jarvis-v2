export default function ComposerShell({
  draft,
  isRunning,
  onCancel,
  onChange,
  onSubmit
}) {
  return (
    <section className="composer-shell panel">
      <div className="composer-meta">
        <span className="eyebrow">Composer</span>
        <span className="composer-state">{isRunning ? "Visible run aktiv" : "Phase 1 shell"}</span>
      </div>
      <form className="composer-box" onSubmit={onSubmit}>
        <label className="composer-label" htmlFor="jarvis-draft">
          Skriv til Jarvis her. Visible chat kober direkte til SSE-streamen.
        </label>
        <textarea
          id="jarvis-draft"
          className="composer-input"
          value={draft}
          onChange={(event) => onChange(event.target.value)}
          placeholder="Skriv en besked til Jarvis..."
          rows={4}
          disabled={isRunning}
        />
        <div className="composer-actions">
          <button type="button" disabled>
            Vedhaeft
          </button>
          <button type="button" disabled>
            Diktat
          </button>
          <button type="button" onClick={onCancel} disabled={!isRunning}>
            Stop
          </button>
          <button type="submit" className="primary" disabled={isRunning || !draft.trim()}>
            {isRunning ? "Streamer..." : "Send"}
          </button>
        </div>
      </form>
    </section>
  );
}
