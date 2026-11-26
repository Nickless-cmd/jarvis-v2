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

  // MAALT 20/10-2026 (Bjorn: «dobbelt beskeden er der stadig»). Den gemte
  // besked har FLERE text-blokke (commentary + final_answer), og
  // `normaliseretTekst` joiner dem uden separator: «…aaben.Flag-kaldet» mod
  // den levende «…aaben. Flag-kaldet». Maalt paa besked 210931: de to tekster
  // deler 1768 tegns suffix, men foerste afvigelse ligger ved tegn 132 — saa
  // `endsWith` paa hele strengen fejlede, og raekken stod paa skaermen.
  it('dropper raekken selv naar blokkene er joinet uden mellemrum', () => {
    const del1 = 'Foerste afsnit af arbejdsteksten.'
    const svar =
      'Det endelige svar staar her og er langt nok til at taelle som et rigtigt svar. ' +
      'Det fortsaetter over flere linjer, praecis som svarene i den virkelige flade, ' +
      'og slutter med en saetning der kun findes i dette ene svar.'
    const raekker = [
      { id: 'u1', role: 'user' },
      {
        id: 'message-abc',
        role: 'assistant',
        content: [
          { type: 'text', text: del1 },
          { type: 'text', text: svar },
        ],
      },
    ]
    // Den levende tekst kom som EN stroem og har mellemrummet; raekken har
    // ikke, fordi blokkene blev joinet. Suffixet er identisk.
    expect(udenAktivRun(raekker, 'r1', true, `Arbejde. ${del1} ${svar}`)).toHaveLength(1)
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

  // MAALT 26/11-2026 (Bjorn: «pacen doer og der sker et glip i smeltet af de 2
  // beskeder»). Siden svaret blev den blok serveren stempler `final_answer`,
  // ligger en runde EFTER svaret som en hale BAG svaret i den levende tekst —
  // mens den persisterede raekke kun baerer svaret. Saa er raekken et PRAEFIKS
  // af den levende tekst, og baade `endsWith` og `delerSuffix` fejler, fordi de
  // kun ser paa haler. Maalt med den aegte funktion foer rettelsen: 2
  // assistent-raekker i stedet for 1 — den persisterede besked stod synligt ved
  // siden af den levende, og de to smeltede sammen med et glip.
  it('dropper raekken naar en runde EFTER svaret ligger som hale bag det', () => {
    const svar =
      'Det endelige svar staar her og er langt nok til at taelle som et rigtigt svar. ' +
      'Det fortsaetter over flere linjer, praecis som svarene i den virkelige flade, ' +
      'og slutter med en saetning der kun findes i dette ene svar.'
    const hale = 'Forslaget ligger klar i komponisten.'
    const raekker = [
      { id: 'u1', role: 'user' },
      { id: 'message-abc', role: 'assistant', content: [{ type: 'text', text: svar }] },
    ]
    // Den levende tekst er svaret PLUS den nye rundes tekst — halen ligger bagefter.
    const ud = udenAktivRun(raekker, 'r1', true, `${svar} ${hale}`)
    expect(ud.map((m) => m.id)).toEqual(['u1'])
  })

  // Modproeven: et KORT svar maa ikke sluge en laengere, anden tekst der
  // tilfaeldigvis starter ens. Praefiks-grenen kraever samme laengdegulv som
  // suffix-grenen, saa den ikke bliver en tom match.
  it('lader en kort raekke staa naar den kun deler begyndelsen med den levende tekst', () => {
    const kort = 'Ja.'
    const raekker = [
      { id: 'u1', role: 'user' },
      { id: 'message-abc', role: 'assistant', content: [{ type: 'text', text: kort }] },
    ]
    const ud = udenAktivRun(raekker, 'r1', true, `${kort} Men det er en helt anden og meget laengere tekst.`)
    expect(ud.map((m) => m.id)).toEqual(['u1', 'message-abc'])
  })
})
