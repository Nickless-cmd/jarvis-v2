import { createContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { whoami, type WhoAmI } from '../lib/api'

export interface AppSettings {
  apiBaseUrl: string
  authToken: string | null
  theme: 'dark'
  defaultModel: string
  defaultThinking: 'think' | 'fast'
  trustDefault: 'ask' | 'trust'
}

export interface SettingsContextValue {
  settings: AppSettings | null
  auth: WhoAmI | null
  isConfigured: boolean
  update: (partial: Partial<AppSettings>) => Promise<void>
}

const DEFAULTS: Omit<AppSettings, 'apiBaseUrl' | 'authToken'> = {
  theme: 'dark',
  defaultModel: 'deepseek-v4-flash',
  defaultThinking: 'think',
  trustDefault: 'ask',
}

interface DeskBridge {
  config: {
    get: () => Promise<{ apiBaseUrl: string; authToken: string | null }>
    set: (cfg: { apiBaseUrl: string; authToken: string | null }) => Promise<boolean>
  }
}

function deskBridge(): DeskBridge | undefined {
  return (window as unknown as { jarvisDesk?: DeskBridge }).jarvisDesk
}

export const SettingsContext = createContext<SettingsContextValue | null>(null)

export function SettingsProvider({
  children,
  initialConfig,
}: {
  children: ReactNode
  initialConfig?: { apiBaseUrl: string; authToken: string | null }
}) {
  const [settings, setSettings] = useState<AppSettings | null>(
    initialConfig ? { ...DEFAULTS, ...initialConfig } : null,
  )
  const [auth, setAuth] = useState<WhoAmI | null>(null)

  // Load fra Electron-config ved rigtig opstart (ingen initialConfig).
  useEffect(() => {
    if (initialConfig) return
    const w = deskBridge()
    if (!w) {
      setSettings({ ...DEFAULTS, apiBaseUrl: '', authToken: null })
      return
    }
    w.config
      .get()
      .then((cfg) => setSettings({ ...DEFAULTS, ...cfg }))
      .catch(() => setSettings({ ...DEFAULTS, apiBaseUrl: '', authToken: null }))
  }, [initialConfig])

  const isConfigured = !!(settings?.apiBaseUrl && settings?.authToken)

  // Cache-first whoami: ved offline-boot beholdes sidste-kendte rolle (ingen
  // overskrivning ved fejl).
  useEffect(() => {
    if (!isConfigured || !settings) return
    whoami({ apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken })
      .then(setAuth)
      .catch(() => {
        /* behold evt. cached auth */
      })
  }, [isConfigured, settings?.apiBaseUrl, settings?.authToken])

  const update = async (partial: Partial<AppSettings>) => {
    setSettings((s) => (s ? { ...s, ...partial } : { ...DEFAULTS, apiBaseUrl: '', authToken: null, ...partial }))
    const w = deskBridge()
    if (w && settings) {
      await w.config.set({
        apiBaseUrl: partial.apiBaseUrl ?? settings.apiBaseUrl,
        authToken: partial.authToken ?? settings.authToken,
      })
    }
  }

  const value = useMemo<SettingsContextValue>(
    () => ({ settings, auth, isConfigured, update }),
    [settings, auth, isConfigured],
  )
  return <SettingsContext.Provider value={value}>{children}</SettingsContext.Provider>
}
