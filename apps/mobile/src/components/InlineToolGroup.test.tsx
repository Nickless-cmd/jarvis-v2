import { act, fireEvent, render } from '@testing-library/react-native'
import { InlineToolGroup, SVAR_KLIP } from './InlineToolGroup'
import type { ToolItem } from '../lib/toolGroup'

const item = (over: Partial<ToolItem> = {}): ToolItem => ({
  label: 'Læste USER.md',
  running: false,
  tool: 'read_file',
  ...over
})

/** Flad liste af testID'er og tekst i render-træets rækkefølge (oppefra og ned). */
const orden = (node: unknown, ud: string[] = []): string[] => {
  if (node == null) return ud
  // Teksten ligger som streng-noder i `toJSON()`-træet — ikke i `children`
  // som en streng, men som sit eget element. Uden denne gren fanges labels
  // som «Læste a.py» aldrig, og en rækkefølge-assertion måler mod -1.
  if (typeof node === 'string') { ud.push(node); return ud }
  if (Array.isArray(node)) { node.forEach((n) => orden(n, ud)); return ud }
  const n = node as { props?: Record<string, unknown>; children?: unknown }
  const p = n.props ?? {}
  if (typeof p.testID === 'string') ud.push(p.testID)
  orden(n.children, ud)
  return ud
}

it('viser ÉN linje for hele runden — ikke én pr. kald', async () => {
  const s = await render(<InlineToolGroup items={[item(), item(), item()]} />)
  expect(s.getByText('Læste 3 filer')).toBeTruthy()
  // Detaljen er der, men den fylder ikke tråden før man beder om den.
  expect(s.queryByTestId('tool-group-details')).toBeNull()
})

it('folder ud og viser hvert enkelt kald', async () => {
  const s = await render(
    <InlineToolGroup items={[item({ label: 'Læste a.py' }), item({ label: 'Læste b.py' })]} />
  )
  await fireEvent.press(s.getByTestId('tool-group'))
  expect(s.getByTestId('tool-group-details')).toBeTruthy()
  expect(s.getByText('Læste a.py')).toBeTruthy()
  expect(s.getByText('Læste b.py')).toBeTruthy()
})

it('ét kald har ingen chevron — den ville være et tomt løfte', async () => {
  const s = await render(<InlineToolGroup items={[item()]} />)
  expect(s.queryByTestId('icon-ChevronRight')).toBeNull()
  await fireEvent.press(s.getByTestId('tool-group'))
  expect(s.queryByTestId('tool-group-details')).toBeNull()
})

/**
 * Runden kan foldes ud når den bærer en TANKE — ikke kun når den har flere kald
 * (Bjørn 29/9-2026: «tænke-linjen ind i runde-linjen efter foldet.. det er det
 * tætteste på chatview I desk»).
 *
 * Desk lægger tænke-blokken inde i `rv-arbejdsdetaljer`
 * (`RaekkeTranskript.tsx:324`). Uden denne udvidelse ville tanken ikke kunne
 * nås: runden har ét kald, `expandable` var falsk, og chevronen ville ikke
 * være der at trykke på. Testen ovenfor skal stadig holde — et kald UDEN en
 * tanke har fortsat intet at folde ud.
 */
it('en runde med ÉT kald men en tanke kan foldes ud — og viser tanken', async () => {
  const s = await render(
    <InlineToolGroup items={[item()]} tanker={[{ key: 't1', text: 'jeg overvejer', seconds: 4 }]} />
  )
  expect(s.getByTestId('tool-status-caret')).toBeTruthy()
  expect(s.queryByTestId('tool-group-details')).toBeNull()
  await fireEvent.press(s.getByTestId('tool-group'))
  expect(s.getByTestId('tool-group-details')).toBeTruthy()
  expect(s.getByTestId('thinking-summary')).toBeTruthy()
  expect(s.getByText('Tænkte i 4s')).toBeTruthy()
})

