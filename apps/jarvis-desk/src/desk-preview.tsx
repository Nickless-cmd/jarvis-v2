/** Local, read-only visual preview of the shared Desk renderer. Never built into dist-web. */
import { createRoot } from 'react-dom/client'
import { App } from './App'
import { SettingsContext, type SettingsContextValue } from './contexts/SettingsContext'

const preview: SettingsContextValue = {
  settings: {
    apiBaseUrl: `${location.origin}/preview-api/`,
    authToken: 'fixture', // noqa: literal-credential — dev-only preview
    theme: 'dark',
    defaultModel: 'Preview',
    defaultThinking: 'think',
    trustDefault: 'ask',
  },
  auth: { role: 'owner', display_name: 'Forhåndsvisning' } as SettingsContextValue['auth'],
  authStatus: 'ready',
  isConfigured: true,
  update: async () => {},
}

createRoot(document.getElementById('root')!).render(
  <SettingsContext.Provider value={preview}>
    <App />
    <div style={{ position: 'fixed', right: 12, bottom: 12, zIndex: 9999,
      padding: '8px 12px', borderRadius: 8, background: '#241f18', color: '#f4d49a',
      border: '1px solid #705b37', fontSize: 12 }}>
      Visuel forhåndsvisning · ingen live data
    </div>
  </SettingsContext.Provider>,
)
