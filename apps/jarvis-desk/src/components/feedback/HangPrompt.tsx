import type { StreamStatus } from '../../lib/streamReducer'

/** R2: watchdog 90s uden event. Brugeren beslutter genoptag (ny tur) eller
 *  afbryd (server-cancel). */
export function HangPrompt({
  status,
  onResume,
  onAbort,
}: {
  status: StreamStatus
  onResume: () => void
  onAbort: () => void
}) {
  if (status !== 'hung') return null

  return (
    <div className="banner banner-connection banner-warn" role="status" aria-live="polite">
      <div className="banner-body">
        <span className="banner-message">Jarvis svarer ikke.</span>
      </div>
      <div className="banner-actions">
        <button type="button" className="banner-retry" onClick={onResume}>Genoptag</button>
        <button type="button" onClick={onAbort}>Afbryd</button>
      </div>
    </div>
  )
}
