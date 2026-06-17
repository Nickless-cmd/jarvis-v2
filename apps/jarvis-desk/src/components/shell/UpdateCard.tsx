/** In-app app-opdaterings-kort (§22.5). Vises når en ny version er tilgængelig
 *  (phase='available' → "Opdatér") eller downloadet (phase='ready' → "Genstart
 *  & opdatér"). Brugeren beslutter; ingen tvungen opdatering. */
export function UpdateCard({ version, phase, onUpdate, onInstall, onDismiss }: {
  version: string
  phase: 'available' | 'ready'
  onUpdate: () => void
  onInstall: () => void
  onDismiss: () => void
}) {
  return (
    <div className="update-card" role="dialog" aria-label="App-opdatering">
      <span className="update-text">
        {phase === 'ready' ? `Version ${version} er klar` : `Ny version ${version} tilgængelig`}
      </span>
      {phase === 'ready'
        ? <button type="button" className="update-btn" onClick={onInstall}>Genstart &amp; opdatér</button>
        : <button type="button" className="update-btn" onClick={onUpdate}>Opdatér</button>}
      <button type="button" className="update-dismiss" aria-label="Luk" onClick={onDismiss}>×</button>
    </div>
  )
}
