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
  /**
   * Et SPOR af progress-blokke, ikke én række pr. blok. Bjørn 23/9-2026:
   * «burde det ikk bare være en linje der opdater status? og så kan man
   * udvide den som de andre?» — ni «Kører kommando: python» under hinanden
   * er støj, ikke information. Bobblevisningen grupperer dem allerede
   * (`progress_trail`, BlocksRenderer.ts:61); det her er det samme greb.
   */
  | { slags: 'spor'; trin: ProgressBlok[] }

type ProgressBlok = Extract<ContentBlock, { type: 'progress' }>

export interface RaekkeOpdeling {
  /** Alt der folder sig sammen bag turens hoved, i rækkefølge. */
  arbejde: ArbejdsElement[]
  /** Det der bliver stående: svaret. Tom liste = intet svar endnu. */
  svar: ContentBlock[]
  /** Til turens hoved: «Thought for {sekunder}s · {kald} tool calls». */
  kald: number
  sekunder: number
}

export type ArbejdsSektion =
  | { slags: 'syntese'; tekst: string }
  | { slags: 'enkelt'; element: ArbejdsElement }
  | { slags: 'runde'; elementer: ArbejdsElement[] }

/** Behold hver syntese synlig, og saml de følgende detaljer i én foldbar række. */
export function opdelArbejdsrunder(arbejde: readonly ArbejdsElement[]): ArbejdsSektion[] {
  const sektioner: ArbejdsSektion[] = []
  let elementer: ArbejdsElement[] = []
  const afslut = () => {
    if (elementer.some((e) => e.slags === 'blok' && e.blok.type === 'tool_use')) {
      sektioner.push({ slags: 'runde', elementer })
    } else {
      for (const element of elementer) sektioner.push({ slags: 'enkelt', element })
    }
    elementer = []
  }
  for (const e of arbejde) {
    if (e.slags === 'mellemsvar') {
      afslut()
      sektioner.push({ slags: 'syntese', tekst: e.tekst })
    } else {
      elementer.push(e)
    }
  }
  afslut()
  return sektioner
}

/** Blokke der tegnes som en række i arbejdsområdet.
 *
 * `progress` er narrationen fra live-working_step, persisteret så forløbet
 * overlever en reload. Den er ARBEJDE uanset hvor den står — lå den i
 * svaret, ville «Analyserede billede…» blive tegnet som replik. */
function erArbejdsBlok(b: ContentBlock): boolean {
  return b.type === 'tool_use' || b.type === 'thinking'
    || b.type === 'skill_surface' || b.type === 'progress'
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
      if (b.type === 'progress') {
        const sidste = arbejde[arbejde.length - 1]
        if (sidste && sidste.slags === 'spor') sidste.trin.push(b)
        else arbejde.push({ slags: 'spor', trin: [b] })
      } else if (erArbejdsBlok(b)) arbejde.push({ slags: 'blok', blok: b })
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

    if (b.type === 'progress') {
      // Fortsaetter et spor frem for at starte en ny raekke.
      const sidste = arbejde[arbejde.length - 1]
      if (sidste && sidste.slags === 'spor') sidste.trin.push(b)
      else arbejde.push({ slags: 'spor', trin: [b] })
      continue
    }
    if (b.type === 'tool_use') kald += 1
    if (b.type === 'thinking' && typeof b.seconds === 'number') sekunder += b.seconds
    arbejde.push({ slags: 'blok', blok: b })
  }

  return { arbejde, svar, kald, sekunder: Math.round(sekunder) }
}

/**
 * Turens hoved, som en tælling. Formen er Bjørns («thought for x sec»,
 * 22/9-2026) — ikke forlæggets «Thought for a while», som skjuler det eneste
 * tal man vil have. Bruges nu kun når der ikke ER arbejde at fortælle om.
 */
export function turHoved(kald: number, sekunder: number): string {
  const tid = sekunder > 0 ? `Thought for ${sekunder}s` : 'Worked'
  // «0 tool calls» er ikke et tal man vil have — det er en tur der tænkte.
  if (kald === 0) return tid
  return `${tid} · ${kald} tool call${kald === 1 ? '' : 's'}`
}

/**
 * Familien i klart sprog. Nøglerne er de samme `familie`-navne som kroppene
 * bruger (`raekkeKroppe.tsx`) — så hovedet og rækkerne altid fortæller samme
 * historie, og en ny familie kun skal læres ét sted.
 */
// Fallbacken står uden for tabellen: et `Record`-opslag giver `| undefined`
// under `noUncheckedIndexedAccess`, og så kan `FRASER.fald` ikke kaldes.
const FALD = (n: number): string => (n === 1 ? 'arbejdede' : `arbejdede i ${n} trin`)

const FRASER: Record<string, (n: number) => string> = {
  fil: (n) => (n === 1 ? 'læste en fil' : `læste ${n} filer`),
  liste: (n) => (n === 1 ? 'søgte en gang' : `søgte ${n} gange`),
  terminal: (n) => (n === 1 ? 'kørte en kommando' : `kørte ${n} kommandoer`),
  skriv: (n) => (n === 1 ? 'skrev en fil' : `skrev ${n} filer`),
  diff: (n) => (n === 1 ? 'redigerede en fil' : `redigerede ${n} filer`),
  web: (n) => (n === 1 ? 'slog noget op' : `slog ${n} ting op`),
  billede: (n) => (n === 1 ? 'så på et billede' : `så på ${n} billeder`),
  spoergsmaal: () => 'spurgte dig',
  opgave: () => 'lagde en plan',
  fald: FALD,
}

/** Flere end tre led, og sætningen bliver en liste man ikke læser. */
const MAKS_LED = 3

function led(dele: string[]): string {
  // `join` frem for `dele[0]`: et indeks-opslag er `| undefined` under
  // noUncheckedIndexedAccess, og tomt/enkelt led skal bare igennem.
  if (dele.length <= 1) return dele.join('')
  return `${dele.slice(0, -1).join(', ')} og ${dele[dele.length - 1]}`
}

/**
 * Turens hoved, fortalt. Bjørn 23/9-2026: «hvordan forslår du punkt 5 skal
 * se ud?»
 *
 * `turHoved` tæller — «Thought for 90s · 9 tool calls». Det er sandt og
 * intetsigende: ni kald kan være ni filer læst eller ni kommandoer kørt, og
 * de to betyder vidt forskellige ting at læse. Her får arbejdet et sprog.
 *
 * Meningen kommer først, sekundet sidst — sekunderne bliver stående, fordi
 * de er det ene tal Bjørn selv bad om at få vist (22/9-2026).
 */
export function turFortalt(
  familier: readonly string[], kald: number, sekunder: number,
): string {
  const antal = new Map<string, number>()
  for (const f of familier) antal.set(f, (antal.get(f) ?? 0) + 1)

  // Største gruppe først — den er det man husker turen for. Map bevarer
  // indsættelsesrækkefølgen, og sort er stabil, så lige store grupper
  // beholder den rækkefølge de blev brugt i.
  const sorteret = [...antal.entries()].sort((a, b) => b[1] - a[1])
  const dele = sorteret.slice(0, MAKS_LED).map(([f, n]) => (FRASER[f] ?? FALD)(n))
  if (sorteret.length > MAKS_LED) dele.push('mere')

  // Uden værktøjer er der kun tanken tilbage, og den har kun et tal.
  if (dele.length === 0) return turHoved(kald, sekunder)

  const saetning = led(dele)
  const stort = saetning.charAt(0).toUpperCase() + saetning.slice(1)
  return sekunder > 0 ? `${stort} · ${sekunder}s` : stort
}
