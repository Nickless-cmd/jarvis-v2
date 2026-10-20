import { describe, expect, it } from 'vitest'
import { udenAktivRun } from './transcriptFilter'

type Række = { id: string; run_id?: string | null; tekst: string }

const gammel: Række = { id: 'message-1', run_id: 'visible-old', tekst: 'gammelt svar' }
const bruger: Række = { id: 'message-2', tekst: 'mit spørgsmål' }
const persisteret: Række = { id: 'message-3', run_id: 'visible-ny', tekst: 'det nye svar' }
const bro: Række = { id: 'a-visible-ny', tekst: 'det nye svar (bro)' }

describe('udenAktivRun', () => {
  it('fjerner både server-rækken og bro-kopien for det run der tegnes levende', () => {
    const ud = udenAktivRun([gammel, bruger, persisteret, bro], 'visible-ny', true)
    expect(ud.map((m) => m.id)).toEqual(['message-1', 'message-2'])
  })

  it('beholder alt når intet run tegnes levende', () => {
    const ud = udenAktivRun([gammel, bruger, persisteret, bro], 'visible-ny', false)
    expect(ud).toHaveLength(4)
  })

  it('beholder rækker uden run_id — «ved ikke» må aldrig droppe et svar', () => {
    const udenKobling: Række = { id: 'message-4', tekst: 'svar fra før koblingen fandtes' }
    const ud = udenAktivRun([udenKobling, persisteret], 'visible-ny', true)
    expect(ud.map((m) => m.id)).toEqual(['message-4'])
  })

  it('rører ikke et andet runs rækker', () => {
    const ud = udenAktivRun([gammel, persisteret], 'visible-andet', true)
    expect(ud).toHaveLength(2)
  })

  it('er en no-op uden aktivt run', () => {
    const ud = udenAktivRun([gammel, persisteret], null, true)
    expect(ud).toHaveLength(2)
  })
})
