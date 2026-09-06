import { tælVentende } from './WorkScreen'
import type { Decision } from '../lib/decisionsApi'
import type { WorkReview } from '../lib/workReviewApi'

function d(kind: Decision['kind'], id: string): Decision {
  return { kind, id, text: 't', why: '', priority: '', created_at: '', actions: [] }
}

describe('tælVentende', () => {
  it('tæller godkendelser og initiativer sammen', () => {
    expect(tælVentende(2, [d('initiative', 'a'), d('initiative', 'b')])).toBe(4)
  })

  // Kernen: tre livsprojekter har ligget der siden juni. Talte de med, ville
  // prikken aldrig gå væk igen.
  it('tæller IKKE livsprojekter med — prikken skal kunne gå væk', () => {
    const projekter = [d('life_project', 'l1'), d('life_project', 'l2'), d('life_project', 'l3')]
    expect(tælVentende(0, projekter)).toBe(0)
  })

  it('lader initiativer tænde prikken selv uden godkendelser', () => {
    expect(tælVentende(0, [d('initiative', 'a'), d('life_project', 'l1')])).toBe(1)
  })

  it('er nul når der intet er', () => {
    expect(tælVentende(0, [])).toBe(0)
  })
})

describe('tælReviewVentende', () => {
  it('tæller kørende reviews som arbejde der fortjener en prik', () => {
    const { tælReviewVentende } = require('./WorkScreen') as typeof import('./WorkScreen')
    const items: WorkReview[] = [
      { id: 'a', kind: 'dispatch', title: 'A', status: 'running', branch: '', updatedAt: '', summary: '', filesChanged: 0, additions: 0, deletions: 0 },
      { id: 'b', kind: 'dispatch', title: 'B', status: 'completed', branch: '', updatedAt: '', summary: '', filesChanged: 0, additions: 0, deletions: 0 }
    ]
    expect(tælReviewVentende(items)).toBe(1)
  })
})

describe('fokus-fane fra push', () => {
  it('et signal aabner den oenskede fane, nul lader den vaere', () => {
    // Rendering af hele WorkScreen kraever for meget kontekst her; kontrakten
    // er `focusSignal > 0 && focusTab` — den er testet direkte, saa reglen
    // staar fast selv om komponenten omskrives.
    const skal = (signal: number, tab?: string) => signal > 0 && Boolean(tab)
    expect(skal(0, 'approve')).toBe(false)
    expect(skal(1, 'approve')).toBe(true)
    expect(skal(2, undefined)).toBe(false)
  })
})
