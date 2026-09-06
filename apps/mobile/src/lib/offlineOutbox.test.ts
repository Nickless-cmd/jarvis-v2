import * as SecureStore from 'expo-secure-store'
import {
  clearOutbox,
  enqueueOutboxItem,
  loadOutbox,
  markOutboxFailed,
  removeOutboxItem
} from './offlineOutbox'

jest.mock('expo-secure-store', () => ({
  __esModule: true,
  getItemAsync: jest.fn(),
  setItemAsync: jest.fn(async () => undefined),
  deleteItemAsync: jest.fn(async () => undefined)
}))

const store = SecureStore as jest.Mocked<typeof SecureStore>

beforeEach(() => {
  jest.clearAllMocks()
})

it('queues chat messages with enough context to replay them after reconnect', async () => {
  store.getItemAsync.mockResolvedValueOnce(null)

  const item = await enqueueOutboxItem({
    kind: 'chat_message',
    sessionId: 's1',
    text: 'fortsæt',
    attachmentIds: ['a1']
  })

  expect(item.id).toMatch(/^outbox-/)
  expect(item.attempts).toBe(0)
  expect(store.setItemAsync).toHaveBeenCalledWith(
    'jarvis.mobile.offlineOutbox',
    expect.stringContaining('"kind":"chat_message"')
  )
})

it('drops delivered items and records retry errors without losing the rest', async () => {
  store.getItemAsync.mockResolvedValueOnce(JSON.stringify([
    { id: 'o1', kind: 'chat_message', createdAt: '2026-09-06T08:00:00.000Z', attempts: 0, sessionId: 's1', text: 'a' },
    { id: 'o2', kind: 'approval_action', createdAt: '2026-09-06T08:01:00.000Z', attempts: 0, approvalId: 'p1', action: 'approve' }
  ]))
  await removeOutboxItem('o1')
  expect(store.setItemAsync).toHaveBeenLastCalledWith(
    'jarvis.mobile.offlineOutbox',
    expect.stringContaining('"id":"o2"')
  )

  store.getItemAsync.mockResolvedValueOnce(JSON.stringify([
    { id: 'o2', kind: 'approval_action', createdAt: '2026-09-06T08:01:00.000Z', attempts: 0, approvalId: 'p1', action: 'approve' }
  ]))
  await markOutboxFailed('o2', 'offline')
  const saved = JSON.parse(String(store.setItemAsync.mock.calls.at(-1)?.[1]))
  expect(saved[0].attempts).toBe(1)
  expect(saved[0].lastError).toBe('offline')
})

it('treats corrupt storage as an empty queue and can clear it', async () => {
  store.getItemAsync.mockResolvedValueOnce('not json')
  await expect(loadOutbox()).resolves.toEqual([])
  await clearOutbox()
  expect(store.deleteItemAsync).toHaveBeenCalledWith('jarvis.mobile.offlineOutbox')
})
