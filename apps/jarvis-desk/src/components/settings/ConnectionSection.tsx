import { useEffect, useState } from 'react'
import { useSettings } from '../../hooks/useSettings'

/** Forbindelse + standardmodel — server/token/model/tænkning. Udskilt fra den gamle
 *  SettingsView (konsolidering: ÉN settings-flade i cowork, ingen dobbelt-truth). */
export function ConnectionSection() {
  const { settings, auth, update } = useSettings()
  const [apiBaseUrl, setApiBaseUrl] = useState('')
  const [authToken, setAuthToken] = useState('')
  const [defaultModel, setDefaultModel] = useState('')
  const [defaultThinking, setDefaultThinking] = useState<'think' | 'fast'>('think')
  const [saved, setSaved] = useState(false)

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
    <div className="settings-section">
      <h3>Forbindelse &amp; model</h3>
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
          {/* Fri tekst med genveje (6/9-2026): vision-varianten fandtes, men
              intet fortalte at den var der — man skulle vide navnet i forvejen.
              Feltet er stadig frit, for pooler skifter hurtigere end appen. */}
          <input type="text" value={defaultModel} placeholder="deepseek-v4-flash"
            list="model-forslag"
            onChange={(e) => setDefaultModel(e.target.value)} />
          <datalist id="model-forslag">
            <option value="deepseek-v4-flash">hurtig, uden syn (standard)</option>
            <option value="deepseek-v4-flash-vision-exp">samme model, MED syn — kan selv se billeder du sender</option>
            <option value="deepseek-v4-pro">dyrere, stærkere ræsonnement</option>
          </datalist>
          {defaultModel.includes('vision')
            ? <span className="settings-hint">Jarvis ser selv billeder du sender — ingen omvej over en anden model.</span>
            : <span className="settings-hint">Billeder du sender bliver beskrevet af en anden model. Vælg vision-varianten, hvis han skal se dem selv.</span>}
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
          <button type="button" className="settings-save" disabled={!dirty} onClick={() => void save()}>Gem</button>
          {saved && <span className="settings-saved">Gemt ✓</span>}
        </div>
      </div>
    </div>
  )
}
