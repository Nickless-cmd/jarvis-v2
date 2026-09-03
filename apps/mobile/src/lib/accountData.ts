import type { ApiConfig } from './types'

/**
 * Brugerens egne data — tælle, slette, eksportere.
 *
 * Sletning er LAGVIS med vilje. Jarvis' hukommelse er fire forskellige ting, og
 * «slet alt» ville dække over fire meget forskellige tab: at slette sine
 * samtaler er noget andet end at få ham til at glemme hvem man er.
 */

export interface DataLayer {
  key: 'sessions' | 'senses' | 'brain' | 'identity' | string
  label: string
  count: number
  unit: string
  detail: string
}

export interface DeleteResult {
  layer?: string
  deleted?: number
  failed?: number
  error?: string
  results?: DeleteResult[]
}

async function call<T>(
  config: ApiConfig,
  path: string,
  method: 'GET' | 'DELETE' = 'GET'
): Promise<T | null> {
  try {
    const url = new URL(path, config.apiBaseUrl).toString()
    const r = await fetch(url, {
      method,
      headers: config.authToken ? { Authorization: `Bearer ${config.authToken}` } : {}
    })
    if (!r.ok) return null
    return (await r.json()) as T
  } catch {
    return null
  }
}

export async function fetchDataOverview(config: ApiConfig): Promise<DataLayer[]> {
  const out = await call<{ layers: DataLayer[] }>(config, '/account/data')
  return out?.layers ?? []
}

/** Uigenkaldeligt. Bekræftelsen hører hjemme FØR dette kald. */
export async function deleteLayer(
  config: ApiConfig,
  layer: string
): Promise<DeleteResult | null> {
  return call<DeleteResult>(config, `/account/data/${encodeURIComponent(layer)}`, 'DELETE')
}

/** URL til eksporten. Kræver token — hentes med fetch, ikke som et link. */
export function exportUrl(config: ApiConfig): string {
  return new URL('/account/export', config.apiBaseUrl).toString()
}

/**
 * «142 samtaler», «1 samtale», «0 samtaler».
 *
 * Identitets-laget måles i TEGN og ikke i stykker, så det har sin egen form:
 * «1.204 tegn» giver mening, «1.204 hvem du er» gør ikke.
 */
export function describeLayer(layer: DataLayer): string {
  const n = Math.max(0, Number(layer.count) || 0)
  if (layer.key === 'identity') {
    return n === 0 ? 'tom' : `${n.toLocaleString('da-DK')} tegn`
  }
  const unit = n === 1 ? singular(layer.unit) : layer.unit
  return `${n.toLocaleString('da-DK')} ${unit}`
}

function singular(unit: string): string {
  if (unit.endsWith('er')) return unit.slice(0, -1)   // samtaler → samtale
  if (unit.endsWith('poster')) return 'post'
  return unit
}

/** Menneskelig kvittering efter en sletning — også når intet blev slettet. */
export function describeResult(res: DeleteResult | null): string {
  if (!res) return 'Det kunne ikke lade sig gøre. Prøv igen.'
  if (res.results) {
    const total = res.results.reduce((sum, r) => sum + (r.deleted ?? 0), 0)
    const failed = res.results.filter((r) => (r.failed ?? 0) > 0).length
    if (failed > 0) return `Slettede ${total}, men ${failed} lag fejlede.`
    return total === 0 ? 'Der var ingenting at slette.' : `Slettede ${total} ting.`
  }
  const n = res.deleted ?? 0
  if ((res.failed ?? 0) > 0) return `Slettede ${n}, men noget fejlede.`
  return n === 0 ? 'Der var ingenting at slette.' : `Slettede ${n}.`
}
