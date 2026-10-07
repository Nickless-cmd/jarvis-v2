import { arbejdslinjeTekst, kortTokens } from './arbejdslinje'

/**
 * Arbejdslinjens sætning. Hver test er mutationsprøvet — se `MUT`-noterne:
 * den adfærd testen påstår at måle er slået fra, og testen er set fejle.
 */
describe('arbejdslinjeTekst', () => {
  it('bygger sætningen i Jarvis stemme — ikke serverens label', () => {
    // MUT: returnér `detail` uændret → fanger.
    expect(arbejdslinjeTekst('Læser fil: useChatScroll.ts', 'read_file'))
      .toBe('Læser useChatScroll.ts')
  })

  it('dropper labelens «fil» — genstanden siger det allerede', () => {
    // MUT: brug `detail` som genstand → giver «Læser Læser fil: …» → fanger.
    expect(arbejdslinjeTekst('Læser fil: visible_tool_labels.py', 'read_file'))
      .not.toContain('fil:')
  })

  it('bash får sit eget verbum, og emnet er allerede renset af serveren', () => {
    // `_bash_hint` springer «cd …» over; vi arver det og sætter kun verbet.
    // MUT: map bash til «Bash» → fanger.
    expect(arbejdslinjeTekst('Bash: npm test', 'bash')).toBe('Kører npm test')
  })

  it('operator_-præfikset skrælles af, så samme værktøj lyder ens', () => {
    // MUT: fjern grundNavn → «operator_read_file» rammer ingen post → fanger.
    expect(arbejdslinjeTekst('Læser fil: MessageList.tsx', 'operator_read_file'))
      .toBe('Læser MessageList.tsx')
  })

  it('et ukendt værktøj står UÆNDRET — vi viser aldrig mindre end i dag', () => {
    // MUT: returnér null for ukendte → linjen forsvinder for ~350 værktøjer.
    expect(arbejdslinjeTekst('Noget nyt: emnet', 'helt_nyt_vaerktoej'))
      .toBe('Noget nyt: emnet')
  })

  it('et verbum uden genstand står alene — ikke «Læser » med hale', () => {
    // MUT: fjern emne-guarden → «Læser » med efterfølgende mellemrum → fanger.
    expect(arbejdslinjeTekst('Læser fil', 'read_file')).toBe('Læser')
  })

  it('hele sætninger uden genstand bruges som de er', () => {
    // Forlægget var `convene_council` — fjernet 7/10-2026. Reglen er den samme:
    // et værktøj i UDEN_GENSTAND må ikke få detailens genstand klistret bagpå.
    // MUT: flyt read_dreams til MED_GENSTAND → «Læser drømmene drømmene» → fanger.
    expect(arbejdslinjeTekst('Læser drømme: noget', 'read_dreams'))
      .toBe('Læser drømmene')
  })

  it('tom eller manglende workingStep tegner intet', () => {
    // MUT: fjern tom-guarden → tom streng vises som en bar linje → fanger.
    expect(arbejdslinjeTekst(null, 'read_file')).toBeNull()
    expect(arbejdslinjeTekst('', 'read_file')).toBeNull()
    expect(arbejdslinjeTekst('   ', 'read_file')).toBeNull()
  })

  it('manglende action falder tilbage til serverens label', () => {
    // Reduceren sætter action for ægte skridt; gør den ikke, står labelen.
    // MUT: antag action altid findes → crash/undefined i strengen → fanger.
    expect(arbejdslinjeTekst('Læser fil: x.ts', null)).toBe('Læser fil: x.ts')
    expect(arbejdslinjeTekst('Læser fil: x.ts')).toBe('Læser fil: x.ts')
  })

  it('en label uden kolon giver verbet alene', () => {
    // MUT: antag at ': ' altid findes → slice(-1) giver skrald → fanger.
    expect(arbejdslinjeTekst('Bash', 'bash')).toBe('Kører')
  })

  it('todo_set får en læsbar sætning hvor serveren har en rå label', () => {
    // Serveren har ingen post for todo_set, så `_reserveetiket` giver
    // «Todo set: 3 opgaver». Her bliver den «Sætter 3 opgaver».
    // MUT: fjern todo_set fra MED_GENSTAND → «Todo set: 3 opgaver» → fanger.
    expect(arbejdslinjeTekst('Todo set: 3 opgaver', 'todo_set')).toBe('Sætter 3 opgaver')
  })
})

describe('kortTokens', () => {
  it('forkorter over tusind — «1.2k», som desk', () => {
    // Desk's regel, ord for ord (`LivenessIndicator.tsx`). MUT: fjern
    // forkortelsen → «45200 tokens» fylder linjen → fanger.
    expect(kortTokens(1234)).toBe('1.2k')
    expect(kortTokens(45200)).toBe('45.2k')
  })

  it('lader tal under tusind stå som de er', () => {
    expect(kortTokens(0)).toBe('0')
    expect(kortTokens(999)).toBe('999')
  })
})
