import { afterEach, describe, expect, it, vi } from 'vitest'
import { hasHostCapability, hostKind, openExternalUrl, prepareExternalWindow } from './host'

afterEach(() => vi.unstubAllGlobals())

describe('host capabilities', () => {
  it('does not offer local OS actions in a browser', () => {
    vi.stubGlobal('jarvisDesk', undefined)
    expect(hostKind()).toBe('web')
    for (const name of ['window', 'folder-picker', 'local-terminal', 'os-notification', 'screen-control', 'updater', 'figure', 'pointer'] as const) {
      expect(hasHostCapability(name)).toBe(false)
    }
  })

  it('checks actual bridge methods rather than a bridge object alone', () => {
    vi.stubGlobal('jarvisDesk', { config: {} })
    expect(hostKind()).toBe('desk')
    expect(hasHostCapability('folder-picker')).toBe(false)
    expect(hasHostCapability('local-terminal')).toBe(false)
    expect(hasHostCapability('window')).toBe(false)
  })

  it('recognizes the methods supplied by Electron preload', () => {
    vi.stubGlobal('jarvisDesk', {
      pickFolder: () => null,
      terminal: { run: () => null },
      vindue: { minimer: () => null },
      notifyShow: () => null,
      markoer: { skærme: () => null },
      updates: { download: () => null },
      figur: { vist: () => null },
    })
    expect(hasHostCapability('folder-picker')).toBe(true)
    expect(hasHostCapability('local-terminal')).toBe(true)
    expect(hasHostCapability('window')).toBe(true)
    expect(hasHostCapability('os-notification')).toBe(true)
    expect(hasHostCapability('screen-control')).toBe(true)
    expect(hasHostCapability('updater')).toBe(true)
    expect(hasHostCapability('figure')).toBe(true)
    expect(hasHostCapability('pointer')).toBe(true)
  })

  it('opens a safe link in the browser and rejects script URLs', () => {
    vi.stubGlobal('jarvisDesk', undefined)
    const open = vi.fn(() => ({}))
    vi.stubGlobal('open', open)
    expect(openExternalUrl('https://example.com/path')).toBe(true)
    expect(open).toHaveBeenCalledWith('https://example.com/path', '_blank', 'noopener,noreferrer')
    expect(openExternalUrl('javascript:alert(1)')).toBe(false)
    expect(open).toHaveBeenCalledTimes(1)
  })

  it('reserves a browser window during a click before an async URL arrives', () => {
    vi.stubGlobal('jarvisDesk', undefined)
    const popup = { opener: window, location: { href: '' }, close: vi.fn() }
    const open = vi.fn(() => popup)
    vi.stubGlobal('open', open)
    const complete = prepareExternalWindow()
    expect(open).toHaveBeenCalledWith('about:blank', '_blank')
    expect(complete('https://accounts.example/connect')).toBe(true)
    expect(popup.location.href).toBe('https://accounts.example/connect')
    expect(popup.opener).toBeNull()
  })
})
