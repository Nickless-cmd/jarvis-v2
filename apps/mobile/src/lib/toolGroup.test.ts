import { countFromResult, summarizeRound, summerDiff, type ToolItem } from './toolGroup'

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

  it('flere FORSKELLIGE kald bliver til ét led PR. VÆRKTØJ', () => {
    // 14/9: linjen sagde «Kørte 2 værktøjer» — en optælling af hvor mange
    // funktionskald der var, hvilket ikke interesserer nogen. Hvad der SKETE
    // stod der ikke. Den gamle forventning står her som det den var: den
    // fattigste mulige beskrivelse af en tur.
    expect(summarizeRound([it_({ tool: 'read_file' }), it_({ tool: 'bash' })]))
      .toBe('Læste en fil, kørte en kommando')
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

// ── linjetal for hele runden ───────────────────────────────────────────────

const med = (t: number, f: number) => it_({ diff: { tilfoejet: t, fjernet: f } })

it('summen laegger kaldenes tal sammen', () => {
  expect(summerDiff([med(3, 1), med(10, 4)])).toEqual({ tilfoejet: 13, fjernet: 5 })
})

it('en runde UDEN redigeringer giver null — ikke +0 -0', () => {
  // «Ingenting at vise» og «nul» er to forskellige beskeder. En runde der kun
  // laeste og soegte skal staa uden tal.
  expect(summerDiff([it_(), it_()])).toBeNull()
})

it('kald uden diff springes over frem for at taelle som nul', () => {
  expect(summerDiff([it_(), med(2, 0), it_()])).toEqual({ tilfoejet: 2, fjernet: 0 })
})

it('en tom runde giver null', () => {
  expect(summerDiff([])).toBeNull()
})

// ─────────────────────────────────────────────────────────────────────────
// En blandet runde sagde ingenting (14/9-2026)
//
// Bjørn vil have Claude Codes linje: «ran a command, edited 3 files +12 −4».
// Huset havde allerede rundelinjen — men for en BLANDET runde sagde den
// «Kørte 5 værktøjer». Det er en optælling af noget der ikke interesserer
// nogen: hvor mange funktionskald der var. Hvad der SKETE stod der ikke.
//
// Nu grupperes runden pr. værktøj og bliver til led: «Kørte en kommando,
// redigerede 3 filer». Rækkefølgen er den kaldene skete i — det er
// fortællingen om turen, og en sortering ville bytte om på årsag og virkning.
// ─────────────────────────────────────────────────────────────────────────

const kald = (tool: string, label = 'x', running = false): ToolItem =>
  ({ label, tool, running }) as ToolItem

describe('summarizeRound — blandede runder', () => {
  it('samler pr. vaerktoej, flest foerst (Claude Desktop sorterer)', () => {
    // «og» foer det sidste led, komma imellem — som i Bjoerns egen
    // formulering: «ran a command, edited 3 files AND restarted api».
    // Foerste udgave af den her test skrev komma ogsaa foer det sidste led;
    // det var mit eget vilkaarlige valg, ikke noget beviset stoettede.
    expect(summarizeRound([kald('bash'), kald('edit_file'), kald('edit_file')]))
      .toBe('Redigerede 2 filer, kørte en kommando')
  })

  it('kun det FOERSTE led har stort begyndelsesbogstav', () => {
    const s = summarizeRound([kald('read_file'), kald('bash')])
    expect(s).toBe('Læste en fil, kørte en kommando')
  })

  it('tre slags led bindes med komma, som i Claude Desktop', () => {
    expect(summarizeRound([kald('bash'), kald('read_file'), kald('edit_file')]))
      .toBe('Kørte en kommando, læste en fil, redigerede en fil')
  })

  it('«en» frem for «1» — det er en saetning, ikke en tabel', () => {
    expect(summarizeRound([kald('bash'), kald('edit_file')]))
      .toBe('Kørte en kommando, redigerede en fil')
  })

  it('ukendte vaerktoejer samles i «brugte et vaerktoej»', () => {
    // Uden det ville et nyt vaerktoej forsvinde ud af saetningen, og linjen
    // ville lyve om hvad turen gjorde.
    expect(summarizeRound([kald('bash'), kald('et_nyt_vaerktoej')]))
      .toBe('Kørte en kommando, brugte et værktøj')
  })

  it('en runde der stadig koerer slutter med prikker', () => {
    expect(summarizeRound([kald('bash', 'x', true), kald('edit_file')]))
      .toMatch(/…$/)
  })

  it('en runde der koerer bruger NUTID', () => {
    expect(summarizeRound([kald('bash', 'x', true), kald('edit_file', 'x', true)]))
      .toBe('Kører en kommando, redigerer en fil…')
  })

  it('ensartede runder er UROERTE', () => {
    // Den gren virkede allerede. En aendring her ville vaere en regression
    // forklaedt som en forbedring.
    expect(summarizeRound([kald('edit_file'), kald('edit_file'), kald('edit_file')]))
      .toBe('Redigerede 3 filer')
  })

  it('ét kald er stadig sin egen beskrivelse', () => {
    expect(summarizeRound([kald('bash', 'Kørte agent.ts')])).toBe('Kørte agent.ts')
  })
})

describe('operator_-varianter er samme handling', () => {
  it('bash og operator_bash tælles sammen — ikke «og kørte en ting»', () => {
    const items = [
      { label: 'Kørte git status', running: false, tool: 'bash' },
      { label: 'Kørte ls', running: false, tool: 'bash' },
      { label: 'Kørte df', running: false, tool: 'operator_bash' },
    ]
    expect(summarizeRound(items)).toBe('Kørte 3 kommandoer')
  })
})

// Bjørn 19/9-2026: «Kørte en ting?» — hans runde var bash, get_weather, bash.
describe('Claude Desktops blandede runde', () => {
  const it_ = (tool: string) => ({ label: tool, running: false, tool })
  it('skærmbilledets runde', () => {
    expect(summarizeRound([it_('bash'), it_('get_weather'), it_('bash')])).toBe('Kørte 2 kommandoer, brugte et værktøj')
  })
  it('flere ukendte samles i ét led', () => {
    expect(summarizeRound([it_('operator_read_file'), it_('read_model_config'), it_('daemon_status'), it_('bash')]))
      .toBe('Brugte 2 værktøjer, læste en fil, kørte en kommando')
  })
  it('kun ukendte af samme slags', () => {
    expect(summarizeRound([it_('get_weather'), it_('get_weather')])).toBe('Brugte 2 værktøjer')
  })
  it('flere end tre led: to plus resten', () => {
    expect(summarizeRound([it_('bash'), it_('bash'), it_('read_file'), it_('edit_file'), it_('write_file'), it_('x')]))
      .toBe('Kørte 2 kommandoer, læste en fil og 3 værktøjer mere')
  })
})
