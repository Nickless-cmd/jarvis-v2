import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { App } from './App'
import { SettingsProvider } from './contexts/SettingsContext'
import { ErrorBoundary } from './components/ErrorBoundary'
import { Vinduesknapper } from './components/shell/Vinduesknapper'
import { loadTheme, applyTheme } from './lib/themeStore'

// Anvend gemt tema før render — undgår flash af forkert tema (§4.11).
applyTheme(loadTheme())

// Globale fejl-fangere (ikke-React-throws + unhandled promise-rejections) —
// logges så en evt. crash-kilde uden for render kan aflæses.
window.addEventListener('error', (e) => {
  // eslint-disable-next-line no-console
  console.error('[jarvis-desk window.error]', e.message, e.error?.stack || '')
})
window.addEventListener('unhandledrejection', (e) => {
  // eslint-disable-next-line no-console
  console.error('[jarvis-desk unhandledrejection]', String(e.reason?.message || e.reason), e.reason?.stack || '')
})

const root = document.getElementById('root')
if (!root) throw new Error('Root element #root not found')

createRoot(root).render(
  <StrictMode>
    {/* Vinduesknapperne staar UDEN FOR App og uden for ErrorBoundary med
        vilje. Vinduet har ingen OS-ramme, saa de er dens eneste knapper —
        og App returnerer foer skallen i mindst tre tilfaelde: mens
        indstillinger hentes (null), paa setup-skaermen, og hvis
        ErrorBoundary fanger en fejl. I alle tre ville et vindue uden
        knapper vaere et vindue man ikke kan lukke. */}
    <Vinduesknapper />
    <ErrorBoundary>
      <SettingsProvider>
        <App />
      </SettingsProvider>
    </ErrorBoundary>
  </StrictMode>,
)
