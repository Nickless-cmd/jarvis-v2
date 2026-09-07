/** Det Android sender ind, når man deler noget TIL Jarvis.
 *
 *  Filtrene i app.json gør at Jarvis står i del-arket. Det her afgør hvad der
 *  så skal ske — og det er ikke oplagt: en delt URL, en delt tekst og et delt
 *  billede skal behandles forskelligt, selvom Android leverer dem gennem
 *  samme dør.
 *
 *  Modulet er RENT. Det modtager en allerede udpakket intent og siger hvad
 *  appen skal gøre. Selve udpakningen hører til i den native lag, og at
 *  blande de to ville gøre denne logik umulig at teste uden en telefon.
 *
 *  Vigtigt valg: delt indhold sendes IKKE af sig selv. Det lander i
 *  komposeren, hvor man kan skrive hvad man vil have gjort ved det. En app
 *  der sender af sig selv, fordi man delte noget, tager en beslutning man
 *  ikke har truffet.
 */

export interface DeltIntent {
  /** "text/plain", "image/jpeg", "application/pdf" … */
  mimeType?: string
  /** EXTRA_TEXT — tekst eller en URL. */
  text?: string
  /** EXTRA_SUBJECT — fx en sides titel når man deler fra en browser. */
  subject?: string
  /** EXTRA_STREAM — content:// URI'er til filer/billeder. */
  uris?: string[]
}

export type DeltHandling =
  | { slags: 'tekst'; udkast: string }
  | { slags: 'link'; url: string; udkast: string }
  | { slags: 'filer'; uris: string[]; udkast: string }
  | { slags: 'ingenting' }

const URL_MOENSTER = /^https?:\/\/\S+$/i

export function tolkDeling(intent: DeltIntent): DeltHandling {
  const uris = (intent.uris ?? []).filter((u) => typeof u === 'string' && u.trim())
  const tekst = String(intent.text ?? '').trim()
  const emne = String(intent.subject ?? '').trim()

  if (uris.length) {
    // Delte filer: teksten er ofte en billedtekst eller tom.
    return { slags: 'filer', uris, udkast: tekst || emne || '' }
  }
  if (!tekst) return { slags: 'ingenting' }

  if (URL_MOENSTER.test(tekst)) {
    // En delt URL uden emne er bar; med emne ved vi hvad siden hed.
    return { slags: 'link', url: tekst, udkast: emne ? `${emne}\n${tekst}` : tekst }
  }
  // Emnet gentages ikke hvis teksten allerede indeholder det.
  const udkast = emne && !tekst.includes(emne) ? `${emne}\n\n${tekst}` : tekst
  return { slags: 'tekst', udkast }
}

/** Kan vi overhovedet tage imod den type? Bruges til at sige det ærligt frem
 *  for at tage imod noget vi taber bagefter. */
export function kanModtage(mimeType?: string): boolean {
  const m = String(mimeType ?? '').toLowerCase()
  if (!m) return true                     // ren tekst-deling har ofte ingen type
  return m.startsWith('text/') || m.startsWith('image/') || m === 'application/pdf'
}
