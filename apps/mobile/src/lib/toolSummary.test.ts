import { describeTool, describeToolResult, subjectFromArgs } from './toolSummary'

describe('emnet trækkes ud af argumenterne', () => {
  it('finder stien og viser kun filnavnet', () => {
    expect(subjectFromArgs('{"path":"/media/projects/jarvis-v2/core/db.py"}')).toBe('db.py')
  })

  it('finder kommandoen', () => {
    expect(subjectFromArgs('{"command":"df -h /"}')).toBe('df')  // som desk: `/` er ingen genstand
  })

  it('virker MENS argumenterne streamer og JSON er ufuldstændig', () => {
    // Uden dette ville linjen stå tom netop mens den er mest interessant.
    expect(subjectFromArgs('{"file_path":"core/services/visible_runs.py')).toBe('visible_runs.py')
  })

  it('klipper meget lange værdier', () => {
    const s = subjectFromArgs(JSON.stringify({ query: 'x'.repeat(200) }))
    expect(s.length).toBeLessThanOrEqual(48)
    expect(s.endsWith('…')).toBe(true)
  })

  it('tomme argumenter giver intet emne — vi finder ikke på noget', () => {
    expect(subjectFromArgs('')).toBe('')
    expect(subjectFromArgs('{}')).toBe('')
  })
})

describe('linjen fortæller hvad han laver', () => {
  it('nutid mens det kører, datid når det er færdigt', () => {
    expect(describeTool('edit_file', '{"path":"a/b/prompt_contract.py"}', true))
      .toBe('Redigerer prompt_contract.py…')
    expect(describeTool('edit_file', '{"path":"a/b/prompt_contract.py"}', false))
      .toBe('Redigerede prompt_contract.py')
  })

  it('bash viser selve kommandoen', () => {
    expect(describeTool('bash', '{"command":"git status"}', false)).toBe('Kørte git status')
  })

  it('ukendt værktøj får et neutralt verbum frem for et gæt', () => {
    expect(describeTool('noget_nyt', '{"path":"x.py"}', false)).toBe('Kørte x.py')
  })

  it('uden emne nævnes værktøjet — aldrig en tom linje', () => {
    expect(describeTool('bash', '', true)).toBe('Kører bash…')
  })
})

describe('persisterede resultater', () => {
  it('læser værktøjsnavnet ud af markøren', () => {
    expect(describeToolResult('[tool_result:abc] [bash]: hej')).toBe('Kørte bash')
    expect(describeToolResult('[tool_result:abc] [read_file]: ...')).toBe('Læste read_file')
  })

  it('ukendt form giver en ærlig, neutral linje', () => {
    expect(describeToolResult('ingen markør her')).toBe('Brugte et værktøj')
  })
})

// Bjørn 19/9-2026, skærmbillede fra telefonen: «Kørte cd /media/projects/…»,
// «Kørte jarvis-test.txt» og «Kørte 2 kommandoer og kørte en ting» — hvor desk
// skrev hvad der faktisk skete. Argumenterne er målt i den tråd.
describe('samme ord som desk', () => {
  it('en kommando siger sin handling, ikke sit mappeskift', () => {
    expect(describeTool('bash', JSON.stringify({ command: 'cd /media/projects/jarvis-v2/apps/mobile && (npx jest src/components)' }), false))
      .toBe('Kørte npx jest')
  })

  it('også mens argumenterne stadig strømmer ind', () => {
    expect(describeTool('bash', '{"command":"cd /media/projects/jarvis-v2 && git status', true)).toBe('Kører git status…')
  })

  it('operator_-værktøjer får deres rigtige verbum', () => {
    expect(describeTool('operator_read_file', JSON.stringify({ path: '/home/bs/test-jarvis-bro/jarvis-test.txt' }), false))
      .toBe('Læste jarvis-test.txt')
    expect(describeTool('operator_bash', JSON.stringify({ command: 'echo "=== hvor er jeg ==="; hostname' }), false))
      .toBe('Kørte echo ===')
  })
})

// Bjørn 19/9-2026 sagde ja: Jarvis skriver linjen selv i `description`,
// som Claude Desktop tegner Bash-kaldets egen beskrivelse.
describe('Jarvis\' egen beskrivelse', () => {
  it('står som linjen — uændret, både mens den kører og bagefter', () => {
    const a = JSON.stringify({ command: 'git status', description: 'Vis arbejdstræets status' })
    expect(describeTool('bash', a, true)).toBe('Vis arbejdstræets status')
    expect(describeTool('operator_bash', a, false)).toBe('Vis arbejdstræets status')
  })
  it('tæller først når feltet er lukket i strømmen', () => {
    expect(describeTool('bash', '{"command":"git status","description":"Vis arbe', true)).toBe('Kører git status…')
    expect(describeTool('bash', '{"command":"git status","description":"Vis status"', true)).toBe('Vis status')
  })
  it('bare kommandoen igen, eller flere linjer, falder tilbage', () => {
    expect(describeTool('bash', JSON.stringify({ command: 'git status', description: 'git status' }), false)).toBe('Kørte git status')
    expect(describeTool('bash', JSON.stringify({ command: 'ls', description: 'a\nb' }), false)).toBe('Kørte ls')
  })
  it('kun kommando-værktøjerne', () => {
    expect(describeTool('read_file', JSON.stringify({ path: '/a.py', description: 'Noget' }), false)).toBe('Læste a.py')
  })
})
