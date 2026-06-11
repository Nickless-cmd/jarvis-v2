import { describe, it, expect } from 'vitest'
import { panelReducer, initialPanelState, MIN_WIDTH } from './panelReducer'
import type { Artifact } from './artifacts'

const art: Artifact = { kind: 'markdown', title: 'T', content: '# x' }

describe('panelReducer', () => {
  it('open sætter open=true + artifact', () => {
    const s = panelReducer(initialPanelState(420), { type: 'open', artifact: art })
    expect(s.open).toBe(true)
    expect(s.artifact).toBe(art)
  })
  it('close nulstiller open men beholder width', () => {
    const opened = panelReducer(initialPanelState(420), { type: 'open', artifact: art })
    const s = panelReducer(opened, { type: 'close' })
    expect(s.open).toBe(false)
    expect(s.width).toBe(420)
  })
  it('replace skifter artifact uden at lukke', () => {
    const opened = panelReducer(initialPanelState(420), { type: 'open', artifact: art })
    const art2: Artifact = { kind: 'code', title: 'C', language: 'js', content: 'a' }
    const s = panelReducer(opened, { type: 'replace', artifact: art2 })
    expect(s.open).toBe(true)
    expect(s.artifact).toBe(art2)
  })
  it('resize clamper til MIN_WIDTH nedadtil', () => {
    const s = panelReducer(initialPanelState(420), { type: 'resize', width: 100 })
    expect(s.width).toBe(MIN_WIDTH)
  })
  it('toggle flipper open frem og tilbage', () => {
    const a = panelReducer(initialPanelState(420), { type: 'toggle' })
    expect(a.open).toBe(true)
    const b = panelReducer(a, { type: 'toggle' })
    expect(b.open).toBe(false)
  })
})
