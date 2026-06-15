import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { App } from './App'
import { SettingsProvider } from './contexts/SettingsContext'
import { loadTheme, applyTheme } from './lib/themeStore'

// Anvend gemt tema før render — undgår flash af forkert tema (§4.11).
applyTheme(loadTheme())

const root = document.getElementById('root')
if (!root) throw new Error('Root element #root not found')

createRoot(root).render(
  <StrictMode>
    <SettingsProvider>
      <App />
    </SettingsProvider>
  </StrictMode>,
)
