import { describe, it, expect } from 'vitest'
import { panelReducer, initialPanelState, MIN_WIDTH } from './panelReducer'
import type { Artifact } from './artifacts'
import type { InspectorTarget } from './inspectorTargets'

const art: Artifact = { kind: 'markdown', title: 'T', content: '# x' }
const artifactTarget: InspectorTarget = { type: 'artifact', artifact: art }

describe('panelReducer', () => {
  it('open-target sætter open=true + target', () => {
    const s = panelReducer(initialPanelState(420), { type: 'open-target', target: artifactTarget })
    expect(s.open).toBe(true)
    expect(s.target).toEqual(artifactTarget)
  })
  it('close nulstiller open men beholder width', () => {
    const opened = panelReducer(initialPanelState(420), { type: 'open-target', target: artifactTarget })
    const s = panelReducer(opened, { type: 'close' })
    expect(s.open).toBe(false)
    expect(s.width).toBe(420)
    expect(s.target).toBeNull()
  })
  it('open-target skifter target uden at lukke', () => {
    const opened = panelReducer(initialPanelState(420), { type: 'open-target', target: artifactTarget })
    const art2: Artifact = { kind: 'code', title: 'C', language: 'js', content: 'a' }
    const target2: InspectorTarget = { type: 'artifact', artifact: art2 }
    const s = panelReducer(opened, { type: 'open-target', target: target2 })
    expect(s.open).toBe(true)
    expect(s.target).toEqual(target2)
  })
  it('går tilbage til forrige target og lukker når historikken er tom', () => {
    const tool: InspectorTarget = {
      type: 'tool', tool: { id: 't1', name: 'web', input: {}, status: 'done' },
    }
    const source: InspectorTarget = {
      type: 'source', source: { url: 'https://dr.dk', domaene: 'dr.dk', origin: 'tool_result' },
    }
    const opened = panelReducer(initialPanelState(420), { type: 'open-target', target: tool })
    const nested = panelReducer(opened, { type: 'open-target', target: source, rememberCurrent: true })
    const backed = panelReducer(nested, { type: 'back' })
    expect(backed.target).toEqual(tool)
    expect(backed.previousTarget).toBeNull()
    expect(panelReducer(backed, { type: 'back' }).open).toBe(false)
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
