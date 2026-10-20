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

  // MAALT 20/10-2026 (Bjorn: «dobbelt beskeden over den igangvaerende pace er
  // tilbage»): `chat_sessions.py` UDELADER `run_id` naar `run_for()` ikke
  // kender beskeden — det sker i vinduet lige efter persistering. Uden noeglen
  // stod den faerdige besked OVEN OVER den der stadig pacede.
  it('dropper den persisterede raekke ogsaa naar run_id mangler', () => {
    const svar = 'A'.repeat(600)
    const raekker = [
      { id: 'u1', role: 'user' },
      { id: 'message-abc', role: 'assistant', content: [{ type: 'text', text: svar }] },
    ]
    // Raekken baerer INTET run_id — kun teksten binder den til turen.
    expect(udenAktivRun(raekker, 'r1', true, `Arbejde. ${svar}`)).toHaveLength(1)
  })

  it('roerer ikke et aeldre svar — kun den sidste assistent-raekke', () => {
    const svar = 'A'.repeat(600)
    const raekker = [
      { id: 'a-old', role: 'assistant', content: [{ type: 'text', text: 'B'.repeat(80) }] },
      { id: 'a-new', role: 'assistant', content: [{ type: 'text', text: svar }] },
    ]
    const ud = udenAktivRun(raekker, null, true, svar)
    expect(ud).toHaveLength(1)
    expect(ud[0]?.id).toBe('a-old')
  })
})
