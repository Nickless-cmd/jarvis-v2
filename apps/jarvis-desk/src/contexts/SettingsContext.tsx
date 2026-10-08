import { createContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { fornyOmNoedvendigt } from '../lib/tokenRenewal'
import { whoami, type WhoAmI } from '../lib/api'
import { StreamError } from '../lib/streamClient'
import { clearBrowserConfig, readBrowserConfig, writeBrowserConfig } from '../lib/browserConfig'
import { onUnauthorized } from '../lib/authEvents'

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
  authStatus?: 'checking' | 'ready' | 'offline' | 'idle'
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
  const browser = !initialConfig && !deskBridge()
  const [authStatus, setAuthStatus] = useState<'checking' | 'ready' | 'offline' | 'idle'>(
    browser ? 'checking' : 'ready',
  )

  // Load fra Electron-config ved rigtig opstart (ingen initialConfig).
  useEffect(() => {
    if (initialConfig) return
    const w = deskBridge()
    if (!w) {
      setSettings({ ...DEFAULTS, ...readBrowserConfig() })
      return
    }
    w.config
      .get()
      .then((cfg) => setSettings({ ...DEFAULTS, ...cfg }))
      .catch(() => setSettings({ ...DEFAULTS, apiBaseUrl: '', authToken: null }))
  }, [initialConfig])

  const isConfigured = !!(settings?.apiBaseUrl && settings?.authToken)

  useEffect(() => {
    if (!browser) return
    return onUnauthorized(() => {
      clearBrowserConfig()
      setAuth(null)
      setAuthStatus('idle')
      setSettings((s) => s ? { ...s, authToken: null } : s)
    })
  }, [browser])

  // Cache-first whoami: ved offline-boot beholdes sidste-kendte rolle (ingen
  // overskrivning ved fejl).
  useEffect(() => {
    if (!isConfigured || !settings) return
    let alive = true
    if (browser) setAuthStatus('checking')
    whoami({ apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken })
      .then((identity) => {
        if (!alive) return
        setAuth(identity)
        if (browser) setAuthStatus('ready')
      })
      .catch((err: unknown) => {
        if (!alive || !browser) return
        if (err instanceof StreamError && err.statusCode === 401) {
          clearBrowserConfig()
          setSettings((s) => s ? { ...s, authToken: null } : s)
          setAuthStatus('idle')
        } else {
          setAuthStatus('offline')
        }
      })
    return () => { alive = false }
  }, [browser, isConfigured, settings?.apiBaseUrl, settings?.authToken])

  const update = async (partial: Partial<AppSettings>) => {
    const next = settings ? { ...settings, ...partial } : { ...DEFAULTS, ...readBrowserConfig(), ...partial }
    setSettings(next)
    if (browser) {
      writeBrowserConfig(next)
      setAuth(null)
      setAuthStatus(next.authToken ? 'checking' : 'idle')
    }
    const w = deskBridge()
    if (w && settings) {
      await w.config.set({
        apiBaseUrl: partial.apiBaseUrl ?? settings.apiBaseUrl,
        authToken: partial.authToken !== undefined ? partial.authToken : settings.authToken,
      })
    }
  }

  // Forny tokenet i god tid. Tokens har fast udløb, og indtil nu var eneste
  // kur at minte et nyt i hånden — det var dét der låste Mikkels telefon ude
  // (927 × 401 paa seks timer med grunden `token expired`).
  //
  // fornyOmNoedvendigt rører kun serveren når der er under en tredjedel af
  // levetiden tilbage, og returnerer den gamle config uændret hvis noget går
  // galt. Derfor er der ingen fejlsti at håndtere her.
  useEffect(() => {
    if (!settings?.authToken || !settings.apiBaseUrl) return
    void fornyOmNoedvendigt(
      { apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken },
      async (c) => { await update({ authToken: c.authToken }) },
    )
    // `update` udelades bevidst: den gendannes hver render og ville gøre
    // effekten til en løkke.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [settings?.apiBaseUrl, settings?.authToken])

  const value = useMemo<SettingsContextValue>(
    () => ({ settings, auth, isConfigured, authStatus: browser ? authStatus : undefined, update }),
    [settings, auth, isConfigured, authStatus, browser],
  )
  return <SettingsContext.Provider value={value}>{children}</SettingsContext.Provider>
}
