/**
 * Hvilke værktøjer der laver medie-arbejde — og hvilken slags.
 *
 * ## Hvorfor de bor her og ikke i komponenten
 *
 * De stod i `components/rich/ImageGeneration.tsx`, fordi det var dér de blev
 * brugt. Men `streamReducer` skal bruge dem: en `image_generation_call` fødes
 * ved `tool_use` og skal vide om kaldet overhovedet ER et billedkald. En
 * reducer må ikke importere en React-komponent for at få et navn — så trækker
 * man hele komponenttræet ind i en ren funktion, og testen af reduceren
 * begynder at kræve en DOM.
 *
 * `ImageGeneration.tsx` re-eksporterer dem, så de tre kaldesteder der har
 * brugt dem siden 27/9 ikke skal røres.
 */

/** De tre værktøjer der FREMBRINGER et billede.
 *
 *  `openrouter_image_edit` er et tyndt lag over genereringen og deler hele
 *  resten af kæden. En betingelse på `openrouter_image` alene ville glemme
 *  redigeringen OG `pollinations_image` — og det ville ingen opdage, fordi
 *  man tester med det værktøj man selv bruger.
 */
export function erBilledVaerktoej(name: string): boolean {
  return name === 'openrouter_image' || name === 'openrouter_image_edit' || name === 'pollinations_image'
}

/** Video-værktøjerne. Egen liste, fordi ventetiden er en HELT anden:
 *  billed-generering er målt til ~8 s, mens `pollinations_video` bruger 39 s
 *  på pipelinen og har op til 600 s timeout. Uden et tegn på liv står turen
 *  død i op til ti minutter. */
export function erVideoVaerktoej(name: string): boolean {
  return name === 'pollinations_video' || name === 'pollinations_video_edit'
}

/** Det eneste syns-værktøj i drift. `operator_screenshot` og
 *  `jarvis_browser_screenshot` TAGER billeder og er målt til ~0,1 s — de har
 *  intet at animere. */
export function erBilledAnalyse(name: string): boolean {
  return name === 'analyze_image'
}

/** Er kaldet et medie-kald overhovedet — generering, video eller analyse?
 *
 *  Bruges af reduceren: kun disse kald får deres egen part. Alle andre bliver
 *  en almindelig `tool_use` i runde-gruppen, som de altid har været. */
export function erMedieVaerktoej(name: string): boolean {
  return erBilledVaerktoej(name) || erVideoVaerktoej(name) || erBilledAnalyse(name)
}

/**
 * Det aspekt et kald har OPLLYST, eller `undefined` når det ikke gør.
 *
 * ## Hvorfor det ikke gættes
 *
 * Målt 18/11-2026 på 171 gemte billeder: 42 % er 9:16, 20 % er 16:9, og
 * resten fordeler sig på fire andre forhold. Der findes intet dominerende
 * aspekt — en reserveret højde fra et median-tal ville være forkert i 58 % af
 * tilfældene og give præcis det layout-hop vi prøver at fjerne.
 *
 * Derfor: kun når værktøjskaldet SELV bærer `aspect_ratio`, reserveres der
 * plads. Ellers får rammen en fast max-højde, og ankomsten kan ikke skubbe
 * noget. Det er samme lære som blink 2: hoppet kommer fra relayoutet, ikke
 * fra højden.
 */
export function aspektFraKald(input: Record<string, unknown> | undefined): string | undefined {
  const raa = input?.aspect_ratio
  if (typeof raa !== 'string') return undefined
  const trimmet = raa.trim()
  // Kun det formular vi kan regne på: "16:9", "1:1", "9:16". Alt andet —
  // "landscape", "square", en tom streng — behandles som ukendt, for et
  // forkert tal er værre end intet tal.
  return /^\d{1,2}:\d{1,2}$/.test(trimmet) ? trimmet : undefined
}

/** Aspekt som et CSS-forhold (`16 / 9`), eller `undefined`. */
export function aspektCss(aspekt: string | undefined): string | undefined {
  if (!aspekt) return undefined
  const [w, h] = aspekt.split(':').map(Number)
  if (!w || !h) return undefined
  return `${w} / ${h}`
}

/**
 * Hvor mange billeder kaldet beder om — `n`, `antal` eller `count`.
 *
 * Ukendt bliver 1: det er det hyppigste, og en reserveret plads til ét billede
 * er den ærligste gætning når vi ikke ved bedre. Et forkert antal ville vise
 * et gitter der aldrig bliver fyldt.
 */
export function forventetAntal(input: Record<string, unknown> | undefined): number {
  for (const noegle of ['n', 'antal', 'count', 'num_images'] as const) {
    const v = input?.[noegle]
    const tal = typeof v === 'number' ? v : typeof v === 'string' ? Number(v) : NaN
    if (Number.isFinite(tal) && tal >= 1 && tal <= 8) return Math.floor(tal)
  }
  return 1
}
