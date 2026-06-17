/** Viser en typed fejl-besked (dansk) med valgfri "Prøv igen" + luk-knap. */
export function ErrorBanner({
  message,
  onDismiss,
  onRetry,
}: {
  message: string
  onDismiss: () => void
  onRetry?: () => void
}) {
  return (
    <div className="banner banner-error">
      <span>{message}</span>
      <div className="banner-actions">
        {onRetry && (
          <button type="button" className="banner-retry" onClick={onRetry}>Prøv igen</button>
        )}
        <button type="button" aria-label="luk" onClick={onDismiss}>×</button>
      </div>
    </div>
  )
}
