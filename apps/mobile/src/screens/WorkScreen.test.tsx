import { tælVentende } from './WorkScreen'
import type { Decision } from '../lib/decisionsApi'

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
