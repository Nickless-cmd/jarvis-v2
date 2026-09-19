/**
 * Linje-diff til diff-arket (Claude Desktop §9, 19/9-2026).
 *
 * Længste fælles delsekvens på linjer — nok til én redigering, som er det et
 * kald indeholder (old_text → new_text). Store tekster (over MAKS linjer på
 * en side) regnes ikke: så vises det gamle som fjernet og det nye som
 * tilføjet, hvilket er sandt, bare mindre præcist — hellere det end at
 * fryse telefonen på en kvadratisk tabel.
 */
export type DiffLinje = { slags: ' ' | '+' | '-'; tekst: string }

export const MAKS = 600

export function linjeDiff(gammel: string, ny: string): DiffLinje[] {
  const a = gammel ? gammel.split('\n') : []
  const b = ny ? ny.split('\n') : []
  if (a.length > MAKS || b.length > MAKS) {
    return [...a.map((t) => ({ slags: '-' as const, tekst: t })), ...b.map((t) => ({ slags: '+' as const, tekst: t }))]
  }
  const n = a.length
  const m = b.length
  // lcs[i][j] = længste fælles delsekvens af a[i..] og b[j..]
  const lcs: number[][] = Array.from({ length: n + 1 }, () => new Array<number>(m + 1).fill(0))
  for (let i = n - 1; i >= 0; i--) {
    for (let j = m - 1; j >= 0; j--) {
      lcs[i]![j] = a[i] === b[j] ? lcs[i + 1]![j + 1]! + 1 : Math.max(lcs[i + 1]![j]!, lcs[i]![j + 1]!)
    }
  }
  const ud: DiffLinje[] = []
  let i = 0
  let j = 0
  while (i < n && j < m) {
    if (a[i] === b[j]) { ud.push({ slags: ' ', tekst: a[i]! }); i++; j++ }
    else if (lcs[i + 1]![j]! >= lcs[i]![j + 1]!) { ud.push({ slags: '-', tekst: a[i]! }); i++ }
    else { ud.push({ slags: '+', tekst: b[j]! }); j++ }
  }
  while (i < n) ud.push({ slags: '-', tekst: a[i++]! })
  while (j < m) ud.push({ slags: '+', tekst: b[j++]! })
  return ud
}
