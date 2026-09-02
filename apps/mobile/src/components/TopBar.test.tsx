import { fireEvent, render } from '@testing-library/react-native'
import { TopBar } from './TopBar'

const base = {
  mode: 'snak' as const,
  onModeChange: jest.fn(),
  onMenu: jest.fn(),
  onSync: jest.fn()
}

beforeEach(() => jest.clearAllMocks())

it('skifter tilstand via segmented control', async () => {
  const screen = await render(<TopBar {...base} />)
  await fireEvent.press(screen.getByLabelText('Arbejde'))
  expect(base.onModeChange).toHaveBeenCalledWith('arbejde')
})

it('menu og sync er selvstændige knapper', async () => {
  const screen = await render(<TopBar {...base} />)
  await fireEvent.press(screen.getByLabelText('Menu'))
  await fireEvent.press(screen.getByLabelText('Synkronisér'))
  expect(base.onMenu).toHaveBeenCalledTimes(1)
  expect(base.onSync).toHaveBeenCalledTimes(1)
})

it('bærer en prik på Arbejde når noget venter', async () => {
  const uden = await render(<TopBar {...base} />)
  expect(uden.queryByTestId('segment-badge-arbejde')).toBeNull()
  const med = await render(<TopBar {...base} pendingWork />)
  expect(med.queryByTestId('segment-badge-arbejde')).not.toBeNull()
})
