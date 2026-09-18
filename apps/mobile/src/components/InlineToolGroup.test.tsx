import { fireEvent, render } from '@testing-library/react-native'
import { InlineToolGroup } from './InlineToolGroup'
import type { ToolItem } from '../lib/toolGroup'

const item = (over: Partial<ToolItem> = {}): ToolItem => ({
  label: 'Læste USER.md',
  running: false,
  tool: 'read_file',
  ...over
})

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

it('spark-cellen er kun bred mens runden arbejder', async () => {
  const bredde = (s: Awaited<ReturnType<typeof render>>) => {
    const st = s.getByTestId('tool-spark').props.style
    return Object.assign({}, ...(Array.isArray(st) ? st.filter(Boolean) : [st])).width
  }
  const koer = await render(<InlineToolGroup items={[item({ running: true }), item()]} />)
  expect(bredde(koer)).toBe(20)
  const faerdig = await render(<InlineToolGroup items={[item(), item()]} />)
  expect(bredde(faerdig)).toBe(0)
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