it('tanken ligger ØVERST i folden — værktøjskaldene under den', async () => {
  // Desk tegner elementerne i den rækkefølge de skete: tanken kom før kaldene.
  const s = await render(
    <InlineToolGroup
      items={[item({ label: 'Læste a.py' }), item({ label: 'Læste b.py' })]}
      tanker={[{ key: 't1', text: 'jeg overvejer', seconds: 4 }]}
    />
  )
  await fireEvent.press(s.getByTestId('tool-group'))
  const r = orden(s.toJSON())
  expect(r.indexOf('thinking-summary')).toBeGreaterThan(-1)
  expect(r.indexOf('thinking-summary')).toBeLessThan(r.indexOf('Læste a.py'))
})

it('tanken staar paa SIN PLADS — efter det kald den kom efter', async () => {
  // Blokkene kommer i raekkefoelgen `thinking, text, tool_use` (maalt 30/9-2026
  // i besked 153522). Tanken der hoerer til et kald staar derfor EFTER det i
  // folden — ikke samlet overst. Desk tegner elementerne i den raekkefoelge de
  // skete (`RaekkeTranskript`), og `foerKald` baerer positionen.
  const s = await render(
    <InlineToolGroup
      items={[item({ label: 'Læste a.py' }), item({ label: 'Læste b.py' })]}
      tanker={[{ key: 't1', text: 'så ser jeg på det', seconds: 4, foerKald: 1 }]}
    />
  )
  await fireEvent.press(s.getByTestId('tool-group'))
  const r = orden(s.toJSON())
  expect(r.indexOf('Læste a.py')).toBeLessThan(r.indexOf('thinking-summary'))
  expect(r.indexOf('thinking-summary')).toBeLessThan(r.indexOf('Læste b.py'))
})

it('en tanke EFTER det sidste kald staar til sidst i folden', async () => {
  const s = await render(
    <InlineToolGroup
      items={[item({ label: 'Læste a.py' })]}
      tanker={[{ key: 't1', text: 'til sidst konkluderer jeg', seconds: 5, foerKald: 1 }]}
    />
  )
  await fireEvent.press(s.getByTestId('tool-group'))
  const r = orden(s.toJSON())
  expect(r.indexOf('Læste a.py')).toBeLessThan(r.indexOf('thinking-summary'))
})

it('linjen er i nutid mens runden kører — og prikkerne ruller i stedet for «…»', async () => {
  // Som desk og Claude Desktop: prikkerne er tre bevægelige prikker, ikke tegn
  // i teksten, så en ellipse i enden ville stå dobbelt.
  const s = await render(<InlineToolGroup items={[item({ running: true }), item()]} />)
  expect(s.getByText('Læser 2 filer')).toBeTruthy()
  // Skjult for skærmlæsere med vilje (kildens aria-hidden).
  expect(s.getByTestId('prikker', { includeHiddenElements: true })).toBeTruthy()
})

it('prikkerne forsvinder og caret\'en står fremme når runden er færdig', async () => {
  const s = await render(<InlineToolGroup items={[item(), item()]} />)
  expect(s.queryByTestId('prikker', { includeHiddenElements: true })).toBeNull()
  expect(s.getByTestId('tool-status-caret')).toBeTruthy()
})

it('</> står fast — også når runden er færdig (Bjørn 19/9-2026)', async () => {
  const bredde = (s: Awaited<ReturnType<typeof render>>) => {
    const st = s.getByTestId('tool-spark').props.style
    return Object.assign({}, ...(Array.isArray(st) ? st.filter(Boolean) : [st])).width
  }
  const koer = await render(<InlineToolGroup items={[item({ running: true }), item()]} />)
  expect(bredde(koer)).toBe(20)
  const faerdig = await render(<InlineToolGroup items={[item(), item()]} />)
  expect(bredde(faerdig)).toBe(20)
})

it('med fast </> ingen spark ved afslutning — ellers stod glyfen der to gange', async () => {
  const s = await render(<InlineToolGroup items={[item({ running: true }), item()]} />)
  await s.rerender(<InlineToolGroup items={[item(), item()]} />)
  expect(s.queryByTestId('ls-spark', { includeHiddenElements: true })).toBeNull()
})

it('en tom runde tegner ingenting', async () => {
  const s = await render(<InlineToolGroup items={[]} />)
  expect(s.queryByTestId('tool-group')).toBeNull()
})

