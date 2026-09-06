import * as SecureStore from 'expo-secure-store'

const OUTBOX_KEY = 'jarvis.mobile.offlineOutbox'

export type OutboxItem =
  | {
      id: string
      kind: 'chat_message'
      createdAt: string
      attempts: number
      sessionId: string
      text: string
      attachmentIds?: string[]
      lastError?: string
    }
  | {
      id: string
      kind: 'approval_action'
      createdAt: string
      attempts: number
      approvalId: string
      action: 'approve' | 'deny'
      lastError?: string
    }
  | {
      id: string
      kind: 'run_action'
      createdAt: string
      attempts: number
      runId: string
      action: 'open' | 'stop'
      lastError?: string
    }

export type NewOutboxItem =
  | Omit<Extract<OutboxItem, { kind: 'chat_message' }>, 'id' | 'createdAt' | 'attempts'>
  | Omit<Extract<OutboxItem, { kind: 'approval_action' }>, 'id' | 'createdAt' | 'attempts'>
  | Omit<Extract<OutboxItem, { kind: 'run_action' }>, 'id' | 'createdAt' | 'attempts'>

function validItem(x: unknown): x is OutboxItem {
  if (!x || typeof x !== 'object') return false
  const item = x as Record<string, unknown>
  return typeof item.id === 'string'
    && typeof item.kind === 'string'
    && typeof item.createdAt === 'string'
    && typeof item.attempts === 'number'
}

async function saveOutbox(items: OutboxItem[]): Promise<void> {
  await SecureStore.setItemAsync(OUTBOX_KEY, JSON.stringify(items))
}

export async function loadOutbox(): Promise<OutboxItem[]> {
  try {
    const raw = await SecureStore.getItemAsync(OUTBOX_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed.filter(validItem) : []
  } catch {
    return []
  }
}

export async function enqueueOutboxItem(input: NewOutboxItem): Promise<OutboxItem> {
  const item = {
    ...input,
    id: `outbox-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`,
    createdAt: new Date().toISOString(),
    attempts: 0
  } as OutboxItem
  await saveOutbox([...(await loadOutbox()), item])
  return item
}

export async function removeOutboxItem(id: string): Promise<void> {
  await saveOutbox((await loadOutbox()).filter((item) => item.id !== id))
}

export async function markOutboxFailed(id: string, error: string): Promise<void> {
  await saveOutbox((await loadOutbox()).map((item) => (
    item.id === id ? { ...item, attempts: item.attempts + 1, lastError: error } : item
  )))
}

export async function clearOutbox(): Promise<void> {
  await SecureStore.deleteItemAsync(OUTBOX_KEY)
}
