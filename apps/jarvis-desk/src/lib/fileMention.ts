import type { ProjectFil } from './projectApi'

export interface AktivMention {
  start: number   // indeks for '@'
  query: string   // det der står efter '@' frem til cursoren
}

/** Finder den @-mention cursoren står i — eller null.
 *
 *  `@` tæller kun som mention-start i begyndelsen af feltet eller efter
 *  whitespace, så en e-mail (bjorn@srvlab.dk) ikke åbner en filliste.
 */
export function findAktivMention(tekst: string, caret: number): AktivMention | null {
  if (caret < 0 || caret > tekst.length) return null
  for (let i = caret - 1; i >= 0; i--) {
    const c = tekst[i] ?? ''
    if (c === '@') {
      const før = i === 0 ? '' : (tekst[i - 1] ?? '')
      if (før !== '' && !/\s/.test(før)) return null
      return { start: i, query: tekst.slice(i + 1, caret) }
    }
    if (/\s/.test(c)) return null
  }
  return null
}

/** Subsekvens-match: giver point, eller -1 hvis tegnene ikke findes i rækkefølge. */
function score(rel: string, q: string): number {
  if (!q) return 0
  const lav = rel.toLowerCase()
  const basen = lav.slice(lav.lastIndexOf('/') + 1)

  // Direkte træf vejer tungest, og et træf i filnavnet mere end i mappestien.
  const iBase = basen.indexOf(q)
  if (iBase === 0) return 1000
  if (iBase > 0) return 800 - iBase
  const iSti = lav.indexOf(q)
  if (iSti >= 0) return 600 - Math.min(iSti, 200)

  // Ellers: tegnene skal optræde i rækkefølge (fx "ctsp" → core/tools/simple…).
  let j = 0
  for (const c of lav) {
    if (c === q[j]) j++
    if (j === q.length) return 300
  }
  return -1
}

/** Rangerer filer mod en query. Korte stier vinder ved lige point. */
export function rangerFiler(filer: ProjectFil[], query: string, maks = 8): ProjectFil[] {
  const q = query.toLowerCase()
  const med: Array<{ f: ProjectFil; s: number }> = []
  for (const f of filer) {
    const s = score(f.rel, q)
    if (s >= 0) med.push({ f, s })
  }
  med.sort((a, b) => b.s - a.s || a.f.rel.length - b.f.rel.length || a.f.rel.localeCompare(b.f.rel))
  return med.slice(0, maks).map((m) => m.f)
}

/** Indsætter den valgte sti i stedet for mentionen. Returnerer ny tekst + cursor. */
export function indsætMention(
  tekst: string,
  mention: AktivMention,
  rel: string,
): { tekst: string; caret: number } {
  const slut = mention.start + 1 + mention.query.length
  // Sæt kun mellemrum ind hvis der ikke allerede står ét — ellers får man
  // «@README.md  og resten» når man retter midt i en sætning.
  const mellemrum = /\s/.test(tekst[slut] ?? '') ? '' : ' '
  const ny = `${tekst.slice(0, mention.start)}@${rel}${mellemrum}${tekst.slice(slut)}`
  return { tekst: ny, caret: mention.start + 1 + rel.length + mellemrum.length }
}
