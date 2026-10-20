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
  run_id?: string | number | null
}

/** Id'et på den lokale bro-kopi af et streamet svar. */
export function broId(runId: string): string {
  return `a-${runId}`
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
): readonly T[] {
  if (!tegnesLevende || !aktivRunId) return beskeder
  const bro = broId(aktivRunId)
  return beskeder.filter(
    (m) => m.id !== bro && String(m.run_id ?? '') !== aktivRunId,
  )
}
