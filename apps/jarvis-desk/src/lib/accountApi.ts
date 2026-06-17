import { apiFetch, type ApiConfig } from './api'

/** GDPR-dataeksport: hent brugerens eget data-bundt (JSON). */
export async function exportMyData(config: ApiConfig): Promise<unknown> {
  return apiFetch(config, '/api/account/export')
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
