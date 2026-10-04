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

it('runde-linjen har hverken prikker eller klokke mens den kører — de er flyttet', async () => {
  // Bjørn 30/9-2026: de tre prikker og min/sec-tælleren sad i runde-linjen, men
  // runden slukkes undervejs mens arbejdet fortsætter. Begge hører derfor til
  // arbejdslinjen nederst nu (se `Arbejdslinje.test.tsx`), og her skal de ikke
  // længere findes — hverken mens runden kører eller efter.
  const s = await render(<InlineToolGroup items={[item({ running: true }), item()]} />)
  expect(s.getByText('Læser 2 filer')).toBeTruthy()
  expect(s.queryByTestId('prikker', { includeHiddenElements: true })).toBeNull()
  expect(s.queryByTestId('runde-tid')).toBeNull()
})

it('caret\'en kommer FOERST når runden er færdig — mens den kører er der ingen', async () => {
  // Prikkerne delte cellen med caret'en. Da de flyttede, stod cellen tom mens
  // runden kørte — og et tomt løfte er værre end ingen dør: chevronen vises
  // nu kun når der faktisk ER noget at folde ud.
  const kører = await render(<InlineToolGroup items={[item({ running: true }), item()]} />)
  expect(kører.queryByTestId('tool-status-caret')).toBeNull()
  const færdig = await render(<InlineToolGroup items={[item(), item()]} />)
  expect(færdig.getByTestId('tool-status-caret')).toBeTruthy()
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
 * Klokken er flyttet til arbejdslinjen (Bjørn 30/9-2026).
 *
 * Runde-linjen bar sin egen min/sec-tæller. Men runden er kort og slukkes
 * undervejs, mens arbejdet fortsætter — så et tal der forsvinder midt i
 * arbejdet er værre end ingen tal. Tælleren bor nu i arbejdslinjen nederst i
 * beskeden, sammen med prikkerne og token-tallet (`Arbejdslinje.test.tsx`).
 *
 * Her skal derfor INTET tal stå — hverken mens runden kører eller efter.
 * «0s»-reglen er væk med den: den fandtes kun fordi klokken stod her.
 */
it('runde-linjen viser INGEN tid — klokken er flyttet til arbejdslinjen', async () => {
  jest.useFakeTimers()
  try {
    const s = await render(<InlineToolGroup items={[item({ running: true }), item()]} />)
    await act(async () => { jest.advanceTimersByTime(3000) })
    await s.rerender(<InlineToolGroup items={[item(), item()]} />)
    expect(s.queryByTestId('runde-tid')).toBeNull()
    expect(s.queryByText('3s')).toBeNull()
    expect(s.queryByText('0s')).toBeNull()
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

type Knude = { props?: Record<string, unknown>; children?: unknown }

/** Vejen fra roden ned til knuden med det givne testID — foraeldrene foerst,
 *  knuden selv sidst. */
const vejTil = (node: unknown, id: string, vej: Knude[] = []): Knude[] | null => {
  if (node == null || typeof node === 'string') return null
  if (Array.isArray(node)) {
    for (const n of node) { const f = vejTil(n, id, vej); if (f) return f }
    return null
  }
  const n = node as Knude
  const her = [...vej, n]
  if (n.props?.testID === id) return her
  return vejTil(n.children, id, her)
}

/** Stilen paa en knude, uanset om den er et array. */
const stil = (n: Knude | undefined): Record<string, unknown> => {
  const st = n?.props?.style
  if (Array.isArray(st)) return Object.assign({}, ...st.map((x) => (x && typeof x === 'object' ? x : {})))
  return (st && typeof st === 'object' ? st : {}) as Record<string, unknown>
}

describe('linjen holder sig inden for skaermen', () => {
  it('hvert led i etikettens kaede kan krympe — i BEGGE tilstande', async () => {
    // En etiket der ikke kan krympe skubber linjen ud over skaermkanten — og
    // tager klokken, +/- og chevronen med sig. Desk loeser det med
    // `min-width: 0` + ellipsis paa `.toolgroup-label`; her skal HVERT led
    // kunne krympe, ikke bare det yderste. Det mellemliggende lag —
    // label-skiftets eget View — manglede baade `flexShrink` og `minWidth`,
    // og dér stoppede krympningen. (Bjørn 30/9-2026: «nogen af runders linjer
    // gaar helt ud af skaermen».)
    //
    // Den KOERENDE linje tegnes af GlidendeTekst (SVG), den FAERDIGE af et
    // almindeligt Text. Kaeden er derfor forskellig, og begge skal maales:
    // [0] er SVG-rammen i den koerende gren; [1] er label-skiftets lag og [2]
    // cellen — de to findes i begge tilstande.
    for (const running of [true, false]) {
      // Shimmer-tilstanden kraever HELE kaeden siden 4/10-2026: `running` alene
      // er ikke nok — runden skal ogsaa vaere turens SIDSTE, og slutsvaret maa
      // ikke vaere begyndt (se `visShimmer` i `InlineToolGroup`). Testen maaler
      // stadig layoutet i BEGGE tilstande; den fremkalder dem blot som fladen
      // nu goer. Uden `streaming`/`sidste` faldt den koerende gren tilbage til
      // den faerdige, og `glidende-tekst` fandtes ikke i traeet.
      const s = await render(<InlineToolGroup
        items={[item({ label: 'x'.repeat(200), running })]}
        streaming={running} sidste={running}
      />)
      const vej = vejTil(s.toJSON(), running ? 'glidende-tekst' : 'linje-titel')
      expect(vej).not.toBeNull()
      // Sidste led i vejen er knuden selv; foraeldrene ligger lige foer den.
      // Det er DEM der skal kunne krympe — roden kan ikke.
      const led = running ? vej!.slice(-3) : vej!.slice(-3, -1)
      expect(led.length).toBeGreaterThanOrEqual(2)
      for (const n of led) {
        expect(stil(n).flexShrink).toBe(1)
        expect(stil(n).minWidth).toBe(0)
      }
      // Skaermkanten er graensen: cellen klipper, uanset hvad flex-loesningen
      // naar frem til. Det er det sidste vaern mod at male ud over kanten.
      expect(stil(vej!.at(-3)!).overflow).toBe('hidden')
    }
  })

  it('tallene og chevronen staar FAST — de maa ikke skubbes ud', async () => {
    // Det er dem der viser at der er mere at se (Bjørn 30/9-2026: «fordi der
    // bliver vist +/- diff og ikon >»). Etiketten er den der viger.
    //
    // Runden er FÆRDIG her: chevronen findes kun da. Prikkerne er flyttet til
    // arbejdslinjen, og caret'en vises først når der er noget at folde ud.
    const s = await render(<InlineToolGroup items={[
      item({ label: 'x'.repeat(200), diff: { tilfoejet: 3, fjernet: 1 } }),
      item({ label: 'y' }),
    ]} />)
    const vej = vejTil(s.toJSON(), 'tool-spark')
    expect(vej).not.toBeNull()
    const raekke = vej![vej!.length - 2]!       // sparkens foraelder ER rækken
    const boern = ((raekke.children ?? []) as Knude[]).map(stil)
    // Praecis ÉN kan krympe — etiketten. Resten staar fast.
    expect(boern.filter((b) => b.flexShrink === 1)).toHaveLength(1)
    expect(boern.filter((b) => b.flexShrink === 0)).toHaveLength(boern.length - 1)
    expect(stil(vejTil(s.toJSON(), 'tool-status-caret')!.at(-1)).flexShrink).toBe(0)
  })
})

// ── Shimmeren lever gennem hullet mellem runder (4/10-2026) ────────────────
//
// Bjørn 3/10-2026: «i runde linjerne … skal shimmer fortsætte til første tænke
// i næste runde, ellers opstår der et par sekunders stilhed hvor du tænker».
//
// `running` alene slukker i samme sekund sidste kald får sit resultat — og
// præcis dér tænker modellen på den næste. Reglen er derfor
// `streaming && sidste && (running || !svarBegyndt)`, spejlet fra desk's
// `RaekkeTranskript.tsx:341`. Den er ikke «der er kommet tekst efter
// værktøjet»: rundeopsummeringen lander MED resultatet og ville slukke
// shimmeren i det vindue den skal dække.
describe('shimmeren lever gennem hullet mellem runder', () => {
  const glimter = (s: Awaited<ReturnType<typeof render>>) =>
    vejTil(s.toJSON(), 'glidende-tekst') !== null

  it('en FAERDIG runde glimter stadig — naar slutsvaret ikke er begyndt', async () => {
    const s = await render(
      <InlineToolGroup items={[item()]} streaming sidste svarBegyndt={false} />,
    )
    expect(glimter(s)).toBe(true)
  })

  it('den slukker naar slutsvaret begynder', async () => {
    const s = await render(<InlineToolGroup items={[item()]} streaming sidste svarBegyndt />)
    expect(glimter(s)).toBe(false)
  })

  it('en runde der IKKE er turens sidste glimter ikke', async () => {
    // Alt før den sidste er overhalet af noget der kom bagefter — det er
    // selve beviset for at den er færdig.
    const s = await render(
      <InlineToolGroup items={[item()]} streaming sidste={false} svarBegyndt={false} />,
    )
    expect(glimter(s)).toBe(false)
  })

  it('en historisk runde — ikke streaming — glimter ikke', async () => {
    const s = await render(<InlineToolGroup items={[item()]} />)
    expect(glimter(s)).toBe(false)
  })

  it('et KOERENDE kald glimter — ogsaa naar svaret er begyndt', async () => {
    const s = await render(
      <InlineToolGroup items={[item({ running: true })]} streaming sidste svarBegyndt />,
    )
    expect(glimter(s)).toBe(true)
  })
})
