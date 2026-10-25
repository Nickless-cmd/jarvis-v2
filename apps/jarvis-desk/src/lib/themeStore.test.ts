import { describe, it, expect, beforeEach, vi } from 'vitest'
import { applyTheme, loadAccent, loadTheme, saveAccent, saveTheme } from './themeStore'

describe('themeStore', () => {
  beforeEach(() => {
    localStorage.clear()
    delete document.documentElement.dataset.theme
    delete document.documentElement.dataset.themeMode
    delete document.documentElement.dataset.accent
  })

  it('default er dark når intet er gemt', () => {
    expect(loadTheme()).toBe('dark')
  })

  it('gemmer og henter tema', () => {
    saveTheme('light')
    expect(loadTheme()).toBe('light')
  })

  it('ignorerer ugyldigt gemt tema', () => {
    localStorage.setItem('jarvisDeskTheme', 'neon')
    expect(loadTheme()).toBe('dark')
  })

  it('migrerer det gamle kontrast-tema til mørkt', () => {
    localStorage.setItem('jarvisDeskTheme', 'contrast')
    expect(loadTheme()).toBe('dark')
  })

  it('gemmer APK-accenten og anvender begge tema-akser på root', () => {
    saveAccent('lilla')
    expect(loadAccent()).toBe('lilla')
    applyTheme('light', 'lilla')
    expect(document.documentElement.dataset.theme).toBe('light')
    expect(document.documentElement.dataset.themeMode).toBe('light')
    expect(document.documentElement.dataset.accent).toBe('lilla')
  })

  it('automatisk følger systemets farveskema uden at ændre accenten', () => {
    const listeners: Array<(event: MediaQueryListEvent) => void> = []
    const query = {
      matches: true,
      addEventListener: vi.fn((_type: string, listener: (event: MediaQueryListEvent) => void) => {
        listeners.push(listener)
      }),
      removeEventListener: vi.fn(),
    } as unknown as MediaQueryList
    vi.stubGlobal('matchMedia', vi.fn(() => query))

    applyTheme('auto', 'rose')
    expect(document.documentElement.dataset.themeMode).toBe('auto')
    expect(document.documentElement.dataset.theme).toBe('dark')
    expect(document.documentElement.dataset.accent).toBe('rose')

    listeners[0]!({ matches: false } as MediaQueryListEvent)
    expect(document.documentElement.dataset.theme).toBe('light')

    applyTheme('dark', 'rose')
    expect(query.removeEventListener).toHaveBeenCalledWith('change', listeners[0])
    vi.unstubAllGlobals()
  })
})
