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

it('linjen er i nutid mens runden kører', async () => {
  const s = await render(<InlineToolGroup items={[item({ running: true }), item()]} />)
  expect(s.getByText('Læser 2 filer…')).toBeTruthy()
})

it('en tom runde tegner ingenting', async () => {
  const s = await render(<InlineToolGroup items={[]} />)
  expect(s.queryByTestId('tool-group')).toBeNull()
})
