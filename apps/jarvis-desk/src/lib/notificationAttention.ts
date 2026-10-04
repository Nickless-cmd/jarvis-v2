const KEY = 'jarvis-desk:notifikationer:sete-v1'
export const NOTIFICATION_READ_EVENT = 'jarvis-desk:notifikation-laest'

type Seen = { acknowledged: string[]; read: string[] }

function load(): Seen {
  try {
    const parsed = JSON.parse(localStorage.getItem(KEY) || '{}') as Partial<Seen>
    return {
      acknowledged: Array.isArray(parsed.acknowledged) ? parsed.acknowledged : [],
      read: Array.isArray(parsed.read) ? parsed.read : [],
    }
  } catch { return { acknowledged: [], read: [] } }
}

function save(value: Seen): void {
  try { localStorage.setItem(KEY, JSON.stringify(value)) } catch { /* private storage may be unavailable */ }
  window.dispatchEvent(new Event(NOTIFICATION_READ_EVENT))
}

export function notificationAttention(ids: string[]): { unread: boolean; attention: boolean } {
  const state = load()
  return {
    unread: ids.some((id) => !state.read.includes(id)),
    attention: ids.some((id) => !state.acknowledged.includes(id)),
  }
}

export function acknowledgeNotifications(ids: string[]): void {
  const state = load()
  state.acknowledged = [...new Set([...state.acknowledged, ...ids])].slice(-500)
  save(state)
}

export function markNotificationsRead(ids: string[]): void {
  const state = load()
  state.read = [...new Set([...state.read, ...ids])].slice(-500)
  state.acknowledged = [...new Set([...state.acknowledged, ...ids])].slice(-500)
  save(state)
}
