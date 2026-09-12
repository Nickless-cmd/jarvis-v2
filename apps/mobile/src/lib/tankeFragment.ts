/**
 * Det sidste stykke tanke — det man kan nå at læse mens den løber.
 *
 * ## Hvorfor ikke bare «Tænker…»
 *
 * Bjørn 12/9-2026: linjen «viser bare tænker», og den burde vise de
 * tanke-fragmenter som live metadata. Forskellen er den samme som mellem en
 * spinner og en ring der fyldes: «der sker noget» mod «dét her sker».
 *
 * ## Hvorfor det SIDSTE og ikke det første
 *
 * Fordi det er dér han er nu. Begyndelsen af en tankerække er det man allerede
 * har set rulle forbi.
 *
 * ## Hvorfor sætning og ikke tegn
 *
 * En hård afskæring midt i et ord flimrer for hvert token der kommer. Ved at
 * tage den sidste hele linje og først derefter forkorte, står teksten stille
 * indtil der faktisk er en ny tanke.
 */
export function tankeFragment(tekst: string | undefined, maks = 80): string {
  const linjer = String(tekst ?? '')
    .split('\n')
    .map((l) => l.trim())
    .filter(Boolean)
  const sidste = linjer[linjer.length - 1] ?? ''
  if (!sidste) return ''
  if (sidste.length <= maks) return sidste
  // Skær ved et mellemrum hvis der er et i nærheden — et ord der er hugget
  // midt over ligner en fejl, ikke en forkortelse.
  const hugget = sidste.slice(0, maks)
  const mellemrum = hugget.lastIndexOf(' ')
  return (mellemrum > maks - 20 ? hugget.slice(0, mellemrum) : hugget).trimEnd() + '…'
}
