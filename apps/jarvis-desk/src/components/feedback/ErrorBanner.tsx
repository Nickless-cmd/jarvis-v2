/** Viser en struktureret fejl-besked (unified fejl-system, central_error_envelope):
 *  severity-farvet, ærlig dansk besked + valgfrit fix-hint, "Prøv igen" (kun hvis
 *  retryable) og en luk-knap der FAKTISK virker. */
export function ErrorBanner({
  message,
  onDismiss,
  onRetry,
  severity = 'error',
  fixHint,
}: {
  message: string
  onDismiss: () => void
  onRetry?: () => void
  severity?: 'info' | 'warning' | 'error' | 'critical'
  fixHint?: string
}) {
  return (
    <div className={`banner banner-error banner-sev-${severity}`} role="alert">
      <div className="banner-body">
        <span className="banner-message">{message}</span>
        {fixHint && <span className="banner-hint">{fixHint}</span>}
      </div>
      <div className="banner-actions">
        {onRetry && (
          <button type="button" className="banner-retry" onClick={onRetry}>Prøv igen</button>
        )}
        <button type="button" className="banner-dismiss" aria-label="luk" onClick={onDismiss}>×</button>
      </div>
    </div>
  )
}
