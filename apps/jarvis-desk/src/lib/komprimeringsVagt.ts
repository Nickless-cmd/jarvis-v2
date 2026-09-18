/**
 * Skal beskederne hentes igen, fordi en ny komprimerings-markør er landet?
 *
 * Bjørn 18/9-2026: «"samtalen er blevet komprimeret" bliver kun vist i chatview
 * hvis man manuelt opdaterer». Komprimeringen kører i baggrunden EFTER turen,
 * så markøren kom aldrig med i turens egen strøm, og intet andet fortalte
 * klienten at den fandtes.
 *
 * `/chat/context-usage` svarer nu med `last_compact_at` — tidspunktet for den
 * seneste markør. Klienten poller den i forvejen hvert 6. sekund, så et skift
 * er signalet.
 *
 * `forrige === null` betyder «ikke set noget endnu for denne session». Den
 * FØRSTE aflæsning er altid bare nulpunktet — beskederne blev netop hentet med
 * sessionen, så en markør der allerede fandtes er allerede på skærmen. At hente
 * igen der ville koste et kald for ingenting ved hvert sessionsskift.
 */
export function skalGenhente(forrige: string | null, nu: string | undefined): boolean {
  if (forrige === null) return false
  const n = nu ?? ''
  return n !== '' && n !== forrige
}
