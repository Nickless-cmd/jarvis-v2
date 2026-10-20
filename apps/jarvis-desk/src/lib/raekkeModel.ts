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

/** En LEVERANCE — noget Jarvis lægger frem TIL brugeren: et billede han har
 *  lavet, eller en fil han har udgivet. Den er ikke arbejde. Den skal SES, og
 *  den må derfor aldrig foldes væk bag turens hoved.
 *
 *  Målt 27/9-2026 i Bjørns tråd: et genereret billede lå MIDT i beskeden —
 *  efter sit eget værktøj, men FØR de senere kald (`analyze_image`,
 *  `remember_this`). Skillelinjen er det sidste `tool_use`, så billedet faldt
 *  i arbejdet og forsvandt bag den sammenfoldede runde. Det samme billede stod
 *  frit i mobilen, fordi mobilen bærer filen på beskeden frem for i en række.
 *  Reglen her er den samme: leverancen hører til svaret. */
function erLeverance(b: ContentBlock): boolean {
  return b.type === 'image' || b.type === 'file' || b.type === 'video'
}

/**
 * Del en assistent-besked op. Rækkefølgen bevares nøjagtigt — en syntese
 * skal stå mellem de to kald den faktisk stod imellem.
 */
export function opdel(blokke: readonly ContentBlock[], underArbejde = false): RaekkeOpdeling {
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
      // En tekst efter et værktøj er først et slutsvar, når serveren sender
      // final_answer_start. Indtil da kan næste runde stadig følge efter.
      if (b.type === 'text' && underArbejde && sidsteKald >= 0) {
        const tekst = b.text.trim()
        if (tekst) arbejde.push({ slags: 'mellemsvar', tekst })
        continue
      }
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
    // Leverancen løftes UD af arbejdet — se `erLeverance`. Uden dette stod et
    // billede lavet midt i turen begravet i den foldede runde (målt 27/9-2026).
    if (erLeverance(b)) { svar.push(b); continue }
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

/* ══════════════════════════════════════════════════════════════════════════
   FASE-PROJEKTIONEN — én liste, hvor blokken bliver på sin plads
   ══════════════════════════════════════════════════════════════════════════

   ## Hvorfor den findes (19/10-2026)

   `opdel` ovenfor returnerer TO arrays: `arbejde` og `svar`. Det er en grænse
   der FLYTTES — og den flyttes ikke bare én gang. Grænsen er indekset for det
   SIDSTE `tool_use`, så:

   - en syntese der lander efter kald 1 ligger i `svar` (den er efter sidste kald)
   - når kald 2 så ankommer, rykker grænsen frem, og SAMME blok hører nu til
     arbejdet — den flytter tilbage

   Målt 19/10-2026: `sammeNode=false`, `mounts foer=0 efter=2`. Teksten er
   identisk i DOM'en før og efter, så ingen tekst-assertion kan se det; kun et
   mount-tal eller `isSameNode` ser det. Det er derfor det har kunnet leve.

   ChatGPT's chat-view har ikke problemet, fordi fasen (`commentary` /
   `final_answer`) er en EGENSKAB på itemet og nøglen er den samme uanset fase:
   React genbruger noden, og teksten bliver bare ved med at strømme ind i den
   samme DOM-node mens søskenden ovenover folder sig sammen.

   ## Reglen her

   Blokken bliver på sin PLADS i rækkefølgen. Kun dens `fase` skifter. Så kan
   rendereren lægge dem som direkte børn af ÉN container, hvor arbejdsdelene
   skjules med `hidden` i stedet for at flyttes — og forælderen er konstant
   hele turen.

   `opdel` bliver stående: den er kontrakten for de 30 tests der beskriver
   HVILKE blokke der er arbejde og hvilke der er svar. Fasen udledes af samme
   regel, så de to kan ikke fortælle to historier.
*/

/** Hvilken side af folden et element hører til. */
export type Fase = 'arbejde' | 'svar'

/** Ét element i den flade, fase-markerede liste.
 *
 * ## Hvorfor der ikke er en `mellemsvar`-slags (målt 19/10-2026)
 *
 * Første udgave kopierede arbejdsteksten ud i `{ slags: 'mellemsvar', tekst }`
 * — ligesom `opdel` gør. Det gjorde fase-skiftet til et TYPE-skift: samme
 * tekst gik fra `mellemsvar` til `blok`, altså en anden komponent for
 * React, og noden blev smidt væk uanset hvor stabil containeren var.
 *
 * Nu er teksten ALTID sin egen `ContentBlock`. Kun `fase` skifter, så
 * rendereren kan bruge ÉN komponent og ÉN nøgle hele turen — og React
 * genbruger noden, præcis som ChatGPT's `phase`-egenskab gør.
 */
export type FaseElement =
  | { fase: Fase; slags: 'blok'; blok: ContentBlock }
  | { fase: Fase; slags: 'spor'; trin: ProgressBlok[] }

export interface FaseProjektion {
  /** Alle elementer i blokkens oprindelige rækkefølge — arbejde og svar blandet. */
  elementer: FaseElement[]
  /** Til turens hoved: «Thought for {sekunder}s · {kald} tool calls». */
  kald: number
  sekunder: number
  /** Er der overhovedet noget at folde? (samme som `arbejde.length > 0`) */
  harArbejde: boolean
}

/**
 * Projektér blok-listen til ÉN fase-markeret liste.
 *
 * Rækkefølgen er blokkens egen — intet flyttes. Fasen følger præcis samme
 * regel som `opdel`: tekst efter det sidste `tool_use` er svar, når
 * `underArbejde` er falsk; ellers er den et mellemsvar i arbejdet.
 */
export function projektion(blokke: readonly ContentBlock[], underArbejde = false): FaseProjektion {
  let sidsteKald = -1
  for (let i = 0; i < blokke.length; i++) {
    const b = blokke[i]
    if (b && b.type === 'tool_use') sidsteKald = i
  }

  const elementer: FaseElement[] = []
  let kald = 0
  let sekunder = 0
  let harArbejde = false

  // Ét spor ad gangen: sammenhængende progress-blokke samles, præcis som i
  // `opdel`. Sporet arver fasen fra sin FØRSTE blok — det er den fase hele
  // rækken vises i, og en række kan ikke stå på to sider af folden.
  const skubSpor = (b: ProgressBlok, fase: Fase) => {
    const sidste = elementer[elementer.length - 1]
    if (sidste && sidste.slags === 'spor' && sidste.fase === fase) sidste.trin.push(b)
    else elementer.push({ fase, slags: 'spor', trin: [b] })
    if (fase === 'arbejde') harArbejde = true
  }

  for (let i = 0; i < blokke.length; i++) {
    const b = blokke[i]
    if (!b) continue

    const efterSidsteKald = i > sidsteKald

    if (b.type === 'text') {
      // Tomme tekstblokke opstår under streaming, før den første delta. De må
      // ikke blive til et tomt element med 16px luft om.
      if (!b.text.trim()) continue
      // Tekst efter det sidste kald er først et slutsvar, når serveren sender
      // final_answer_start. Indtil da kan næste runde stadig følge efter.
      //
      // Blokken selv følger med — IKKE en kopi af teksten. Det er hele
      // pointen: når fasen skifter fra 'arbejde' til 'svar', er `blok` det
      // samme objekt, så rendereren kan genbruge DOM-noden i stedet for at
      // bygge en ny. Se `FaseElement` ovenfor.
      //
      // Betingelsen spejler `opdel`s tre grene. Den sidste halvdel er målt
      // 19/10-2026: `opdel` gør kun en tekst til mellemsvar når der FINDES et
      // kald (`sidsteKald >= 0`). En besked uden værktøjskald er derfor rent
      // svar — også mens turen kører. Uden den halvdel blev en kald-fri tur
      // lagt i arbejdet, hvor den hørte til svaret.
      const fase: Fase = efterSidsteKald && (!underArbejde || sidsteKald < 0) ? 'svar' : 'arbejde'
      elementer.push({ fase, slags: 'blok', blok: b })
      if (fase === 'arbejde') harArbejde = true
      continue
    }

    if (b.type === 'progress') {
      // `opdel` lægger ALTID progress i arbejdet — dens progress-gren har
      // ingen fase-betingelse, hverken før eller efter sidste kald. Målt
      // 19/10-2026: `[tool_use, progress×3, text]` gav `blok,spor` mod `blok`.
      // Reglen bevares her, så de to projektioner ikke fordeler forskelligt.
      skubSpor(b, 'arbejde')
      continue
    }

    // Leverancen løftes UD af arbejdet — se `erLeverance`. Uden dette stod et
    // billede lavet midt i turen begravet i den foldede runde (målt 27/9-2026).
    if (erLeverance(b)) {
      elementer.push({ fase: 'svar', slags: 'blok', blok: b })
      continue
    }

    if (b.type === 'tool_use') kald += 1

    // Arbejdsblokke er arbejde uanset hvor de står — en tanke må aldrig tegnes
    // som replik. Alt andet efter sidste kald (fx `tool_use_summary`) falder i
    // svaret, så intet forsvinder tavst.
    const erArbejde = erArbejdsBlok(b) || !efterSidsteKald
    // Sekunderne tælles KUN for tanker FØR sidste kald — samme regel som
    // `opdel`, hvis `continue` i grenen efter sidste kald springer
    // sekunder-linjen over. Målt: `[tool_use, thinking]` gav 3 mod 0. Det er
    // en inkonsistens i `opdel` (en tanke efter sidste kald vises i arbejdet
    // men tælles ikke), og den bevares her, så de to projektioner ikke kan
    // vise to forskellige tal for den samme tur.
    if (!efterSidsteKald && b.type === 'thinking' && typeof b.seconds === 'number') {
      sekunder += b.seconds
    }
    elementer.push({ fase: erArbejde ? 'arbejde' : 'svar', slags: 'blok', blok: b })
    if (erArbejde) harArbejde = true
  }

  return { elementer, kald, sekunder: Math.round(sekunder), harArbejde }
}
