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

// ─────────────────────────────────────────────────────────────────────────
// Serveren måler nu, klienten behøver ikke gætte (14/9-2026)
//
// `toolDiff` regner ud af kaldets ARGUMENTER, og for `write_file` stod der en
// ærlig kommentar: «KUN tilføjet. Vi ved ikke om filen fandtes; at kalde dens
// tidligere indhold for «fjernet» ville være et gæt på et tal man ikke har.»
//
// Klienten havde ret — den KUNNE ikke vide det. Men serveren kan: den har
// filen i hånden lige før den skriver. `edit_file`/`write_file` returnerer nu
// `linjer_tilfoejet` og `linjer_fjernet`, målt på det faktiske indhold.
//
// Rækkefølgen er derfor: MÅLT slår gættet. Ikke omvendt.
// ─────────────────────────────────────────────────────────────────────────

import { diffFraResultat } from './toolDiff'

describe('diffFraResultat', () => {
  it('bruger serverens målte tal', () => {
    expect(diffFraResultat('{"status":"ok","linjer_tilfoejet":12,"linjer_fjernet":4}'))
      .toEqual({ tilfoejet: 12, fjernet: 4 })
  })

  it('tager imod et objekt lige så vel som en streng', () => {
    // Desk får `result` som objekt, mobilen som (evt. ufuldstændig) JSON.
    expect(diffFraResultat({ linjer_tilfoejet: 3, linjer_fjernet: 0 }))
      .toEqual({ tilfoejet: 3, fjernet: 0 })
  })

  it('giver null når serveren ikke har målt noget', () => {
    // Et læsende værktøj har ingen tal. null, ikke {0,0}: «ingenting at vise»
    // og «nul» er to forskellige beskeder.
    expect(diffFraResultat('{"status":"ok","text":"hej"}')).toBeNull()
  })

  it('giver null på et ufuldstændigt resultat midt i streamen', () => {
    expect(diffFraResultat('{"status":"ok","linjer_til')).toBeNull()
  })

  it('giver null på tomt og på vrøvl', () => {
    expect(diffFraResultat('')).toBeNull()
    expect(diffFraResultat(undefined)).toBeNull()
    expect(diffFraResultat('ikke json')).toBeNull()
  })

  it('accepterer et rent nul-nul resultat som MÅLT', () => {
    // En edit der erstattede nul steder ER målt til nul. Det er ikke det
    // samme som at der ikke findes tal.
    expect(diffFraResultat('{"linjer_tilfoejet":0,"linjer_fjernet":0}'))
      .toEqual({ tilfoejet: 0, fjernet: 0 })
  })

  it('afviser tal der ikke er tal', () => {
    expect(diffFraResultat('{"linjer_tilfoejet":"tolv","linjer_fjernet":4}')).toBeNull()
  })
})

// ─────────────────────────────────────────────────────────────────────────
// Argumenterne kommer som en STRENG under streaming (14/9-2026)
//
// Bjoern: «+xx og -xx mangler for den runde hvor han redigeret en fil».
//
// Under streaming lander et vaerktoejs argumenter i `partialJson` — en streng
// samlet af `input_json_delta` — og IKKE i `input`. `toolDiff` kiggede kun i
// `input`, saa den saa et tomt objekt og gav null. `toolBody` i MessageList
// har hele tiden foretrukket `partialJson`; diff'en gjorde ikke.
// ─────────────────────────────────────────────────────────────────────────

describe('toolDiff med streamede argumenter', () => {
  it('parser en JSON-streng', () => {
    const s = JSON.stringify({ path: 'a.py', old_text: 'a\nb', new_text: 'x' })
    expect(toolDiff('edit_file', s)).toEqual({ tilfoejet: 1, fjernet: 2 })
  })

  it('et objekt virker stadig', () => {
    expect(toolDiff('edit_file', { old_text: 'a\nb', new_text: 'x' }))
      .toEqual({ tilfoejet: 1, fjernet: 2 })
  })

  it('en HALV streng midt i streamen giver null frem for at kaste', () => {
    // Argumenterne kommer stykvis. Indtil de er hele, er der intet at vise —
    // og en raekke der kaster ville tage hele traaden med sig.
    expect(toolDiff('edit_file', '{"path":"a.py","old_te')).toBeNull()
  })

  it('en tom streng giver null', () => {
    expect(toolDiff('edit_file', '')).toBeNull()
  })

  it('write_file virker ogsaa fra en streng', () => {
    expect(toolDiff('write_file', JSON.stringify({ content: 'en\nto\ntre' })))
      .toEqual({ tilfoejet: 3, fjernet: 0 })
  })

  it('multi_edit virker ogsaa fra en streng', () => {
    const s = JSON.stringify({ edits: [{ old_text: 'a', new_text: 'b' },
                                       { old_text: 'c\nd', new_text: 'e' }] })
    expect(toolDiff('multi_edit', s)).toEqual({ tilfoejet: 2, fjernet: 3 })
  })
})
