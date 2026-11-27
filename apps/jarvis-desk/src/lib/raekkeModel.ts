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
  /**
   * Svaret i RÆKKEFØLGE, delt så runder efter foldet kan tegnes som runder.
   *
   * `svar` alene er flad: den kan ikke fortælle om en blok var en ny runde
   * værktøjskald eller et stykke tekst. Uden den forskel faldt runderne efter
   * foldet i bobble-sproget (se `SvarSektion`). Læses af `RaekkeTranskript`;
   * `svar` bliver stående uændret til gate-beregningen (`svarBegyndt`).
   */
  svarSektioner: SvarSektion[]
  /** Til turens hoved: «Thought for {sekunder}s · {kald} tool calls». */
  kald: number
  sekunder: number
}

export type ArbejdsSektion =
  | { slags: 'syntese'; tekst: string }
  | { slags: 'enkelt'; element: ArbejdsElement }
  | { slags: 'runde'; elementer: ArbejdsElement[] }

/**
 * En sektion af SVARET — efter foldet.
 *
 * Efter den første `final_answer`-blok kan der komme nye værktøjskald (fx en
 * hukommelses-skrivning, et `suggest_next_task`). De er arbejde, men de hører
 * til EFTER svaret: de skal stå synligt og kan ikke gemmes i den fold der
 * allerede er lukket.
 *
 * Bjørn 27/11-2026: «runderne uden for hoved bruger ikk samme visning som dem
 * inden i hoved... de rigtige er dem inde i foldet». Målt på hans to
 * skærmbilleder: uden for foldet faldt de i `svar`, som tegnes af
 * `BlocksRenderer` — bobble-sproget med `ToolGroupCard`s faste `</>`-ikon, ur,
 * og tænkningen som sin EGEN linje. Inde i folden tegnes de af `Arbejdsrunde`:
 * ét ikon kun på den aktive runde, tænkningen samlet ind bag chevronen, én
 * linje pr. runde. To sprog for den samme ting, valgt af ét boolean-flag.
 *
 * Sektionen her bærer rækkefølgen: teksten og runderne stod blandet i `svar`,
 * og en flad opdeling ville flytte dem. `blokke` er alt der ikke er arbejde
 * (tekst, leverancer), `runde` er en sammenhængende runde værktøjskald.
 */
