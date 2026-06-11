import { useSettings } from '../hooks/useSettings'

/** Indstillinger: server, token, defaults. Token-mgmt-panel uddybes i egen spec. */
export function SettingsView() {
  const { settings, auth } = useSettings()
  return (
    <div className="view-placeholder settings-view">
      <h2>Indstillinger</h2>
      <dl>
        <dt>Server</dt><dd>{settings?.apiBaseUrl || '–'}</dd>
        <dt>Bruger</dt><dd>{auth?.display_name ?? '–'} ({auth?.role ?? '–'})</dd>
        <dt>Model</dt><dd>{settings?.defaultModel ?? '–'}</dd>
        <dt>Thinking</dt><dd>{settings?.defaultThinking ?? '–'}</dd>
      </dl>
    </div>
  )
}
