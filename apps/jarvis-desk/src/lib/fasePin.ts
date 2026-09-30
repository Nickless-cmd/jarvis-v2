/**
 * Faa alle synlige loaders til at gaa I FASE (spec punkt 8).
 *
 * En CSS-animation starter naar elementet monteres. Fire loaders der monteres
 * paa fire forskellige tidspunkter puster derfor forskudt — og det ser
 * forkert ud paa en maade der er svaer at pege paa: man ser at noget roder,
 * uden at kunne sige hvad.
 *
 * Rettelsen er en NEGATIV `animation-delay`. En delay paa `-400ms` starter
 * animationen som om den havde koert i 400ms allerede, saa et element der
 * monteres midt i cyklussen lander paa den fase alle andre er i. Regner man
 * forsinkelsen ud af dokument-tiden, er alle pinnet til det samme nulpunkt.
 *
 * Lille aendring, stor effekt — og den koster ingen JavaScript efter
 * monteringen: browseren driver stadig animationen selv.
 */

/**
 * Den negative forsinkelse der pinner en animation til dokument-tid nul.
 *
 * `nu` kan gives, saa den kan maales uden at vente paa et ur.
 */
export function faseForsinkelse(varighedMs: number, nu?: number): string {
  const v = Number(varighedMs)
  // En varighed paa 0 eller derunder har ingen fase. Uden vagten ville
  // `% 0` give NaN, og `animation-delay: NaNms` er en ugyldig vaerdi der
  // faar hele deklarationen til at falde bort — altsaa ingen animation.
  if (!Number.isFinite(v) || v <= 0) return '0ms'
  const t = Number.isFinite(nu as number) ? (nu as number) : tid()
  // Dobbelt modulo: en negativ `nu` (nogle test-ure) ville ellers give en
  // POSITIV forsinkelse, og saa stod loaderen stille indtil den indhentede.
  const fase = ((t % v) + v) % v
  return `${-fase}ms`
}

function tid(): number {
  try {
    if (typeof performance !== 'undefined' && typeof performance.now === 'function') {
      return performance.now()
    }
  } catch {
    // jsdom uden performance — falder tilbage paa Date.
  }
  return Date.now()
}

/** Klar til `style={...}` paa et element hvis animation varer `varighedMs`. */
export function faseStil(varighedMs: number, nu?: number): { animationDelay: string } {
  return { animationDelay: faseForsinkelse(varighedMs, nu) }
}
