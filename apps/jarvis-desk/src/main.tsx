import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { App } from './App'
import { SettingsProvider } from './contexts/SettingsContext'
import { ErrorBoundary } from './components/ErrorBoundary'
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
    <ErrorBoundary>
      <SettingsProvider>
        <App />
      </SettingsProvider>
    </ErrorBoundary>
  </StrictMode>,
)
