import * as SecureStore from 'expo-secure-store'

/** Fastgjorte beskeder — de få linjer man vil kunne finde igen.
 *
 *  Gemmes pr. session, så en pin i én samtale ikke forurener en anden. Lagret
 *  er SecureStore, fordi det er dét appen i forvejen bruger; nøglerne er små
 *  (en liste af besked-id'er), så der er ingen grund til at trække en ny
 *  afhængighed ind for det.
 *
 *  Ingen server-side: en pin er en privat bogmærkning af noget der allerede
 *  ligger i samtalen. Den skal ikke koste et kald, og den skal virke offline.
 */

const PRAEFIKS = 'jarvis:pinned:'
const MAKS = 50   // en «pin» der rummer alt er ikke en pin

function noegle(sessionId: string): string {
  // SecureStore tillader kun [A-Za-z0-9._-]; session-id'er kan indeholde andet.
  return PRAEFIKS + String(sessionId || 'default').replace(/[^A-Za-z0-9._-]/g, '_')
}

export async function laesPins(sessionId: string): Promise<string[]> {
  try {
    const raa = await SecureStore.getItemAsync(noegle(sessionId))
    if (!raa) return []
    const v = JSON.parse(raa)
    return Array.isArray(v) ? v.filter((x) => typeof x === 'string') : []
  } catch {
    // Et ulæseligt lager må ikke koste adgang til samtalen.
    return []
  }
}

async function skriv(sessionId: string, ids: string[]): Promise<void> {
  try {
    await SecureStore.setItemAsync(noegle(sessionId), JSON.stringify(ids.slice(-MAKS)))
  } catch {
    /* stille: en pin der ikke kan gemmes må ikke vælte UI'et */
  }
}

/** Slå fast/løs. Returnerer den nye liste, så kalderen kan sætte state uden
 *  at læse igen. */
export async function skiftPin(sessionId: string, messageId: string): Promise<string[]> {
  const id = String(messageId || '')
  if (!id) return laesPins(sessionId)
  const nu = await laesPins(sessionId)
  const ny = nu.includes(id) ? nu.filter((x) => x !== id) : [...nu, id]
  await skriv(sessionId, ny)
  return ny
}

export async function ryd(sessionId: string): Promise<void> {
  try {
    await SecureStore.deleteItemAsync(noegle(sessionId))
  } catch {
    /* stille */
  }
}

/** Beskederne der er fastgjort, i samtalens egen rækkefølge — ikke i den
 *  rækkefølge de blev pinnet. Man leder efter dem dér hvor de stod. */
export function pinnedeIRaekkefoelge<T extends { id: string }>(
  beskeder: T[], pins: string[],
): T[] {
  const saet = new Set(pins)
  return beskeder.filter((m) => saet.has(String(m.id)))
}
