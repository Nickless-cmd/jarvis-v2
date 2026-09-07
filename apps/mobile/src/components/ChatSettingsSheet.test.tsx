import { fireEvent, render } from '@testing-library/react-native'
import { ChatSettingsSheet } from './ChatSettingsSheet'
import { STANDARD } from '../lib/chatSettings'

const vis = async (over: Partial<React.ComponentProps<typeof ChatSettingsSheet>> = {}) => {
  const onChange = jest.fn()
  const onClose = jest.fn()
  const screen = await render(
    <ChatSettingsSheet visible cfg={STANDARD} onChange={onChange} onClose={onClose} {...over} />
  )
  return { screen, onChange, onClose }
}

it('viser hvad hver kontakt BETYDER, ikke bare hvad den hedder', async () => {
  const { screen } = await vis()
  expect(screen.getByText(/Kun samtale-værktøjer/)).toBeTruthy()
  expect(screen.getByText(/beder om lov, før han ændrer/)).toBeTruthy()
})

it('forklaringen skifter med tilstanden — så man kan se hvad man lige slog til', async () => {
  const { screen } = await vis({ cfg: { ...STANDARD, vaerktoejer: 'fuldt', spoergFoerst: false } })
  expect(screen.getByText(/hele værktøjskassen/)).toBeTruthy()
  expect(screen.getByText(/handler uden at spørge/)).toBeTruthy()
})

it('slår værktøjs-omfang om', async () => {
  const { screen, onChange } = await vis()
  fireEvent(screen.getByTestId('chatcfg-tools'), 'valueChange', true)
  expect(onChange).toHaveBeenCalledWith({ vaerktoejer: 'fuldt' })
})

it('slår «spørg først» fra', async () => {
  const { screen, onChange } = await vis()
  fireEvent(screen.getByTestId('chatcfg-ask'), 'valueChange', false)
  expect(onChange).toHaveBeenCalledWith({ spoergFoerst: false })
})

it('model-valget skjules helt når der ikke er noget at vælge imellem', async () => {
  const { screen } = await vis()
  expect(screen.queryByTestId('chatcfg-models')).toBeNull()
})

it('«Som appen» er et eksplicit valg, ikke et tomt felt', async () => {
  const { screen, onChange } = await vis({ modeller: [{ model: 'pro', label: 'Pro' }] })
  expect(screen.getByTestId('chatcfg-model-default')).toBeTruthy()
  fireEvent.press(screen.getByTestId('chatcfg-model-pro'))
  expect(onChange).toHaveBeenCalledWith({ model: 'pro' })
})

it('har INGEN memory-scope-kontakt — serveren har intet felt for den', async () => {
  const { screen } = await vis()
  expect(screen.queryByText(/memory scope/i)).toBeNull()
  expect(screen.queryByText(/hukommelses-omfang/i)).toBeNull()
})

it('lukker', async () => {
  const { screen, onClose } = await vis()
  fireEvent.press(screen.getByTestId('chatcfg-close'))
  expect(onClose).toHaveBeenCalled()
})
