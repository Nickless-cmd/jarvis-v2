import type { StreamStatus } from '../../lib/streamReducer'

/** Forbindelsens ene statuskort. Automatisk genforbindelse vises som aktivitet;
 * manuel genoptagelse dukker foerst op, naar den automatiske vej har givet op. */
export function InterruptedBanner({
  status,
  onResume,
  onAbort,
}: {
  status: StreamStatus
  onResume: () => void
  onAbort: () => void
}) {
  if (status === 'reconnecting') {
    return (
      <div className="banner banner-connection banner-reconnecting" role="status" aria-live="polite">
        <div className="banner-body">
          <span className="banner-message">Forbindelsen røg — genforbinder…</span>
        </div>
        <div className="banner-actions">
          <button type="button" className="banner-dismiss" aria-label="afbryd" onClick={onAbort}>×</button>
        </div>
      </div>
    )
  }
  if (status !== 'interrupted') return null

  return (
    <div className="banner banner-connection banner-warn" role="status" aria-live="polite">
      <div className="banner-body">
        <span className="banner-message">Forbindelse afbrudt.</span>
        <span className="banner-hint">Automatisk genforbindelse lykkedes ikke.</span>
      </div>
      <div className="banner-actions">
        <button type="button" className="banner-retry" onClick={onResume}>Genoptag</button>
      </div>
    </div>
  )
}
