import { describe, it, expect } from 'vitest'
import { opdel, opdelArbejdsrunder, turFortalt, turHoved } from './raekkeModel'
import type { ContentBlock } from './sseProtocol'

/**
 * Opdelingen er hele rækkevisningen.
 *
 * Fejler den, ser man enten et svar der forsvinder ind bag en foldet gruppe,
 * eller en narrationslinje der bliver stående som om den var svaret. Begge
 * dele er tavse: der kastes intet, og alle blokke er der stadig.
 */

const tekst = (t: string): ContentBlock => ({ type: 'text', text: t })
const kald = (navn: string): ContentBlock => ({ type: 'tool_use', id: navn, name: navn, input: {} })
const tanke = (s: number): ContentBlock => ({ type: 'thinking', thinking: '…', seconds: s })

describe('opdel', () => {
  it('lægger tekst MELLEM to kald i arbejdet, ikke i svaret', () => {
    const { arbejde, svar } = opdel([
      kald('bash'),
      tekst('Den svarer 200. Nu henter jeg kataloget.'),
      kald('bash'),
      tekst('Færdig.'),
    ])
    expect(arbejde.map((e) => e.slags)).toEqual(['blok', 'mellemsvar', 'blok'])
    expect(arbejde[1]).toEqual({ slags: 'mellemsvar', tekst: 'Den svarer 200. Nu henter jeg kataloget.' })
    expect(svar).toEqual([tekst('Færdig.')])
  })

  it('bevarer rækkefølgen — en syntese skal stå mellem DE kald den stod imellem', () => {
    const { arbejde } = opdel([
      kald('search'), tekst('A'), kald('fetch'), tekst('B'), kald('read'),
    ])
    expect(arbejde.map((e) => {
      if (e.slags === 'mellemsvar') return e.tekst
      if (e.slags === 'spor') return 'spor'
      return (e.blok as { name: string }).name
    }))
      .toEqual(['search', 'A', 'fetch', 'B', 'read'])
  })

  it('en besked UDEN kald er rent svar — intet tomt arbejdsområde', () => {
    // Faelden: havde reglen vaeret «sidste tekstblok er svaret», ville det
    // foerste afsnit her lande i en gruppe, og der ville staa
    // «Thought for 0s · 0 tool calls» over en almindelig replik.
    const { arbejde, svar, kald: n } = opdel([tekst('Første afsnit.'), tekst('Andet afsnit.')])
    expect(arbejde).toEqual([])
    expect(svar).toHaveLength(2)
    expect(n).toBe(0)
  })

  it('lader alt efter det sidste kald være svar — også flere afsnit', () => {
    const { svar } = opdel([kald('bash'), tekst('Et.'), tekst('To.')])
    expect(svar.map((b) => (b as { text: string }).text)).toEqual(['Et.', 'To.'])
  })

  it('springer tomme tekstblokke over — de opstår før første delta', () => {
    const { arbejde } = opdel([kald('bash'), tekst('   '), kald('bash')])
    expect(arbejde.filter((e) => e.slags === 'mellemsvar')).toEqual([])
  })

  it('samler sammenhængende progress-blokke til ÉT spor', () => {
    // Bjoern 23/9-2026: ni «Koerer kommando: python» under hinanden er stoej.
    // Én linje der opdaterer sig, med hele forloebet i kroppen.
    const p = (m: string): ContentBlock => ({
      type: 'progress', tool_use_id: 't', parent_tool_use_id: null, message: m, status: 'running',
    })
    const { arbejde } = opdel([kald('bash'), p('et'), p('to'), p('tre'), tekst('svar')])
    expect(arbejde.map((e) => e.slags)).toEqual(['blok', 'spor'])
    const spor = arbejde[1]
    if (spor?.slags !== 'spor') throw new Error('forventede et spor')
    expect(spor.trin.map((t) => t.message)).toEqual(['et', 'to', 'tre'])
  })

  it('bryder sporet når der kommer noget imellem', () => {
    const p = (m: string): ContentBlock => ({
      type: 'progress', tool_use_id: 't', parent_tool_use_id: null, message: m, status: 'running',
    })
    const { arbejde } = opdel([kald('a'), p('et'), kald('b'), p('to'), tekst('svar')])
    expect(arbejde.map((e) => e.slags)).toEqual(['blok', 'spor', 'blok', 'spor'])
  })

  it('tæller kald og lægger tænketiden sammen', () => {
    const o = opdel([tanke(12), kald('a'), tanke(9), kald('b'), tekst('svar')])
    expect(o.kald).toBe(2)
    expect(o.sekunder).toBe(21)
  })

  it('holder en afsluttende tanke i ARBEJDET — ikke i svaret', () => {
    // Skillelinjen gaelder TEKST. En tanke er arbejde uanset hvor den staar:
    // lagde vi den i svaret, ville raa tankestroem blive tegnet som replik,
    // med tænke-raekkens indhold spredt ud som brodtekst.
    const { arbejde, svar } = opdel([kald('a'), tanke(3)])
    expect(arbejde.map((e) => e.slags)).toEqual(['blok', 'blok'])
    expect(svar).toEqual([])
  })

  it('er tom for en tom besked', () => {
    expect(opdel([])).toEqual({ arbejde: [], svar: [], kald: 0, sekunder: 0 })
  })
})

