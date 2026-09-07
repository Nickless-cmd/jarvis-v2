import type { LocationPrecision } from './location'

/** «Recent contexts» — det man har lige ved hånden, samlet ét sted.
 *
 *  Bjørns liste: kamera, lokation, sidste fil, clipboard, current device.
 *  Pointen er ikke at tilføje nye evner — de findes alle i forvejen — men at
 *  man ikke skal igennem fem forskellige menuer for at give ham noget.
 *
 *  Modulet er RENT: det henter ikke selv noget. Skærmen leverer hvad der er
 *  tilgængeligt, og her afgøres kun hvad der skal VISES og hvordan. Det gør
 *  det testbart uden at mocke fem native moduler, og det holder listen fri af
 *  tilladelses-logik.
 *
 *  En kontekst der ikke er tilgængelig vises IKKE som en død knap. Den vises
 *  med grunden — «kamera er slået fra» — så man ved hvad man skal gøre ved
 *  det, i stedet for at trykke forgæves.
 */

export type KontekstSlags = 'kamera' | 'lokation' | 'fil' | 'udklip' | 'enhed'

export interface KontekstInput {
  kameraTilladt: boolean
  lokationsPraecision: LocationPrecision
  /** Navn på sidste fil man delte/valgte, hvis nogen. */
  sidsteFil?: string
  /** Har udklipsholderen tekst lige nu? (Indholdet vises ALDRIG her.) */
  udklipHarTekst: boolean
  enhedsNavn?: string
}

export interface KontekstPunkt {
  slags: KontekstSlags
  titel: string
  /** Kort forklaring — eller grunden til at den ikke kan bruges. */
  detalje: string
  tilgaengelig: boolean
}

export function byggeKontekster(i: KontekstInput): KontekstPunkt[] {
  const lokTil = i.lokationsPraecision !== 'off'
  return [
    {
      slags: 'kamera',
      titel: 'Tag et billede',
      detalje: i.kameraTilladt ? 'Kameraet er klar' : 'Kameraet er slået fra i indstillinger',
      tilgaengelig: i.kameraTilladt,
    },
    {
      slags: 'lokation',
      titel: 'Del hvor du er',
      detalje: lokTil ? `Præcision: ${i.lokationsPraecision}` : 'Lokation er slået fra',
      tilgaengelig: lokTil,
    },
    {
      slags: 'fil',
      titel: 'Vedhæft en fil',
      // Sidste fil er en genvej, ikke en betingelse — man kan altid vælge en ny.
      detalje: i.sidsteFil ? `Senest: ${i.sidsteFil}` : 'Vælg fra enheden',
      tilgaengelig: true,
    },
    {
      slags: 'udklip',
      titel: 'Indsæt fra udklipsholder',
      detalje: i.udklipHarTekst ? 'Der ligger tekst klar' : 'Udklipsholderen er tom',
      tilgaengelig: i.udklipHarTekst,
    },
    {
      slags: 'enhed',
      titel: 'Denne enhed',
      detalje: i.enhedsNavn || 'Ukendt enhed',
      tilgaengelig: Boolean(i.enhedsNavn),
    },
  ]
}

/** De brugbare først — man leder efter dét man kan gøre NU, ikke efter en
 *  liste over hvad man har slået fra. Rækkefølgen inden for hver gruppe
 *  bevares, så knapperne ikke hopper rundt mellem to visninger. */
export function sorteretTilVisning(punkter: KontekstPunkt[]): KontekstPunkt[] {
  return [...punkter.filter((p) => p.tilgaengelig), ...punkter.filter((p) => !p.tilgaengelig)]
}
