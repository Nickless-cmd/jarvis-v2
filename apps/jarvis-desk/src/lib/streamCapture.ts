/**
 * Rå optagelse af ALT der streames — set fra klienten.
 *
 * Bjørn 8/9-2026: «lad os logge mine samtaler over de næste par dage … den
 * skal optage helt ude fra klienten, ALT streaming, alt.»
 *
 * ## Hvorfor i klienten
 *
 * Serverens data kunne ikke forklare det han ser. Målt over 30 timer:
 *
 *     samme runde startet flere gange      0
 *     round-retries                        0
 *     udbyder-kald vs. runder              +1 i 104 af 114 (arkitektur)
 *     samme værktøj i træk                 343
 *     samme værktøj OG samme argumenter    0
 *
 * Alt peger på at der ikke genereres dobbelt. Men han ser noget — og det han
 * ser, ser han i klienten. Så optagelsen sker på de **rå SSE-rammer før de
 * parses**, dér hvor intet endnu er fortolket eller kasseret.
 *
 * ## Kun hans egne
 *
 * Optagelsen bor i HANS desk-app på HANS maskine. Andres samtaler passerer
 * aldrig denne proces. Det er en stærkere garanti end et bruger-filter ville
 * være — der er ikke noget at filtrere.
 *
 * ## Filen er hele samtalen i klartekst
 *
 * Derfor: skrives lokalt, sendes aldrig nogen steder, og **udløber af sig
 * selv** efter det antal dage der blev slået til. En optagelse man skal huske
 * at slukke, bliver ikke slukket.
 */

export interface Ramme {
  /** Millisekunder siden epoch — rækkefølge og huller er hele pointen. */
  t: number
  /** SSE-event-navnet, fx `message_start`, `content_block_delta`. */
  e: string
  /** Rå data-streng, uparset. Også hvis den er ugyldig JSON. */
  d: string
}

type Bro = {
  capture?: {
    status: () => Promise<{ active: boolean }>
    append: (lines: string[]) => Promise<boolean>
  }
}

function bro(): Bro['capture'] | undefined {
  return (window as unknown as { jarvisDesk?: Bro }).jarvisDesk?.capture
}

// Skrivningen batches: én IPC pr. ramme ville lægge tusindvis af kald oven i
// en stream vi netop mistænker for timing-problemer. Måleredskabet må ikke
// ændre det det måler.
const FLUSH_MS = 400
const MAX_BUFFER = 500

let aktiv: boolean | null = null       // null = ikke spurgt endnu
let buffer: Ramme[] = []
let timer: ReturnType<typeof setTimeout> | null = null

/** Spørg broen om optagelsen kører. Cachet — status ændrer sig ikke pr. ramme. */
export async function opdaterStatus(): Promise<boolean> {
  const c = bro()
  if (!c) { aktiv = false; return false }
  try {
    aktiv = (await c.status()).active
  } catch {
    aktiv = false
  }
  return aktiv
}

async function flush(): Promise<void> {
  timer = null
  const c = bro()
  if (!c || buffer.length === 0) { buffer = []; return }
  const linjer = buffer.map((r) => JSON.stringify(r))
  buffer = []
  try {
    await c.append(linjer)
  } catch {
    // En fejlet skrivning må aldrig kunne vælte streamen. Rammerne er tabt,
    // og det er den rigtige pris — optagelsen er et redskab, ikke data nogen
    // regner med.
  }
}

/**
 * Optag én rå SSE-ramme. Kaldes fra `streamClient` FØR parsing.
 *
 * Synkron og billig: alt tungt sker i flush. Kaster aldrig.
 */
export function optag(eventName: string, dataStr: string): void {
  if (aktiv === false) return
  if (aktiv === null) {
    // Første ramme: spørg én gang, og lad denne slippe forbi. Vi taber højst
    // én ramme ved appstart frem for at gøre hver ramme til et await.
    void opdaterStatus()
    return
  }
  buffer.push({ t: Date.now(), e: eventName, d: dataStr })
  if (buffer.length >= MAX_BUFFER) { void flush(); return }
  if (timer === null) timer = setTimeout(() => { void flush() }, FLUSH_MS)
}

/** Til tests og til at tømme før appen lukker. */
export function _nulstil(): void {
  aktiv = null
  buffer = []
  if (timer !== null) { clearTimeout(timer); timer = null }
}

export function _sætAktiv(v: boolean | null): void { aktiv = v }
export function _buffer(): Ramme[] { return buffer }
export async function _flushNu(): Promise<void> {
  if (timer !== null) { clearTimeout(timer); timer = null }
  await flush()
}
