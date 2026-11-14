import type { DeskLocationPayload, LocationMode } from './deskLocation'

/** Et vellykket opslag gælder længe: IP/manuel ændrer sig sjældent. */
export const OK_TTL_MS = 10 * 60_000
/**
 * Et FEJLET opslag gælder kortere, men det gælder. Målt 14/11-2026: Electron uden GOOGLE_API_KEY
 * melder en hårdkodet position, reverse-geocoden svarer 502, opslaget giver null — og ingen cachede
 * null, så hvert 5. sekunds ping gentog det. ~0,8 kald/s mod `/geo/reverse` (89 af 90 på 10 min
 * var 502) i en server der i forvejen var mættet af polling.
 */
export const FEJL_TTL_MS = 2 * 60_000

type Svar = DeskLocationPayload | Record<string, never> | undefined

export interface LocationResolverDeps {
  loadMode: () => LocationMode
  getLocation: (mode: LocationMode) => Promise<DeskLocationPayload | null>
  now?: () => number
}

/**
 * Lokation til presence-pinget. `{}` sendes ÉN gang når metoden slås fra (rydder serverens sted);
 * `undefined` betyder «send ingen lokation i dette ping».
 */
export function createLocationResolver(deps: LocationResolverDeps): () => Promise<Svar> {
  const now = deps.now ?? Date.now
  let cachedLoc: DeskLocationPayload | null = null
  let cachedAt = 0
  let cachedMode: LocationMode | null = null
  let cachedTtl = 0
  let clearedOff = false
  let undervejs: Promise<Svar> | null = null

  const hent = async (mode: LocationMode): Promise<Svar> => {
    const loc = await deps.getLocation(mode)
    // Et tidligere godt sted overlever en fejl; en anden metodes sted gør ikke.
    if (loc) cachedLoc = loc
    else if (cachedMode !== mode) cachedLoc = null
    cachedMode = mode
    cachedAt = now()
    cachedTtl = loc ? OK_TTL_MS : FEJL_TTL_MS
    return cachedLoc ?? undefined
  }

  return async () => {
    const mode = deps.loadMode()
    if (mode === 'off') {
      cachedLoc = null
      cachedMode = null
      cachedAt = 0
      if (clearedOff) return undefined
      clearedOff = true
      return {}
    }
    clearedOff = false
    if (cachedMode === mode && now() - cachedAt < cachedTtl) return cachedLoc ?? undefined
    if (undervejs) return undervejs
    undervejs = hent(mode).finally(() => { undervejs = null })
    return undervejs
  }
}
