import { useEffect, useState } from 'react'

/** 1:1 med mobilens `prikSekvens.ts`. Desk bruger dem på runde-, tanke- og
 *  skill-linjen mens de kører (Bjørn 17/9-2026). */

/** Hvor lang tid ét trin i prik-sekvensen varer. */
export const TRIN_MS = 420

/**
 * «.» → «..» → «...» → «.» …
 *
 * ## Hvorfor prikker og ikke et lys
 *
 * Fordi ordet er kort og fast. Et lys der glider gennem «Tænker» er den samme
 * bevægelse hver eneste gang og siger intet om at tiden går; prikker der
 * lægges til gør. De to tegn er ikke i modstrid — lyset siger «her arbejdes»,
 * prikkerne siger «og det tager tid».
 *
 * ## Hvorfor bredden er fast
 *
 * Etiketten skal ikke hoppe. Ved at fylde op med tynde mellemrum står
 * teksten efter prikkerne stille, uanset hvor i sekvensen man er.
 */
export function prikker(trin: number, maks = 3): string {
  const n = ((Math.floor(trin) % maks) + maks) % maks + 1
  // U+2009 THIN SPACE. Et almindeligt mellemrum bliver ofte klippet væk i
  // slutningen af en tekst; et tyndt gør ikke, og det fylder omtrent som et
  // punktum.
  return '.'.repeat(n) + ' '.repeat(maks - n)
}

/** Trinnet i sekvensen, mens `live`. Står stille (0) når linjen er færdig. */
export function usePrikTrin(live: boolean): number {
  const [trin, setTrin] = useState(0)
  useEffect(() => {
    if (!live) return
    const t = setInterval(() => setTrin((n) => n + 1), TRIN_MS)
    return () => clearInterval(t)
  }, [live])
  return trin
}

/** «Kører npm test…» → «Kører npm test» + løbende prikker. */
export function medPrikker(tekst: string, trin: number): string {
  return tekst.replace(/…$/, '') + prikker(trin)
}
