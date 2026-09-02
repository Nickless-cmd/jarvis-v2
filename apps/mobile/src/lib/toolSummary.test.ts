import { describeTool, describeToolResult, subjectFromArgs } from './toolSummary'

describe('emnet trækkes ud af argumenterne', () => {
  it('finder stien og viser kun filnavnet', () => {
    expect(subjectFromArgs('{"path":"/media/projects/jarvis-v2/core/db.py"}')).toBe('db.py')
  })

  it('finder kommandoen', () => {
    expect(subjectFromArgs('{"command":"df -h /"}')).toBe('df -h /')
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
