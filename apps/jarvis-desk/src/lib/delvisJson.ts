/**
 * Reparation af HALV JSON — så en flade kan tegnes mens svaret løber.
 *
 * ## Hvorfor den findes (målt 14/11-2026)
 *
 * `parseNativeRichSpec` kalder `JSON.parse`, som kaster på halv JSON og
 * returnerer `null`. Fladen blev derfor først synlig når hele blokken var
 * skrevet. Målt over 14 dage: 121 flader, median svarlængde 4.179 tegn, og
 * selve JSON-blokken tager ~11 s at streame ved ~53 tegn/s. I de 11 sekunder
 * stod der «flade forberedes…» — en sand, men død ventetid.
 *
 * ## Det den IKKE gør
 *
 * Den gætter ikke. Et element der er halvt skrevet (`["SE",8` hvor der kan
 * komme `9` efter) bliver KLIPPET VÆK, ikke afsluttet med et gæt. Vi tegner
 * kun det der er bevisligt komplet: en struktur der allerede er lukket med
 * `}` eller `]`.
 *
 * Det er forskellen mellem en flade der vokser sandt og en flade der viser
 * tal der ikke findes. Den anden slags ville være værre end at vente.
 */

/**
 * Reparer en afklippet JSON-streng ved at fjerne det ufuldstændige hale og
 * lukke de strukturer der stadig er åbne.
 *
 * Returnerer `null` når der ikke findes et sikkert klippepunkt — så er der
 * intet at tegne, og kalderen falder tilbage til «forberedes».
 */
export function reparérDelvisJson(raa: string): string | null {
  const tekst = raa.trim()
  if (!tekst.startsWith('{') && !tekst.startsWith('[')) return null

  // Ét gennemløb. Vi holder styr på om vi er inde i en streng (og om det
  // næste tegn er escaped), og hvilke strukturer der er åbne.
  const stak: string[] = []
  let iStreng = false
  let escaped = false
  // Sidste position hvor alt før den var en KOMPLET, afsluttet struktur.
  // Det er det eneste sted vi tør klippe.
  let sikkertSlut = -1
  let sikkertStak: string[] = []

  for (let i = 0; i < tekst.length; i += 1) {
    const c = tekst[i]

    if (iStreng) {
      if (escaped) {
        escaped = false
      } else if (c === '\\') {
        escaped = true
      } else if (c === '"') {
        iStreng = false
      }
      continue
    }

    if (c === '"') {
      iStreng = true
      continue
    }

    if (c === '{' || c === '[') {
      stak.push(c === '{' ? '}' : ']')
      continue
    }

    if (c === '}' || c === ']') {
      // Ubalanceret lukning: input er ikke halvt, det er ødelagt. Ingen gæt.
      if (stak.pop() !== c) return null
      if (stak.length > 0) {
        // En hel struktur inde i en anden: dette er et sikkert klippepunkt.
        sikkertSlut = i + 1
        sikkertStak = [...stak]
      }
      continue
    }

    // Et komma er IKKE et sikkert klippepunkt. Målt 14/11-2026: reglen
    // «alt før kommaet var komplet» tog den halve række med — `["SE",8`
    // blev klippet ved kommaet til `["SE"`, så fladen viste en række med
    // ét land og intet tal. Kommaet beviser at det FOREGÅENDE er komplet,
    // ikke at det følgende er det.
  }

  // Hele strengen var gyldig set fra vores side — men `JSON.parse` fejlede
  // alligevel, så vi stoler ikke på den. Kun et bevisligt klippepunkt dur.
  if (sikkertSlut <= 0) return null

  let klippet = tekst.slice(0, sikkertSlut)
  // Et hale-komma ville gøre os til en ny ugyldig streng. Fjern det.
  klippet = klippet.replace(/,\s*$/, '')
  // Luk de strukturer der stadig var åbne ved klippepunktet, inderst først.
  const lukket = klippet + [...sikkertStak].reverse().join('')
  return lukket
}

/**
 * Er dette en flade der stadig bliver skrevet? Bruges til at afgøre om en
 * halv blok skal tegnes delvist eller vente.
 *
 * En blok uden afsluttende `}` kan ikke være færdig, uanset hvad `JSON.parse`
 * ellers måtte mene om den.
 */
export function erDelvis(raa: string): boolean {
  const t = raa.trim()
  if (!t) return false
  const sidste = t[t.length - 1]
  return sidste !== '}' && sidste !== ']'
}
