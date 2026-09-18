import { describe, expect, it, beforeEach } from 'vitest'
import { laesKodeMappe } from './artefakter'

// Artefakt-fladen læser SAMME valg som code-visningen. To valg af «den
// aktuelle mappe» ville før eller siden pege to steder hen.
describe('laesKodeMappe', () => {
  beforeEach(() => localStorage.clear())

  it('en mappe på din maskine er wsPath', () => {
    localStorage.setItem('jarvis-desk:code-ws', JSON.stringify({ kind: 'workstation', root: 'repo', wsPath: '/media/projects/jarvis-v2' }))
    expect(laesKodeMappe()).toEqual({ root: '/media/projects/jarvis-v2', kind: 'workstation' })
  })

  it('en server-mappe er den navngivne rod', () => {
    localStorage.setItem('jarvis-desk:code-ws', JSON.stringify({ kind: 'container', root: 'repo' }))
    expect(laesKodeMappe()).toEqual({ root: 'repo', kind: 'container' })
  })

  it('intet valg endnu: repoet på serveren', () => {
    expect(laesKodeMappe()).toEqual({ root: 'repo', kind: 'container' })
  })

  it('workstation uden mappe falder tilbage til serveren frem for en tom sti', () => {
    localStorage.setItem('jarvis-desk:code-ws', JSON.stringify({ kind: 'workstation' }))
    expect(laesKodeMappe().kind).toBe('container')
  })

  it('tåler et ødelagt lager', () => {
    localStorage.setItem('jarvis-desk:code-ws', '{ikke json')
    expect(laesKodeMappe()).toEqual({ root: 'repo', kind: 'container' })
  })
})
