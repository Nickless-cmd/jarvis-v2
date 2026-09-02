import { fireEvent, render } from '@testing-library/react-native'
import { InlineToolLine } from './InlineToolLine'

it('viser handlingen i datid på én linje', async () => {
  const s = await render(<InlineToolLine summary="Ændrede 16 filer" />)
  expect(s.getByText('Ændrede 16 filer')).toBeTruthy()
  expect(s.getByText('</>')).toBeTruthy()
})

it('uden onPress er der ingen chevron og intet at trykke på', async () => {
  const s = await render(<InlineToolLine summary="Læste db.py" />)
  expect(s.queryByTestId('inline-tool-line')).toBeNull()
  expect(s.queryByText('›')).toBeNull()
})

it('med onPress kan linjen åbnes', async () => {
  const onPress = jest.fn()
  const s = await render(<InlineToolLine summary="Læste db.py" onPress={onPress} />)
  expect(s.getByText('›')).toBeTruthy()
  await fireEvent.press(s.getByTestId('inline-tool-line'))
  expect(onPress).toHaveBeenCalled()
})

it('linjen klipper frem for at vokse — ro i tråden', async () => {
  const s = await render(<InlineToolLine summary={'x'.repeat(400)} />)
  expect(s.getByText('x'.repeat(400)).props.numberOfLines).toBe(1)
})
