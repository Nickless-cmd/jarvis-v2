/** Only public renderer files are eligible. URL normalisation happens before this check. */
export function shouldCache(url: URL): boolean {
  if (url.origin !== globalThis.location.origin || url.search) return false
  const path = url.pathname
  return path === '/' || path === '/index.html' || path === '/favicon.svg' ||
    path === '/manifest.webmanifest' || path === '/icons/icon-192.png' ||
    path === '/icons/icon-512.png' || path.startsWith('/assets/')
}
