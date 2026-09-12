import { toolDiff } from './toolDiff'

it('edit_file taeller begge sider', () => {
  expect(toolDiff('edit_file', { old_text: 'a\nb\nc', new_text: 'a\nx' }))
    .toEqual({ tilfoejet: 2, fjernet: 3 })
})

it('operator-varianten regnes ens', () => {
  // Samme vaerktoej, anden maskine. Praefikset maa ikke give to svar.
  expect(toolDiff('operator_edit_file', { old_text: 'a', new_text: 'b\nc' }))
    .toEqual({ tilfoejet: 2, fjernet: 1 })
})

it('en SLETNING er -N +0, ikke +1', () => {
  // Tom streng er nul linjer. «+1» ville vaere en linje der ikke findes.
  expect(toolDiff('edit_file', { old_text: 'a\nb', new_text: '' }))
    .toEqual({ tilfoejet: 0, fjernet: 2 })
})

it('afsluttende linjeskift taeller ikke som en ekstra linje', () => {
  expect(toolDiff('edit_file', { old_text: 'a\nb\n', new_text: 'a\n' }))
    .toEqual({ tilfoejet: 1, fjernet: 2 })
})

it('multi_edit laegger sine dele sammen — baade edits og items', () => {
  const e = [{ old_text: 'a', new_text: 'b\nc' }, { old_text: 'x\ny', new_text: 'z' }]
  expect(toolDiff('multi_edit', { edits: e })).toEqual({ tilfoejet: 3, fjernet: 3 })
  expect(toolDiff('operator_multi_edit', { items: e })).toEqual({ tilfoejet: 3, fjernet: 3 })
})

it('write_file siger kun hvad der blev SKREVET', () => {
  // Vi ved ikke om filen fandtes; at kalde dens tidligere indhold «fjernet»
  // ville vaere et gaet paa et tal man ikke har.
  expect(toolDiff('write_file', { content: 'a\nb\nc' }))
    .toEqual({ tilfoejet: 3, fjernet: 0 })
})

it('et vaerktoej der ikke redigerer giver NULL, ikke nul', () => {
  // Saa staar raekken uden tal frem for med et opdigtet nul.
  expect(toolDiff('bash', { command: 'ls' })).toBeNull()
  expect(toolDiff('read_file', { path: '/x' })).toBeNull()
})

it('manglende eller forkerte argumenter giver null frem for at braekke', () => {
  expect(toolDiff('edit_file', null)).toBeNull()
  expect(toolDiff('edit_file', { old_text: 42 })).toBeNull()
  expect(toolDiff('multi_edit', { edits: 'ikke et array' })).toBeNull()
  expect(toolDiff('multi_edit', { edits: [{ path: '/x' }] })).toBeNull()
})
