import { act, fireEvent, render } from '@testing-library/react-native'
import { InlineToolGroup } from './InlineToolGroup'

/** Claude Desktop §9 på telefonen (19/9-2026): en redigerings-række åbner diff-arket. */
const items = [
  { label: 'Redigerede login.py', running: false, tool: 'edit_file', diff: { tilfoejet: 1, fjernet: 1 },
    aendring: { sti: '/repo/core/login.py', gammel: 'a\nreturn None\nc', ny: 'a\nreturn bruger\nc' } },
  { label: 'Læste auth.py', running: false, tool: 'read_file' },
]

it('en redigering i den udfoldede runde åbner diff-arket med linjerne', async () => {
  const s = await render(<InlineToolGroup items={items} />)
  await act(async () => { fireEvent.press(s.getByTestId('tool-group')) })
  expect(s.queryByTestId('diff-ark')).toBeNull()
  await act(async () => { fireEvent.press(s.getByTestId('aendring-0')) })
  expect(s.getByTestId('diff-ark')).toBeTruthy()
  expect(s.getByText('login.py')).toBeTruthy()
  expect(s.getByText('- return None')).toBeTruthy()
  expect(s.getByText('+ return bruger')).toBeTruthy()
})

it('en læsning kan ikke trykkes', async () => {
  const s = await render(<InlineToolGroup items={items} />)
  await act(async () => { fireEvent.press(s.getByTestId('tool-group')) })
  expect(s.queryByTestId('aendring-1')).toBeNull()
})
