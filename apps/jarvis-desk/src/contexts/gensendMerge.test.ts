import { describe, expect, it } from 'vitest'
import { mergeServer, type LocalMessage } from './SessionContext'
import { udenErstattede } from '../lib/gensendDublet'

const brugerMsg = (id: string, text: string, clientStatus?: LocalMessage['clientStatus']): LocalMessage => ({
  id, role: 'user', content: [{ type: 'text', text }], created_at: '2026-11-12T10:00:00Z',
  parent_id: null, ...(clientStatus ? { clientStatus } : {}),
}) as LocalMessage

describe('gensend: præcis én brugerbesked', () => {
  it('den NYE optimistiske overlever en poll mens serveren kun har den gamle kopi', () => {
    const gammel = brugerMsg('srv-1', 'kør igen', 'server_confirmed')
    const ny = brugerMsg('u-99', 'kør igen', 'optimistic_user')
    const flettet = mergeServer([gammel, ny], [gammel])
    expect(flettet.map((m) => m.id)).toEqual(['srv-1', 'u-99'])
  })
  it('efter gensend + skjult original står der præcis én brugerbesked (den nye)', () => {
    const gammel = brugerMsg('srv-1', 'kør igen', 'server_confirmed')
    const ny = brugerMsg('u-99', 'kør igen', 'optimistic_user')
    const flettet = mergeServer([gammel, ny], [gammel])
    const set = udenErstattede(flettet, new Set(['srv-1']))
    expect(set.filter((m) => m.role === 'user').map((m) => m.id)).toEqual(['u-99'])
  })
  it('normal send: serveren har indhentet → ingen dublet', () => {
    const opt = brugerMsg('u-1', 'hej', 'optimistic_user')
    const flettet = mergeServer([opt], [brugerMsg('srv-1', 'hej')])
    expect(flettet.map((m) => m.id)).toEqual(['srv-1'])
  })
})
