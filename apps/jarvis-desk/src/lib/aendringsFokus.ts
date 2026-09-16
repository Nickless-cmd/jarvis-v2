/** Lille pub/sub: «åbn Ændringer-ruden på DENNE fil».
 *
 *  Bjørn 16/9-2026: «når man klikker på dem åbner de i den changes panel du
 *  lige har lavet og viser diff».
 *
 *  Modul-niveau af samme grund som coworkZone: afsenderen er et kort dybt nede
 *  i beskedstrømmen (EditedFilesCard inde i BlocksRenderer inde i MessageRow),
 *  og modtageren er ChatView. De deler ingen provider-gren, og at trække en
 *  callback gennem fem lag props ville binde hvert af dem til en detalje de
 *  ikke har andet med at gøre.
 */
type Lytter = (sti: string) => void

let lyttere: Lytter[] = []

export function visAendring(sti: string): void {
  for (const l of lyttere) {
    try { l(sti) } catch { /* en lytter må ikke vælte de andre */ }
  }
}

export function paaAendringsFokus(lytter: Lytter): () => void {
  lyttere.push(lytter)
  return () => { lyttere = lyttere.filter((l) => l !== lytter) }
}
