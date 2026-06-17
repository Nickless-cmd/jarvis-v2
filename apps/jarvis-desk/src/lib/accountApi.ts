import { apiFetch, type ApiConfig } from './api'

/** GDPR-dataeksport: hent brugerens eget data-bundt (JSON). */
export async function exportMyData(config: ApiConfig): Promise<unknown> {
  return apiFetch(config, '/api/account/export')
}

export interface QuotaItem {
  kind: string
  used: number
  limit: number | null
  remaining: number | null
  warn: boolean
}
export interface QuotaOverview { tier: string; items: QuotaItem[] }

/** Self-scope kvote-/forbrugs-overblik (tier + brug pr. type). */
export async function getQuota(config: ApiConfig): Promise<QuotaOverview> {
  return apiFetch<QuotaOverview>(config, '/api/account/quota')
}

/** Trigger en browser-download af et JSON-objekt. */
export function downloadJson(data: unknown, filename: string): void {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