it('linjetallene staar paa den FOLDEDE linje', async () => {
  // Gruppen er foldet som standard. Uden summen dér ville tallene vaere
  // usynlige det meste af tiden - og saa var de lige saa godt blevet i badgen.
  const s = await render(
    <InlineToolGroup items={[
      { label: 'Rettede a.py', running: false, tool: 'edit_file', diff: { tilfoejet: 12, fjernet: 3 } },
      { label: 'Rettede b.py', running: false, tool: 'edit_file', diff: { tilfoejet: 1, fjernet: 0 } },
    ]} />,
  )
  expect(s.getByText('+13')).toBeTruthy()
  expect(s.getByText('−3')).toBeTruthy()
})

it('en runde der kun LAESTE staar uden tal', async () => {
  const s = await render(
    <InlineToolGroup items={[{ label: 'Læste USER.md', running: false, tool: 'read_file' }]} />,
  )
  expect(s.queryByText('+0')).toBeNull()
  expect(s.queryByText('−0')).toBeNull()
})

// Claude Desktop 1:1 (19/9-2026): rundens sætning ERSTATTER den mekaniske
// tekst. Før stod den som overskrift over linjen — samme regel som desk nu.
it('rundens sætning erstatter den mekaniske tekst', async () => {
  const s = await render(<InlineToolGroup items={[item(), item(), item()]} etiket="Fandt fejlen i login" />)
  expect(s.getByText('Fandt fejlen i login')).toBeTruthy()
  expect(s.queryByText('Læste 3 filer')).toBeNull()
  expect(s.queryByTestId('tool-group-etiket')).toBeNull()
})

it('uden sætning står den mekaniske tekst', async () => {
  const s = await render(<InlineToolGroup items={[item(), item(), item()]} />)
  expect(s.getByText('Læste 3 filer')).toBeTruthy()
})

/**
 * «0s» er ikke et tal (Bjørn 29/9-2026: «0s skal væk fra tool result linjen»).
 *
 * En runde der blev færdig på under et sekund gik gennem `Math.floor(sek)` og
 * skrev «0s» ud for sit ikon. SkillLinjen vægter allerede ved ét sekund
 * (`sek >= 1` i SkillLinje.tsx:37) — det er husets eget skel; her manglede det.
 * Grænsen er ét sekund: derover vises tallet som før.
 */
it('en runde under ét sekund viser INGEN tid — ikke «0s»', async () => {
  jest.useFakeTimers()
  try {
    const s = await render(<InlineToolGroup items={[item({ running: true }), item()]} />)
    await act(async () => { jest.advanceTimersByTime(400) })
    await s.rerender(<InlineToolGroup items={[item(), item()]} />)
    expect(s.queryByTestId('runde-tid')).toBeNull()
    expect(s.queryByText('0s')).toBeNull()
  } finally {
    jest.useRealTimers()
  }
})

it('en runde over ét sekund viser tiden som før', async () => {
  jest.useFakeTimers()
  try {
    const s = await render(<InlineToolGroup items={[item({ running: true }), item()]} />)
    await act(async () => { jest.advanceTimersByTime(3000) })
    await s.rerender(<InlineToolGroup items={[item(), item()]} />)
    expect(s.getByTestId('runde-tid')).toBeTruthy()
    expect(s.getByText('3s')).toBeTruthy()
  } finally {
    jest.useRealTimers()
  }
})

/**
 * Kaldets SVAR kan foldes ud — Bjørn 30/9-2026: «Tool result linjen mangler at
 * kunne foldes ud.. og vises hvad du lavet i run».
 *
 * Før var folden en liste af ETIKETTER: «Læste USER.md» — men ikke ét ord af
 * hvad der stod i filen. Kun kald der redigerede noget havde en krop
 * (`aendring`, udledt af argumenterne), så alt andet arbejde var uigennemsigtigt.
 * Nu bærer hvert kald sit resultat, og det kan åbnes.
 */
it('et kald med et svar er LUKKET som standard — svaret fylder ikke tråden', async () => {
  const s = await render(
    <InlineToolGroup items={[item({ result: 'filens indhold her' }), item({ label: 'Læste b.py' })]} />
  )
  await fireEvent.press(s.getByTestId('tool-group'))
  expect(s.queryByTestId('svar-0')).toBeNull()
  expect(s.queryByText('filens indhold her')).toBeNull()
})

