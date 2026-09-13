import * as MediaLibrary from 'expo-media-library/legacy'

/**
 * Gem et billede i telefonens galleri.
 *
 * ## Hvorfor den findes
 *
 * Fuldskærms-visningen kunne vise et billede og ikke andet: målt 13/9-2026
 * havde den ÉN knap, luk. Et billede Jarvis havde lavet kunne man se og ikke
 * få ud af appen — og det er hele pointen med at lave det.
 *
 * ## Hvorfor udfaldet er et ORD og ikke en boolean
 *
 * «Det virkede ikke» er tre forskellige ting for brugeren: han sagde nej til
 * galleriet (så gør vi ikke mere), telefonen kunne ikke skrive filen (så kan
 * et nyt forsøg måske hjælpe), eller vi fik aldrig spurgt. Kun den første
 * kræver at HAN gør noget, og det er den eneste grund til at kende forskellen.
 */
export type GemUdfald = 'gemt' | 'afvist' | 'fejlet'

/** Endelser galleriet kan læse. Rækkefølgen er uden betydning — vi søger. */
const BILLED_ENDELSER = ['.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp', '.heic', '.heif']

const ENDELSE_FRA_MIME: Record<string, string> = {
  'image/png': '.png',
  'image/jpeg': '.jpg',
  'image/webp': '.webp',
  'image/gif': '.gif',
  'image/bmp': '.bmp',
  'image/heic': '.heic',
  'image/heif': '.heif',
}

/**
 * Filnavnet billedet gemmes under.
 *
 * ## Hvorfor det ikke bare er `attachment_id`
 *
 * For det første: uden en ENDELSE ved galleriet ikke hvad det får. Det var
 * præcis hvad `AuthImage`s cache-navn gav — `img-<attachment-id>` uden endelse
 * — og en fil uden type bliver afvist, ikke gemt under et gæt.
 *
 * For det andet: `billede` frem for en tom streng. Et navn uden indhold giver
 * en post i galleriet man ikke kan kende fra de næste hundrede.
 *
 * Endelsen tages fra filnavnet hvis den er der, ellers fra mime-typen, og
 * ellers `.png` — de billeder Jarvis laver er PNG eller JPEG, og galleriet
 * læser indholdet, så et forkert gæt koster et forkert navn og ikke en fejl.
 */
export function filnavnMedEndelse(filnavn = '', mime = ''): string {
  const rent = String(filnavn || '').replace(/[^A-Za-z0-9._-]/g, '_')
  const lav = rent.toLowerCase()
  const fundet = BILLED_ENDELSER.find((e) => lav.endsWith(e))
  const renMime = String(mime || '').toLowerCase().split(';')[0]!.trim()
  // Endelsen bevares i den form brugeren skrev den — `foto.JPEG` skal ikke
  // omdøbes til `foto.jpeg` undervejs. Kun naar vi LAANER fra mime-typen,
  // skriver vi den selv.
  const endelse = fundet
    ? rent.slice(rent.length - fundet.length)
    : (ENDELSE_FRA_MIME[renMime] ?? '.png')
  const uden = fundet ? rent.slice(0, rent.length - fundet.length) : rent
  return `${uden || 'billede'}${endelse}`
}

/**
 * Læg en LOKAL fil i galleriet. Filen skal allerede være hentet.
 *
 * ## Hvorfor tilladelsen spørges om, men svaret ikke afgør noget
 *
 * På Android 13 og nyere kan appen skrive sine EGNE billeder til galleriet
 * gennem MediaStore uden nogen tilladelse. På ældre versioner kræver det
 * `WRITE_EXTERNAL_STORAGE`. Vi kan ikke se forskel herfra, og et nej til
 * tilladelsen betyder derfor IKKE at gemningen ville fejle.
 *
 * Så vi spørger (for det er den eneste vej til et nej der faktisk blokerer),
 * forsøger at gemme uanset svaret, og lader UDFALDRET afgøre sandheden: blev
 * filen gemt, står der gemt — også selv om brugeren sagde nej til en
 * tilladelse der ikke var nødvendig.
 *
 * Et nej + en fejl er «afvist», for da er det brugerens valg der holder os
 * tilbage. Et ja + en fejl er «fejlet», for da er det vores.
 */
export async function gemTilGalleriet(lokalSti: string): Promise<GemUdfald> {
  if (!lokalSti) return 'fejlet'

  let tilladelse = false
  try {
    const svar = await MediaLibrary.requestPermissionsAsync()
    tilladelse = Boolean(svar?.granted)
  } catch {
    // Svarer broen ikke, er det ikke et nej — så vi forsøger alligevel.
    tilladelse = false
  }

  try {
    await MediaLibrary.saveToLibraryAsync(lokalSti)
    return 'gemt'
  } catch {
    return tilladelse ? 'fejlet' : 'afvist'
  }
}
