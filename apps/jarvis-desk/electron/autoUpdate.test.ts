import { describe, it, expect, vi } from 'vitest'
import { wireUpdater } from './autoUpdate'

function fakeUpdater() {
  const handlers: Record<string, (x: unknown) => void> = {}
  return {
    autoDownload: true,
    on: (ev: string, cb: (x: unknown) => void) => { handlers[ev] = cb },
    checkForUpdates: vi.fn(),
    downloadUpdate: vi.fn(),
    quitAndInstall: vi.fn(),
    _emit: (ev: string, x?: unknown) => handlers[ev]?.(x),
  }
}

describe('wireUpdater', () => {
  it('update-available → send til renderer; download kun ved kald', () => {
    const up = fakeUpdater()
    const sent: unknown[] = []
    const api = wireUpdater(up as never, (ch, p) => sent.push([ch, p]))
    expect(up.autoDownload).toBe(false)
    up._emit('update-available', { version: '0.3.0' })
    expect(sent).toContainEqual(['update:available', { version: '0.3.0' }])
    expect(up.downloadUpdate).not.toHaveBeenCalled()
    api.download()
    expect(up.downloadUpdate).toHaveBeenCalled()
  })

  it('update-downloaded → ready; installNow kalder quitAndInstall', () => {
    const up = fakeUpdater()
    const sent: unknown[] = []
    const api = wireUpdater(up as never, (ch, p) => sent.push([ch, p]))
    up._emit('update-downloaded', { version: '0.3.0' })
    expect(sent).toContainEqual(['update:ready', { version: '0.3.0' }])
    api.installNow()
    expect(up.quitAndInstall).toHaveBeenCalled()
  })
})
