import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { clearAuthConfig, loadAuthConfig, saveAuthConfig } from '../lib/authStore'
import { DEFAULT_API_BASE_URL, type ApiConfig } from '../lib/types'

interface AuthContextValue {
  config: ApiConfig | null
  loading: boolean
  signInWithToken: (apiBaseUrl: string, authToken: string) => Promise<void>
  signOut: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [config, setConfig] = useState<ApiConfig | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadAuthConfig()
      .then(setConfig)
      .finally(() => setLoading(false))
  }, [])

  const value = useMemo<AuthContextValue>(
    () => ({
      config,
      loading,
      signInWithToken: async (apiBaseUrl, authToken) => {
        const next = { apiBaseUrl: apiBaseUrl || DEFAULT_API_BASE_URL, authToken }
        await saveAuthConfig(next)
        setConfig(await loadAuthConfig())
      },
      signOut: async () => {
        await clearAuthConfig()
        setConfig(null)
      }
    }),
    [config, loading]
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) {
    throw new Error('useAuth must be used within AuthProvider')
  }

  return ctx
}
