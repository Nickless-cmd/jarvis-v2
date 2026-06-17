import * as SecureStore from 'expo-secure-store'
import { DEFAULT_API_BASE_URL, type ApiConfig } from './types'

const KEY = 'jarvis.mobile.auth'

function normalizeApiBaseUrl(value: string): string {
  const trimmed = value.trim() || DEFAULT_API_BASE_URL
  return trimmed.endsWith('/') ? trimmed : `${trimmed}/`
}

export async function loadAuthConfig(): Promise<ApiConfig | null> {
  const raw = await SecureStore.getItemAsync(KEY)
  if (!raw) return null

  const parsed = JSON.parse(raw) as Partial<ApiConfig>
  if (!parsed.authToken || !parsed.apiBaseUrl) return null

  return {
    apiBaseUrl: normalizeApiBaseUrl(parsed.apiBaseUrl),
    authToken: parsed.authToken
  }
}

export async function saveAuthConfig(config: ApiConfig): Promise<void> {
  const normalized: ApiConfig = {
    apiBaseUrl: normalizeApiBaseUrl(config.apiBaseUrl),
    authToken: config.authToken.trim()
  }

  if (!normalized.authToken) {
    throw new Error('authToken required')
  }

  await SecureStore.setItemAsync(KEY, JSON.stringify(normalized))
}

export async function clearAuthConfig(): Promise<void> {
  await SecureStore.deleteItemAsync(KEY)
}
