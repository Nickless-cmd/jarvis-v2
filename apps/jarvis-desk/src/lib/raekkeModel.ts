/**
 * Rækkevisningen: fra flad blok-liste til «arbejde + svar».
 *
 * ## Hvorfor den er et eget modul
 *
 * Delingen er hele forskellen mellem det der virker og det der ikke gør, og
 * den har intet med React at gøre. Den ligger her, så den kan måles uden at
 * rendere noget — se `raekkeModel.test.ts`.
 *
 * ## Reglen (Bjørn 22/9-2026)
 *
 * «hans små korte synteser mellem tool kald … det du lige har lavet er flere
 * beskeder med endelig svar.»
 *
 * En assistent-besked er én flad liste. Rækkevisningen skal dele den i to:
 *
 * - **arbejdet** — værktøjskald, tanker, og de korte tekststykker Jarvis
 *   skriver MELLEM kaldene. Det folder sig sammen bag én linje.
 * - **svaret** — de tekst-blokke der ligger efter det SIDSTE værktøjskald.
 *   Det står frit og forsvinder aldrig.
 *
 * Skillelinjen gælder KUN tekst. En tanke er arbejde uanset hvor den står:
 * lagde vi en afsluttende tanke i svaret, ville rå tankestrøm blive tegnet
 * som replik.
 *
 * Skillelinjen er altså det sidste `tool_use`. Alt tekst før det er
 * narration undervejs; alt tekst efter er svaret. Ingen anden markør er
 * nødvendig, og vi opfinder ikke en: serveren sender ikke nogen.
 *
 * ## Kanten der er nem at ramme forkert
 *
 * En besked UDEN værktøjskald er rent svar. Havde vi sagt «sidste tekstblok
 * er svaret», ville en besked med to afsnit have lagt det første afsnit ind
 * i et tomt arbejdsområde — og så stod der «Thought for 0s · 0 tool calls»
 * over en almindelig replik. Derfor er reglen bundet til `tool_use`, ikke
 * til tekstens plads.
 */
import type { ContentBlock } from './sseProtocol'

/** Et element i arbejdsområdet: enten en række eller et kort mellemsvar. */
export type ArbejdsElement =
  | { slags: 'blok'; blok: ContentBlock }
  | { slags: 'mellemsvar'; tekst: string }

export interface RaekkeOpdeling {
  /** Alt der folder sig sammen bag turens hoved, i rækkefølge. */
  arbejde: ArbejdsElement[]
  /** Det der bliver stående: svaret. Tom liste = intet svar endnu. */
  svar: ContentBlock[]
  /** Til turens hoved: «Thought for {sekunder}s · {kald} tool calls». */
  kald: number
  sekunder: number
}

/** Blokke der tegnes som en række i arbejdsområdet. */
function erArbejdsBlok(b: ContentBlock): boolean {
  return b.type === 'tool_use' || b.type === 'thinking' || b.type === 'skill_surface'
}

/**
 * Del en assistent-besked op. Rækkefølgen bevares nøjagtigt — en syntese
 * skal stå mellem de to kald den faktisk stod imellem.
 */
export function opdel(blokke: readonly ContentBlock[]): RaekkeOpdeling {
  // Skillelinjen: indekset EFTER det sidste vaerktoejskald. Findes der ingen
  // kald, er hele beskeden svar, og arbejdsomraadet forbliver tomt.
  let sidsteKald = -1
  for (let i = 0; i < blokke.length; i++) {
    const b = blokke[i]
    if (b && b.type === 'tool_use') sidsteKald = i
  }

  const arbejde: ArbejdsElement[] = []
  const svar: ContentBlock[] = []
  let kald = 0
  let sekunder = 0

  for (let i = 0; i < blokke.length; i++) {
    const b = blokke[i]
    if (!b) continue

    if (i > sidsteKald) {
      // Efter det sidste kald: TEKST er svar. Arbejdsblokke er stadig
      // arbejde — se skillelinjen i hovedkommentaren. Alt andet (fx
      // `tool_use_summary`) falder i svaret, saa intet forsvinder tavst.
      if (erArbejdsBlok(b)) arbejde.push({ slags: 'blok', blok: b })
      else svar.push(b)
      continue
    }

    if (b.type === 'text') {
      // Tomme tekstblokke opstaar under streaming, foer den foerste delta.
      // De maa ikke blive til et tomt mellemsvar med 16px luft om.
      const tekst = b.text.trim()
      if (tekst) arbejde.push({ slags: 'mellemsvar', tekst })
      continue
    }

    if (b.type === 'tool_use') kald += 1
    if (b.type === 'thinking' && typeof b.seconds === 'number') sekunder += b.seconds
    arbejde.push({ slags: 'blok', blok: b })
  }

  return { arbejde, svar, kald, sekunder: Math.round(sekunder) }
}

/**
 * Turens hoved. Formen er Bjørns («thought for x sec», 22/9-2026) — ikke
 * forlæggets «Thought for a while», som skjuler det eneste tal man vil have.
 */
export function turHoved(kald: number, sekunder: number): string {
  const tid = sekunder > 0 ? `Thought for ${sekunder}s` : 'Worked'
  const k = `${kald} tool call${kald === 1 ? '' : 's'}`
  return `${tid} · ${k}`
}