export type SvarSektion =
  | { slags: 'blokke'; blokke: ContentBlock[] }
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
    // `approval` hører til ARBEJDET (2/11-2026). Uden den faldt en godkendelse
    // der stod efter sidste værktøjskald i `svar` — og blev tegnet som en del
    // af replikken, nederst i beskeden under slutteksten. Målt på Bjørns
    // skærmbillede af code mode: «Hvorfor vises de i bunden af din besked?»
    // `chatFlowModel` havde reglen; denne model havde den ikke, så fixet i
    // `fletGodkendelser` blev kun synligt i chat mode.
    || b.type === 'approval'
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
export function opdel(blokke: readonly ContentBlock[], underArbejde = false, _svarLaast = false): RaekkeOpdeling {
  // Skillelinjen: indekset EFTER det sidste vaerktoejskald. Findes der ingen
  // kald, er hele beskeden svar, og arbejdsomraadet forbliver tomt.
  let sidsteKald = -1
  for (let i = 0; i < blokke.length; i++) {
    const b = blokke[i]
    if (b && b.type === 'tool_use') sidsteKald = i
  }

  // Er svaret BEGYNDT, kan et senere vaerktoejskald ikke goere det til arbejde.
  //
  // MÅLT 21/11-2026 (Bjørn: «du kalder en extra runde efter din slut besked og
  // det forvirre hovede.. og giver de tomme skærme efter foldet og dump»): en
  // tur der skriver sit svar og DEREFTER kalder et vaerktoej — fx en
  // hukommelses-skrivning — flyttede skillelinjen frem til det kald. Saa faldt
  // slutteksten ned i arbejdet, som ligger inde i folden: tom skaerm, og
  // teksten dumpet bagefter.
  //
  // Reglen: naar der ingen tekst er efter det sidste kald, hoerer den tekst der
  // staar FOER det til svaret — kaldet er en efterhaands-handling, ikke en ny
  // runde. Vi gaar tilbage kald for kald indtil graensen har tekst efter sig.
  //
  // ── LÅST (26/11-2026) ────────────────────────────────────────────────────
  //
  // MÅLT 26/11-2026 (Bjørn: «blinket sker fordi hoved først folder ved din
  // sidste syntese og så merger vi syntese og slut besked»): gennemløbet
  // ovenfor kørte FORFRA ved hver render. Det gjorde graensen til en funktion
  // af listens NUVÆRENDE længde, ikke af hvad brugeren allerede havde set:
  // landede der en syntese efter svaret, fandt det nye gennemløb tekst efter
  // det NYE sidste kald — og graensen rykkede FREM. Slutbeskeden blev dermed
  // arbejde, mens den stod på skærmen, og den sene syntese blev det eneste
  // svar. Det er den «teleportering» der har været repareret på visningen
  // mange gange uden at forsvinde: fejlen sad i klassificeringen.
  //
  // Graensen er derfor MONOTON: den maa gaa baglaens, aldrig frem. Vi finder
  // den baglaens-graense der giver det STØRSTE svar — altså den tidligste
  // grænse hvor der stadig er tekst efter sig — og bruger den. Så kan en
  // senere blok ikke skubbe noget ind i folden, uanset hvor mange runder der
  // kommer bagefter.
  // Den FØRSTE blok serveren selv har stemplet `final_answer` — hvor svaret
  // begyndte. -1 = serveren har ikke sagt det, og klienten gætter ikke.
  // The persisted code boundary survives legacy phase normalisation. Read
  // block metadata even when the historical row has no transient live lock.
  let foersteSvar = blokke.findIndex((b) => b?.type === 'text' && b.code_answer_start)
  const explicitProtocol = blokke.some((b) => b?.type === 'text' && b.code_answer_protocol === 1)
  if (foersteSvar < 0 && !explicitProtocol) {
    foersteSvar = blokke.findIndex((b) => b?.type === 'text' && b.phase === 'final_answer')
  }
  if (foersteSvar >= 0 && sidsteKald < 0) {
    // A plain multi-block reply has no work boundary to hide earlier prose.
    foersteSvar = blokke.findIndex((b) => b?.type === 'text')
  }
  if (foersteSvar >= 0) {
    sidsteKald = -1
    for (let i = 0; i < foersteSvar; i++) {
      if (blokke[i]?.type === 'tool_use') sidsteKald = i
    }
  }

  const arbejde: ArbejdsElement[] = []
  const svar: ContentBlock[] = []
  let kald = 0
  let sekunder = 0

  // ── Runden EFTER foldet hører til efter foldet (Bjørn 26/11-2026) ────────
  //
  // MÅLT 26/11-2026 i en headless browser: efter foldet var gruppe-højden 0
  // både FØR og EFTER det sene kald — 3902 af 3,6 mio. pixels ændrede sig,
  // udelukkende i hovedets label. Kaldet lå i `arbejde`, som er den gruppe
  // der foldes, så runden var usynlig indtil man åbnede hovedet.
  //
  // Bjørn: «runderne skal blive stående synlige efter foldet — og først fade
  // ud når serveren melder done. Ikke gemmes væk, ikke flyttes.»
  //
  // `arbejdeEfterSvar` i reduceren råber allerede «her er arbejde efter
  // svaret», men den styrer kun om folden skal ÅBNE. Klassificeringen her
  // svarede «det er arbejde» — og så lukkede folden det inde igen.
  //
  // Reglen: alt efter den første `final_answer`-blok er EFTER folden. Et
  // værktøjskald der er arbejde, men står efter svaret, er en ny runde
  // brugeren skal kunne se — ikke arbejde der skal skjules. Kun når svaret
  // ikke er begyndt, hører kaldet til i folden.
  const efterFold = foersteSvar >= 0

  // ── Grænsen er serverens `final_answer`, ikke `underArbejde` ─────────────
  //
  // MÅLT 27/11-2026 på Bjørns sekvens `runde → syntese → fold → slutbesked →
  // runde → syntese`: mellemsyntesen der lå FØR foldet blev teleporteret UD af
  // folden i det øjeblik foldet skete. Den lå i arbejdet mens turen kørte, og
  // stod så pludselig i svaret — fordi `underArbejde` falder til falsk når
  // `finalAnswerStarted` bliver sand, så det samme gennemløb klassificerede
  // blokken efter en anden regel end den den var VIST under.
  //
  // Det er samme fejlklasse som «teleporteringen» beskrevet ovenfor, men den
  // ramte en anden blok: ikke slutbeskeden, men syntesen før den. Kuren er den
  // samme — grænsen må ikke være en funktion af et flag der skifter midt i
  // turen. Er svaret stemplet, hører alt FØR den første `final_answer` til
  // arbejdet, uanset om foldet allerede er sket.
  //
  // Uden et `final_answer`-stempel er grænsen som før: det sidste kald.
  const graense = foersteSvar >= 0 ? foersteSvar - 1 : sidsteKald

  for (let i = 0; i < blokke.length; i++) {
    const b = blokke[i]
    if (!b) continue

    if (i > graense) {
      // En tekst efter et værktøj er først et slutsvar, når serveren sender
      // final_answer_start. Indtil da kan næste runde stadig følge efter.
      if (b.type === 'text' && underArbejde && foersteSvar < 0 && sidsteKald >= 0) {
        const tekst = b.text.trim()
        if (tekst) arbejde.push({ slags: 'mellemsvar', tekst })
        continue
      }
      // Efter det sidste kald: TEKST er svar. Arbejdsblokke er stadig
      // arbejde — se skillelinjen i hovedkommentaren. Alt andet (fx
      // `tool_use_summary`) falder i svaret, saa intet forsvinder tavst.
      //
      // Undtagelsen er runden EFTER foldet: står blokken efter den første
      // `final_answer`, er den en ny runde brugeren skal se, ikke arbejde
      // der skal skjules. Se `efterFold` ovenfor.
      if (b.type === 'progress' && !efterFold) {
        const sidste = arbejde[arbejde.length - 1]
        if (sidste && sidste.slags === 'spor') sidste.trin.push(b)
        else arbejde.push({ slags: 'spor', trin: [b] })
      } else if (erArbejdsBlok(b) && !efterFold) arbejde.push({ slags: 'blok', blok: b })
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

  return {
    arbejde,
    svar,
    svarSektioner: sektionerFraSvar(svar),
    kald,
    sekunder: Math.round(sekunder),
  }
}

/**
 * Del svaret i blokke og runder, så rækkefølgen bevares.
 *
 * Kun `erArbejdsBlok` afgør hvad der er en runde — den SAMME regel som `opdel`
 * bruger til at afgøre hvad der er arbejde. Det er med vilje: en blok der er
 * arbejde inde i folden skal også være en rundelinje uden for den. Ellers
 * tegnes de to steder af hvert sit sprog, og det er netop den divergens Bjørn
 * målte 27/11-2026 (ikon, ur og en løs tænke-linje uden for folden mod én
 * samlet linje inde i den).
 */
function sektionerFraSvar(svar: readonly ContentBlock[]): SvarSektion[] {
  const sektioner: SvarSektion[] = []
  let blokke: ContentBlock[] = []
  let elementer: ArbejdsElement[] = []

  const afslutBlokke = () => {
    if (blokke.length === 0) return
    sektioner.push({ slags: 'blokke', blokke })
    blokke = []
  }
  const afslutRunde = () => {
    if (elementer.length === 0) return
    sektioner.push({ slags: 'runde', elementer })
    elementer = []
  }

  for (const b of svar) {
    if (!erArbejdsBlok(b)) {
      afslutRunde()
      blokke.push(b)
      continue
    }
    afslutBlokke()
    if (b.type === 'progress') {
      // Fortsætter sporet frem for at starte en ny række — samme greb som i
      // `opdel`, så en runde med ni progress-blokke bliver én linje.
      const sidste = elementer[elementer.length - 1]
      if (sidste && sidste.slags === 'spor') sidste.trin.push(b)
      else elementer.push({ slags: 'spor', trin: [b] })
      continue
    }
    elementer.push({ slags: 'blok', blok: b })
  }
  afslutRunde()
  afslutBlokke()
  return sektioner
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

/* 15/11-2026: her lå `FRASER`, `MAKS_LED` og `led()` — oversættelsen af
   værktøjsfamilier til prosa («læste 6 filer og kørte 3 kommandoer»). Da
   hovedet skiftede til «Arbejdet · 42s», mistede alle tre deres læsere.
   De er fjernet frem for at blive stående: en tabel ingen kalder er
   dokumentation der lyver om hvad koden gør. */

/**
 * Turens hoved, fortalt. Bjørn 23/9-2026: «hvordan forslår du punkt 5 skal
 * se ud?»
 *
 * `turHoved` tæller — «Thought for 90s · 9 tool calls». Det er sandt og
 * intetsigende: ni kald kan være ni filer læst eller ni kommandoer kørt, og
 * de to betyder vidt forskellige ting at læse. Her får arbejdet et sprog.
 *
 * ## Opremsningen er væk (15/11-2026)
 *
 * Før stod der «Kørte 9 kommandoer og læste en fil · 42s». Bjørn: «denne
 * generiske dele af hoved når det er foldet skal væk, skiftet til Arbejdet
 * eller Worked efterfulgt af turens tid». Opremsningen var en gættet
 * oversættelse af værktøjsnavne til prosa, og den læste som en maskinrapport
 * oven over et svar man allerede havde læst. Hovedet er turens RESULTAT, ikke
 * en kvittering for hvad der blev kørt — tiden er det ene tal Bjørn selv bad
 * om (22/9-2026), og den bliver.
 *
 * `familier` og `kald` er stadig parametre: de bærer turen, og en fremtidig
 * form kan få brug for dem. At fjerne dem ville tvinge hvert kaldssted til at
 * ændre signatur for en ændring der kun er i teksten.
 */
export function turFortalt(
  _familier: readonly string[], _kald: number, sekunder: number,
): string {
  return sekunder > 0 ? `Arbejdet · ${sekunder}s` : 'Arbejdet'
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
      // ── SERVERENS SEMANTIK FØRST (Bjørn 26/11-2026) ────────────────────
      //
      // `block.phase` sættes af serveren (`sse_v2_events.py`: 'commentary' |
      // 'final_answer') og er derfor AUTORITATIV: den siger hvad blokken ER,
      // ikke hvor den står. Den læses først, og en blok der har fået sin fase
      // fra serveren kan ALDRIG omklassificeres af en senere blok.
      //
      // Det var fejlen: fasen blev udelukkende udledt af positionen efter
      // sidste `tool_use`. Når en ny runde ankom, flyttede `sidsteKald` sig,
      // og et allerede vist slutsvar tippede tilbage i arbejdet — midt i
      // turen, mens pacen rullede. Det er den «dynamiske semantiske
      // omklassificering» kravet forbyder: samme blok, ny fase, ny visning.
      //
      // Positionsreglen bevares som FALLBACK for blokke uden `phase` — ældre
      // persisterede ture og providers der ikke sender feltet. Den er ikke
      // længere den primære kilde.
      //
      // Fallback'en spejler `opdel`s tre grene. Den sidste halvdel er målt
      // 19/10-2026: `opdel` gør kun en tekst til mellemsvar når der FINDES et
      // kald (`sidsteKald >= 0`). En besked uden værktøjskald er derfor rent
      // svar — også mens turen kører. Uden den halvdel blev en kald-fri tur
      // lagt i arbejdet, hvor den hørte til svaret.
      const fase: Fase = b.phase === 'final_answer'
        ? 'svar'
        : b.phase === 'commentary'
          ? 'arbejde'
          : (efterSidsteKald && (!underArbejde || sidsteKald < 0) ? 'svar' : 'arbejde')
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