it('et tryk på kaldet folder svaret ud', async () => {
  const s = await render(
    <InlineToolGroup items={[item({ result: 'filens indhold her' }), item({ label: 'Læste b.py' })]} />
  )
  await fireEvent.press(s.getByTestId('tool-group'))
  await fireEvent.press(s.getByText('Læste USER.md'))
  expect(s.getByTestId('svar-0')).toBeTruthy()
  expect(s.getByText('filens indhold her')).toBeTruthy()
})

it('et kald UDEN svar kan ikke aabnes — der er intet at vise', async () => {
  const s = await render(<InlineToolGroup items={[item(), item()]} />)
  await fireEvent.press(s.getByTestId('tool-group'))
  expect(s.queryByTestId('svar-0')).toBeNull()
  expect(s.queryByTestId('svar-1')).toBeNull()
})

it('et redigeret kald gaar til DIFF-arket — ikke svar-folden', async () => {
  // Diff-arket er rigere end rå tekst for et redigeret kald; den vej bevares.
  const s = await render(
    <InlineToolGroup items={[
      item({ label: 'Rettede a.py', tool: 'edit_file',
             aendring: { sti: 'a.py', gammel: 'gammel', ny: 'ny' },
             result: 'File edited successfully' }),
      item({ label: 'Læste b.py' }),
    ]} />
  )
  await fireEvent.press(s.getByTestId('tool-group'))
  expect(s.getByTestId('aendring-0')).toBeTruthy()
  expect(s.queryByTestId('svar-0')).toBeNull()
})

