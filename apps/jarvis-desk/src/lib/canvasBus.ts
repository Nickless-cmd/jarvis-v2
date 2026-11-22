/** Lille pub/sub fra canvas-panelet til samtalen.
 *
 *  Panelet bor i App (SplitLayout/InspectorPanel), men beskeden skal ud af
 *  ChatView, som ejer send-stien og køen. De deler ingen provider-gren, så
 *  samme mønster som `fileTreeHighlight`: modul-niveau, ingen context-plumbing.
 */
export interface CanvasSend {
  titel: string
  tekst: string
}

type Lytter = (c: CanvasSend) => void
let lyttere: Lytter[] = []

/** Returnerer true hvis nogen lytter — panelet kan ellers ikke love at noget skete. */
export function sendCanvas(c: CanvasSend): boolean {
  if (lyttere.length === 0) return false
  for (const l of lyttere) {
    try { l(c) } catch { /* en lytter må ikke vælte de andre */ }
  }
  return true
}

export function onCanvasSend(l: Lytter): () => void {
  lyttere.push(l)
  return () => { lyttere = lyttere.filter((x) => x !== l) }
}

/** Gør canvas-teksten til en besked. Fenced, så modellen ser hvor dokumentet slutter. */
export function canvasBesked(c: CanvasSend): string {
  return `Jeg har rettet i canvas «${c.titel}». Her er den nuværende version:\n\n\`\`\`\n${c.tekst}\n\`\`\``
}
