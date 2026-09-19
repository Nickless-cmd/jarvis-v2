/**
 * Del markdown i blokke der kan parses HVER FOR SIG — til streaming.
 *
 * Målt 19/9-2026 (Jarvis' fund, vores måling): MarkdownRenderer parsede HELE
 * den akkumulerede tekst ved hver delta. Et svar på 13.500 tegn i 24-tegns
 * stykker: 566 renders, tiden pr. render voksede fra 2,9 til 27,5 ms —
 * kvadratisk, og nok til at mætte render-tråden mod slutningen af et langt
 * svar. Det var den hakkende streaming.
 *
 * Med blokke er en færdig blok en uforanderlig streng; den memoiseres og
 * parses aldrig igen. Kun den sidste — den der stadig skrives — parses.
 *
 * Et skel lægges kun ved en tom linje UDEN FOR en kodeblok, og kun hvor den
 * næste blok ikke hører til den forrige:
 *  - næste linje starter med mellemrum/tab (fortsættelse i et listepunkt
 *    eller en indrykket kodeblok),
 *  - næste linje er et listepunkt og den forrige blok var en liste («løs»
 *    liste med tomme linjer mellem punkterne — ellers blev det to lister).
 * Tabeller har aldrig tomme linjer inden i sig og deles derfor aldrig.
 */
const LISTEPUNKT = /^\s{0,3}(?:[-*+]|\d{1,9}[.)])\s/

export function delIBlokke(md: string): string[] {
  const linjer = md.split('\n')
  const blokke: string[] = []
  let aktuel: string[] = []
  let iFence = false
  let fenceTegn = ''

  const aabnFence = (l: string) => /^\s{0,3}(`{3,}|~{3,})/.exec(l)?.[1] ?? ''

  for (let i = 0; i < linjer.length; i++) {
    const l = linjer[i]!
    const f = aabnFence(l)
    if (f) {
      if (!iFence) { iFence = true; fenceTegn = f[0]! }
      else if (f[0] === fenceTegn) { iFence = false }
    }
    if (!iFence && l.trim() === '' && aktuel.length > 0) {
      const naeste = linjer.slice(i + 1).find((x) => x.trim() !== '')
      const blokErListe = aktuel.some((x) => LISTEPUNKT.test(x))
      const fortsaetter = naeste !== undefined && (
        /^[ \t]/.test(naeste) || (blokErListe && LISTEPUNKT.test(naeste))
      )
      if (!fortsaetter && naeste !== undefined) {
        blokke.push(aktuel.join('\n') + '\n')
        aktuel = []
        continue
      }
    }
    aktuel.push(l)
  }
  if (aktuel.length > 0) blokke.push(aktuel.join('\n'))
  return blokke
}
