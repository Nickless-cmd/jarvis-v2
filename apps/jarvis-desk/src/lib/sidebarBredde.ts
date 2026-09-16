/**
 * Sidepanelets bredde — trukket med musen, husket på tværs af genstarter.
 *
 * Bjørn 16/9-2026: «venstre panel mangler træk og slip til breden».
 *
 * Bredden bor i CSS-variablen `--sidebar-bredde` på :root, fordi BÅDE
 * gitteret (`.window`) og titelbjælkens venstrekant læser den. Trækket
 * skriver derfor samme sted som stylesheet'et — ikke en inline-bredde på
 * sidebaren, som ville lade bjælken blive stående og efterlade en stribe.
 */
export const BREDDE_NOEGLE = 'jarvis-desk:sidebar-bredde'

/** Grænserne. Under 200 px kan en sessionstitel ikke læses; over 520 px er
 *  det ikke længere et panel, men en kolonne der spiser samtalen. */
export const MIN_BREDDE = 200
export const MAKS_BREDDE = 520
export const STANDARD_BREDDE = 290

export function klem(px: number): number {
  if (!Number.isFinite(px)) return STANDARD_BREDDE
  return Math.round(Math.min(MAKS_BREDDE, Math.max(MIN_BREDDE, px)))
}

/** Læs den gemte bredde. Ugyldig eller manglende værdi giver standarden —
 *  ikke 0, som ville skjule panelet uden at nogen havde bedt om det. */
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
  document.documentElement.style.setProperty('--sidebar-bredde', `${klem(px)}px`)
}
