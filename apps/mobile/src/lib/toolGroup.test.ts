import { countFromResult, summarizeRound, type ToolItem } from './toolGroup'

const it_ = (over: Partial<ToolItem> = {}): ToolItem => ({
  label: 'Læste USER.md',
  running: false,
  tool: 'read_file',
  ...over
})

describe('én linje pr. runde', () => {
  it('ét kald beholder sin egen beskrivelse', () => {
    expect(summarizeRound([it_()])).toBe('Læste USER.md')
  })

  it('flere ENS kald tælles op', () => {
    expect(summarizeRound([it_(), it_(), it_()])).toBe('Læste 3 filer')
  })

  it('ental bøjes rigtigt', () => {
    expect(summarizeRound([it_({ tool: 'bash' }), it_({ tool: 'bash' })])).toBe('Kørte 2 kommandoer')
  })

  it('flere FORSKELLIGE kald bliver til «værktøjer»', () => {
    expect(summarizeRound([it_({ tool: 'read_file' }), it_({ tool: 'bash' })])).toBe('Kørte 2 værktøjer')
  })

  it('nutid mens runden kører', () => {
    expect(summarizeRound([it_({ running: true }), it_()])).toBe('Læser 2 filer…')
  })

  it('resultatets egen optælling vinder over antal kald', () => {
    // «Ændrede 16 filer» siger mere end «Kørte 2 værktøjer».
    const s = summarizeRound([
      it_({ tool: 'edit_file', count: 9 }),
      it_({ tool: 'edit_file', count: 7 })
    ])
    expect(s).toBe('Redigerede 16 filer')
  })

  it('tom runde giver tom linje', () => {
    expect(summarizeRound([])).toBe('')
  })
})

describe('optælling læses ud af resultatet — vi gætter ikke', () => {
  it('finder tallet når det står der', () => {
    expect(countFromResult('16 filer ændret')).toBe(16)
    expect(countFromResult('changed 4 files')).toBe(4)
    expect(countFromResult('7 matches')).toBe(7)
  })

  it('returnerer undefined når der intet tal er', () => {
    expect(countFromResult('ok')).toBeUndefined()
    expect(countFromResult('')).toBeUndefined()
  })

  it('nul tæller ikke som en optælling', () => {
    expect(countFromResult('0 filer')).toBeUndefined()
  })
})
