import type { ApiConfig } from './types'

export interface UpdateManifest {
  version: string
  version_code: number
  notes: string
  filename: string
}

/** true hvis manifestets version_code er strengt højere end den installerede. */
export function compareVersion(installedVc: number, manifest: { version_code?: number }): boolean {
  const remote = manifest.version_code
  if (typeof remote !== 'number') return false
  return remote > installedVc
}

/**
 * Henter /mobile/latest og returnerer manifestet hvis det er nyere end
 * `installedVc`, ellers null. Alle fejl (netværk, ikke-ok, malformet) → null.
 */
export async function checkForUpdate(
  config: ApiConfig,
  installedVc: number
): Promise<UpdateManifest | null> {
  try {
    const url = new URL('/mobile/latest', config.apiBaseUrl).toString()
    const r = await fetch(url, {
      headers: config.authToken ? { Authorization: `Bearer ${config.authToken}` } : {},
    })
    if (!r.ok) return null
    const data = (await r.json()) as Partial<UpdateManifest>
    if (!compareVersion(installedVc, data)) return null
    return data as UpdateManifest
  } catch {
    return null
  }
}
