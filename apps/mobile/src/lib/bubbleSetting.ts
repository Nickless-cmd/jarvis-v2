import * as SecureStore from 'expo-secure-store'

const KEY = 'jarvis.mobile.bubblePersist'

/** Ren parser (testbar) — "1" = til. */
export function parseBubblePersist(raw: string | null): boolean {
  return raw === '1'
}

export async function loadBubblePersist(): Promise<boolean> {
  try {
    return parseBubblePersist(await SecureStore.getItemAsync(KEY))
  } catch {
    return false
  }
}

export async function saveBubblePersist(on: boolean): Promise<void> {
  try {
    await SecureStore.setItemAsync(KEY, on ? '1' : '0')
  } catch {
    /* no-op */
  }
}
