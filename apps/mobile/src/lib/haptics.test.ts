import * as Haptics from 'expo-haptics'
import { haptik } from './haptics'

jest.mock('expo-haptics', () => ({
  impactAsync: jest.fn(async () => {}),
  notificationAsync: jest.fn(async () => {}),
  ImpactFeedbackStyle: { Light: 'light', Medium: 'medium' },
  NotificationFeedbackType: { Success: 'success', Warning: 'warning', Error: 'error' },
}))

beforeEach(() => jest.clearAllMocks())

it('send er let — den sker mange gange', async () => {
  await haptik('send')
  expect(Haptics.impactAsync).toHaveBeenCalledWith('light')
})

it('stop er tungere — det er et indgreb', async () => {
  await haptik('stop')
  expect(Haptics.impactAsync).toHaveBeenCalledWith('medium')
})

it('godkend og afvis føles FORSKELLIGT', async () => {
  await haptik('godkend')
  await haptik('afvis')
  const kald = (Haptics.notificationAsync as jest.Mock).mock.calls.map((c) => c[0])
  expect(kald).toEqual(['success', 'warning'])
})

it('en enhed uden vibrator vælter ikke send-knappen', async () => {
  ;(Haptics.impactAsync as jest.Mock).mockRejectedValueOnce(new Error('ingen vibrator'))
  await expect(haptik('send')).resolves.toBeUndefined()
})
