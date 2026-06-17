import * as SecureStore from 'expo-secure-store'

// Husk hvilken session brugeren sidst var i, så app'en åbner samme sted.
const KEY = 'jarvis.mobile.lastSession'

export async function saveLastSession(sessionId: string): Promise<void> {
  if (!sessionId) return
  try {
    await SecureStore.setItemAsync(KEY, sessionId)
  } catch {
    // Persistering er best-effort — en fejl må ikke vælte chatten.
  }
}

export async function loadLastSession(): Promise<string | null> {
  try {
    return await SecureStore.getItemAsync(KEY)
  } catch {
    return null
  }
}

export async function clearLastSession(): Promise<void> {
  try {
    await SecureStore.deleteItemAsync(KEY)
  } catch {
    // ignore
  }
}
