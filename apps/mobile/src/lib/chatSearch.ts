import type { ChatMessage } from './types'

/** Søgning INDE i den aktive samtale.
 *
 *  En lang tur kan have hundredvis af beskeder, og den eneste vej tilbage til
 *  «hvad var det nu han sagde om broen» har været at scrolle. Søgningen er
 *  ren klient-side: beskederne ligger allerede i hukommelsen, så et
 *  server-kald ville være langsommere og virke dårligere offline.
 */

export interface SoegeTraef {
  /** Beskedens id — bruges til at scrolle hen til den. */
  id: string
  /** Indeks i den viste liste, så listen kan scrolle uden opslag. */
  index: number
  rolle: ChatMessage['role']
  /** Uddrag med træffet i midten, så man kan genkende det uden at åbne. */
  uddrag: string
  /** Hvor i uddraget træffet står — til fremhævning. */
  traefStart: number
  traefLaengde: number
}

const UDDRAG_FOER = 40
const UDDRAG_EFTER = 60

/** Teksten der faktisk kan søges i.
 *
 *  `content` er hele turen klasket sammen; har beskeden strukturerede blokke,
 *  er de sandheden — men til søgning vil man finde ALT man kan se, også
 *  værktøjs-output. Derfor slås blokkenes tekst sammen med content.
 */
export function soegbarTekst(m: ChatMessage): string {
  const dele: string[] = [String(m.content ?? '')]
  const blokke = (m as unknown as { blocks?: unknown }).blocks
  if (Array.isArray(blokke)) {
    for (const b of blokke) {
      if (b && typeof b === 'object') {
        const o = b as Record<string, unknown>
        for (const n of ['text', 'thinking', 'content']) {
          if (typeof o[n] === 'string') dele.push(o[n] as string)
        }
      }
    }
  }
  return dele.filter(Boolean).join('\n')
}

function lavUddrag(tekst: string, i: number, laengde: number) {
  const fra = Math.max(0, i - UDDRAG_FOER)
  const til = Math.min(tekst.length, i + laengde + UDDRAG_EFTER)
  const foer = fra > 0 ? '…' : ''
  const efter = til < tekst.length ? '…' : ''
  // Nye linjer gør uddraget uroligt i en enkelt-linjes række.
  const raa = tekst.slice(fra, til).replace(/\s+/g, ' ')
  return { uddrag: `${foer}${raa}${efter}`, start: foer.length + (i - fra) }
}

/** Find alle beskeder der matcher. Tom query → ingen træf (ikke ALLE). */
export function soegIBeskeder(beskeder: ChatMessage[], query: string): SoegeTraef[] {
  const q = String(query ?? '').trim().toLowerCase()
  if (q.length < 2) return []      // ét tegn matcher alt og hjælper ingen

  const ud: SoegeTraef[] = []
  beskeder.forEach((m, index) => {
    const tekst = soegbarTekst(m)
    const i = tekst.toLowerCase().indexOf(q)
    if (i < 0) return
    const { uddrag, start } = lavUddrag(tekst, i, q.length)
    ud.push({
      id: String(m.id), index, rolle: m.role,
      uddrag, traefStart: start, traefLaengde: q.length,
    })
  })
  return ud
}

/** Næste/forrige træf, med ombrydning. Tom liste → 0. */
export function flytTraef(antal: number, nuvaerende: number, retning: 1 | -1): number {
  if (antal <= 0) return 0
  return (nuvaerende + retning + antal) % antal
}
