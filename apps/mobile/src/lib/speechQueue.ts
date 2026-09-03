/**
 * Deler et svar der stadig strømmer op i stykker der kan læses højt NU.
 *
 * Før ventede oplæsningen til hele svaret stod færdigt. På et langt svar er det
 * mange sekunders tavshed hvor der ikke sker noget — og i en samtale er tavshed
 * ikke neutral, den ligner at der er gået noget i stykker.
 *
 * Enheden er en SÆTNING, ikke et ord og ikke et afsnit. Et ord ad gangen ville
 * gøre syntesen hakkende (hvert stykke får sin egen intonation), og et afsnit
 * ad gangen ville genindføre ventetiden.
 */

/** Et skilletegn efterfulgt af mellemrum/linjeskift/slut. Decimaltal som 3.4
 *  rammes ikke af sig selv — dér følger et ciffer, ikke et mellemrum. */
const BOUNDARY = '[.!?…:](?=\\s|$)|\\n'

/** Danske forkortelser med ét punktum. En forkortelse der fejlagtigt tælles som
 *  sætningsslut giver en pause MIDT i en sætning; en sætningsslut der
 *  fejlagtigt tælles som forkortelse gør bare stykket lidt længere. Den
 *  billigste fejl er at holde igen, så listen må gerne være rundhåndet. */
const ABBREV = new Set([
  'ca', 'kl', 'nr', 'jf', 'stk', 'mio', 'mia', 'pga', 'inkl', 'ekskl',
  'evt', 'dvs', 'osv', 'bl', 'fx', 'th', 'tv', 'ang', 'iflg', 'vedr',
])

/**
 * Er punktummet på `dot` slutningen på en forkortelse frem for på en sætning?
 *
 * To tegn på det: ordet står på listen, eller ordet indeholder selv et punktum
 * («bl.a.», «f.eks.», «m.m.») — dét mønster findes ikke i almindelige ord.
 */
function isAbbreviation(text: string, dot: number): boolean {
  let i = dot - 1
  while (i >= 0 && !/\s/.test(text[i] as string)) i--
  const token = text.slice(i + 1, dot)
  if (token.includes('.')) return true
  return ABBREV.has(token.toLowerCase())
}

/** Uden en øvre grænse ville en lang stribe uden tegnsætning aldrig blive sagt. */
const HARD_WRAP = 260

/** Under dette er et stykke for kort til at stå alene — «Ja.» efterfulgt af en
 *  pause lyder afhakket. Det slås sammen med det næste i stedet. */
const MIN_CHARS = 24

export interface SpeakableResult {
  /** Stykker klar til at blive sagt, i rækkefølge. */
  chunks: string[]
  /** Hvor langt inde i `full` vi nu er nået. Gives tilbage næste gang. */
  taken: number
}

/** Er der en kodeblok der er begyndt men ikke lukket endnu? */
export function hasOpenFence(text: string): boolean {
  return (text.match(/```/g) || []).length % 2 === 1
}

/**
 * Hent de stykker af `full` der kan siges nu, givet at `taken` tegn allerede er
 * afleveret. `done` = svaret er færdigt, så resten skal med uanset hvad.
 */
export function takeSpeakable(full: string, taken: number, done = false): SpeakableResult {
  const pending = full.slice(taken)
  if (!pending.trim()) return { chunks: [], taken: done ? full.length : taken }

  // En kodeblok der er åbnet men ikke lukket holdes tilbage. Halvdelen af en
  // kodeblok læst højt er værre end at vente — og når den lukker, bliver den
  // alligevel nævnt som «bash-kode» i stedet for at blive stavet.
  if (!done && hasOpenFence(pending)) return { chunks: [], taken }

  const chunks: string[] = []
  // `start` er begyndelsen på det stykke vi er ved at samle. Den flytter sig
  // KUN når noget er afleveret — det er dét der slår korte stumper sammen med
  // den næste sætning i stedet for at sige dem for sig.
  let start = 0
  const re = new RegExp(BOUNDARY, 'g')
  let m: RegExpExecArray | null
  while ((m = re.exec(pending)) !== null) {
    const end = m.index + m[0].length
    if (m[0] === '.' && isAbbreviation(pending, m.index)) continue
    const piece = pending.slice(start, end).trim()
    if (!piece) { start = end; continue }
    if (piece.length < MIN_CHARS) continue
    chunks.push(piece)
    start = end
  }

  let rest = pending.slice(start)
  if (!done && rest.length > HARD_WRAP) {
    const cut = rest.lastIndexOf(' ', HARD_WRAP)
    if (cut > MIN_CHARS) {
      const head = rest.slice(0, cut).trim()
      if (head) { chunks.push(head); start += cut + 1 }
      rest = pending.slice(start)
    }
  }

  if (done) {
    const tail = rest.trim()
    if (tail) chunks.push(tail)
    return { chunks, taken: full.length }
  }

  return { chunks, taken: taken + start }
}
