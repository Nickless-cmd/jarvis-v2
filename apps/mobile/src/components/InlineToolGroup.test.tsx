import { act, fireEvent, render } from '@testing-library/react-native'
import { InlineToolGroup } from './InlineToolGroup'
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
