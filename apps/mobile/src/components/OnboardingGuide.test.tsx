import { act, fireEvent, render } from '@testing-library/react-native'
import { OnboardingGuide } from './OnboardingGuide'

jest.mock('expo-secure-store', () => ({
  getItemAsync: jest.fn().mockResolvedValue(null),
  setItemAsync: jest.fn().mockResolvedValue(undefined),
}))
jest.mock('../lib/permissionRequests', () => ({ bedOmTilladelse: jest.fn() }))

const vis = async (props: Partial<React.ComponentProps<typeof OnboardingGuide>> = {}) => {
  const onDone = jest.fn()
  const spoerg = jest.fn().mockResolvedValue(true)
  const screen = await render(
    <OnboardingGuide visible onDone={onDone} spoerg={spoerg} {...props} />
  )
  return { screen, onDone, spoerg }
}

it('starter med push — uden den kan han slet ikke nå dig', async () => {
  const { screen } = await vis()
  expect(screen.getByText('Må han sige til?')).toBeTruthy()
  expect(screen.getByTestId('onboarding-count').props.children.join('')).toBe('1 af 4')
})

it('spørger systemet og går videre', async () => {
  const { screen, spoerg } = await vis()
  await act(async () => { fireEvent.press(screen.getByTestId('onboarding-ja')) })
  expect(spoerg).toHaveBeenCalledWith('push')
  expect(screen.getByText('Vil du kunne tale til ham?')).toBeTruthy()
})

it('et NEJ fører lige så langt som et ja — guiden er ikke en tvang', async () => {
  const { screen, spoerg } = await vis()
  spoerg.mockResolvedValue(false)
  await act(async () => { fireEvent.press(screen.getByTestId('onboarding-ja')) })
  expect(screen.getByText('Vil du kunne tale til ham?')).toBeTruthy()
})

it('«Ikke nu» spørger IKKE systemet — en afvist dialog kan brændes af for altid', async () => {
  const { screen, spoerg } = await vis()
  await act(async () => { fireEvent.press(screen.getByTestId('onboarding-spring')) })
  expect(spoerg).not.toHaveBeenCalled()
  expect(screen.getByText('Vil du kunne tale til ham?')).toBeTruthy()
})

it('springer trin over der allerede er givet', async () => {
  const { screen } = await vis({ alleredeGivet: ['push', 'mikrofon'] })
  expect(screen.getByText('Må han se hvad du ser?')).toBeTruthy()
  expect(screen.getByTestId('onboarding-count').props.children.join('')).toBe('1 af 2')
})

it('sidste trin afslutter guiden', async () => {
  const { screen, onDone } = await vis({ alleredeGivet: ['push', 'mikrofon', 'kamera'] })
  await act(async () => { fireEvent.press(screen.getByTestId('onboarding-spring')) })
  expect(onDone).toHaveBeenCalled()
})

it('«spring det hele over» slipper ud med det samme', async () => {
  const { screen, onDone } = await vis()
  await act(async () => { fireEvent.press(screen.getByTestId('onboarding-luk')) })
  expect(onDone).toHaveBeenCalled()
})

it('viser intet når alt allerede er givet', async () => {
  const { screen } = await vis({ alleredeGivet: ['push', 'mikrofon', 'kamera', 'lokation'] })
  expect(screen.queryByTestId('onboarding')).toBeNull()
})
