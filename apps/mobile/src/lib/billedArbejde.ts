/**
 * Hvilket billedarbejde kører lige nu — generering eller analyse?
 *
 * Ét opslag, så navnene ikke skal stå ordret flere steder i MessageList.
 * Da `openrouter_image_edit` kom til, var det præcis den slags der bliver
 * husket ét sted og glemt et andet. Spejler desks
 * `components/rich/ImageGeneration.tsx`.
 */

export function erBilledVaerktoej(name: string): boolean {
  return name === 'openrouter_image' || name === 'openrouter_image_edit' || name === 'pollinations_image'
}

/** Det eneste syns-værktøj i drift. `jarvis_browser_screenshot` TAGER
 *  billeder og er målt til ~0,02 s — det har intet at animere. */
export function erBilledAnalyse(name: string): boolean {
  return name === 'analyze_image'
}

export type BilledArbejde =
  | { slags: 'generering' }
  /** `kilde` er navnet, til etiketten. `sti` er den FULDE sti — den eneste af
   *  de to der kan hentes, gennem `/visning/billede`. */
  | { slags: 'analyse'; kilde: string; sti: string }

/**
 * Navnet på det billede der kigges på: sidste led af stien, ellers værten på
 * en URL. Tom når kaldet ikke siger hvad det ser på.
 *
 * `partialJson` læses FØRST-som-fallback: mens kaldet streames ind ligger
 * argumenterne dér som en streng, ikke i `input` — samme grund som `toolDiff`
 * i MessageList har den.
 */
/** Kaldets argumenter: `input` først, ellers `partialJson` mens kaldet streames
 *  ind. Én kilde til sandheden, så navn og sti ikke kan læse hver sit felt. */
function analyseArg(
  input?: Record<string, unknown>, partialJson?: string,
): Record<string, unknown> | undefined {
  if (input && Object.keys(input).length > 0) return input
  if (!partialJson) return input
  try {
    const p: unknown = JSON.parse(partialJson)
    return p && typeof p === 'object' ? (p as Record<string, unknown>) : input
  } catch {
    return input // Halvfærdig JSON under streaming — så står animationen uden navn.
  }
}

export function billedKilde(input?: Record<string, unknown>, partialJson?: string): string {
  const arg = analyseArg(input, partialJson)
  const sti = typeof arg?.image_path === 'string' ? arg.image_path : ''
  if (sti) return sti.split(/[\\/]/).filter(Boolean).pop() ?? ''
  const url = typeof arg?.image_url === 'string' ? arg.image_url : ''
  if (!url) return ''
  const m = /^[a-z][a-z0-9+.-]*:\/\/([^/?#]+)/i.exec(url.trim())
  return m?.[1] ? m[1].replace(/^[^@]*@/, '').replace(/:\d+$/, '') : ''
}

/** Den fulde sti til det billede der kigges på — kun når kaldet giver en
 *  absolut unix-sti. `/visning/billede` afviser alt andet (Windows-stier,
 *  URL'er), og så står rammen tom frem for at hente noget vi ikke må vise. */
export function billedSti(input?: Record<string, unknown>, partialJson?: string): string {
  const arg = analyseArg(input, partialJson)
  const sti = typeof arg?.image_path === 'string' ? arg.image_path : ''
  return sti.startsWith('/') ? sti : ''
}

type Kald = { name: string; status?: string; input?: Record<string, unknown>; partialJson?: string }

/** Kører kaldet stadig? En blok uden status er lige begyndt. */
export function koerer(status?: string): boolean {
  return status !== 'done' && status !== 'error'
}

/** Det billedarbejde ét kald er — eller null hvis det ikke er billedarbejde
 *  eller allerede er færdigt. */
export function billedArbejdeFor(kald: Kald): BilledArbejde | null {
  if (!koerer(kald.status)) return null
  if (erBilledVaerktoej(kald.name)) return { slags: 'generering' }
  if (erBilledAnalyse(kald.name)) {
    return {
      slags: 'analyse',
      kilde: billedKilde(kald.input, kald.partialJson),
      sti: billedSti(kald.input, kald.partialJson),
    }
  }
  return null
}