describe('turHoved', () => {
  it('skriver sekunder, ikke «a while» (Bjørn 22/9-2026)', () => {
    expect(turHoved(9, 90)).toBe('Thought for 90s · 9 tool calls')
  })
  it('bøjer ental', () => {
    expect(turHoved(1, 7)).toBe('Thought for 7s · 1 tool call')
  })
  it('siger ikke «0s» når der ikke blev tænkt', () => {
    expect(turHoved(2, 0)).toBe('Worked · 2 tool calls')
  })
  it('lader «0 tool calls» være — en tur der kun tænkte har ikke et kald at tælle', () => {
    expect(turHoved(0, 12)).toBe('Thought for 12s')
  })
})

describe('turFortalt', () => {
  it('fortæller hvad arbejdet var, ikke hvor mange kald', () => {
    // Bjørn 23/9-2026: «hvordan forslår du punkt 5 skal se ud?» — ni kald
    // kan være ni filer læst eller ni kommandoer kørt, og de to betyder
    // vidt forskellige ting at læse.
    const f = [...Array(6).fill('fil'), ...Array(3).fill('terminal')]
    expect(turFortalt(f, 9, 90)).toBe('Læste 6 filer og kørte 3 kommandoer · 90s')
  })
  it('bøjer ental — «en fil», ikke «1 filer»', () => {
    expect(turFortalt(['fil'], 1, 7)).toBe('Læste en fil · 7s')
  })
  it('sætter den største gruppe først', () => {
    expect(turFortalt(['terminal', 'terminal', 'fil'], 3, 0))
      .toBe('Kørte 2 kommandoer og læste en fil')
  })
  it('dropper tiden når der ikke blev tænkt', () => {
    expect(turFortalt(['diff', 'diff'], 2, 0)).toBe('Redigerede 2 filer')
  })
  it('klipper til tre led og siger «mere» frem for at skjule resten', () => {
    expect(turFortalt(['fil', 'liste', 'terminal', 'skriv'], 4, 5))
      .toBe('Læste en fil, søgte en gang, kørte en kommando og mere · 5s')
  })
  it('falder tilbage til tællingen når der slet ikke blev brugt værktøjer', () => {
    expect(turFortalt([], 0, 12)).toBe('Thought for 12s')
  })
  it('giver en ukendt familie en ærlig frase frem for at forsvinde', () => {
    expect(turFortalt(['noget-nyt'], 1, 3)).toBe('Arbejdede · 3s')
  })
})

describe('opdelArbejdsrunder', () => {
  it('bevarer synteser mellem foldbare værktøjsrunder', () => {
    const { arbejde } = opdel([
      tekst('Jeg finder filen.'), kald('read_file'), kald('grep'),
      tekst('Jeg retter fejlen.'), kald('edit_file'),
      tekst('Rettet.'),
    ])
    const sektioner = opdelArbejdsrunder(arbejde)
    expect(sektioner.map((s) => s.slags)).toEqual(['syntese', 'runde', 'syntese', 'runde'])
    expect(sektioner[0]).toEqual({ slags: 'syntese', tekst: 'Jeg finder filen.' })
    expect(sektioner[1]).toMatchObject({ slags: 'runde' })
    expect(sektioner[2]).toEqual({ slags: 'syntese', tekst: 'Jeg retter fejlen.' })
    expect(sektioner[3]).toMatchObject({ slags: 'runde' })
    expect(sektioner.filter((s) => s.slags === 'runde').map((s) => s.elementer.length)).toEqual([2, 1])
  })

  it('bruger en neutral fallback når Jarvis ikke selv skrev en arbejdslinje', () => {
    const { arbejde } = opdel([kald('read_file'), kald('bash'), tekst('Færdig.')])
    expect(opdelArbejdsrunder(arbejde)).toEqual([{
      slags: 'runde',
      elementer: arbejde,
    }])
  })

  it('bevarer tanke og progress i den værktøjsrunde de tilhører', () => {
    const p: ContentBlock = { type: 'progress', tool_use_id: 'read_file', parent_tool_use_id: null, message: 'Læser', status: 'running' }
    const { arbejde } = opdel([tekst('Jeg læser.'), tanke(2), kald('read_file'), p, tekst('Svar.')])
    const runde = opdelArbejdsrunder(arbejde)[1]
    expect(runde?.slags).toBe('runde')
    if (runde?.slags !== 'runde') throw new Error('forventede en arbejdsrunde')
    expect(runde.elementer.map((e) => e.slags)).toEqual(['blok', 'blok', 'spor'])
  })

  it('laver ikke en tom arbejdsrunde af en tanke uden værktøjskald', () => {
    const { arbejde } = opdel([tanke(3), tekst('Jeg læser filen.'), kald('read_file'), tekst('Svar.')])
    expect(opdelArbejdsrunder(arbejde).map((s) => s.slags)).toEqual(['enkelt', 'syntese', 'runde'])
  })
})
