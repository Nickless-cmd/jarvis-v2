import { getTree, type TreeEntry, type ApiConfig } from './api'

/** Session-cache for mappe-listings, så fil-træet ikke re-henter samme mappe
 *  hver gang panelet/tab'en mountes (lokalt = ét bro-kald pr. mappe = tungt).
 *  Cache-first: returnér med det samme hvis kendt, ellers hent + gem. */
const _cache = new Map<string, TreeEntry[]>()

function keyOf(kind: string, root: string, path: string): string {
  return `${kind}|${root}|${path}`
}

/** Synkront cache-opslag (til instant første-render uden flimmer). */
export function peekTree(kind: string, root: string, path: string): TreeEntry[] | undefined {
  return _cache.get(keyOf(kind, root, path))
}

export async function getTreeCached(
  config: ApiConfig, kind: 'container' | 'workstation', root: string, path: string,
): Promise<TreeEntry[]> {
  const k = keyOf(kind, root, path)
  const hit = _cache.get(k)
  if (hit) return hit
  const entries = await getTree(config, kind, root, path)
  _cache.set(k, entries)
  return entries
}

/** Invalidér en mappe (fx efter en skrivning, så en ny fil dukker op). */
export function invalidateTree(kind: string, root: string, path: string): void {
  _cache.delete(keyOf(kind, root, path))
}

/** Ryd alt (fx ved skift af workspace/root). */
export function clearTreeCache(): void {
  _cache.clear()
}
