import type { ApiConfig } from './api'

/**
 * GDPR-eksport som ZIP — hentet som binær og gemt direkte.
 *
 * Hvorfor ikke `apiFetch`: den parser svaret som JSON, og et ZIP-arkiv er
 * bytes. Hvorfor ikke et udløbende link (besluttet 24/10-2026): et link der
 * dør efter 24 timer gør portabilitet til en tidsbegrænset rettighed. Serveren
 * streamer arkivet, klienten gemmer det med det samme — intet efterlades.
 */
export async function downloadExportZip(config: ApiConfig): Promise<void> {
  const url = new URL('/api/account/export.zip', config.apiBaseUrl).toString()
  const headers: Record<string, string> = {}
  if (config.authToken) headers.Authorization = `Bearer ${config.authToken}`
  const res = await fetch(url, { method: 'GET', headers })
  if (!res.ok) throw new Error(`eksport fejlede: HTTP ${res.status}`)
  const blob = await res.blob()
  const navn =
    res.headers.get('Content-Disposition')?.match(/filename="([^"]+)"/)?.[1] ??
    'jarvis-mine-data.zip'
  const objUrl = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = objUrl
  a.download = navn
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(objUrl), 1000)
}
