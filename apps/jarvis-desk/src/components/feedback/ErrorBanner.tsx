/** Viser en typed fejl-besked (dansk) med luk-knap. */
export function ErrorBanner({ message, onDismiss }: { message: string; onDismiss: () => void }) {
  return (
    <div className="banner banner-error">
      <span>{message}</span>
      <button type="button" aria-label="luk" onClick={onDismiss}>×</button>
    </div>
  )
}
