/**
 * Kopiér tekst — og sig ærligt om det lykkedes.
 *
 * Bjørn 18/9-2026: «kopi ikon under hans beskeder virker ikke». Der var to
 * fejl oven i hinanden:
 *
 * 1. Electrons `setPermissionCheckHandler` svarede `false` til alt der ikke
 *    var `media`, så `clipboard-sanitized-write` blev afvist i den PAKKEDE
 *    app. I dev (localhost) fejlede den ikke på samme måde — derfor slap den
 *    igennem.
 * 2. Knappen satte sit flueben uden at vente på løftet. Den kvitterede altså
 *    for en kopiering der aldrig skete.
 *
 * Den første er rettet i main-processen. Denne funktion er den anden halvdel:
 * ét sted der VED om teksten nåede udklipsholderen.
 *
 * Faldbakken er `document.execCommand('copy')` på et midlertidigt felt. Den er
 * forældet, men den går uden om Permissions API'et helt og virker også i en
 * kontekst hvor `navigator.clipboard` ikke findes. Den koster kun noget når
 * den moderne vej allerede har fejlet.
 */
export async function skrivTilUdklipsholder(tekst: string): Promise<boolean> {
  if (!tekst) return false

  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(tekst)
      return true
    }
  } catch {
    // Afvist eller utilgængelig — prøv den gamle vej frem for at give op.
  }

  try {
    const felt = document.createElement('textarea')
    felt.value = tekst
    // Uden for skærmen, men IKKE display:none — et skjult felt kan ikke få
    // markering, og uden markering kopierer execCommand ingenting.
    felt.setAttribute('readonly', '')
    felt.style.position = 'fixed'
    felt.style.top = '-1000px'
    felt.style.opacity = '0'
    document.body.appendChild(felt)
    felt.select()
    const ok = document.execCommand('copy')
    document.body.removeChild(felt)
    return ok
  } catch {
    return false
  }
}
