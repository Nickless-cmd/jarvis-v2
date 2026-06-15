import { describe, it, expect, beforeEach } from 'vitest'
import { loadTheme, saveTheme, applyTheme } from './themeStore'

describe('themeStore', () => {
  beforeEach(() => { localStorage.clear(); delete document.documentElement.dataset.theme })

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

  it('applyTheme sætter data-theme på root', () => {
    applyTheme('contrast')
    expect(document.documentElement.dataset.theme).toBe('contrast')
  })
})
