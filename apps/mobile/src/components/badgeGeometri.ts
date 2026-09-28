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
 * Bjørn 28/9-2026, første melding: «i header feltet(badge) der holder session
 * navn skal have en fast størrelse. Ikke større end feltet(badge) i højre side
 * af header». Højden var allerede låst til `BADGE_H` siden 12/9 — det var
 * BREDDEN der løb: `CodeTitle` havde kun `flexShrink: 1`, så et langt
 * session-navn voksede frit (målt 229 dp) og dominerede hele bjælken.
 *
 * ## Hvorfor 106 var forkert — og hvorfor det er 142 nu
 *
 * Jeg satte loftet til højre pilles bredde, 106 dp. Det var den forkerte
 * reference: de to badges har ikke samme indhold. Højre pille er ring + hopp +
 * prikker; titel-pillen er titel + `repo · vært · prik`. Bjørn så resultatet
 * med det samme: «badge skal være længere.. indholdet stikker ud over».
 *
 * Målt i hans skærmbillede (densitet 2,625): kontekst-linjen fyldte **298 px =
 * 113,5 dp** alene. Med 28 dp polstring kræver den 142 dp. Ved 106 dp var der
 * 78 dp til et indhold der ville 113,5 — og fordi hverken rækken eller
 * `meta`-teksterne måtte skrumpe (`flexShrink` manglede), flød de ud over
 * kanten i stedet for at klippe sig selv.
 *
 * 142 er derfor ikke et rundt tal: det er loftet hvor pillens eget faste
 * indhold lige præcis er der. Titlen er den del der giver sig — den forkortes
 * med `numberOfLines={1}`.
 *
 * Et loft, ikke en fast bredde: et kort navn må gerne give en smal pille. Det
 * er kun den lange titel der ikke må skubbe bjælken.
 */
export const BADGE_MAKS_B = 142
