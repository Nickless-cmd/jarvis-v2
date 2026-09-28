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

it('viser vaelgeren som en kompakt popover ved komponisten', async () => {
  const screen = await render(<ModelPicker {...base} bottomOffset={110} />)
  expect(screen.getByTestId('model-popover')).toHaveStyle({ bottom: 110 })
  expect(screen.getByTestId('model-popover')).toHaveStyle({ borderRadius: 24 })
})

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

/**
 * Udbyderen under hvert modelnavn.
 *
 * Bjørn 28/9-2026: «en lille skrift under hver model så jeg kan se hvilken
 * udbyder modellen hører til». Navnet alene siger det ikke: «gpt-5.5» kommer
 * fra openai-codex, og «deepseek-v4-pro» findes både hos deepseek og som
 * `:cloud` hos ollama. To rækker der ser ens ud, men rammer hver sin maskine.
 */
it('skriver udbyderen under hvert modelnavn', async () => {
  const screen = await render(
    <ModelPicker
      {...base}
      onThinkingModeChange={undefined}
      choices={[
        { model: 'deepseek-v4-pro', providerChoice: 'deepseek', label: 'V4 Pro' },
        { model: 'deepseek-v4-pro:cloud', providerChoice: 'ollama', label: 'V4 Pro Cloud' },
        { model: 'gpt-5.5', providerChoice: 'openai-codex', label: 'GPT-5.5' }
      ]}
    />
  )
  await waitFor(() => expect(screen.getByText('V4 Pro')).toBeTruthy())
  expect(screen.getByText('deepseek')).toBeTruthy()
  expect(screen.getByText('ollama')).toBeTruthy()
  expect(screen.getByText('openai-codex')).toBeTruthy()
})

it('to modeller med samme navn kan skelnes på udbyderen', async () => {
  const screen = await render(
    <ModelPicker
      {...base}
      onThinkingModeChange={undefined}
      choices={[
        { model: 'deepseek-v4-pro', providerChoice: 'deepseek', label: 'V4 Pro' },
        { model: 'deepseek-v4-pro:cloud', providerChoice: 'ollama', label: 'V4 Pro' }
      ]}
    />
  )
  await waitFor(() => expect(screen.getAllByText('V4 Pro')).toHaveLength(2))
  expect(screen.getByText('deepseek')).toBeTruthy()
  expect(screen.getByText('ollama')).toBeTruthy()
})

it('uden en udbyder står modellen alene — ingen tom linje', async () => {
  const screen = await render(
    <ModelPicker
      {...base}
      onThinkingModeChange={undefined}
      choices={[{ model: 'x', providerChoice: '', label: 'Uden udbyder' }]}
    />
  )
  await waitFor(() => expect(screen.getByText('Uden udbyder')).toBeTruthy())
  expect(screen.queryByText('')).toBeNull()
})
