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

// Husk det valgte composer-model-valg på tværs af app-genstart (FEATURE 1:
// før var det kun React-state → faldt tilbage til default ved genstart).
const MODEL_KEY = 'jarvis.mobile.modelChoice'

export interface StoredModelChoice {
  model: string
  providerChoice: string
  label: string
}

/** Ren parser (testbar): validér det persisterede JSON til en StoredModelChoice. */
export function parseModelChoice(raw: string | null): StoredModelChoice | null {
  if (!raw) return null
  try {
    const p = JSON.parse(raw) as Partial<StoredModelChoice>
    if (
      p &&
      typeof p.model === 'string' &&
      typeof p.providerChoice === 'string' &&
      typeof p.label === 'string'
    ) {
      return { model: p.model, providerChoice: p.providerChoice, label: p.label }
    }
    return null
  } catch {
    return null
  }
}

export async function saveModelChoice(choice: StoredModelChoice): Promise<void> {
  try {
    await SecureStore.setItemAsync(MODEL_KEY, JSON.stringify(choice))
  } catch {
    // best-effort
  }
}

export async function loadModelChoice(): Promise<StoredModelChoice | null> {
  try {
    return parseModelChoice(await SecureStore.getItemAsync(MODEL_KEY))
  } catch {
    return null
  }
}
