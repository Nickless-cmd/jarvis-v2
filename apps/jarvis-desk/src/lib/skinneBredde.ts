/**
 * Skinnens bredde — trukket med musen, husket på tværs af genstarter.
 *
 * Bjørn 26/9-2026: «i højre side af desk de 3 paneler ændringer,
 * baggrundsjobs og browser panelet… jeg mangler træk/slip altså at kunne
 * udvide dem til siden.. lige som man kan med venstre panel.»
 *
 * Samme mønster som `sidebarBredde.ts`, og af samme grund: bredden bor i
 * CSS-variablen `--skinne-bredde` på :root, fordi BÅDE skinnen selv
 * (`.code-right-stack`) og den padding samtalen gør plads med
 * (`.har-skinne …`) læser den. Trækket skriver derfor samme sted som
 * stylesheet'et — ikke en inline-bredde på skinnen, som ville lade paddingen
 * blive stående og efterlade en stribe tomt.
 */
export const BREDDE_NOEGLE = 'jarvis-desk:skinne-bredde'

/** Grænserne. Under 280 px kan en jobtitel og en filsti ikke læses; over
 *  760 px er det ikke længere et panel, men en kolonne der spiser samtalen. */
export const MIN_BREDDE = 280
export const MAKS_BREDDE = 760
export const STANDARD_BREDDE = 360

export function klem(px: number): number {
  if (!Number.isFinite(px)) return STANDARD_BREDDE
  return Math.round(Math.min(MAKS_BREDDE, Math.max(MIN_BREDDE, px)))
}

/** Læs den gemte bredde. Ugyldig eller manglende værdi giver standarden —
 *  ikke 0, som ville skjule skinnen uden at nogen havde bedt om det. */
export function laesBredde(): number {
  try {
    const raa = localStorage.getItem(BREDDE_NOEGLE)
    if (!raa) return STANDARD_BREDDE
    const n = Number(raa)
    return Number.isFinite(n) && n > 0 ? klem(n) : STANDARD_BREDDE
  } catch {
    // Privat vindue eller blokeret lager: en bredde er ikke værd at vælte
    // appen over.
    return STANDARD_BREDDE
  }
}

export function gemBredde(px: number): void {
  try { localStorage.setItem(BREDDE_NOEGLE, String(klem(px))) } catch { /* se ovenfor */ }
}

/** Skriv bredden derhen hvor BEGGE læsere ser den. */
export function anvendBredde(px: number): void {
  document.documentElement.style.setProperty('--skinne-bredde', `${klem(px)}px`)
}
