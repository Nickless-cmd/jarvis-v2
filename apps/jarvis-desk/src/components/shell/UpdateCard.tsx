/** In-app app-opdaterings-kort (§22.5). Vises når en ny version er tilgængelig
 *  (phase='available' → "Opdatér") eller downloadet (phase='ready' → "Genstart
 *  & opdatér"). Brugeren beslutter; ingen tvungen opdatering. */
export function UpdateCard({ version, phase, busy = false, error = '', onUpdate, onInstallNow, onInstall, onDismiss }: {
  version: string
  phase: 'available' | 'ready'
  busy?: boolean
  error?: string
  onUpdate: () => void
  onInstallNow: () => void
  onInstall: () => void
  onDismiss: () => void
}) {
  return (
    <div className="update-card" role="dialog" aria-label="App-opdatering">
      <span className="update-text">
        {phase === 'ready' ? `Version ${version} er klar` : `Ny version ${version} tilgængelig`}
      </span>
      <div className="update-actions">
        {phase === 'ready'
          ? <button type="button" className="update-btn" disabled={busy} onClick={onInstall}>Genstart &amp; installér</button>
          : <>
            <button type="button" className="update-btn secondary" disabled={busy} onClick={onUpdate}>Hent</button>
            <button type="button" className="update-btn" disabled={busy} onClick={onInstallNow}>{busy ? 'Henter…' : 'Installér nu'}</button>
          </>}
      </div>
      <button type="button" className="update-dismiss" aria-label="Luk opdatering" disabled={busy} onClick={onDismiss}>×</button>
      {error && <p className="update-error" role="alert">{error}</p>}
    </div>
  )
}
