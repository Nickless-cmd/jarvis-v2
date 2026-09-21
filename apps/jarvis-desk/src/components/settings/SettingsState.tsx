import type { ResourceStatus } from '../../hooks/useSettingsResource'

export function SettingsState({ status, label, onRetry }: {
  status: ResourceStatus
  label: string
  onRetry: () => void
}) {
  if (status === 'ready') return null
  return (
    <div className={`settings-feedback ${status}`} role={status === 'error' ? 'alert' : 'status'}>
      <p>{status === 'missing' ? 'Opret forbindelse til Jarvis for at se dette indhold.'
        : status === 'loading' ? `Henter ${label}…` : `Kunne ikke hente ${label}.`}</p>
      {status === 'error' && <button type="button" onClick={onRetry}>Prøv igen</button>}
    </div>
  )
}

export function SettingsActionError({ message }: { message: string }) {
  return message ? <p className="settings-feedback error" role="alert">{message}</p> : null
}
