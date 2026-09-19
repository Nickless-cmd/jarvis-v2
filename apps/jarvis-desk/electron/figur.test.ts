import { afterAll, beforeEach, describe, expect, it, vi } from 'vitest'
import fs from 'node:fs'

vi.mock('electron', () => {
  const handlers = new Map<string, (...args: unknown[]) => unknown>()
  class FakeWindow {
    static last: FakeWindow | null = null
    static fromWebContents() { return FakeWindow.last }
    bounds = { x: 0, y: 0, width: 300, height: 150 }
    webContents = {}
    constructor() { FakeWindow.last = this }
    setBounds(bounds: typeof this.bounds) { this.bounds = bounds }
    getBounds() { return this.bounds }
    setAlwaysOnTop() {}
    setVisibleOnAllWorkspaces() {}
    once() {}
    on() {}
    destroy() { FakeWindow.last = null }
  }
  const Menu = {
    last: [] as Array<{ label: string; click: () => void }>,
    buildFromTemplate(items: Array<{ label: string; click: () => void }>) {
      Menu.last = items
      return { popup: () => {} }
    },
  }
  return {
    app: { getPath: () => '/tmp/jarvis-desk-figur-ipc-test' },
    BrowserWindow: FakeWindow,
    ipcMain: { handle: (name: string, fn: (...args: unknown[]) => unknown) => handlers.set(name, fn), handlers },
    Menu,
    screen: {
      getPrimaryDisplay: () => ({ workArea: { x: 0, y: 0, width: 1920, height: 1080 } }),
      getAllDisplays: () => [{ workArea: { x: 0, y: 0, width: 1920, height: 1080 } }],
      getDisplayNearestPoint: () => ({ workArea: { x: 0, y: 0, width: 1920, height: 1080 } }),
      getCursorScreenPoint: () => ({ x: 600, y: 400 }),
    },
  }
})

import { BrowserWindow, ipcMain, Menu } from 'electron'
import { lukFigur, opretFigur, registrerFigurIpc } from './figur'

type FakeWindow = { bounds: { x: number; y: number; width: number; height: number }; getBounds: () => { x: number; y: number; width: number; height: number } }
const handlers = (ipcMain as unknown as { handlers: Map<string, (...args: unknown[]) => unknown> }).handlers
const last = () => (BrowserWindow as unknown as { last: FakeWindow | null }).last!

describe('figurens Electron-bro', () => {
  beforeEach(() => {
    lukFigur()
    fs.rmSync('/tmp/jarvis-desk-figur-ipc-test', { recursive: true, force: true })
  })
  afterAll(() => {
    lukFigur()
    fs.rmSync('/tmp/jarvis-desk-figur-ipc-test', { recursive: true, force: true })
  })

  it('holder figurens skærmposition, når boblen flytter under den', () => {
    registrerFigurIpc({ preload: 'x', indlaes: () => {}, aabnSamtale: () => {}, stemme: () => {} })
    opretFigur('x', () => {})
    const before = last().getBounds()
    const anchor = before.y + 70
    handlers.get('figur:hoejde')!({}, 300, 275, 70, 'over', 70)
    expect(last().getBounds().y + 300 - 275 + 70).toBe(anchor)
    handlers.get('figur:hoejde')!({}, 300, 275, 70, 'under', 70)
    expect(last().getBounds().y + 70).toBe(anchor)
  })

  it('husker figurens midtpunkt efter vinduet genåbnes', () => {
    registrerFigurIpc({ preload: 'x', indlaes: () => {}, aabnSamtale: () => {}, stemme: () => {} })
    opretFigur('x', () => {})
    const anchor = last().getBounds().y + 70
    handlers.get('figur:hoejde')!({}, 300, 275, 70, 'under', 70)
    lukFigur()
    opretFigur('x', () => {})
    expect(last().getBounds().y + 70).toBe(anchor)
  })

  it('højrekliksmenuen skjuler figuren og gemmer valget', () => {
    const changed = vi.fn()
    registrerFigurIpc({ preload: 'x', indlaes: () => {}, aabnSamtale: () => {}, stemme: () => {}, onVistAendret: changed })
    opretFigur('x', () => {})
    handlers.get('figur:menu')!({ sender: {} })
    const menu = Menu as unknown as { last: Array<{ label: string; click: () => void }> }
    expect(menu.last[0]?.label).toBe('Skjul figur')
    menu.last[0]!.click()
    expect((BrowserWindow as unknown as { last: FakeWindow | null }).last).toBeNull()
    expect(JSON.parse(fs.readFileSync('/tmp/jarvis-desk-figur-ipc-test/figur.json', 'utf8')).vist).toBe(false)
    expect(changed).toHaveBeenCalledWith(false)
  })
})
