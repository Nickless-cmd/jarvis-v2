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
import { closingFence, openingFence, type FenceMark } from './fenceScanner'

const LISTEPUNKT = /^\s{0,3}(?:[-*+]|\d{1,9}[.)])\s/

export function delIBlokke(md: string): string[] {
  const linjer = md.split('\n')
  const blokke: string[] = []
  let aktuel: string[] = []
  let fence: FenceMark | null = null

  for (let i = 0; i < linjer.length; i++) {
    const l = linjer[i]!
    // 29/9-2026: samme længde- og tegnregler som rendererens fence-scanner;
    // ellers kunne en kort ``` i en ````-blok splitte koden i to blokke.
    if (fence) {
      if (closingFence(l, fence)) fence = null
    } else {
      fence = openingFence(l)
    }
    if (!fence && l.trim() === '' && aktuel.length > 0) {
      // 29/9-2026: slice kopierede hele resten af dokumentet ved hvert skel;
      // indeks-opslag bevarer samme næste linje uden at kopiere den lange hale.
      let j = i + 1
      while (j < linjer.length && linjer[j]!.trim() === '') j++
      const naeste = j < linjer.length ? linjer[j] : undefined
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
