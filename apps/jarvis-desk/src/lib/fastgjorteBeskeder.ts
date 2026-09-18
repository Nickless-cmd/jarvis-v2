/**
 * Fastgjorte beskeder — de få linjer man vil kunne finde igen.
 *
 * Bjørn 18/9-2026: pin-knappen skulle «kobles til noget rigtigt». Den var ren
 * `useState` i handlingsrækken: den farvede sig selv og glemte det ved næste
 * tegning. Ikke en gemt markering, bare en knap der så ud som om den huskede.
 *
 * ## Samme semantik som mobilen
 *
 * `apps/mobile/src/lib/pinnedMessages.ts` har gjort det her siden før: pr.
 * session, loft på 50, ingen server. Navnene her er de samme, så de to sider
 * kan sammenlignes linje for linje og ikke driver fra hinanden. Forskellen er
 * lageret — mobilen har SecureStore, desk har localStorage — og at desk er
 * synkron, fordi localStorage er det.
 *
 * ## Hvorfor ikke serverside
 *
 * En pin er en privat bogmærkning af noget der ALLEREDE ligger i samtalen.
 * Den skal ikke koste et kald, og den skal virke når nettet ikke gør. Bliver
 * det senere noget der skal følge med til telefonen, er det en anden beslutning
 * end den her — og den skal tages med åbne øjne, ikke som en bivirkning.
 *
 * ## Hvor de fører hen
 *
 * Mobilen gemmer pins men VISER dem aldrig — `pinnedeIRaekkefoelge` har kun
 * testen som kalder. En pin man ikke kan navigere til er knap nok fastgjort,
 * så i desk bliver et pin til et anker på besked-skinnen ved siden af
 * kapitlerne. Se `railAnkre.ts`.
 */
const PRAEFIKS = 'jarvis-desk:fastgjort:'
const MAKS = 50   // en «pin» der rummer alt er ikke en pin

function noegle(sessionId: string): string {
  return PRAEFIKS + String(sessionId || 'default')
}

export function laesPins(sessionId: string): string[] {
  try {
    const raa = localStorage.getItem(noegle(sessionId))
    if (!raa) return []
    const v = JSON.parse(raa)
    return Array.isArray(v) ? v.filter((x): x is string => typeof x === 'string') : []
  } catch {
    // Et ulæseligt lager må ikke koste adgang til samtalen.
    return []
  }
}

function skriv(sessionId: string, ids: string[]): void {
  try {
    // Loftet klipper de ÆLDSTE væk. Den nyeste pin er den man lige satte.
    localStorage.setItem(noegle(sessionId), JSON.stringify(ids.slice(-MAKS)))
  } catch {
    /* stille: en pin der ikke kan gemmes må ikke vælte UI'et */
  }
}

/** Slå fast/løs. Returnerer den nye liste, så kalderen kan sætte state uden
 *  at læse igen. */
export function skiftPin(sessionId: string, messageId: string): string[] {
  const id = String(messageId || '')
  if (!id) return laesPins(sessionId)
  const nu = laesPins(sessionId)
  const ny = nu.includes(id) ? nu.filter((x) => x !== id) : [...nu, id]
  skriv(sessionId, ny)
  return ny
}

export function ryd(sessionId: string): void {
  try {
    localStorage.removeItem(noegle(sessionId))
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
