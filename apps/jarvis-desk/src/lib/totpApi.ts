import { apiFetch, type ApiConfig } from './api'

export interface TotpStatus {
  configured: boolean
  account: string | null
}

export interface TotpSetupResult {
  secret: string
  provisioning_uri: string
  account: string
}

export async function getTotpStatus(config: ApiConfig): Promise<TotpStatus> {
  return apiFetch<TotpStatus>(config, '/auth/totp/status')
}

export async function setupTotp(config: ApiConfig): Promise<TotpSetupResult> {
  return apiFetch<TotpSetupResult>(config, '/auth/totp/setup', { method: 'POST' })
}

export async function revokeTotp(config: ApiConfig): Promise<void> {
  await apiFetch(config, '/auth/totp/revoke', { method: 'POST' })
}
