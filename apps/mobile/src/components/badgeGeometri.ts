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
