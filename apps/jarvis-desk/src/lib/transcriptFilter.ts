/**
 * Hvilke rækker må transskriptet tegne, mens et run stadig tegnes levende?
 *
 * Bagrund (Bjørn 20/10-2026): «svaret er bump landet når hoved folder … så
 * dukker den endelige svar op hen over den besked der pacer, til pacen er
 * forbi». Samme run kan findes TO steder på én gang:
 *
 *  1. den levende tur, der stadig paces, og
 *  2. serverens persisterede række (eller bro-kopien `a-<run_id>`).
 *
 * Filteret fandtes, men var bundet til `afslutterSvarPacing`, som kræver
 * `status === 'done'` OG at `finalBlocks` har tekst. Falder en af de to bort —
 * fx fordi turen går tilbage til værktøjsarbejde efter svaret, så den sidste
 * grænse ligger EFTER teksten og `finalBlocks` er tom — står begge rækker på
 * skærmen samtidig, og det ser ud som om svaret lander oven på pacen.
 *
 * Reglen er derfor knyttet til det faktum der betyder noget: **tegnes dette run
 * levende, må dets persisterede række ikke også tegnes.** Det gælder både mens
 * strømmen løber og mens slutpacen indhenter den.
 *
 * Koblingen til run'et er præcis: `run_id` på server-rækken (sat af
 * `besked_run_kobling`) og id'et `a-<run_id>` på bro-kopien. En række UDEN
 * `run_id` betyder «ved ikke» og beholdes — en tom nøgle må aldrig droppe et
 * gammelt svar.
 */

export interface TransskriptRække {
  id: string
  role?: string
  content?: unknown
  run_id?: string | number | null
}

/**
 * Normaliseret tekst af en bloksamling — så SAMME svar kan genkendes uden en
 * run-nøgle.
 *
 * Målt 20/10-2026 (Bjørn: «dobbelt beskeden over den igangværende pace er
 * tilbage»): `chat_sessions.py` UDELADER `run_id` når `run_for()` ikke kender
 * beskeden — det sker i vinduet lige efter persistering, før koblingen er
 * skrevet. I det vindue står den persisterede række uden nøgle, filteret kan
 * ikke matche den, og brugeren ser den færdige besked oven over den der stadig
 * paces. Målt i test: 2 assistent-rækker i stedet for 1.
 */
export function normaliseretTekst(content: unknown): string {
  if (typeof content === 'string') return content.replace(/\s+/g, ' ').trim()
  if (!Array.isArray(content)) return ''
  return content
    .filter((b): b is { type?: string; text?: string } => !!b && typeof b === 'object')
    .filter((b) => b.type === 'text' && typeof b.text === 'string')
    .map((b) => String(b.text))
    .join('')
    .replace(/\s+/g, ' ')
    .trim()
}

/** Id'et på den lokale bro-kopi af et streamet svar. */
export function broId(runId: string): string {
  return `a-${runId}`
}

/**
 * Hvor meget afslutning to tekster skal dele for at være samme svar.
 *
 * Målt 20/10-2026 (Bjørn: «dobbelt beskeden er der stadig»): den gemte besked
 * har FLERE text-blokke (`commentary` + `final_answer`), og de joines uden
 * separator — «…åben.Flag-kaldet» mod den levende «…åben. Flag-kaldet». Målt på
 * besked 210931 delte de to tekster **1768 tegns** suffix, men den første
 * afvigelse lå ved tegn 132, så et `endsWith` på hele strengen fejlede 1300
 * tegn før afslutningen — og rækken stod på skærmen ved siden af pacen.
 *
 * Et helt svar deler sin afslutning; to forskellige svar gør ikke. 120 tegn er
 * rigeligt til at skelne, og kort nok til at et kort svar også fanges.
 */
const SUFFIX_LOFT = 120
const SUFFIX_GULV = 40

function delerSuffix(a: string, b: string): boolean {
  const n = Math.min(a.length, b.length)
  if (n < SUFFIX_GULV) return false
  const krav = Math.min(SUFFIX_LOFT, Math.max(SUFFIX_GULV, Math.floor(n * 0.6)))
  let i = 0
  while (i < n && a[a.length - 1 - i] === b[b.length - 1 - i]) i += 1
  return i >= krav
}

/**
 * Fjern det aktive runs egne rækker fra transskriptet.
 *
 * @param beskeder     transskriptets rækker, i visningsrækkefølge
 * @param aktivRunId   runnet der tegnes levende lige nu
 * @param tegnesLevende om den levende tur faktisk er på skærmen
 */
export function udenAktivRun<T extends TransskriptRække>(
  beskeder: readonly T[],
  aktivRunId: string | null | undefined,
  tegnesLevende: boolean,
  levendeTekst?: string,
): readonly T[] {
  if (!tegnesLevende) return beskeder
  const bro = aktivRunId ? broId(aktivRunId) : null
  const levende = (levendeTekst ?? '').replace(/\s+/g, ' ').trim()
  // Kun den SIDSTE assistent-række kan være den persisterede kopi af den
  // levende tur. Ældre svar må aldrig røres, uanset hvor ens teksten er.
  let sidsteAssistent = -1
  for (let i = beskeder.length - 1; i >= 0; i -= 1) {
    if (beskeder[i]?.role === 'assistant') { sidsteAssistent = i; break }
  }
  return beskeder.filter((m, i) => {
    if (bro && m.id === bro) return false
    if (aktivRunId && String(m.run_id ?? '') === aktivRunId) return false
    // Nøgle-fri faldback: samme svar, men rækken manglede `run_id`.
    // Rækken kan bære KUN slutsvaret mens den levende tur også bærer
    // arbejdsteksten foran — derfor sammenlignes halen, ikke hele strengen.
    if (levende && i === sidsteAssistent) {
      const raekke = normaliseretTekst(m.content)
      if (
        raekke.length >= 20 &&
        (levende === raekke || levende.endsWith(raekke) || delerSuffix(levende, raekke))
      ) return false
    }
    return true
  })
}
