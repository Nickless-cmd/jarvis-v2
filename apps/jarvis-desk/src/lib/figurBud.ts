/**
 * Bud fra Jarvis-figuren til hovedvinduet, der skal overleve at en flade
 * monteres EFTER buddet kom.
 *
 * Stemme-ikonet under figuren (Codex' samme ikon) viser hovedvinduet og
 * skal starte samtale-mode. Men står man i Arbejde, findes ChatView ikke
 * endnu — den monteres først når TakeoverHost har skiftet til chat. Et
 * almindeligt event ville ramme ingen. Derfor ligger buddet her, til den
 * første der kan tage det.
 */
type Lytter = () => void

let stemmeVenter = false
const lyttere = new Set<Lytter>()

export function bestilStemme(): void {
  stemmeVenter = true
  lyttere.forEach((l) => l())
}

/** Tag buddet (én gang). Kaldes ved montering og når der bestilles. */
export function tagStemmeBud(): boolean {
  const v = stemmeVenter
  stemmeVenter = false
  return v
}

export function onStemmeBud(l: Lytter): () => void {
  lyttere.add(l)
  return () => { lyttere.delete(l) }
}
