import { describe, it, expect, beforeEach } from 'vitest'
import { loadPanelWidth, savePanelWidth } from './panelStore'

beforeEach(() => localStorage.clear())

describe('panelStore', () => {
  it('returnerer default når intet er gemt', () => {
    expect(loadPanelWidth(500)).toBe(500)
  })
  it('gemmer og henter width', () => {
    savePanelWidth(640)
    expect(loadPanelWidth(500)).toBe(640)
  })
  it('ignorerer korrupt værdi', () => {
    localStorage.setItem('jarvis-desk:panelWidth', 'abc')
    expect(loadPanelWidth(500)).toBe(500)
  })
})
