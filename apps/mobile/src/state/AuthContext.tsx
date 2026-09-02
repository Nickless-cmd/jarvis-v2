import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { clearAuthConfig, loadAuthConfig, normalizeApiBaseUrl, saveAuthConfig } from '../lib/authStore'
import { DEFAULT_API_BASE_URL, type ApiConfig } from '../lib/types'

interface AuthContextValue {
  config: ApiConfig | null
  loading: boolean
  signInWithToken: (apiBaseUrl: string, authToken: string) => Promise<void>
  signOut: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

async function validateAuthToken(config: ApiConfig): Promise<void> {
  let response: Response

  try {
    response = await fetch(`${config.apiBaseUrl}api/whoami`, {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${config.authToken}`
      }
    })
  } catch {
    throw new Error('Kunne ikke kontakte Jarvis API for at validere token')
  }

  if (!response.ok) {
    throw new Error('Token blev afvist af Jarvis API')
  }
}

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
        const next = {
          apiBaseUrl: normalizeApiBaseUrl(apiBaseUrl || DEFAULT_API_BASE_URL),
          authToken: authToken.trim()
        }

        await validateAuthToken(next)
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
