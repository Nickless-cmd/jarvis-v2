export type HostCapability = 'window' | 'folder-picker' | 'local-terminal' |
  'os-notification' | 'screen-control' | 'updater' | 'figure' | 'pointer'

function bridge(): Record<string, unknown> | undefined {
  if (typeof window === 'undefined') return undefined
  const value = (window as Window & { jarvisDesk?: unknown }).jarvisDesk
  return value && typeof value === 'object' ? value as Record<string, unknown> : undefined
}

export function hostKind(): 'desk' | 'web' { return bridge() ? 'desk' : 'web' }

const paths: Record<HostCapability, readonly string[]> = {
  window: ['vindue', 'minimer'],
  'folder-picker': ['pickFolder'],
  'local-terminal': ['terminal', 'run'],
  'os-notification': ['notifyShow'],
  'screen-control': ['markoer', 'skærme'],
  updater: ['updates', 'download'],
  figure: ['figur', 'vist'],
  pointer: ['markoer', 'skærme'],
}

export function hasHostCapability(name: HostCapability): boolean {
  let value: unknown = bridge()
  for (const part of paths[name]) {
    if (!value || typeof value !== 'object') return false
    value = (value as Record<string, unknown>)[part]
  }
  return typeof value === 'function'
}

function safeExternalUrl(url: string): boolean {
  try { return ['https:', 'http:'].includes(new URL(url).protocol) } catch { return false }
}

export function openExternalUrl(url: string): boolean {
  if (!safeExternalUrl(url)) return false
  const external = bridge()?.openExternal
  if (typeof external === 'function') {
    void Promise.resolve(external(url)).catch(() => {})
    return true
  }
  return !!window.open(url, '_blank', 'noopener,noreferrer')
}

/** Reserve a tab synchronously during the click; the caller can fetch its URL later. */
export function prepareExternalWindow(): (url: string | null) => boolean {
  if (hostKind() === 'desk') return (url) => url ? openExternalUrl(url) : false
  const popup = window.open('about:blank', '_blank')
  if (popup) popup.opener = null
  return (url) => {
    if (!popup) return false
    if (!url || !safeExternalUrl(url)) { popup.close(); return false }
    popup.location.href = url
    return true
  }
}
