import * as SecureStore from 'expo-secure-store'

// Husk hvilken session brugeren sidst var i, så app'en åbner samme sted.
const KEY = 'jarvis.mobile.lastSession'

export interface SidstePlads {
  id: string
  /**
   * Stod vi i code-fladen? `null` betyder UVIST — ikke «nej».
   *
   * Tre tilstande, ikke to. Nøglen indeholdt før kun et session-id, og der er
   * fladen ukendt. Læste man det som «chat», ville en gemt code-samtale åbne
   * i chat-fladen én gang efter opdateringen — præcis den modstrid det her
   * skulle fjerne. Kun i DEN tilstand spørger klienten samtalen om dens art;
   * ellers er det brugerens eget valg der gælder.
   */
  kode: boolean | null
}

/**
 * Session og flade gemmes SAMMEN, i én nøgle.
 *
 * Bjørn 12/9-2026: «appen glemmer code mode så starter den stadig op i chat
 * mode med en code session loaded». To nøgler kan blive uenige — én kan ikke.
 * Det er ikke sparsommelighed; det er den eneste form hvor tilstanden ikke kan
 * være halvt gendannet.
 */
export async function saveLastSession(sessionId: string, kode = false): Promise<void> {
  if (!sessionId) return
  try {
    await SecureStore.setItemAsync(KEY, JSON.stringify({ id: sessionId, kode: !!kode }))
  } catch {
    // Persistering er best-effort — en fejl må ikke vælte chatten.
  }
}

export async function loadLastSession(): Promise<SidstePlads | null> {
  try {
    const raa = await SecureStore.getItemAsync(KEY)
    if (!raa) return null
    // BAGUDKOMPATIBELT: nøglen indeholdt før en bar session-id-streng. Uden det
    // her ville alle der opdaterer miste deres sidste samtale én gang — og det
    // ville ligne at appen havde glemt dem.
    if (!raa.trimStart().startsWith('{')) return { id: raa, kode: null }
    const o = JSON.parse(raa) as { id?: unknown; kode?: unknown }
    const id = typeof o.id === 'string' ? o.id : ''
    return id ? { id, kode: typeof o.kode === 'boolean' ? o.kode : null } : null
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
