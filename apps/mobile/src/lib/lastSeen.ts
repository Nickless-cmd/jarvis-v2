import * as SecureStore from 'expo-secure-store'

const KEY = 'jarvis.mobile.lastSeen'

export async function loadLastSeen(): Promise<Record<string, number>> {
  try {
    const raw = await SecureStore.getItemAsync(KEY)
    if (!raw) return {}
    const parsed = JSON.parse(raw)
    if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
      return parsed as Record<string, number>
    }
    return {}
  } catch {
    return {}
  }
}

export async function markSeen(sessionId: string, count: number): Promise<void> {
  try {
    const map = await loadLastSeen()
    map[sessionId] = count
    await SecureStore.setItemAsync(KEY, JSON.stringify(map))
  } catch {
    /* best-effort: ulæst-status er ikke kritisk */
  }
}
