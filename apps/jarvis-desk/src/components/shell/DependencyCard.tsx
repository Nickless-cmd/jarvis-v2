/** Dependency-doctor-kort: viser manglende værktøjer (git/gh/node/rg) og lader
 *  brugeren installere dem via app'en (per-OS, main-proces). Vises kun når noget
 *  mangler — ellers render intet (app'en virker "før git er installeret"). */
export function DependencyCard({ missing, onInstall, onDismiss, busy }: {
  missing: string[]
  onInstall: (tool: string) => void
  onDismiss: () => void
  busy: string
}) {
  if (!missing.length) return null
  return (
    <div className="dep-card" role="dialog" aria-label="Manglende værktøjer">
      <div className="dep-head">Jarvis mangler nogle værktøjer</div>
      <ul className="dep-list">
        {missing.map((t) => (
          <li key={t} className="dep-row">
            <span className="dep-tool">{t}</span>
            <button type="button" className="dep-btn" disabled={busy === t} onClick={() => onInstall(t)}>
              {busy === t ? 'Installerer…' : 'Installér'}
            </button>
          </li>
        ))}
      </ul>
      <button type="button" className="dep-dismiss" aria-label="Luk" onClick={onDismiss}>×</button>
    </div>
  )
}
