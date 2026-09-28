/**
 * Headerens badge-højde — ÉT tal, delt af alle tre.
 *
 * Bjørn 12/9-2026: «den er lidt større end de 2 andre badges». Den var 47 dp
 * mod 40, fordi titlens højde blev til af sig selv: to tekstlinjer plus
 * polstring, hvor de to andre havde tallet skrevet direkte.
 *
 * Det er derfor konstanten ligger her og ikke i TopBar. Et tal der er skrevet
 * ét sted og udregnet et andet holder kun indtil nogen ændrer en skriftstørrelse
 * — og så er det ikke til at se på koden at de to nogensinde skulle passe
 * sammen. Nu er «lige høje» noget de ER, ikke noget de tilfældigvis blev.
 *
 * Målt i ChatGPT-appen på Bjørns enhed; se TopBar for hele geometrien og for
 * hvorfor densiteten er 2,625 og ikke 3,0.
 */
export const BADGE_H = 40

/**
 * Headerens badge-BREDDE — loftet for titel-pillen.
 *
 * Bjørn 28/9-2026: «i header feltet(badge) der holder session navn skal have en
 * fast størrelse. Ikke større end feltet(badge) i højre side af header».
 *
 * Målt i hans skærmbillede (densitet 2,625): titel-pillen var 229 dp bred mod
 * højre pilles 106 dp. Højden var allerede låst til `BADGE_H` siden 12/9 — det
 * var BREDDEN der løb: `CodeTitle` havde kun `flexShrink: 1`, så et langt
 * session-navn voksede frit og dominerede hele bjælken.
 *
 * 106 dp er den højre pilles faktiske bredde: ring 22 + hopp 24 + prikker 20
 * + to mellemrum à 7 + polstring 13 i hver side. Det er dét tal Bjørn peger på
 * med «feltet i højre side», og det holder så længe højre pille ikke selv
 * vokser — derfor bor det her og ikke i `TopBar`.
 *
 * Et loft, ikke en fast bredde: et kort navn må gerne give en smal pille. Det
 * er kun den lange titel der ikke må skubbe bjælken.
 */
export const BADGE_MAKS_B = 106