it('et meget langt svar klippes — og det siges hoejt', async () => {
  // `fald`-familien beholder den rå vej: der er ingen form at klippe i. Har
  // kaldet en krop (bash, fil, liste), klipper KROPPEN — ikke denne gren.
  // `db_query` står i ingen tabel, og svaret her er ren tekst, så formen er
  // også `fald`. Det er præcis den gren der skal måles.
  const langt = 'x'.repeat(SVAR_KLIP + 250)
  const s = await render(
    <InlineToolGroup items={[
      item({ label: 'Forespurgte databasen', tool: 'db_query', result: langt }),
      item({ label: 'Læste b.py' }),
    ]} />
  )
  await fireEvent.press(s.getByTestId('tool-group'))
  await fireEvent.press(s.getByText('Forespurgte databasen'))
  expect(s.getByText(/afkortet \(/)).toBeTruthy()
})

it('et bash-kald faar TERMINAL-kroppen — ikke rå tekst', async () => {
  // Kernen i ændringen (Bjørn 30/9-2026: «vi har ingen form visning»): et
  // bash-kald og en fil-læsning så ens ud. Nu udtrækkes stdout af JSON-blobben
  // og tegnes som terminal.
  const s = await render(
    <InlineToolGroup items={[
      item({ label: 'Kørte npm test', tool: 'bash', result: '{"stdout": "5 passed", "exit_code": 0}' }),
      item({ label: 'Læste b.py' }),
    ]} />
  )
  await fireEvent.press(s.getByTestId('tool-group'))
  await fireEvent.press(s.getByText('Kørte npm test'))
  expect(s.getByTestId('krop-terminal')).toBeTruthy()
  expect(s.getByText('5 passed')).toBeTruthy()
})

it('en fil-laesning faar FIL-kroppen — med linjenumre', async () => {
  const s = await render(
    <InlineToolGroup items={[
      item({ label: 'Læste krop.ts', tool: 'read_file', result: '{"content": "const a = x\\nexport b"}' }),
      item({ label: 'Læste b.py' }),
    ]} />
  )
  await fireEvent.press(s.getByTestId('tool-group'))
  await fireEvent.press(s.getByText('Læste krop.ts'))
  expect(s.getByTestId('krop-fil')).toBeTruthy()
})

it('en soegning faar LISTE-kroppen — hitlisten, ikke raa JSON', async () => {
  const s = await render(
    <InlineToolGroup items={[
      item({
        label: 'Søgte i filer',
        tool: 'search',
        result: '{"results":[{"file":"a.ts","line":42,"text":"const x = 1"}]}',
      }),
      item({ label: 'Læste b.py' }),
    ]} />
  )
  await fireEvent.press(s.getByTestId('tool-group'))
  await fireEvent.press(s.getByText('Søgte i filer'))
  expect(s.getByTestId('krop-liste')).toBeTruthy()
  expect(s.getByText('a.ts:42')).toBeTruthy()
  expect(s.getByText('const x = 1')).toBeTruthy()
})

it('et kald UDEN tabel men MED liste-form faar ogsaa liste-kroppen', async () => {
  // Familien følger resultatets FORM, ikke kun navnet: en liste ER en liste,
  // uanset hvilket værktøj der sendte den. Det er den regel der løfter de
  // værktøjer ingen har skrevet en krop til.
  //
  // `titel` er ikke blandt de kendte feltnavne, så punktet vises som
  // `nøgle=værdi`. Det er med vilje: et ukendt felt skal vise SINE data, ikke
  // et opfundet ord.
  const s = await render(
    <InlineToolGroup items={[
      item({ label: 'Hentede aftaler', tool: 'list_events', result: '{"events":[{"titel":"moede"}]}' }),
      item({ label: 'Læste b.py' }),
    ]} />
  )
  await fireEvent.press(s.getByTestId('tool-group'))
  await fireEvent.press(s.getByText('Hentede aftaler'))
  expect(s.getByTestId('krop-liste')).toBeTruthy()
  expect(s.getByText('titel=moede')).toBeTruthy()
})

it('et liste-kald hvis svar IKKE er en liste falder til RAA tekst — ikke en tom ramme', async () => {
  // Vagt mod den fejl testen «et meget langt svar klippes» fandt: familien er
  // `liste`, men der er intet at tegne. Uden `kanTegneKrop` forsvandt indholdet.
  const s = await render(
    <InlineToolGroup items={[
      item({ label: 'Forespurgte Centralen', tool: 'central_query', result: 'alt er i orden' }),
      item({ label: 'Læste b.py' }),
    ]} />
  )
  await fireEvent.press(s.getByTestId('tool-group'))
  await fireEvent.press(s.getByText('Forespurgte Centralen'))
  expect(s.queryByTestId('krop-liste')).toBeNull()
  expect(s.getByText('alt er i orden')).toBeTruthy()
})

it('et ukendt vaerktoej beholder den RAA form — vi gaetter ikke en krop', async () => {
  const s = await render(
    <InlineToolGroup items={[
      item({ label: 'Forespurgte databasen', tool: 'central_query', result: 'svar-teksten' }),
      item({ label: 'Læste b.py' }),
    ]} />
  )
  await fireEvent.press(s.getByTestId('tool-group'))
  await fireEvent.press(s.getByText('Forespurgte databasen'))
  expect(s.queryByTestId('krop-terminal')).toBeNull()
  expect(s.queryByTestId('krop-fil')).toBeNull()
  expect(s.getByTestId('svar-0')).toBeTruthy()
})

it('svaret staar UNDER kaldets etiket — ikke i stedet for den', async () => {
  const s = await render(
    <InlineToolGroup items={[item({ result: 'svar-teksten' }), item({ label: 'Læste b.py' })]} />
  )
  await fireEvent.press(s.getByTestId('tool-group'))
  await fireEvent.press(s.getByText('Læste USER.md'))
  const r = orden(s.toJSON())
  expect(r.indexOf('Læste USER.md')).toBeGreaterThan(-1)
  expect(r.indexOf('Læste USER.md')).toBeLessThan(r.indexOf('svar-0'))
})

it('et redigeret kald faar INGEN svar-chevron — kun diff-vejen', async () => {
  // Uden denne vagt kunne et redigeret kald baere BAADE en diff-knap og en
  // svar-fold: to doere til samme kald, hvor den ene aabner et tomt svar.
  // Maalt paa chevrons, fordi svar-rammen er lukket som standard og derfor
  // ikke kan skelne de to.
  const s = await render(
    <InlineToolGroup items={[
      item({ label: 'Rettede a.py', tool: 'edit_file',
             aendring: { sti: 'a.py', gammel: 'g', ny: 'n' }, result: 'ok' }),
      item({ label: 'Læste b.py' }),
    ]} />
  )
  await fireEvent.press(s.getByTestId('tool-group'))
  // Kun runde-caret'en. Havde det redigerede kald ogsaa en svar-chevron,
  // stod der to.
  expect(s.queryAllByTestId('icon-ChevronDown').length).toBe(1)
})

describe('folden — de ni nye former', () => {
  it('et minde-kald faar MIND-kroppen, bygget af argumenterne', async () => {
    // `remember_this` svarer kun `{id}`. Uden argumenterne stod raekken med
    // `id brn_…` — beviset i stedet for det der blev skrevet.
    const s = await render(<InlineToolGroup items={[
      item({
        label: 'Skrev et minde', tool: 'remember_this', result: '{"id":"brn_1"}',
        input: '{"title":"Fundet","content":"En linje"}',
      }),
      item({ label: 'Læste b.py' }),
    ]} />)
    await fireEvent.press(s.getByTestId('tool-group'))
    await fireEvent.press(s.getByText('Skrev et minde'))
    expect(s.getByTestId('krop-minde')).toBeTruthy()
    expect(s.getByText('Fundet')).toBeTruthy()
  })

  it('et soegekald med traef-liste faar WEB-kroppen', async () => {
    const s = await render(<InlineToolGroup items={[
      item({
        label: 'Soegte paa nettet', tool: 'web_search',
        result: '{"results":[{"url":"https://a.dk","title":"En side"}]}',
      }),
      item({ label: 'Læste b.py' }),
    ]} />)
    await fireEvent.press(s.getByTestId('tool-group'))
    await fireEvent.press(s.getByText('Soegte paa nettet'))
    expect(s.getByTestId('krop-web')).toBeTruthy()
    expect(s.getByText('En side')).toBeTruthy()
  })

  it('en opgaveliste faar OPGAVE-kroppen — ikke en almindelig liste', async () => {
    const s = await render(<InlineToolGroup items={[
      item({
        label: 'Satte opgaver', tool: 'todo_set',
        result: '{"count":2,"todos":[{"content":"a","status":"completed"},{"content":"b","status":"in_progress"}]}',
      }),
      item({ label: 'Læste b.py' }),
    ]} />)
    await fireEvent.press(s.getByTestId('tool-group'))
    await fireEvent.press(s.getByText('Satte opgaver'))
    expect(s.getByTestId('krop-opgave')).toBeTruthy()
    expect(s.getByText(/1 af 2/)).toBeTruthy()
  })

  it('et afvist kald faar FEJL-kroppen — ikke sin tomme form', async () => {
    // Et afvist bash-kald ville ellers vise sin tomme stdout og et exit-tal,
    // som om det var koert.
    const s = await render(<InlineToolGroup items={[
      item({
        label: 'Kørte noget', tool: 'bash',
        result: '{"status":"approval_needed","error":"Afventer godkendelse"}',
      }),
      item({ label: 'Læste b.py' }),
    ]} />)
    await fireEvent.press(s.getByTestId('tool-group'))
    await fireEvent.press(s.getByText('Kørte noget'))
    expect(s.getByTestId('krop-fejl')).toBeTruthy()
    expect(s.getByText('Afventer godkendelse')).toBeTruthy()
  })

  it('et spoergsmaal viser baade spoergsmaalet og svaret', async () => {
    const s = await render(<InlineToolGroup items={[
      item({
        label: 'Spurgte', tool: 'pause_and_ask',
        result: '{"answer":"Den anden"}', input: '{"question":"Hvilken?"}',
      }),
      item({ label: 'Læste b.py' }),
    ]} />)
    await fireEvent.press(s.getByTestId('tool-group'))
    await fireEvent.press(s.getByText('Spurgte'))
    expect(s.getByTestId('krop-spoergsmaal')).toBeTruthy()
    expect(s.getByText('Hvilken?')).toBeTruthy()
    expect(s.getByText('Den anden')).toBeTruthy()
  })
})
