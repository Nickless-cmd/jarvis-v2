export const BILLED_GRID_GAP = 2
export const BILLED_FLISE_MIN_BREDDE = 72
export const BILLED_FLISE_MAX_BREDDE = 200

/**
 * Fordeler fliser i balancerede pakkerækker.
 *
 * Rækkens aspekt er udledt af flisernes egne proportioner; det modtages ikke
 * fra serveren som et separat `row_aspect_ratio`.
 */
export function fordelBilledRaekker(
  antal: number,
  tilgaengeligBredde: number,
  minBredde = BILLED_FLISE_MIN_BREDDE,
  maxBredde = BILLED_FLISE_MAX_BREDDE,
  gap = BILLED_GRID_GAP,
): number[] {
  const fliser = Math.max(0, Math.floor(antal))
  if (fliser === 0) return []

  const bredde = Math.max(0, tilgaengeligBredde)
  // En række behøver ikke optage mere plads end fliserne kan bruge ved deres
  // maksimum. Resten står tomt i stedet for at strække fliserne over 200 px.
  const brugbarBredde = Math.min(bredde, fliser * maxBredde + (fliser - 1) * gap)
  const flestPrRaekke = Math.min(
    fliser,
    Math.max(1, Math.floor((brugbarBredde + gap) / (minBredde + gap))),
  )
  const raekker = Math.max(1, Math.ceil(fliser / flestPrRaekke))
  const grundAntal = Math.floor(fliser / raekker)
  const ekstra = fliser % raekker

  // Den balancerede fordeling undgår en enlig sidste flise.
  return Array.from({ length: raekker }, (_, i) => grundAntal + (i < ekstra ? 1 : 0))
}
