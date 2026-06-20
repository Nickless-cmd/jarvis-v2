import { useEffect, useState } from 'react'
import { useSettings } from '../hooks/useSettings'
import { PluginsPanel } from '../components/settings/PluginsPanel'
import { LocationSection } from '../components/settings/LocationSection'
import { TotpSetup } from '../components/settings/TotpSetup'
import { DataPrivacyPanel } from '../components/DataPrivacyPanel'
import { QuotaPanel } from '../components/QuotaPanel'
import { AboutPanel } from '../components/AboutPanel'
import { KeyboardHelpPanel } from '../components/KeyboardHelpPanel'

/** Indstillinger — redigerbar: server, token, default-model + thinking.
 *  Server/token persisteres via Electron-bridge; gemmes ved "Gem". */
export function SettingsView() {
  const { settings, auth, update } = useSettings()
  const [apiBaseUrl, setApiBaseUrl] = useState('')
  const [authToken, setAuthToken] = useState('')
  const [defaultModel, setDefaultModel] = useState('')
  const [defaultThinking, setDefaultThinking] = useState<'think' | 'fast'>('think')
  const [saved, setSaved] = useState(false)

  // Synk lokale felter når settings loader/ændrer sig.
  useEffect(() => {
    if (!settings) return
    setApiBaseUrl(settings.apiBaseUrl)
    setAuthToken(settings.authToken ?? '')
    setDefaultModel(settings.defaultModel)
    setDefaultThinking(settings.defaultThinking)
  }, [settings])

  const dirty =
    !!settings &&
    (apiBaseUrl !== settings.apiBaseUrl ||
      (authToken || null) !== settings.authToken ||
      defaultModel !== settings.defaultModel ||
      defaultThinking !== settings.defaultThinking)

  const save = async () => {
    await update({
      apiBaseUrl: apiBaseUrl.trim(),
      authToken: authToken.trim() || null,
      defaultModel: defaultModel.trim() || 'deepseek-v4-flash',
      defaultThinking,
    })
    setSaved(true)
    setTimeout(() => setSaved(false), 1800)
  }

  return (
    <div className="view-placeholder settings-view">
      <h2>Indstillinger</h2>
      <div className="settings-form">
        <label>
          <span>Server (API base URL)</span>
          <input type="text" value={apiBaseUrl} placeholder="https://api.srvlab.dk"
            onChange={(e) => setApiBaseUrl(e.target.value)} />
        </label>
        <label>
          <span>Token</span>
          <input type="password" value={authToken} placeholder="bearer-token"
            onChange={(e) => setAuthToken(e.target.value)} />
        </label>
        <label>
          <span>Standardmodel</span>
          <input type="text" value={defaultModel} placeholder="deepseek-v4-flash"
            onChange={(e) => setDefaultModel(e.target.value)} />
        </label>
        <label>
          <span>Tænkning</span>
          <select value={defaultThinking} onChange={(e) => setDefaultThinking(e.target.value as 'think' | 'fast')}>
            <option value="think">think (afbalanceret)</option>
            <option value="fast">fast (intuitivt)</option>
          </select>
        </label>

        <div className="settings-meta">
          Logget ind som <strong>{auth?.display_name ?? '–'}</strong> ({auth?.role ?? '–'})
        </div>

        <div className="settings-actions">
          <button type="button" className="settings-save" disabled={!dirty} onClick={() => void save()}>
            Gem
          </button>
          {saved && <span className="settings-saved">Gemt ✓</span>}
        </div>
      </div>

      {auth?.role === 'owner' && (
        <TotpSetup
          config={settings ? { apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken } : undefined}
        />
      )}
      {auth?.role === 'owner' && (
        <PluginsPanel
          config={settings ? { apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken } : undefined}
        />
      )}

      <QuotaPanel
        config={settings ? { apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken } : undefined}
      />

      <DataPrivacyPanel
        config={settings ? { apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken } : undefined}
      />

      <LocationSection />

      <KeyboardHelpPanel />

      <AboutPanel apiBaseUrl={settings?.apiBaseUrl} role={auth?.role} model={defaultModel} />
    </div>
  )
}
