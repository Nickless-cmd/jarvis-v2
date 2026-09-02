import { fireEvent, render } from '@testing-library/react-native'
import { SegmentedControl } from './SegmentedControl'

const options = [
  { value: 'snak' as const, label: 'Snak' },
  { value: 'arbejde' as const, label: 'Arbejde' }
]

it('markerer det aktive segment for skærmlæsere', async () => {
  const screen = await render(<SegmentedControl options={options} value="snak" onChange={() => {}} />)
  expect(screen.getByLabelText('Snak').props.accessibilityState.selected).toBe(true)
  expect(screen.getByLabelText('Arbejde').props.accessibilityState.selected).toBe(false)
})

it('melder valget videre', async () => {
  const onChange = jest.fn()
  const screen = await render(<SegmentedControl options={options} value="snak" onChange={onChange} />)
  await fireEvent.press(screen.getByLabelText('Arbejde'))
  expect(onChange).toHaveBeenCalledWith('arbejde')
})

it('viser kun en prik når der er noget at vise', async () => {
  const uden = await render(<SegmentedControl options={options} value="snak" onChange={() => {}} />)
  expect(uden.queryByTestId('segment-badge-arbejde')).toBeNull()

  const med = await render(
    <SegmentedControl
      options={[options[0], { ...options[1], badge: true }]}
      value="snak"
      onChange={() => {}}
    />
  )
  expect(med.queryByTestId('segment-badge-arbejde')).not.toBeNull()
})
