import { describe, it, expect } from 'vitest'
import { lookupTool } from './toolRegistry'

describe('toolRegistry', () => {
  it('known tool → curated label + summary', () => {
    const m = lookupTool('web_search')
    expect(m.label).toBe('Websøgning')
    expect(m.summarize({ query: 'vejr københavn' })).toBe('vejr københavn')
  })

  it('open_ui_panel summarises open vs close', () => {
    const m = lookupTool('open_ui_panel')
    expect(m.summarize({ panel: 'preview' })).toContain('preview')
    expect(m.summarize({ action: 'close' })).toBe('luk')
  })

  it('unknown tool → Title-Case fallback (never raw snake_case)', () => {
    const m = lookupTool('some_new_internal_tool')
    expect(m.label).toBe('Some New Internal Tool')
    expect(typeof m.summarize).toBe('function')
  })

  it('operator_ prefix is humanised', () => {
    const m = lookupTool('operator_read_file')
    expect(m.label).toBe('Læs fil')
  })

  it('remember_this opsummerer titlen frem for privat indhold', () => {
    const meta = lookupTool('remember_this')
    expect(meta.label).toBe('Minde')
    expect(meta.summarize({ title: 'Korte svar', content: 'Lang privat tekst' })).toBe('Korte svar')
  })

  it('hyppige opgave- og hukommelsesværktøjer har danske navne', () => {
    expect(lookupTool('list_side_tasks').label).toBe('Flaggede opgaver')
    expect(lookupTool('flag_side_task').label).toBe('Flag til senere')
    expect(lookupTool('search_jarvis_brain').label).toBe('Søg i hukommelsen')
    expect(lookupTool('read_brain_entry').label).toBe('Læs minde')
  })
})
