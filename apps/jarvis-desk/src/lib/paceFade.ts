/**
 * KOBLINGEN MELLEM PACERENS TEMPO OG ORD-ANIMATIONENS LÆNGDE.
 *
 * ## Hvorfor den findes
 *
 * Bjørn 23/11-2026: «ord for ord animationen køre så hurtigt det næsten virker
 * klumperne … ikke 5 ord, 2 max 3». Den daværende rettelse skar farvens
 * varighed ned fra 220 ms til 120 ms — et FAST tal.
 *
 * Men et fast tal kan ikke være rigtigt samtidig med at paceren skifter tempo.
 * MÅLT: `PACE_GULV` er 48 tegn/s og `PACE_LOFT` er 4000. Ved grundtempoet
 * ankommer der et ord hver ~125 ms; ved 600 tegn/s hver ~10 ms. Med en fast
 * fade på 120 ms betyder det, at der ved høj rate er **12 ord i fade
 * samtidigt** — præcis den klump Bjørn beskriver — mens den samme 120 ms ved
 * grundtempoet er helt rolig.
 *
 * Koblingen gør tallet til en FUNKTION af raten: hurtigere pacer → kortere
 * fade, så antallet af ord i fade forbliver nogenlunde konstant i stedet for
 * at vokse med tempoet.
 *
 * ## Hvad de to tal betyder
 *
 * `fadeMsForRate` sigter efter at faden varer cirka lige så længe som
 * mellemrummet mellem to ords ankomst. Så er der ~1 ord i fade ad gangen
 * uanset tempo.
 *
 * Gulvet på 70 ms er der, fordi en fade under ~4 frames ved 60 Hz ikke læses
 * som en glidning men som et hop — og et hop er den fejl vi startede med.
 *
 * `delayMsForFade` er den korte pause hvor ordet står i ankomstfarven FØR
 * glidningen begynder. Den skal være en ANDEL af faden, ikke et fast tal:
 * med fast delay 40 ms og fade 70 ms ville der kun være 30 ms til selve
 * glidningen, og så er vi tilbage ved hoppet. Målt forhold i den kurve Bjørn
 * godkendte 23/11: 40/120 ≈ 0,33.
 *
 * ## Bagudkompatibel
 *
 * Uden nogen der sætter `--pace-fade-ms` falder CSS'en tilbage til variantens
 * egne tal, og adfærden er præcis som før denne fil fandtes.
 */

/** Gennemsnitlig ordlængde i kodepunkter, inkl. det mellemrum der følger med.
 *
 *  MÅLT på dansk prosa i denne tråd: 5–7 tegn pr. ord inkl. mellemrum. 6 er
 *  midten, og tallet bruges kun til at oversætte tegn/s til ord/s — en fejl på
 *  ét tegn flytter fade-længden ~17 %, hvilket ligger inden for det
 *  `FADE_GULV_MS` alligevel opsluger ved høj rate. */
export const ORD_LAENGDE_TEGN = 6

/** Korteste fade der stadig læses som en glidning. 4 frames ved 60 Hz.
 *
 *  ⚠️ MÅLT 24/11-2026 — dette tal blev FORSØGT hævet til 130, og det blev
 *  rullet tilbage med en måling som grund. Et højere gulv gør klumpen VÆRRE,
 *  ikke bedre: gulvet er ikke det der begrænser antallet af ord i fade, det er
 *  det der SKABER det, fordi det tvinger faden op over ankomstintervallet.
 *
 *  Målt ved 642 tegn/s (topraten i `paceRate.maaling`), hvor ordene ankommer
 *  hvert 9,3 ms:
 *
 *    gulv  70 ms → 7,5 ord i fade
 *    gulv 130 ms → 13,9 ord i fade
 *
 *  Gulvet skal altså holdes så LAVT som det kan læses, ikke hæves. Det ægte
 *  problem ved høj rate ligger i `DELAY_LOFT_MS`, ikke her. */
export const FADE_GULV_MS = 70

/** Længste fade. Over dette hober ordene sig op selv ved grundtempoet.
 *
 *  220 ms er `Snappy`s oprindelige farve-varighed — den vi målte 11 samtidige
 *  accent-ord med. Den er loftet, ikke målet. */
export const FADE_LOFT_MS = 220

/** Delay som andel af faden. Se filens hovedkommentar. */
export const DELAY_ANDEL_AF_FADE = 0.33

/** Delay må ikke overstige dette — det er `Snappy`s eget tal og den øvre
 *  grænse hvor ankomstfarven stadig føles som et blink frem for en pause.
 *
 *  ⚠️ MÅLT 24/11-2026: 40 ms var for lavt til at bære sin egen begrundelse.
 *  Delayet er `min(40, fade × 0,33)`, så det MÆTTER ved fade = 40/0,33 =
 *  **121 ms** — og holder derefter op med at følge faden. Ved den rolige ende
 *  (fade 125 ms) blev delay og glidning derfor næsten lige store, hvilket er
 *  præcis det `delayMsForFade` findes for at forhindre.
 *
 *  60 ms flytter mætningen til fade = 182 ms, altså over hele det interval
 *  faden faktisk arbejder i (70–220 ms). Så følger delayet faden i hele
 *  kurven, og forholdet 0,33 holder som det blev målt 23/11. */
export const DELAY_LOFT_MS = 60

/**
 * Farve-animationens varighed i millisekunder for en given pacer-rate.
 *
 * @param rate pacerens visningshastighed i kodepunkter pr. sekund
 *             (`PACE_GULV` = 48, `PACE_LOFT` = 4000). 0 eller negativ =
 *             intet målt endnu → loftet, så den første frame ikke hakker.
 */
export function fadeMsForRate(rate: number): number {
  if (!(rate > 0) || !Number.isFinite(rate)) return FADE_LOFT_MS
  const mellemrumMs = (1000 * ORD_LAENGDE_TEGN) / rate
  return Math.min(FADE_LOFT_MS, Math.max(FADE_GULV_MS, mellemrumMs))
}

/**
 * Ankomstfarvens pause i millisekunder, udledt af fadens længde.
 *
 * Holdes som en andel, så forholdet mellem «stå i accentfarven» og «glide til
 * slutfarven» er det samme ved alle tempi. Et fast delay ville ved kort fade
 * spise hele glidningen.
 */
export function delayMsForFade(fadeMs: number): number {
  if (!(fadeMs > 0) || !Number.isFinite(fadeMs)) return DELAY_LOFT_MS
  return Math.min(DELAY_LOFT_MS, fadeMs * DELAY_ANDEL_AF_FADE)
}
