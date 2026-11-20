/**
 * DIL lag 3: compile-lag. Markup (JSON) → program + konstanttabel.
 *
 * ## Hvad den gør
 * Én gennemgang over fladens træ, før `parseNativeRichSpec` tolker det:
 *   1. Halv JSON trunkeres til sidste komplette konstruktion (`reparérDelvisJson`) — S2.
 *   2. `{#each}`/`{#if}` (lag 2, `udfoldKontrol`) udfoldes pr. TEKST, med fladens `data`-objekt
 *      som kontekst. `data` er ikke en del af den tegnede flade og fjernes.
 *   3. Hvert element (objekt med `type`) kompileres for sig i en try/catch: en fejl dræber ÉT
 *      element (det droppes og noteres i `diagnostik`), ikke hele fladen.
 *   4. Alle tekster samles i en konstanttabel; programmet er en flad liste af instruktioner
 *      `{ id, forælder, type, konstanter: [indeks…] }` i dokumentorden.
 *
 * ## To forbud (spec lag 3)
 *   - Roden må ikke TRUNKERES: en halv rod uden komplet `type` giver `null` (intet at tegne),
 *     ikke en gættet rod.
 *   - Roden må ikke FJERNES: fejler roden selv, bliver den stående med sin rå tekst, og fejlen
 *     noteres. Kun børn kan droppes.
 *
 * Renderen tolker stadig den udfoldede `rod` (via `parseNodeObj`); programmet bruges til
 * efterkontrollen (`fladeVisning.ts`, S3). Filen er byte-identisk i desk og mobil.
 */
import { reparérDelvisJson } from './delvisJson'
import { udfoldKontrol } from './udtryk'

type Json = Record<string, unknown>

export interface FladeInstruktion {
  id: number
  forælder: number
  type: string
  konstanter: number[]
}

export interface FladeDiagnostik {
  sti: string
  grund: string
}

export interface FladeProgram {
  rod: Json
  program: FladeInstruktion[]
  konstanter: string[]
  diagnostik: FladeDiagnostik[]
  /** Kilden var halv og blev klippet til sidste komplette konstruktion. */
  trunkeret: boolean
}

const erObjekt = (v: unknown): v is Json => !!v && typeof v === 'object' && !Array.isArray(v)
const harType = (v: unknown): v is Json => erObjekt(v) && typeof v.type === 'string' && v.type !== ''

export function kompilérFlade(raa: string, delvis = false): FladeProgram | null {
  let raw: unknown
  let trunkeret = false
  try {
    raw = JSON.parse(raa)
  } catch {
    if (!delvis) return null
    const repareret = reparérDelvisJson(raa)
    if (!repareret) return null
    try { raw = JSON.parse(repareret) } catch { return null }
    trunkeret = true
  }
  // Forbud 1: roden må ikke trunkeres. En rod uden komplet `type` kan ikke tegnes.
  if (!harType(raw)) return null

  const data: Record<string, unknown> = erObjekt(raw.data) ? raw.data : {}
  const diagnostik: FladeDiagnostik[] = []
  const konstanter: string[] = []
  const indeks = new Map<string, number>()
  const program: FladeInstruktion[] = []

  const konstant = (s: string): number => {
    let i = indeks.get(s)
    if (i === undefined) { i = konstanter.length; konstanter.push(s); indeks.set(s, i) }
    return i
  }

  /** Kopi af ét element-undertræ hvor strenge er udfoldet. Kaster ved en fejl i elementet. */
  function tekster(v: unknown, sti: string, ud: number[], erRod: boolean): unknown {
    if (typeof v === 'string') {
      const r = udfoldKontrol(v, data)
      if (r.advarsler.length > 0) throw new Error(`${sti}: ${r.advarsler[0]}`)
      ud.push(konstant(r.tekst))
      return r.tekst
    }
    if (Array.isArray(v)) return v.map((x, i) => tekster(x, `${sti}[${i}]`, ud, false))
    if (erObjekt(v)) {
      const kopi: Json = {}
      for (const [k, x] of Object.entries(v)) {
        if (erRod && k === 'data') continue
        // Underelementer (med `type`, i en børneliste) kompileres af `node` — ikke her.
        kopi[k] = tekster(x, `${sti}.${k}`, ud, false)
      }
      return kopi
    }
    return v
  }

  function node(n: Json, sti: string, forælder: number, erRod: boolean): Json | null {
    const id = program.length
    const instr: FladeInstruktion = { id, forælder, type: String(n.type), konstanter: [] }
    program.push(instr)
    // Børnelisterne holdes ude af elementets egne tekster; hvert barn kompileres for sig.
    const skjult: Array<[unknown[], unknown[]]> = []
    const eget: Json = { ...n }
    if (Array.isArray(n.children)) { const ny: unknown[] = []; skjult.push([n.children, ny]); eget.children = [] }
    if (Array.isArray(n.tabs)) {
      eget.tabs = n.tabs.map((t) => {
        if (!erObjekt(t) || !Array.isArray(t.children)) return t
        const ny: unknown[] = []
        skjult.push([t.children, ny])
        return { ...t, children: [] }
      })
    }
    let ud: Json
    try {
      ud = tekster(eget, sti, instr.konstanter, erRod) as Json
    } catch (e) {
      const grund = e instanceof Error ? e.message : String(e)
      diagnostik.push({ sti, grund })
      if (!erRod) { program.length = id; return null }  // forbud 2 gælder kun roden
      ud = { ...n }
      delete ud.data
    }
    // Børn
    let k = 0
    const kopiLister = [ud.children, ...(Array.isArray(ud.tabs) ? ud.tabs.map((t) => erObjekt(t) ? t.children : undefined) : [])]
    const maal = kopiLister.filter(Array.isArray) as unknown[][]
    for (const [kilde] of skjult) {
      const ny: unknown[] = []
      kilde.forEach((barn, i) => {
        if (!harType(barn)) { ny.push(barn); return }
        const k2 = node(barn, `${sti}.children[${i}]`, id, false)
        if (k2) ny.push(k2)
      })
      const slot = maal[k]
      if (slot) slot.push(...ny)
      k += 1
    }
    return ud
  }

  const rod = node(raw, '$', -1, true) as Json
  return { rod, program, konstanter, diagnostik, trunkeret }
}
