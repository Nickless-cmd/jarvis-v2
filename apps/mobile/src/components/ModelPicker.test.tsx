import { fireEvent, render, waitFor } from '@testing-library/react-native'
import { ModelPicker } from './ModelPicker'

const choices = [
  { model: '', providerChoice: 'deepseek', label: 'Deepseek' },
  { model: 'deepseek-v4-flash', providerChoice: 'deepseek', label: 'V4 Flash' }
]

const base = {
  open: true,
  choices,
  selectedLabel: 'Deepseek',
  thinkingMode: 'think' as const,
  onThinkingModeChange: jest.fn(),
  onSelect: jest.fn(),
  onClose: jest.fn()
}

beforeEach(() => jest.clearAllMocks())

it('viser tænkning som liste med flueben — og ikke permissions', async () => {
  const onThinkingModeChange = jest.fn()
  const screen = await render(<ModelPicker {...base} onThinkingModeChange={onThinkingModeChange} />)

  // Ordene er desks, ikke vores: dens THINK_KORT er {fast:'Hurtig',
  // think:'Auto'}. Mobilen skrev «Think/Fast» — det var dét der ikke lignede.
  fireEvent.press(screen.getByText('Hurtig'))

  expect(onThinkingModeChange).toHaveBeenCalledWith('fast')
  expect(screen.queryByText('Godkendelser')).toBeNull()
  expect(screen.queryByText('Trust')).toBeNull()
})

it('modellen ligger bag en undermenu — listen er ikke synlig ved åbning', async () => {
  // Bjørn 28/9-2026: «med samme visning når åbnet». Billedet viser tænkningen
  // som liste ØVERST og modellen som en række med chevron NEDERST. Lå
  // modellisten øverst igen, var formen den gamle — og den fælder her.
  const screen = await render(<ModelPicker {...base} />)

  expect(screen.queryByText('V4 Flash')).toBeNull()
  expect(screen.getByText('Intelligens')).toBeTruthy()

  fireEvent.press(screen.getByLabelText('Model: Deepseek'))

  await waitFor(() => expect(screen.getByText('V4 Flash')).toBeTruthy())
})

it('byder alle TRE niveauer serveren kender — og melder det rigtige', async () => {
  // Bjørn 28/9-2026: «Kun 3. Serveren kender». De tre er fast/think/deep, og
  // serveren ærer dem alle: fast slår thinking FRA, deep sætter
  // reasoning_effort="max". Et niveau uden en tilstand bag sig er en knap der
  // løjer — og et niveau der ikke kan MELDES er lige så galt.
  const onThinkingModeChange = jest.fn()
  const screen = await render(<ModelPicker {...base} onThinkingModeChange={onThinkingModeChange} />)

  expect(screen.getByText('Hurtig')).toBeTruthy()
  expect(screen.getByText('Automatisk')).toBeTruthy()
  expect(screen.getByText('Dyb')).toBeTruthy()

  fireEvent.press(screen.getByText('Dyb'))
  expect(onThinkingModeChange).toHaveBeenCalledWith('deep')
})

it('et valg i model-listen melder modellen og lukker', async () => {
  const onSelect = jest.fn()
  const onClose = jest.fn()
  const screen = await render(<ModelPicker {...base} onSelect={onSelect} onClose={onClose} />)

  fireEvent.press(screen.getByLabelText('Model: Deepseek'))
  await waitFor(() => expect(screen.getByText('V4 Flash')).toBeTruthy())
  fireEvent.press(screen.getByText('V4 Flash'))

  expect(onSelect).toHaveBeenCalledWith(choices[1])
  expect(onClose).toHaveBeenCalled()
})

it('uden tænke-valg står modellisten direkte — ingen tom undermenu', async () => {
  const screen = await render(
    <ModelPicker {...base} onThinkingModeChange={undefined} />
  )

  expect(screen.queryByText('Intelligens')).toBeNull()
  expect(screen.queryByText('Tænkning')).toBeNull()
  expect(screen.getByText('V4 Flash')).toBeTruthy()
})
